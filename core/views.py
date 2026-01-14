import random
import string

from datetime import timedelta

import djoser.views
import structlog
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from djoser import utils
from djoser.conf import settings

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import permission_classes, api_view
from rest_framework.response import Response

from bhmc.settings import DJANGO_ENV
from damcup.utils import is_points, get_point_rows
from documents.models import Document
from documents.utils import open_xlsx_workbook, open_xls_workbook
from events.models import Event
from register.models import Player
from scores.utils import get_score_type, get_course
from .models import BoardMember, MajorChampion, Ace, LowScore, SeasonSettings
from .serializers import BoardMemberSerializer, AceSerializer, LowScoreSerializer, MajorChampionSerializer, \
    SeasonSettingsSerializer
from .tasks import debug_task

is_localhost = DJANGO_ENV != "prod"
logger = structlog.get_logger(__name__)


class BoardMemberViewSet(viewsets.ModelViewSet):
    serializer_class = BoardMemberSerializer
    queryset = BoardMember.objects.all()

    @method_decorator(cache_page(60 * 60 * 4))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class MajorChampionViewSet(viewsets.ModelViewSet):
    serializer_class = MajorChampionSerializer

    def get_queryset(self):
        queryset = MajorChampion.objects.all()
        season = self.request.query_params.get("season", None)
        event_id = self.request.query_params.get("event", None)
        player_id = self.request.query_params.get("player", None)

        if season is not None:
            queryset = queryset.filter(season=season)
        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if player_id is not None:
            queryset = queryset.filter(player=player_id)
        queryset = queryset.order_by("event__start_date", "flight", "is_net")

        return queryset

    @method_decorator(cache_page(60 * 60 * 4))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class LowScoreViewSet(viewsets.ModelViewSet):
    serializer_class = LowScoreSerializer

    def get_queryset(self):
        queryset = LowScore.objects.all()
        season = self.request.query_params.get("season", None)

        if season is not None:
            queryset = queryset.filter(season=season)

        return queryset

    @method_decorator(cache_page(60 * 60 * 1))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AceViewSet(viewsets.ModelViewSet):
    serializer_class = AceSerializer

    def get_queryset(self):
        queryset = Ace.objects.all()
        season = self.request.query_params.get("season", None)
        player_id = self.request.query_params.get("player_id", None)

        if season is not None:
            queryset = queryset.filter(season=season)
        if player_id is not None:
            queryset = queryset.filter(player=player_id)
            queryset = queryset.order_by("-season")

        return queryset

    @method_decorator(cache_page(60 * 60 * 4))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class SeasonSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = SeasonSettingsSerializer

    def get_queryset(self):
        queryset = SeasonSettings.objects.all()
        is_active = self.request.query_params.get("is_active", None)
        season = self.request.query_params.get("season", None)

        if season is not None:
            queryset = queryset.filter(season=season)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset.order_by("-season")


class TokenCreateView(djoser.views.TokenCreateView):
    def _action(self, serializer):
        token = utils.login_user(self.request, serializer.user)
        token_serializer_class = settings.SERIALIZERS.token

        response = Response()
        data = token_serializer_class(token).data

        response.set_cookie(
            key = "access_token",
            path = "/",
            value = data["auth_token"],
            max_age = timedelta(days=90),
            secure = not is_localhost,
            httponly = True,
            samesite = "Lax",
            domain = ".bhmc.org" if not is_localhost else None,
        )

        response.data = "Welcome!"
        response.status_code = status.HTTP_200_OK
        return response


class TokenDestroyView(djoser.views.TokenDestroyView):
    """Use this endpoint to logout user (remove user authentication token)."""

    permission_classes = settings.PERMISSIONS.token_destroy

    def post(self, request):
        response = Response()
        response.delete_cookie(
            key = "access_token",
            path = "/",
            samesite = "Lax",
            domain = ".bhmc.org" if not is_localhost else None,
        )
        response.status_code = status.HTTP_204_NO_CONTENT
        utils.logout_user(request)
        return response


@api_view(("GET",))
@permission_classes((permissions.AllowAny,))
def ping_celery(request):
    debug_task.delay()
    return Response(data="task started", status=200)


