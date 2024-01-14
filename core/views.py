import os
from datetime import timedelta

import djoser.views
from djoser import utils
from djoser.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response

from bhmc.settings import is_development, to_bool
from .models import BoardMember, MajorChampion, Ace, LowScore, SeasonSettings
from .serializers import BoardMemberSerializer, AceSerializer, LowScoreSerializer, MajorChampionSerializer, \
    SeasonSettingsSerializer


is_localhost = to_bool(is_development)

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
            max_age = timedelta(days=30),
            secure = not is_localhost,
            httponly = True,
            samesite = "Lax",
            domain = "api.bhmc.org" if not is_localhost else None,
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
            domain = "api.bhmc.org" if not is_localhost else None,
        )
        response.status_code = status.HTTP_204_NO_CONTENT
        utils.logout_user(request)
        return response