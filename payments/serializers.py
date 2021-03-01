import stripe
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import serializers

from register.models import RegistrationFee, Player, RegistrationSlot
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

        user = self.context.get("request").user
        fees = validated_data.pop("payment_details")
        event = validated_data.pop("event")

        # A = an admin is registering on behalf of a player
        notification_type = validated_data.get("notification_type", None)
        if notification_type == "A":
            player_email = self.context.get("request").query_params.get("player", None)
            return save_admin_payment(event, fees, player_email, validated_data)

        event_fee_ids = [fee["event_fee"].id for fee in fees]
        amount_due = sum([f.amount for f in event.fees.all() if f.id in event_fee_ids])
        payment_details = calculate_payment_amount(amount_due)
        stripe_amount_due = int(payment_details[0] * 100)  # total (with fees) in cents

        player = Player.objects.get(email=user.email)
        if player.stripe_customer_id is None or player.stripe_customer_id.strip() == "":
            customer = stripe.Customer.create()
            player.stripe_customer_id = customer.stripe_id
            player.save()

        notification_type = derive_notification_type(event, player)

        intent = stripe.PaymentIntent.create(
            amount=stripe_amount_due,
            currency="usd",
            payment_method_types=["card"],
            description="Online payment for {} ({}) by {}".format(
                event.name,
                event.start_date.strftime("%Y-%m-%d"),
                user.get_full_name()),
            metadata={
                "user_name": user.get_full_name(),
                "user_email": user.email,
                "event_id": event.id,
                "event_name": event.name,
                "event_date": event.start_date.strftime("%Y-%m-%d"),
            },
            customer=player.stripe_customer_id,
            # setup_future_usage="on_session" if player.save_last_card else None,
        )
        payment = Payment.objects.create(event=event, user=user,
                                         payment_code=intent.stripe_id,
                                         payment_key=intent.client_secret,
                                         payment_amount=payment_details[0],
                                         transaction_fee=payment_details[-1],
                                         notification_type=notification_type)
        payment.save()

        for fee in fees:
            registration_fee = RegistrationFee(event_fee=fee["event_fee"],
                                               registration_slot=fee["registration_slot"],
                                               payment=payment)
            registration_fee.save()

        return payment

    def update(self, instance, validated_data):
        fees = validated_data.pop("payment_details")
        event = validated_data.pop("event")

        event_fee_ids = [fee["event_fee"].id for fee in fees]
        amount_due = sum([f.amount for f in event.fees.all() if f.id in event_fee_ids])
        payment_details = calculate_payment_amount(amount_due)
        stripe_amount_due = int(payment_details[0] * 100)  # total (with fees) in cents

        stripe.PaymentIntent.modify(instance.payment_code, amount=stripe_amount_due)

        instance.payment_amount = payment_details[0]
        instance.transaction_fee = payment_details[-1]
        instance.save()

        instance.payment_details.all().delete()

        for fee in fees:
            registration_fee = RegistrationFee(event_fee=fee["event_fee"],
                                               registration_slot=fee["registration_slot"],
                                               payment=instance)
            registration_fee.save()

        return instance


def save_admin_payment(event, fees, player_email, validated_data):
    user = User.objects.get(email=player_email)
    payment_amount = Decimal(validated_data.get("payment_amount", 0))

    payment = Payment.objects.create(event=event,
                                     user=user,
                                     payment_code=validated_data.get("payment_code"),
                                     payment_key="admin",
                                     payment_amount=payment_amount,
                                     transaction_fee=0,
                                     confirmed=True,
                                     notification_type="A")
    payment.save()

    for idx, fee in enumerate(fees):
        registration_fee = RegistrationFee(event_fee=fee["event_fee"],
                                           registration_slot=fee["registration_slot"],
                                           is_paid=(payment_amount > 0),
                                           payment=payment)
        registration_fee.save()

        slot = fee["registration_slot"]
        slot.status = "R"
        slot.save()

        # Assign the user to the player on behalf of whom the admin is registering
        if idx == 0:
            registration = slot.registration
            registration.user = user
            registration.save()

    return payment


def derive_notification_type(event, player):

    if event.id == settings.REGISTRATION_EVENT_ID:
        previous_season = RegistrationSlot.objects\
            .filter(event=settings.PREVIOUS_REGISTRATION_EVENT_ID)\
            .filter(player_id=player.id)\
            .filter(status="R")
        if len(previous_season) == 1:
            return "R"
        else:
            return "N"
    elif event.id == settings.MATCH_PLAY_EVENT_ID:
        return "M"

    return "C"
