from django.db import connection

from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from events.models import EventFee


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

    payment_details = get_payment_details_by_event(event_id)
    return Response(payment_details, status=200)
