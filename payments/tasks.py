import structlog

from celery import shared_task
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from payments.emails import send_payment_notification, send_refund_notification
from payments.models import Payment, Refund
from register.models import Player, Registration

logger = structlog.getLogger(__name__)


def _get_stripe_system_user():
    """
    Ensure a non-active system user exists for Stripe-initiated refunds.
    
    If the user does not exist, creates one with username "stripe_system" and default email "stripe@system.local" and is_active set to False.
    
    Returns:
        User: The User instance representing the Stripe system user.
    """
    user, _ = User.objects.get_or_create(
        username="stripe_system",
        defaults={"email": "stripe@system.local", "is_active": False},
    )
    return user


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def handle_payment_complete(self, payment_intent):
    """
    Handle a completed Stripe PaymentIntent received via webhook and record local payment state.
    
    Processes the provided `payment_intent` payload to confirm the associated Payment, mark related payment details as paid, transition the related Registration to confirmed, update membership status, and attempt to send a payment notification.
    
    Parameters:
        payment_intent (dict): Stripe PaymentIntent payload; expected to include `id` and `metadata` containing `user_email` and `registration_id`.
    
    Returns:
        dict: Outcome summary with keys:
            - `message`: human-readable status of processing (or notification failure detail),
            - `payment_code`: the local Payment.payment_code after processing,
            - `metadata`: the original `payment_intent` metadata.
    """
    stripe_id = payment_intent.get("id")
    metadata = payment_intent.get("metadata")
    user_email = metadata.get("user_email")
    registration_id = metadata.get("registration_id")

    logger.info(
        "Stripe webhook processing", payment_id=stripe_id, user_email=user_email
    )

    payment = Payment.objects.get(payment_code=stripe_id)

    # exit early if we have already confirmed this payment
    if payment.confirmed:
        return {
            "message": "Stripe webhook already processed",
            "payment_code": payment.payment_code,
            "metadata": metadata,
        }

    payment.payment_code = stripe_id if payment.payment_amount > 0 else "no charge"
    payment.confirmed = True
    payment.confirm_date = timezone.now()
    payment.save()

    payment_details = list(payment.payment_details.all())
    for detail in payment_details:
        detail.is_paid = True
        detail.save()

    # Transitions the slot status from processing to reserved
    registration = Registration.objects.payment_confirmed(registration_id)

    logger.info("Payment confirmed", payment_code=stripe_id, user=user_email)

    _update_membership(registration)

    try:
        player = Player.objects.get(email=user_email)
        send_payment_notification(payment, registration, player)
    except Exception as e:
        return {
            "message": f"Send notification failure: {str(e)}",
            "payment_code": payment.payment_code,
            "metadata": metadata,
        }

    logger.info("Stripe webhook processing complete", user=user_email)

    return {
        "message": "Stripe webhook processed",
        "payment_code": payment.payment_code,
        "metadata": metadata,
    }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def handle_refund_created(self, refund):
    # NOTE: https://support.stripe.com/questions/understanding-fees-for-refunded-payments
    # Refunds are not subject to the Stripe fee, but the original charge fee is not refunded.
    """
    Create or locate a local Refund record for a Stripe refund and notify the application.
    
    Parameters:
        refund (dict): Stripe refund payload expected to include keys `id`, `payment_intent`, `reason`, and `amount` (amount is in cents).
    
    Returns:
        dict: A result payload with keys:
            - `message`: short status message,
            - `payment_code`: the Stripe payment intent id associated with the refund,
            - `metadata`: human-readable refund details including refund id and amount (in the application's currency units).
    
    Side effects:
        - Ensures a Payment exists for the refund's `payment_intent`; if not found, no local Refund is created.
        - Creates a local Refund record when one does not already exist.
        - Attempts to send a refund notification via `send_refund_notification`.
    """
    refund_id = refund.get("id")
    payment_intent_id = refund.get("payment_intent")
    reason = refund.get("reason")
    amount = refund.get("amount") / 100

    # Ensure we have a payment record
    try:
        payment = Payment.objects.get(payment_code=payment_intent_id)
    except ObjectDoesNotExist:
        logger.error(
            "Refund created but no payment found",
            refund_id=refund_id,
            payment_intent_id=payment_intent_id,
        )
        return {
            "message": "Refund created but no payment found",
            "payment_code": payment_intent_id,
            "metadata": f"Refund id: {refund_id}, amount: {amount}",
        }

    # Ensure we have a refund record (get_or_create handles race condition with serializer)
    local_refund, created = Refund.objects.get_or_create(
        refund_code=refund_id,
        defaults={
            "payment": payment,
            "refund_amount": amount,
            "issuer": _get_stripe_system_user(),
            "notes": reason,
            "confirmed": False,
        },
    )
    if created:
        logger.info(
            "Refund created at Stripe", refund_id=refund_id, payment_intent_id=payment_intent_id
        )
    else:
        logger.info(
            "Refund found - created by our system",
            id=local_refund.id,
            refund_id=refund_id,
            payment_intent_id=payment_intent_id,
        )

    try:
        send_refund_notification(payment, local_refund)
    except Exception as e:
        logger.error("Refund notification failed", error=str(e))

    return {
        "message": "Refund created",
        "payment_code": payment_intent_id,
        "metadata": f"Refund id: {refund_id}, amount: {amount}",
    }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def handle_refund_confirmed(self, refund):
    """
    Mark a local Refund record as confirmed when a Stripe refund is finalized.
    
    Parameters:
        refund (dict): Stripe refund payload containing at least the keys:
            - "id": Stripe refund identifier
            - "payment_intent": associated payment intent identifier
            - "amount": refund amount in the smallest currency unit (e.g., cents)
    
    Returns:
        dict: {
            "message": confirmation message,
            "payment_code": the original payment intent id,
            "metadata": brief string with refund id and amount in currency units (amount / 100)
        }
    
    Raises:
        ObjectDoesNotExist: if no local Refund with the given refund id exists (causes the task to retry).
    """
    refund_id = refund.get("id")
    payment_intent_id = refund.get("payment_intent")
    amount = refund.get("amount") / 100

    # Update the refund record
    try:
        refund = Refund.objects.get(refund_code=refund_id)
        refund.confirmed = True
        refund.save()
        logger.info("Refund confirmed", payment_intent_id=payment_intent_id, refund_id=refund_id)
        return {
            "message": "Refund confirmed",
            "payment_code": payment_intent_id,
            "metadata": f"Refund id: {refund_id}, amount: {amount}",
        }
    except ObjectDoesNotExist:
        logger.warning(
            "Refund not found, will retry",
            refund_id=refund_id,
            payment_intent_id=payment_intent_id,
        )
        raise  # Triggers autoretry


@shared_task(bind=True)
def delete_abandoned_payments(self):
    """
    Run cleanup for abandoned payments and report how many were removed.
    
    Returns:
        result (dict): {"message": "Abandoned payments cleanup complete", "count": <int>} where `count` is the number of removed abandoned payments.
    """
    logger.info("Scheduled job: delete abandoned payments")
    count = Payment.objects.cleanup_abandoned()
    return {"message": "Abandoned payments cleanup complete", "count": count}


def _update_membership(registration):
    # R is a season membership event
    """
    Mark players on a season registration as members.
    
    If the registration's event has type "R" (season membership), this sets `is_member = True`
    and saves each player associated with slots whose status is "R".
    
    Parameters:
        registration: Registration instance whose event and slots are used to determine which players become members.
    """
    if registration.event.event_type == "R":
        for slot in registration.slots:
            # Support multiple players for a registration
            if slot.status == "R":
                player = slot.player
                player.is_member = True
                player.save()