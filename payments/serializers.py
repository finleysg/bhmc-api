import stripe
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import serializers

from register.models import RegistrationFee, Player, RegistrationSlot
from register.serializers import RegistrationFeeSerializer
# noinspection PyPackages
from .models import Payment


class PaymentReportSerializer(serializers.ModelSerializer):

    user_first_name = serializers.CharField(source="user.first_name")
    user_last_name = serializers.CharField(source="user.last_name")
    # payment_details = PaymentDetailSerializer(many=True)

    class Meta:
        model = Payment
        fields = ("id", "event", "user_first_name", "user_last_name", "payment_code", "confirmed", "payment_date",
                  "payment_amount", "transaction_fee")


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

        # A = an admin is registering on behalf of a player
        notification_type = validated_data.get("notification_type", None)
        if notification_type == "A":
            player_email = self.context.get("request").query_params.get("player", None)
            return save_admin_payment(event, payment_details, player_email, validated_data)

        amount_due = get_amount_due(event, payment_details)
        stripe_payment = calculate_payment_amount(amount_due)
        stripe_amount_due = int(stripe_payment[0] * 100)  # total (with fees) in cents

        player = Player.objects.get(email=user.email)
        if player.stripe_customer_id is None or player.stripe_customer_id.strip() == "":
            customer = stripe.Customer.create()
            player.stripe_customer_id = customer.stripe_id
            player.save()

        notification_type = derive_notification_type(event, player, payment_details)

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
                                         payment_amount=stripe_payment[0],
                                         transaction_fee=stripe_payment[-1],
                                         notification_type=notification_type)
        payment.save()

        for detail in payment_details:
            registration_fee = RegistrationFee(event_fee=detail["event_fee"],
                                               registration_slot=detail["registration_slot"],
                                               payment=payment)
            registration_fee.save()

        return payment

    def update(self, instance, validated_data):
        payment_details = validated_data.pop("payment_details")
        event = validated_data.pop("event")

        amount_due = get_amount_due(event, payment_details)
        stripe_payment = calculate_payment_amount(amount_due)
        stripe_amount_due = int(stripe_payment[0] * 100)  # total (with fees) in cents

        stripe.PaymentIntent.modify(instance.payment_code, amount=stripe_amount_due)

        instance.payment_amount = stripe_payment[0]
        instance.transaction_fee = stripe_payment[-1]
        instance.save()

        # recreate the payment details
        instance.payment_details.all().delete()
        for detail in payment_details:
            registration_fee = RegistrationFee(event_fee=detail["event_fee"],
                                               registration_slot=detail["registration_slot"],
                                               payment=instance)
            registration_fee.save()

        return instance


def calculate_payment_amount(amount_due):
    transaction_fixed_cost = Decimal(0.3)
    transaction_percentage = Decimal(0.029)
    total = (amount_due + transaction_fixed_cost) / (Decimal(1.0) - transaction_percentage)
    transaction_fee = total - amount_due
    return total, transaction_fee


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


def derive_notification_type(event, player, payment_details):

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

    # bit of a roundabout way to get this info, but if there are
    # no required fees in the payment details, we know this is an
    # "edit" (skins payment, or other fees, after the initial registration)
    if has_required_fees(event, payment_details):
        return "C"


def get_amount_due(event, payment_details):
    amount_due = Decimal(0.0)
    event_fees = event.fees.all()
    event_fee_ids = [detail["event_fee"].id for detail in payment_details]
    for event_fee_id in event_fee_ids:
        event_fee = next(iter([f.amount for f in event_fees if f.id == event_fee_id]))
        amount_due += event_fee

    return amount_due


def has_required_fees(event, payment_details):
    event_fees = event.fees.all()
    event_fee_ids = [detail["event_fee"].id for detail in payment_details]
    required = next(iter([f for f in event_fees if f.is_required and f.id in event_fee_ids]), None)
    return required is not None
