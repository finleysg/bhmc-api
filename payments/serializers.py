import stripe
from rest_framework import serializers

from register.models import RegistrationFee
from register.serializers import RegistrationFeeSerializer
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):

    payment_code = serializers.CharField(required=False)
    payment_details = RegistrationFeeSerializer(many=True)

    class Meta:
        model = Payment
        fields = ("id", "event", "user", "payment_code", "payment_key", "notification_type", "confirmed",
                  "payment_details")

    def create(self, validated_data):
        user = self.context.get('request').user
        fees = validated_data.pop("payment_details")
        event = validated_data.pop("event")

        event_fee_ids = [fee['event_fee'].id for fee in fees]
        amount_due = sum([f.amount for f in event.fees.all() if f.id in event_fee_ids])

        intent = stripe.PaymentIntent.create(
            amount=amount_due * 100,
            currency='usd',
            description='Online payment for {} ({}) by {}'.format(
                event.name,
                event.start_date.strftime('%Y-%m-%d'),
                user.get_full_name()),
            metadata={
                'user_name': user.get_full_name(),
                'user_email': user.email,
                'event_id': event.id,
                'event_name': event.name,
                'event_date': event.start_date.strftime('%Y-%m-%d'),
            },
        )
        payment = Payment.objects.create(event=event, user=user,
                                         payment_code=intent.stripe_id,
                                         payment_key=intent.client_secret,
                                         notification_type=validated_data.get("notification_type"))
        payment.save()

        for fee in fees:
            registration_fee = RegistrationFee(event_fee=fee['event_fee'],
                                               registration_slot=fee['registration_slot'],
                                               payment=payment)
            registration_fee.save()

        return payment
