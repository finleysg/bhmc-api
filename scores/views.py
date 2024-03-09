import structlog

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from courses.models import Course
from documents.models import Document
from documents.utils import open_xls_workbook
from events.models import Event
from register.models import Player
from scores.models import EventScore
from scores.serializers import EventScoreSerializer
from scores.utils import is_hole_scores, get_score_type, get_course, get_score_rows, get_player_name, get_scores


logger = structlog.get_logger()


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

        if season != "0":
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
    failures = []

    wb = open_xls_workbook(document)
    for sheet in wb.sheets():
        if is_hole_scores(sheet):
            score_type = get_score_type(sheet.name)
            course_name = get_course(sheet.name)
            course = [course for course in courses if course.name == course_name][0]

            for i in get_score_rows(sheet):
                try:
                    player_name = get_player_name(sheet.cell(i, 0).value, score_type)
                    player = player_map.get(player_name)
                    if player is None:
                        message = f"player {player_name} not found when importing {score_type} scores"
                        logger.warn(message)
                        failures.append(message)
                        continue

                    score_map = get_scores(sheet, i)
                    if score_map is not None:
                        save_scores(event, course, player, score_map, score_type == "net")
                except Exception as e:
                    failures.append(str(e))
                    logger.error(e)


    # do not keep the data file
    document.file.delete()
    document.delete()

    return Response(data=failures, status=200)


def save_scores(event, course, player, score_map, is_net):
    scores = EventScore.objects.filter(event=event, player=player, is_net=is_net)
    if len(scores) == 0:
        new_scores = []
        for hole in course.holes.all():
            new_scores.append(EventScore(event=event, player=player, hole=hole, score=score_map[hole.hole_number], is_net=is_net))
        EventScore.objects.bulk_create(new_scores)
    else:
        for hole in course.holes.all():
            score = next(
                (obj for obj in scores if obj.hole.hole_number == hole.hole_number),
                None
            )
            score.score = score_map[hole.hole_number]
        EventScore.objects.bulk_update(scores, ["score"])