import logging
import stripe

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from sentry_sdk import capture_message, capture_exception

from payments.emails import send_notification
from payments.models import Payment
from payments.serializers import PaymentSerializer
from register.models import Player

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY
webhook_secret = settings.STRIPE_WEBHOOK_SECRET


@permission_classes((permissions.IsAuthenticated,))
class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = Payment.objects.all()
        event_id = self.request.query_params.get('event', None)
        is_self = self.request.query_params.get('player', None)
        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if is_self == "me":
            queryset = queryset.filter(user=self.request.user)
            queryset = queryset.order_by('-id')  # make it easy to grab the most recent
        return queryset

    def get_serializer_context(self):
        """
        pass request attribute to serializer
        """
        context = super(PaymentViewSet, self).get_serializer_context()
        return context

    def destroy(self, request, *args, **kwargs):
        queryset = Payment.objects.all()
        payment = queryset.get(pk=kwargs.get("pk"))
        stripe.PaymentIntent.cancel(payment.payment_code)
        return super(PaymentViewSet, self).destroy(request, *args, **kwargs)


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def player_cards(request):
    email = request.user.email
    player = Player.objects.get(email=email)
    if player.stripe_customer_id:
        cards = stripe.PaymentMethod.list(customer=player.stripe_customer_id, type="card")
        return Response(cards, status=200)

    return Response([], status=200)


@api_view(("POST",))
@permission_classes((permissions.IsAuthenticated,))
def player_card(request):
    email = request.user.email
    player = Player.objects.get(email=email)
    if player.stripe_customer_id is None:
        customer = stripe.Customer.create()
        player.stripe_customer_id = customer.stripe_id
        player.save()

    intent = stripe.SetupIntent.create(customer=player.stripe_customer_id, usage="on_session")
    return Response(intent, status=200)


@api_view(("DELETE",))
@permission_classes((permissions.IsAuthenticated,))
def remove_card(request, payment_method):
    stripe.PaymentMethod.detach(payment_method)
    return Response(status=204)


# This is a webhook registered with Stripe
@csrf_exempt
@api_view(("POST",))
@permission_classes((permissions.AllowAny,))
def payment_complete(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = stripe.Webhook.construct_event(
        payload, sig_header, webhook_secret
    )

    # Handle the event
    if event is None:
        return Response(status=400)
    elif event.type == 'payment_intent.payment_failed':
        capture_message("Payment failure: " + event.stripe_id, level="error")
        capture_message(event.data.object.last_payment_error.message, level="error")
    elif event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        handle_payment_complete(payment_intent)
    else:
        capture_message("Stripe callback: " + event.type, level="info")

    return Response(status=204)


def handle_payment_complete(payment_intent):
    payment = Payment.objects.get(payment_code=payment_intent.stripe_id)

    # exit early if we have already confirmed this payment
    if payment.confirmed:
        capture_message("Already confirmed payment " + payment.payment_code, level="info")
        return

    payment.confirmed = True
    payment.save()

    payment_details = list(payment.payment_details.all())
    for detail in payment_details:
        detail.is_paid = True
        detail.save()

    # We are doing extra work here, since the slot record
    # can be duplicated across payment details
    slots = [detail.registration_slot for detail in payment_details]
    for slot in slots:
        slot.status = "R"
        slot.save()

    # important, but don't cause the payment intent to fail
    try:
        clear_available_slots(payment.event, slots[0].registration)
        email = payment_intent.metadata.get("user_email")
        player = Player.objects.get(email=email)
        send_notification(payment, slots, player)
    except Exception as e:
        capture_message("Send notification failure: " + payment.payment_code, level="error")
        capture_exception(e)


def save_customer_id(payment_intent):
    email = payment_intent.metadata.get("user_email")
    player = Player.objects.get(email=email)
    if player.stripe_customer_id is None:
        player.stripe_customer_id = payment_intent.customer
        player.save()

    return player


def clear_available_slots(event, registration):
    if event.can_choose:
        registration.slots.filter(status="P").update(**{"status": "A", "player": None})
    else:
        registration.slots.filter(status="P").delete()
