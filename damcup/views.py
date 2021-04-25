import csv
from decimal import Decimal

import math
from django.db import connection
from django.db.models.aggregates import Sum, Count
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from sentry_sdk import capture_exception, capture_message

from damcup.models import DamCup, SeasonLongPoints
from damcup.serializers import DamCupSerializer, SeasonLongPointsSerializer
from documents.models import Document
from events.models import Event
from register.models import Player
from reporting.views import fetch_all_as_dictionary


def get_top_gross_points(season, top_n):
    with connection.cursor() as cursor:
        cursor.callproc("TopGrossPoints", [season, top_n])
        return fetch_all_as_dictionary(cursor)


def get_top_net_points(season, top_n):
    with connection.cursor() as cursor:
        cursor.callproc("TopNetPoints", [season, top_n])
        return fetch_all_as_dictionary(cursor)


class DamCupViewSet(viewsets.ModelViewSet):
    serializer_class = DamCupSerializer
    queryset = DamCup.objects.all().order_by("-season")


class SeasonLongPointsViewSet(viewsets.ModelViewSet):
    serializer_class = SeasonLongPointsSerializer

    def get_queryset(self):
        queryset = SeasonLongPoints.objects.all()
        event_id = self.request.query_params.get("event_id", None)

        if event_id is not None:
            queryset = queryset.filter(event=event_id)

        return queryset.select_related("player").order_by("player__last_name")


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def get_top_points(request, season, category, top_n):

    if category == "gross":
        return Response(get_top_gross_points(season, top_n), status=200)
    elif category == "net":
        return Response(get_top_net_points(season, top_n), status=200)
    else:
        raise ValueError("category must be 'gross' or 'net'")


@api_view(("POST",))
@permission_classes((permissions.IsAuthenticated,))
def import_points(request):

    event_id = request.data.get("event_id", 0)
    document_id = request.data.get("document_id", 0)
    additional_info = request.data.get("additional_info", None)

    event = Event.objects.get(pk=event_id)
    document = Document.objects.get(pk=document_id)

    # with open(document.file.read(), newline='') as csvfile:
    with document.file.open("r") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        next(reader)  # skip header

        for row in reader:
            gross_points = 0 if row[3] == "" else int(round_half_up(Decimal(row[3])))
            net_points = 0 if row[4] == "" else int(round_half_up(Decimal(row[4])))
            if gross_points > 0:
                player = Player.objects.filter(ghin=row[0]).first()
                if player is None:
                    capture_message("ghin {} not found when importing points".format(row[0]), level="error")
                else:
                    points = SeasonLongPoints.objects.filter(event=event, player=player).first()
                    if points is None:
                        points = SeasonLongPoints(event=event, player=player, additional_info=additional_info,
                                                  gross_points=gross_points, net_points=net_points)
                    else:
                        points.gross_points = gross_points
                        points.net_points = net_points
                        points.additional_info = additional_info

                    points.save()

    return Response(status=204)


def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n*multiplier + Decimal(0.5)) / multiplier
