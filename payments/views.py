import json
import logging
import stripe

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from payments.email import send_notification
from payments.models import Payment
from payments.serializers import PaymentSerializer

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = Payment.objects.all()
        event_id = self.request.query_params.get('event_id', None)
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


# This is a webhook registered with Stripe
@csrf_exempt
@api_view(("POST",))
@permission_classes((permissions.AllowAny,))
def payment_complete(request):
    payload = request.body
    event = unpack_stripe_event(payload)

    # Handle the event
    if event is None:
        return Response(status=400)
    elif event.type == 'payment_intent.created':
        logger.info("Payment created: " + event.stripe_id)
    elif event.type == 'payment_intent.canceled':
        logger.warning("Payment canceled: " + event.stripe_id)
    elif event.type == 'payment_intent.payment_failed':
        logger.error("Payment failure: " + event.stripe_id)
    elif event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        handle_payment_complete(payment_intent)
    elif event.type == 'payment_method.attached':
        logger.info("Payment attached: " + event.stripe_id)
    elif event.type == 'charge.succeeded':
        logger.info("Charge succeeded: " + event.stripe_id)
    else:
        logger.warning("Unexpected Stripe callback: " + event.type)
        # return Response(status=400)

    return Response(status=204)


def handle_payment_complete(payment_intent):
    payment = Payment.objects.get(payment_code=payment_intent.stripe_id)

    payment.confirmed = True
    payment.save()

    fees = list(payment.payment_details.all())
    slots = [fee.registration_slot for fee in fees]
    for slot in slots:
        slot.status = "R"
        slot.save()

    send_notification(payment, fees, slots)


def unpack_stripe_event(payload):
    try:
        event = stripe.Event.construct_from(
            json.loads(payload), stripe.api_key
        )
    except ValueError as e:
        logger.error("Failed to unpack the json response from Stripe.")
        logger.error(e)
        return None

    return event
