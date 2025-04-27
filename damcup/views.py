import csv

import structlog

from django.db import connection
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response

from core.util import current_season
from damcup.models import DamCup, SeasonLongPoints
from damcup.serializers import DamCupSerializer, SeasonLongPointsSerializer
from damcup.utils import round_half_up, is_points, get_point_rows
from documents.models import Document
from documents.utils import open_xls_workbook
from events.models import Event
from register.models import Player
from reporting.views import fetch_all_as_dictionary
from scores.utils import get_score_type, get_course

logger = structlog.get_logger(__name__)


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
        season = self.request.query_params.get("season", None)
        event_id = self.request.query_params.get("event", None)
        player_id = self.request.query_params.get("player", None)

        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if season is not None:
            queryset = queryset.filter(event__season=season)
        if player_id is not None:
            queryset = queryset.filter(player=player_id)

        return queryset.select_related("player").order_by("player__last_name")

    @action(detail=False, methods=["get"])
    def top_points(self, request):
        season = request.query_params.get("season", current_season())
        category = request.query_params.get("category", "gross")
        top_n = int(request.query_params.get("top", "20"))

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

    event = Event.objects.get(pk=event_id)
    document = Document.objects.get(pk=document_id)
    players = Player.objects.filter(is_member=True).all()
    player_map = {player.player_name(): player for player in players}
    failures = []

    wb = open_xls_workbook(document)
    for sheet in wb.sheets():
        if is_points(sheet):
            score_type = get_score_type(sheet.name)
            course_name = get_course(sheet.name)

            for i in get_point_rows(sheet):
                try:
                    player_name = sheet.cell(i, 1).value
                    if player_name == "":
                        continue

                    player = player_map.get(player_name)
                    if player is None:
                        message = f"player {player_name} not found when importing {score_type} points"
                        logger.warn(message)
                        failures.append(message)
                        continue

                    player_points = int(round_half_up(sheet.cell(i, 4).value))
                    points = SeasonLongPoints.objects.filter(event=event, player=player, additional_info=course_name).first()
                    if points is None:
                        points = SeasonLongPoints(event=event, player=player, additional_info=course_name,
                                                  gross_points=player_points if score_type == "gross" else 0,
                                                  net_points=player_points if score_type == "net" else 0)
                    else:
                        points.gross_points = player_points if score_type == "gross" else points.gross_points
                        points.net_points = player_points if score_type == "net" else points.net_points

                    points.save()
                except Exception as e:
                    failures.append(str(e))
                    logger.error(e)

    return Response(data=failures, status=200)


@api_view(("POST",))
@permission_classes((permissions.IsAuthenticated,))
def import_major_points(request):

    event_id = request.data.get("event_id", 0)
    document_id = request.data.get("document_id", 0)

    event = Event.objects.get(pk=event_id)
    document = Document.objects.get(pk=document_id)
    players = Player.objects.filter(is_member=True).all()
    player_map = {player.ghin: player for player in players}
    failures = []

    with document.file.open("r") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        next(reader)
        for row in reader:
            try:
                ghin = str(int(row[0]))
                player = player_map.get(ghin)
                if player is None:
                    message = f"GHIN {ghin} not found when importing {event.name} points"
                    logger.warn(message)
                    failures.append(message)
                    continue

                gross_points = int(round_half_up(row[3]))
                net_points = int(round_half_up(row[4]))
                points = SeasonLongPoints.objects.filter(event=event, player=player, additional_info=event.name).first()
                if points is None:
                    points = SeasonLongPoints(event=event, player=player, additional_info=event.name,
                                              gross_points=gross_points, net_points=net_points)
                else:
                    points.gross_points = gross_points
                    points.net_points = net_points

                points.save()
            except Exception as e:
                failures.append(str(e))
                logger.error(e)

    document.file.delete()
    document.delete()

    return Response(data=failures, status=200)
