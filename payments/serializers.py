from decimal import Decimal

import stripe

from django.db import IntegrityError
from rest_framework import serializers

from payments.models import Payment, Refund
from payments.utils import get_amount_due, calculate_payment_amount, derive_notification_type
from register.models import RegistrationFee, Player
from register.serializers import RegistrationFeeSerializer

class PaymentReportSerializer(serializers.ModelSerializer):

    user_first_name = serializers.CharField(source="user.first_name")
    user_last_name = serializers.CharField(source="user.last_name")
    payment_details = RegistrationFeeSerializer(many=True)

    class Meta:
        model = Payment
        fields = ("id", "event", "user_first_name", "user_last_name", "payment_code", "payment_key", "payment_date",
                  "notification_type", "confirmed", "payment_amount", "transaction_fee", "payment_details")


class PaymentSerializer(serializers.ModelSerializer):

    payment_code = serializers.CharField(required=False)
    payment_details = RegistrationFeeSerializer(many=True)

    class Meta:
        model = Payment
        fields = ("id", "event", "user", "payment_code", "payment_key", "notification_type", "confirmed",
                  "payment_amount", "transaction_fee", "payment_details")

    def create(self, validated_data):

        user = self.context.get("request").user
        payment_details = validated_data.pop("payment_details")
        event = validated_data.pop("event")

        amount_due = Decimal(0.0)
        amounts = [detail["amount"] for detail in payment_details]
        for amount in amounts:
            amount_due += amount

        stripe_payment = calculate_payment_amount(amount_due)

        player = Player.objects.get(email=user.email)

        notification_type = derive_notification_type(event, player, payment_details)

        if amount_due == 0:
            # No charge events
            for detail in payment_details:
                slot = detail["registration_slot"]
                if slot.player is not None:
                    slot.status = "R"
                    slot.save()
                else:
                    slot.delete()

        payment = Payment.objects.create(event=event, user=user,
                                         payment_amount=stripe_payment[0],
                                         transaction_fee=stripe_payment[-1],
                                         confirmed=(amount_due == 0),
                                         notification_type=notification_type)
        payment.save()

        for detail in payment_details:
            registration_fee = RegistrationFee(event_fee=detail["event_fee"],
                                               registration_slot=detail["registration_slot"],
                                               amount=detail["amount"],
                                               payment=payment)
            registration_fee.save()

        return payment

    def update(self, instance, validated_data):
        payment_details = validated_data.pop("payment_details")
        event = validated_data.pop("event")

        amount_due = Decimal(0.0)
        amounts = [detail["amount"] for detail in payment_details]
        for amount in amounts:
            amount_due += amount

        stripe_payment = calculate_payment_amount(amount_due)
        # stripe_amount_due = int(stripe_payment[0] * 100)  # total (with fees) in cents

        # stripe.PaymentIntent.modify(instance.payment_code, amount=stripe_amount_due)

        instance.payment_amount = stripe_payment[0]
        instance.transaction_fee = stripe_payment[-1]
        instance.save()

        # recreate the payment details
        instance.payment_details.all().delete()
        for detail in payment_details:
            registration_fee = RegistrationFee(event_fee=detail["event_fee"],
                                               registration_slot=detail["registration_slot"],
                                               amount=detail["amount"],
                                               payment=instance)
            registration_fee.save()

        return instance


class RefundSerializer(serializers.ModelSerializer):
    refund_code = serializers.CharField(required=False)

    class Meta:
        model = Refund
        fields = ("id", "payment", "refund_code", "refund_amount", "notes", )

    def create(self, validated_data):
        """
        Create a Stripe refund for the provided payment and persist a corresponding Refund record.
        
        Expects validated_data to contain:
        - payment: Payment instance to refund.
        - refund_amount: Decimal/float refund amount in major currency units (e.g., dollars); this is converted to cents for Stripe.
        - notes (optional): Text notes for the refund (defaults to empty string).
        
        If saving the Refund raises an IntegrityError because a concurrent webhook already created the same refund, the existing Refund with the matching refund_code is fetched and returned.
        
        Returns:
            Refund: The created or existing Refund instance.
        """
        user = self.context.get("request").user
        notes = validated_data.get("notes", "")
        payment = validated_data.get("payment")
        refund_amount = validated_data.get("refund_amount")
        stripe_refund_amount = int(refund_amount * 100)  # total in cents

        stripe_refund = stripe.Refund.create(
            payment_intent=payment.payment_code,
            amount=stripe_refund_amount,
            reason="requested_by_customer",
        )

        try:
            refund = Refund(payment=payment,
                            issuer=user,
                            refund_code=stripe_refund.stripe_id,
                            refund_amount=refund_amount,
                            notes=notes)
            refund.save()
        except IntegrityError:
            # Webhook won the race - fetch the existing record
            refund = Refund.objects.get(refund_code=stripe_refund.stripe_id)

        return refund