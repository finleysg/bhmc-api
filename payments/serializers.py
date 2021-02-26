import stripe
from decimal import Decimal
from rest_framework import serializers

from register.models import RegistrationFee, Player
from register.serializers import RegistrationFeeSerializer
# noinspection PyPackages
from .models import Payment


def calculate_payment_amount(amount_due):
    transaction_fixed_cost = Decimal(0.3)
    transaction_percentage = Decimal(0.029)
    total = (amount_due + transaction_fixed_cost) / (Decimal(1.0) - transaction_percentage)
    transaction_fee = total - amount_due
    return total, transaction_fee


class PaymentSerializer(serializers.ModelSerializer):

    payment_code = serializers.CharField(required=False)
    payment_details = RegistrationFeeSerializer(many=True)

    class Meta:
        model = Payment
        fields = ("id", "event", "user", "payment_code", "payment_key", "notification_type", "confirmed",
                  "payment_amount", "transaction_fee", "payment_details")

    def create(self, validated_data):
        user = self.context.get('request').user
        fees = validated_data.pop("payment_details")
        event = validated_data.pop("event")

        event_fee_ids = [fee['event_fee'].id for fee in fees]
        amount_due = sum([f.amount for f in event.fees.all() if f.id in event_fee_ids])
        payment_details = calculate_payment_amount(amount_due)
        stripe_amount_due = int(payment_details[0] * 100)  # total (with fees) in cents

        player = Player.objects.get(email=user.email)
        if player.stripe_customer_id is None or player.stripe_customer_id.strip() == "":
            customer = stripe.Customer.create()
            player.stripe_customer_id = customer.stripe_id
            player.save()

        intent = stripe.PaymentIntent.create(
            amount=stripe_amount_due,
            currency='usd',
            payment_method_types=["card"],
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
            customer=player.stripe_customer_id,
            # setup_future_usage="on_session" if player.save_last_card else None,
        )
        payment = Payment.objects.create(event=event, user=user,
                                         payment_code=intent.stripe_id,
                                         payment_key=intent.client_secret,
                                         payment_amount=payment_details[0],
                                         transaction_fee=payment_details[-1],
                                         notification_type=validated_data.get("notification_type"))
        payment.save()

        for fee in fees:
            registration_fee = RegistrationFee(event_fee=fee['event_fee'],
                                               registration_slot=fee['registration_slot'],
                                               payment=payment)
            registration_fee.save()

        return payment

    def update(self, instance, validated_data):
        fees = validated_data.pop("payment_details")
        event = validated_data.pop("event")

        event_fee_ids = [fee['event_fee'].id for fee in fees]
        amount_due = sum([f.amount for f in event.fees.all() if f.id in event_fee_ids])
        payment_details = calculate_payment_amount(amount_due)
        stripe_amount_due = int(payment_details[0] * 100)  # total (with fees) in cents

        stripe.PaymentIntent.modify(instance.payment_code, amount=stripe_amount_due)

        instance.payment_amount = payment_details[0]
        instance.transaction_fee = payment_details[-1]
        instance.save()

        instance.payment_details.all().delete()

        for fee in fees:
            registration_fee = RegistrationFee(event_fee=fee['event_fee'],
                                               registration_slot=fee['registration_slot'],
                                               payment=instance)
            registration_fee.save()

        return instance
