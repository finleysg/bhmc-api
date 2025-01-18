import structlog

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from payments.emails import send_notification
from payments.models import Payment, Refund
from register.models import Player, Registration

logger = structlog.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def handle_payment_complete(self, payment_intent):
    
    stripe_id = payment_intent.get("id")
    metadata = payment_intent.get("metadata")
    user_email = metadata.get("user_email")
    registration_id = metadata.get("registration_id")

    logger.info("Stripe webhook processing", payment_id=stripe_id, user_email=user_email)

    payment = Payment.objects.get(payment_code=stripe_id)

    # exit early if we have already confirmed this payment
    if payment.confirmed:
        return {
            "message": "Stripe webhook already processed", 
            "payment_code": payment.payment_code, 
            "metadata": metadata
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
    slots = Registration.objects.payment_confirmed(registration_id)

    logger.info("Payment confirmed", payment_code=stripe_id, user=user_email)

    _update_membership(payment.event, slots)

    try:
        player = Player.objects.get(email=user_email)
        send_notification(payment, slots, player)
    except Exception as e:
        return {
            "message": f"Send notification failure: {str(e)}", 
            "payment_code": payment.payment_code, 
            "metadata": metadata
        }

    return {
        "message": "Stripe webhook processed", 
        "payment_code": payment.payment_code, 
        "metadata": metadata
    }


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def handle_refund_complete(charge):
    for refund in charge.refunds.data:
        try:
            local_refund = Refund.objects.get(refund_code=refund.stripe_id)
            local_refund.confirmed = True
            local_refund.save()
            logger.info("Refund confirmed by Stripe", refundCode=refund.stripe_id, local=True)
        except ObjectDoesNotExist:
            # We get this hook for refunds created in the Stripe UI
            # so we will have no record to tie together
            logger.info("Refund confirmed by Stripe", refundCode=refund.stripe_id, local=False)
            pass


def _update_membership(event, slots):
    # R is a season membership event
    if event.event_type == "R":
        for slot in slots:
            # Support multiple players for a registration
            if slot.status == "R":
                player = slot.player
                player.is_member = True
                player.save()
