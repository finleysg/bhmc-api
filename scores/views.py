import requests
import urllib

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from sentry_sdk import capture_exception, capture_message
from xlrd import open_workbook

from courses.models import Course
from documents.models import Document
from events.models import Event
from register.models import Player
from scores.models import EventScore
from scores.serializers import EventScoreSerializer
from scores.utils import is_hole_scores, get_score_type, get_course, get_score_rows, get_player_name, PlayerScore, \
    get_scores


class EventScoreViewSet(viewsets.ModelViewSet):
    serializer_class = EventScoreSerializer

    def get_queryset(self):
        queryset = EventScore.objects.all()
        season = self.request.query_params.get("season", None)
        player_id = self.request.query_params.get("player_id", None)
        is_net = self.request.query_params.get("is_net", "false")

        if season is None or player_id is None:
            return

        queryset = queryset.filter(player=player_id)
        queryset = queryset.filter(event__season=season)
        if is_net == "true":
            queryset = queryset.filter(is_net=True)
        else:
            queryset = queryset.filter(is_net=False)

        return queryset.order_by("event__start_date", "hole")


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

    existing_scores = EventScore.objects.filter(event=event).count()
    if existing_scores > 0:
        return Response(status=409, data="scores have already been imported for this event")

    file_name, headers = urllib.request.urlretrieve(document.file.url)
    wb = open_workbook(file_name)
    for s in wb.sheets():
        if is_hole_scores(s):
            score_type = get_score_type(s.name)
            course_name = get_course(s.name)
            course = [course for course in courses if course.name == course_name][0]

            for i in get_score_rows(s):
                try:
                    player_name = get_player_name(s.cell(i, 0).value, score_type)
                    player = player_map.get(player_name)
                    if player is None:
                        capture_message(f"player {player_name} not found when importing scores", level="error")
                        continue

                    score_map = get_scores(s, i)
                    if score_map is not None:
                        save_scores(event, course, player, score_map, score_type == "net")
                except:
                    capture_exception()

    return Response(status=204)


def save_scores(event, course, player, score_map, is_net):
    for hole in course.holes.all():
        event_score = EventScore(event=event, player=player, hole=hole, score=score_map[hole.hole_number],
                                 is_net=is_net)
        event_score.save()
