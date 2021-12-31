from rest_framework import viewsets

from .models import BoardMember, MajorChampion, Ace, LowScore, SeasonSettings
from .serializers import BoardMemberSerializer, AceSerializer, LowScoreSerializer, MajorChampionSerializer, \
    SeasonSettingsSerializer


class BoardMemberViewSet(viewsets.ModelViewSet):
    serializer_class = BoardMemberSerializer
    queryset = BoardMember.objects.all()


class MajorChampionViewSet(viewsets.ModelViewSet):
    serializer_class = MajorChampionSerializer

    def get_queryset(self):
        queryset = MajorChampion.objects.all()
        season = self.request.query_params.get("season", None)
        player_id = self.request.query_params.get("player_id", None)

        if season is not None:
            queryset = queryset.filter(season=season)
        if player_id is not None:
            queryset = queryset.filter(player=player_id)
        queryset = queryset.order_by("-season", "event_name", "flight")

        return queryset


class LowScoreViewSet(viewsets.ModelViewSet):
    serializer_class = LowScoreSerializer

    def get_queryset(self):
        queryset = LowScore.objects.all()
        season = self.request.query_params.get("season", None)

        if season is not None:
            queryset = queryset.filter(season=season)

        return queryset


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
