from django.db.models import Sum
from rest_framework import viewsets

from .models import PlayerPoints
from .serializers import PlayerPointsSerializer, SeasonPointsSerializer


class PlayerPointsViewSet(viewsets.ModelViewSet):

    serializer_class = PlayerPointsSerializer

    def get_queryset(self):
        queryset = PlayerPoints.objects.all()
        season = self.request.query_params.get("season", None)
        event_id = self.request.query_params.get("event_id", None)
        player_id = self.request.query_params.get("player_id", None)

        if season is not None:
            queryset = queryset.filter(event__season=season)
        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if player_id is not None:
            queryset = queryset.filter(player=player_id)
        return queryset


class SeasonsPointsViewSet(viewsets.ModelViewSet):
    serializer_class = SeasonPointsSerializer

    def get_queryset(self):
        queryset = PlayerPoints.objects.all()
        season = self.request.query_params.get("season", None)
        if season is not None:
            queryset = queryset.filter(event__season=season)

        return queryset.annotate(
            total_points1=Sum("points1"),
            total_points2=Sum("points2")
        )
