import stripe
import structlog

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from events.models import Event
from payments.models import Payment, Refund
from payments.serializers import PaymentSerializer, RefundSerializer
from payments.tasks import handle_payment_complete, handle_refund_created, handle_refund_confirmed
from payments.utils import calculate_refund_amount, get_amount_due, calculate_payment_amount, round_half_up, \
    update_to_unpaid
from register.models import Player, Registration

logger = structlog.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY
webhook_secret = settings.STRIPE_WEBHOOK_SECRET

#============================ ViewSets ============================#

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

    @action(detail=True, methods=['put'], permission_classes=[IsAdminUser])
    def move_payment(self, request, pk):
        target_event_id = request.data.get("target_event_id", None)

        payment = Payment.objects.get(pk=pk)
        payment.event = target_event_id
        payment.save()

        return Response(status=204)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def stripe_amount(self, request, pk):
        try:
            payment = Payment.objects.get(pk=pk)
        except ObjectDoesNotExist:
            logger.warn("No payment found when calculating payment amount.", payment_id=pk)
            return Response("No payment found. Your registration may have timed out. Cancel your current registration and start again.", status=404)

        payment_details = list(payment.payment_details.all())

        amount_due = get_amount_due(None, payment_details)
        stripe_payment = calculate_payment_amount(amount_due)
        stripe_amount_due = int(round_half_up(stripe_payment[0] * 100))

        return Response(stripe_amount_due, status=200)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def customer_session(self, request):
        email = request.user.email
        player = Player.objects.get(email=email)

        if player.stripe_customer_id is None:
            customer = stripe.Customer.create()
            player.stripe_customer_id = customer.id
            player.save()

        session = stripe.CustomerSession.create(
            customer=player.stripe_customer_id,
            components={
                "payment_element": {
                    "enabled": True,
                    "features": {
                        "payment_method_redisplay": "enabled",
                        "payment_method_save": "enabled",
                        "payment_method_save_usage": "on_session",
                        "payment_method_remove": "enabled",
                    }
                }
            }
        )
        return Response(session, status=200)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def payment_intent(self, request, pk):
        try:
            event_id = request.data.get("event_id", 0)
            registration_id = request.data.get("registration_id", 0)
            user = request.user
            player = Player.objects.get(email=user.email)
            event = Event.objects.get(pk=event_id)
            payment = Payment.objects.get(pk=pk)
            payment_details = list(payment.payment_details.all())

            amount_due = get_amount_due(event, payment_details)
            stripe_payment = calculate_payment_amount(amount_due)
            stripe_amount_due = int(round_half_up(stripe_payment[0] * 100))  # total (with fees) in cents

            if amount_due > 0 and (player.stripe_customer_id is None or player.stripe_customer_id.strip() == ""):
                customer = stripe.Customer.create()
                player.stripe_customer_id = customer.id
                player.save()

            intent = stripe.PaymentIntent.create(
                amount=stripe_amount_due,
                currency="usd",
                automatic_payment_methods={"enabled": True},
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
                    "registration_id": registration_id,
                },
                customer=player.stripe_customer_id,
                receipt_email=user.email,
            )
            logger.info("Payment intent created", payment_id=pk, intent_id=intent.id, status=intent.status)

            payment.payment_code = intent.id
            payment.payment_key = intent.client_secret
            payment.save()

            # Updates the registration slots to processing and frees up any slots without players
            Registration.objects.payment_processing(registration_id)

            return Response(intent, status=200)

        except Exception as e:
            logger.error("Payment intent creation failed", payment_id=pk, message=str(e))
            return Response(str(e), status=400)


@permission_classes((permissions.IsAuthenticated,))
class RefundViewSet(viewsets.ModelViewSet):
    serializer_class = RefundSerializer

    def get_queryset(self):
        queryset = Payment.objects.all()
        event_id = self.request.query_params.get("event", None)
        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        return queryset

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUser])
    def issue_refunds(self, request):
        refunds = request.data.get("refunds", [])
        successful_refunds = []
        failures = []
        for refund in refunds:
            try:
                payment = Payment.objects.get(pk=refund["payment"])
                refund_amount = calculate_refund_amount(payment, refund["refund_fees"])
                result = Refund.objects.create_refund(request.user, payment, refund_amount, refund["notes"])
                update_to_unpaid(refund["refund_fees"])
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


#============================ Stripe Webhook ============================#

@csrf_exempt
@api_view(("POST",))
@permission_classes((permissions.AllowAny,))
def payment_complete_acacia(request):
    try:
        # Verify and construct the Stripe event
        payload = request.body
        sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

        if event is None:
            return Response(status=400)

        handlers = {
            "payment_intent.payment_failed": _handle_payment_failed,
            "payment_intent.succeeded": _handle_payment_succeeded,
            "refund.created": _handle_refund_created,
            "refund.updated": _handle_refund_updated,
        }

        handler = handlers.get(event.type)
        if handler:
            handler(event)
        else:
            logger.debug("Unhandled event", event_type=event.type)

        return Response(status=200)

    except stripe.error.SignatureVerificationError as se:
        logger.error("Invalid signature in webhook", error=str(se))
        return Response(status=400)
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        return Response(status=400)



@csrf_exempt
@api_view(("POST",))
@permission_classes((permissions.AllowAny,))
def payment_complete_clover(request):
    try:
        # Verify and construct the Stripe event
        payload = request.body
        sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

        if event is None:
            return Response(status=400)

        handlers = {
            "payment_intent.payment_failed": _handle_payment_failed,
            "payment_intent.succeeded": _handle_payment_succeeded,
            "refund.created": _handle_refund_created,
            "refund.updated": _handle_refund_updated,
        }

        handler = handlers.get(event.type)
        if handler:
            handler(event)
        else:
            logger.debug("Unhandled event", event_type=event.type)

        return Response(status=200)

    except stripe.error.SignatureVerificationError as se:
        logger.error("Invalid signature in webhook", error=str(se))
        return Response(status=400)
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        return Response(status=400)


def _handle_payment_failed(event):
    payment_intent = event.data.object
    error = payment_intent.last_payment_error
    logger.warn("Payment failure",
                event_id=event.id,
                payment_intent_id=payment_intent.id,
                error_message=error.message if error else "Unknown error",
                error_code=error.code if error else None,
                error_type=error.type if error else None,
                user_email=payment_intent.metadata.get("user_email"))


def _handle_payment_succeeded(event):
    payment_intent = event.data.object
    handle_payment_complete.delay(payment_intent)


def _handle_refund_created(event):
    refund = event.data.object
    handle_refund_created.delay(refund)


def _handle_refund_updated(event):
    refund = event.data.object
    handle_refund_confirmed.delay(refund)
