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


def get_payment_details_by_event(event_id):
    with connection.cursor() as cursor:
        cursor.callproc("GetPaymentDetailsByEvent", [event_id])
        return fetch_all_as_dictionary(cursor)


def get_skins_by_event(event_id):
    with connection.cursor() as cursor:
        cursor.callproc("GetSkinsByEvent", [event_id])
        return fetch_all_as_dictionary(cursor)


def get_membership_data(season_event_id, previous_season_event_id):
    with connection.cursor() as cursor:
        cursor.callproc("MembershipReport", [season_event_id, previous_season_event_id])
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
                registration[fee.fee_type.name] = fee.amount if player_fee["is_paid"] == 1 else 0
            else:
                registration[fee.fee_type.name] = None

    return Response(registrations, status=200)


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def payment_report(request, event_id):
    payments = Payment.objects.all().filter(event=event_id)
    serializer = PaymentReportSerializer(payments, context={"request": request}, many=True)
    return Response(serializer.data)


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def skins_report(request, event_id):

    skins = get_skins_by_event(event_id)
    return Response(skins, status=200)


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def membership_report(request, season):

    current_season = SeasonSettings.objects.get(season=season)
    previous_season = SeasonSettings.objects.get(season=season-1)
    membership = get_membership_data(current_season.member_event.id, previous_season.member_event.id)
    return Response(membership, status=200)
