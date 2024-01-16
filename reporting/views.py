from django.db import connection

from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.models import SeasonSettings
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


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def event_report(request, event_id):

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


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def payment_report(request, event_id):
    payments = get_payments_by_event(event_id)
    return Response(payments, status=200)


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def skins_report(request, event_id):

    skins = get_skins_by_event(event_id)
    return Response(skins, status=200)


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def membership_report(request, season):

    membership = get_membership_data(season)
    return Response(membership, status=200)
