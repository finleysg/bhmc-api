import stripe
from django.db import models, transaction


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

