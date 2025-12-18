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
    """Get or create system user for Stripe-initiated refunds."""
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
    finally:
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
    logger.info("Scheduled job: delete abandoned payments")
    count = Payment.objects.cleanup_abandoned()
    return {"message": "Abandoned payments cleanup complete", "count": count}


def _update_membership(registration):
    # R is a season membership event
    if registration.event.event_type == "R":
        for slot in registration.slots:
            # Support multiple players for a registration
            if slot.status == "R":
                player = slot.player
                player.is_member = True
                player.save()
