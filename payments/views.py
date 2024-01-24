import stripe
import structlog

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from payments.emails import send_notification
from payments.models import Payment, Refund
from payments.serializers import PaymentSerializer, RefundSerializer
from payments.utils import calculate_refund_amount
from register.models import Player, Registration

logger = structlog.getLogger()
stripe.api_key = settings.STRIPE_SECRET_KEY
webhook_secret = settings.STRIPE_WEBHOOK_SECRET


@permission_classes((permissions.IsAuthenticated,))
class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = Payment.objects.all()
        event_id = self.request.query_params.get("event", None)
        is_self = self.request.query_params.get("player", None)
        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if is_self == "me":
            queryset = queryset.filter(user=self.request.user)
            queryset = queryset.order_by("-id")  # make it easy to grab the most recent
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


@permission_classes((permissions.IsAuthenticated,))
class RefundViewSet(viewsets.ModelViewSet):
    serializer_class = RefundSerializer

    def get_queryset(self):
        queryset = Payment.objects.all()
        event_id = self.request.query_params.get("event", None)
        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        return queryset


@api_view(("PUT",))
@permission_classes((permissions.IsAuthenticated,))
def confirm_payment(request, payment_id):
    registration_id = request.data.get("registrationId", 0)
    payment_method_id = request.data.get("paymentMethodId", "")
    save_card = request.data.get("saveCard", False)

    try:
        payment = Payment.objects.get(pk=payment_id)

        # update status on the slots to processing
        Registration.objects.payment_processing(registration_id)

        if save_card:
            intent = stripe.PaymentIntent\
                .confirm(payment.payment_code, payment_method=payment_method_id, setup_future_usage="on_session")
        else:
            intent = stripe.PaymentIntent.confirm(payment.payment_code, payment_method=payment_method_id)

        logger.info("Payment confirmed", payment=payment_id, registration=registration_id)
        return Response(intent.status, status=200)

    except Exception as e:
        logger.error("Confirm payment failed", registration=registration_id, payment=payment_id, message=str(e))
        Registration.objects.undo_payment_processing(registration_id)
        return Response(str(e), status=400)


@api_view(("POST",))
@permission_classes((permissions.IsAuthenticated,))
def create_refunds(request):
    refunds = request.data.get("refunds", [])
    successful_refunds = []
    failures = []
    for refund in refunds:
        try:
            payment = Payment.objects.get(pk=refund["payment"])
            refund_amount = calculate_refund_amount(payment, refund["refund_fees"])
            result = Refund.objects.create_refund(request.user, payment, refund_amount, refund["notes"])
            successful_refunds.append("Refund of {} created for {}".format(result.refund_amount, result.payment.id))
        except Exception as e:
            message = "Refund failed for {}: {}".format(refund, str(e))
            logger.error(message)
            failures.append(message)

    if len(failures) > 0:
        status = 400
    else:
        status = 200

    return Response({"refunds": successful_refunds, "failures": failures}, status=status)


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def player_cards(request):
    email = request.user.email
    player = Player.objects.get(email=email)
    if player.stripe_customer_id:
        cards = stripe.PaymentMethod.list(customer=player.stripe_customer_id, type="card")
        return Response(cards.data, status=200)

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
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
    event = stripe.Webhook.construct_event(
        payload, sig_header, webhook_secret
    )

    # Handle the event
    if event is None:
        return Response(status=400)
    elif event.type == "payment_intent.payment_failed":
        logger.warn("Payment failure", stripeId=event.stripe_id, message=event.data.object.last_payment_error.message)
    elif event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        handle_payment_complete(payment_intent)
    elif event.type == "charge.refunded":
        charge = event.data.object
        handle_refund_complete(charge)
    else:
        pass

    return Response(status=204)


def handle_payment_complete(payment_intent):
    payment = Payment.objects.get(payment_code=payment_intent.stripe_id)

    # exit early if we have already confirmed this payment
    if payment.confirmed:
        logger.info("Payment already confirmed by Stripe", paymentCode=payment.payment_code)
        return

    payment.confirmed = True
    payment.confirm_date = timezone.now()
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

    # Season registration handling
    update_membership(payment.event, slots)

    logger.info("Payment confirmed by Stripe", paymentCode=payment.payment_code)

    # important, but don"t cause the payment intent to fail
    try:
        # clear_available_slots(payment.event, slots[0].registration)
        email = payment_intent.metadata.get("user_email")
        player = Player.objects.get(email=email)
        send_notification(payment, slots, player)
    except Exception as e:
        logger.error("Send notification failure", paymentCode=payment.payment_code, message=str(e))


def handle_refund_complete(charge):
    for refund in charge.refunds.data:
        try:
            local_refund = Refund.objects.get(refund_code=refund.stripe_id)
            local_refund.confirmed = True
            local_refund.save()
            logger.info("Refund confirmed by Stripe", refundCode=refund.stripe_id, local=True)
        except ObjectDoesNotExist:
            # We get this hook for refunds created in the Stripe UI
            # so we will have not record to tie together
            logger.info("Refund confirmed by Stripe", refundCode=refund.stripe_id, local=False)
            pass


def save_customer_id(payment_intent):
    email = payment_intent.metadata.get("user_email")
    player = Player.objects.get(email=email)
    if player.stripe_customer_id is None:
        player.stripe_customer_id = payment_intent.customer
        player.save()

    return player


def update_membership(event, slots):
    try:
        # R is a season membership event
        if event.event_type == "R":
            for slot in slots:
                # Support multiple players for a registration
                if slot.status == "R":
                    player = slot.player
                    player.is_member = True
                    player.save()
    except Exception as e:
        logger.error("Membership update failure", message=str(e))
