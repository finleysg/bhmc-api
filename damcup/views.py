import csv
from decimal import Decimal

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from sentry_sdk import capture_exception, capture_message

from damcup.models import DamCup, SeasonLongPoints
from damcup.serializers import DamCupSerializer, SeasonLongPointsSerializer
from documents.models import Document
from events.models import Event
from register.models import Player


class DamCupViewSet(viewsets.ModelViewSet):
    serializer_class = DamCupSerializer
    queryset = DamCup.objects.all().order_by("-season")


class SeasonLongPointsViewSet(viewsets.ModelViewSet):
    serializer_class = SeasonLongPointsSerializer

    def get_queryset(self):
        queryset = SeasonLongPoints.objects.all()
        event_id = self.request.query_params.get("event_id", None)
        document_id = self.request.query_params.get("document_id", None)

        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if document_id is not None:
            queryset = queryset.filter(source=document_id)
            queryset = queryset.order_by("-gross_points")
        return queryset.select_related("player")


@api_view(("POST",))
@permission_classes((permissions.IsAuthenticated,))
def import_points(request):

    event_id = request.data.get("event_id", 0)
    document_id = request.data.get("document_id", 0)

    event = Event.objects.get(pk=event_id)
    document = Document.objects.get(pk=document_id)

    # with open(document.file.read(), newline='') as csvfile:
    with document.file.open("r") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        next(reader)  # skip header

        for row in reader:
            gross_points = row[3]
            net_points = row[4]
            if gross_points is not None and gross_points != "":
                player = Player.objects.filter(ghin=row[0]).first()
                if player is None:
                    capture_message("ghin {} not found when importing points".format(row[0]))
                else:
                    points = SeasonLongPoints.objects.filter(event=event, player=player).first()
                    if points is None:
                        points = SeasonLongPoints(source=document, event=event, player=player,
                                                  gross_points=Decimal(gross_points), net_points=Decimal(net_points))
                    else:
                        points.gross_points = Decimal(gross_points)
                        points.net_points = Decimal(net_points)

                    points.save()

    return Response(status=204)
