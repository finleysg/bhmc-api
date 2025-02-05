import stripe
import structlog

from django.db import models, transaction

logger = structlog.getLogger(__name__)


class PaymentManager(models.Manager):

    def cleanup_abandoned(self):
        # Player reviewed the payment details but abandoned the registration. We know they are
        # abandoned because they have no payment code, which became possible after the 2025 payment changes.
        # Run in the overnight to ensure we're not deleting payments that are still in progress.
        abandoned_payments = self.filter(payment_code="").filter(confirmed=False)
        count = len(abandoned_payments)
        for payment in abandoned_payments:
            try:
                logger.debug("Deleting abandoned payment", payment_id=payment.id, user=payment.user.email)
                payment.delete()
            except Exception as e:
                logger.error("Failed to delete abandoned payment", payment_id=payment.id, error=str(e))

        logger.info("Abandoned payments cleanup complete", count=count)

        return count


class RefundManager(models.Manager):

    @transaction.atomic()
    def create_refund(self, user, payment, refund_amount, notes):
        stripe_refund_amount = int(refund_amount * 100)  # total in cents

        stripe_refund = stripe.Refund.create(
            payment_intent=payment.payment_code,
            amount=stripe_refund_amount,
            reason="requested_by_customer",
        )

        refund = self.create(payment=payment,
                             issuer=user,
                             refund_code=stripe_refund.stripe_id,
                             refund_amount=refund_amount,
                             notes=notes)
        refund.save()

        return refund
