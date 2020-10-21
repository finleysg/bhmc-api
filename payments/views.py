import json
import logging
import stripe

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.email import send_notification
from payments.models import Payment
from payments.serializers import PaymentSerializer
from register.models import RegistrationSlot

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()

    def get_serializer_context(self):
        """
        pass request attribute to serializer
        """
        context = super(PaymentViewSet, self).get_serializer_context()
        return context


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
    event_id = payment_intent.metadata.get("event_id")
    fee_ids = payment_intent.metadata.get("fee_ids")
    fee_id_list = [int(fee_id) for fee_id in fee_ids.split(',')]

    payment.confirmed = True
    payment.save()

    RegistrationSlot.objects.update_slots_for_payment(payment, fee_id_list)

    send_notification(payment, event_id)


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