@api_view(("POST",))
@permission_classes((permissions.IsAuthenticated,))
def import_champions(request):

    event_id = request.data.get("event_id", 0)
    document_id = request.data.get("document_id", 0)

    event = Event.objects.get(pk=event_id)
    season = event.season
    event_name = event.name

    players = Player.objects.filter(is_member=True).all()
    player_map = {player.player_name(): player for player in players}
    existing_champions = {champ.player.id: champ for champ in list(MajorChampion.objects.filter(event=event))}

    document = Document.objects.get(pk=document_id)
    wb = open_xlsx_workbook(document)
    sheet = wb.active
    last_row = sheet.max_row
    failures = []

    # skip header row
    for i in range(2, last_row + 1):
        flight = sheet.cell(row=i, column=1).value
        if flight is None:
            break

        champion = sheet.cell(row=i, column=2).value
        score = sheet.cell(row=i, column=3).value
        is_net = False if sheet.cell(row=i, column=4).value is None else sheet.cell(row=i, column=4).value

        try:
            players, errors = get_players(champion, player_map)
            team_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
            for player in players:
                existing = existing_champions.get(player.id)
                if existing is None:
                    new_champion = MajorChampion.objects.create(season=season,
                                                                event=event,
                                                                event_name=event_name,
                                                                flight=flight,
                                                                player=player,
                                                                team_id=team_id,
                                                                score=score,
                                                                is_net=is_net)
                    new_champion.save()
                else:
                    existing.flight = flight
                    existing.score = score
                    existing.is_net = is_net
                    existing.team_id = team_id
                    existing.save()

            for error in errors:
                failures.append(error)

        except Exception as ex:
            failures.append(str(ex))

    # do not keep the data file
    document.file.delete()
    document.delete()

    return Response(data=failures, status=200)


@api_view(("POST",))
@permission_classes((permissions.IsAuthenticated,))
def import_low_scores(request):

    event_id = request.data.get("event_id", 0)
    document_id = request.data.get("document_id", 0)

    event = Event.objects.get(pk=event_id)
    document = Document.objects.get(pk=document_id)
    failures = []

    wb = open_xls_workbook(document)
    for sheet in wb.sheets():
        if is_points(sheet):
            score_type = get_score_type(sheet.name)
            course_name = get_course(sheet.name)
            low_score = 100

            for i in get_point_rows(sheet):
                if isinstance(sheet.cell(i, 3).value, (int, float)):
                    this_score = int(sheet.cell(i, 3).value)
                    if this_score < low_score:
                        low_score = this_score

            current_low_score = LowScore.objects.filter(season=event.season,
                                                        course_name=course_name,
                                                        is_net=score_type == "net").first()

            logger.info(f"Tonight's low {score_type} score on the {course_name}: {low_score}")
            if current_low_score is None:
                save_low_score(event, course_name, score_type, low_score, sheet, failures)
            else:
                if low_score < current_low_score.score:
                    LowScore.objects.filter(season=event.season, course_name=course_name, is_net=score_type == "net").delete()
                    save_low_score(event, course_name, score_type, low_score, sheet, failures)
                elif low_score == current_low_score.score:
                    save_low_score(event, course_name, score_type, low_score, sheet, failures)

    return Response(data=failures, status=200)


def save_low_score(event, course_name, score_type, score, sheet, failures):
    players = Player.objects.filter().all()
    player_map = {player.player_name(): player for player in players}
    for i in get_point_rows(sheet):
        if isinstance(sheet.cell(i, 3).value, (int, float)):
            this_score = int(sheet.cell(i, 3).value)
            if this_score == score:
                player_name = sheet.cell(i, 1).value
                player = player_map.get(player_name)

                if player is None:
                    message = f"player {player_name} not found when importing low scores"
                    failures.append(message)
                    continue

                try:
                    logger.info(f"Saving low {score_type} score of {score} for {player_name} on the {course_name}")
                    low_score = LowScore.objects.create(season=event.season, course_name=course_name, player=player,
                                                        score=score, is_net=score_type == "net")
                    low_score.save()
                except Exception as ex:
                    failures.append(str(ex))


def get_players(champion, player_map):
    players = []
    errors = []
    partners = champion.split(" + ")
    for partner in partners:
        player = player_map.get(partner.strip())
        if player is None:
            errors.append(f"Player {partner} not found")
        else:
            players.append(player)

    return players, errors
