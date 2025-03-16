from django.db import connection

from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response

from core.models import SeasonSettings
from core.util import current_season
from events.models import EventFee
from payments.models import Payment
from payments.serializers import PaymentReportSerializer


def fetch_all_as_dictionary(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_registrations_by_event(event_id):
    with connection.cursor() as cursor:
        cursor.callproc("GetRegistrationsByEvent", [event_id])
        return fetch_all_as_dictionary(cursor)


def get_registration_fees_by_event(event_id):
    with connection.cursor() as cursor:
        cursor.callproc("GetRegistrationFeesByEvent", [event_id])
        return fetch_all_as_dictionary(cursor)


def get_payments_by_event(event_id):
    with connection.cursor() as cursor:
        cursor.callproc("GetPaymentsByEvent", [event_id])
        return fetch_all_as_dictionary(cursor)


def get_skins_by_event(event_id):
    with connection.cursor() as cursor:
        cursor.callproc("GetSkinsByEvent", [event_id])
        return fetch_all_as_dictionary(cursor)


def get_membership_data(season):
    with connection.cursor() as cursor:
        cursor.callproc("MembershipReport", [season])
        return fetch_all_as_dictionary(cursor)


def payment_details(payment_id):
    with connection.cursor() as cursor:
        cursor.callproc("PaymentDetails", [payment_id])
        return fetch_all_as_dictionary(cursor)


def refund_details(payment_id):
    with connection.cursor() as cursor:
        cursor.callproc("RefundDetails", [payment_id])
        return fetch_all_as_dictionary(cursor)


@permission_classes((permissions.IsAuthenticated,))
class ReportViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["get"])
    def event_registration(self, request):
        event_id = request.query_params.get("event_id", None)
        if event_id is None:
            return Response("An event_id is required", status=400)

        event_fees = EventFee.objects.all().filter(event=event_id).select_related("fee_type")
        registration_fees = get_registration_fees_by_event(event_id)
        registrations = get_registrations_by_event(event_id)

        for registration in registrations:
            for fee in event_fees:
                player_fee = next(
                    (
                        rf
                        for rf in registration_fees
                        if rf["event_fee_id"] == fee.id
                        and rf["player_id"] == registration["player_id"]
                    ),
                    None,
                )
                if player_fee is not None:
                    registration[fee.fee_type.name] = player_fee.get("amount_paid", None)
                    registration["is_override"] = 1 if player_fee.get("amount_paid", None) == fee.override_amount else 0
                    registration["override_for"] = fee.override_restriction
                else:
                    registration[fee.fee_type.name] = None
                    registration["is_override"] = None
                    registration["override_for"] = None

        return Response(registrations, status=200)

    @action(detail=False, methods=["get"])
    def payments(self, request):
        event_id = request.query_params.get("event_id", None)
        if event_id is None:
            return Response("An event_id is required", status=400)

        payments = get_payments_by_event(event_id)
        return Response(payments, status=200)

    @action(detail=False, methods=["get"])
    def skins(self, request):
        event_id = request.query_params.get("event_id", None)
        if event_id is None:
            return Response("An event_id is required", status=400)

        skins = get_skins_by_event(event_id)
        return Response(skins, status=200)

    @action(detail=False, methods=["get"])
    def membership(self, request):
        season = request.query_params.get("season", current_season())
        membership = get_membership_data(season)
        return Response(membership, status=200)

    @action(detail=False, methods=["get"])
    def payment_details(self, request):
        payment_id = request.query_params.get("payment_id", None)
        if payment_id is None:
            return Response("A payment_id is required", status=400)

        details = payment_details(payment_id)
        return Response(details, status=200)

    @action(detail=False, methods=["get"])
    def refund_details(self, request):
        payment_id = request.query_params.get("payment_id", None)
        if payment_id is None:
            return Response("A payment_id is required", status=400)

        details = refund_details(payment_id)
        return Response(details, status=200)
