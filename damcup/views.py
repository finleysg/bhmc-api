import csv
from decimal import Decimal

import math
from django.db import connection
from django.db.models.aggregates import Sum, Count
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from sentry_sdk import capture_exception, capture_message

from courses.models import Course
from damcup.models import DamCup, SeasonLongPoints, Scores
from damcup.serializers import DamCupSerializer, SeasonLongPointsSerializer
from documents.models import Document
from events.models import Event
from register.models import Player, RegistrationSlot
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
@permission_classes((permissions.AllowAny,))
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


@api_view(("POST",))
@permission_classes((permissions.IsAuthenticated,))
def import_scores(request):

    event_id = request.data.get("event_id", 0)
    document_id = request.data.get("document_id", 0)

    event = Event.objects.get(pk=event_id)
    document = Document.objects.get(pk=document_id)
    courses = list(Course.objects.all())
    players = Player.objects.all()
    player_map = {player.player_name(): player for player in players}

    with document.file.open("r") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        next(reader)  # skip header

        for row in reader:
            course = [course for course in courses if course.name == row[0]][0]
            player = player_map.get(row[1])

            if player is None:
                capture_message("player {} not found when importing scores".format(row[1]), level="error")
                continue

            save_score(1, row[2], event, course, player)
            save_score(2, row[3], event, course, player)
            save_score(3, row[4], event, course, player)
            save_score(4, row[5], event, course, player)
            save_score(5, row[6], event, course, player)
            save_score(6, row[7], event, course, player)
            save_score(7, row[8], event, course, player)
            save_score(8, row[9], event, course, player)
            save_score(9, row[10], event, course, player)

    return Response(status=204)


def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n*multiplier + Decimal(0.5)) / multiplier


def save_score(hole_number, cell, event, course, player):
    if cell.isnumeric():
        hole = [hole for hole in course.holes.all() if hole.hole_number == hole_number][0]
        score = int(cell)
        hole_score = Scores(event=event, player=player, hole=hole, score=score)
        hole_score.save()
