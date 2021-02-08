from django.conf import settings
from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from reporting.views import fetch_all_as_dictionary
from .models import Registration, RegistrationSlot, Player
from .serializers import (
    RegistrationSlotSerializer,
    RegistrationSerializer,
    PlayerSerializer,
    SimplePlayerSerializer,
    UpdatableRegistrationSlotSerializer,
)


@permission_classes((permissions.IsAuthenticated,))
class PlayerViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        email = self.request.query_params.get("email", None)
        if email is None and self.action == "list":
            return SimplePlayerSerializer
        return PlayerSerializer

    def get_queryset(self):
        queryset = Player.objects.all()
        email = self.request.query_params.get("email", None)

        if email is not None:
            queryset = queryset.filter(email=email)

        return queryset

    def get_serializer_context(self):
        context = super(PlayerViewSet, self).get_serializer_context()
        return context


class RegistrationViewSet(viewsets.ModelViewSet):

    serializer_class = RegistrationSerializer

    def get_queryset(self):
        queryset = Registration.objects.all()
        event_id = self.request.query_params.get("event_id", None)
        player_id = self.request.query_params.get("player_id", None)
        seasons = self.request.query_params.getlist("seasons", None)
        is_self = self.request.query_params.get("player", None)

        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if player_id is not None:
            queryset = queryset.filter(slots__player_id=player_id)
        if seasons:
            queryset = queryset.filter(event__season__in=seasons)
        if is_self == "me":
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        signed_up_by = self.request.user.get_full_name()
        serializer.save(signed_up_by=signed_up_by, **self.request.data)


class RegistrationSlotViewsSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == "partial_update":
            return UpdatableRegistrationSlotSerializer
        else:
            return RegistrationSlotSerializer

    def get_queryset(self):
        queryset = RegistrationSlot.objects.all()
        event_id = self.request.query_params.get("event_id", None)
        player_id = self.request.query_params.get("player_id", None)
        is_open = self.request.query_params.get("is_open", False)
        seasons = self.request.query_params.getlist("seasons", None)

        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if player_id is not None:
            queryset = queryset.filter(player=player_id)
        if seasons:
            queryset = queryset.filter(event__season__in=seasons)
        if is_open:
            queryset = queryset.filter(player__isnull=True)
        return queryset


@api_view(
    [
        "PUT",
    ]
)
@permission_classes((permissions.IsAuthenticated,))
def cancel_reserved_slots(request, registration_id):

    if registration_id == 0:
        raise ValidationError("Missing registration_id")

    Registration.objects.cancel_registration(registration_id)

    return Response(status=204)


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def player_search(request):
    event_id = request.query_params.get("event_id", 0)
    pattern = request.query_params.get("pattern", "")

    with connection.cursor() as cursor:
        cursor.callproc(
            "SearchPlayers",
            [
                pattern,
                event_id,
                settings.REGISTRATION_EVENT_ID,
                settings.PREVIOUS_REGISTRATION_EVENT_ID,
            ],
        )
        players = fetch_all_as_dictionary(cursor)

    return Response(players, status=200)


@api_view(
    [
        "GET",
    ]
)
@permission_classes((permissions.IsAuthenticated,))
def friends(request, player_id):
    event_id = request.query_params.get("event_id", 0)
    with connection.cursor() as cursor:
        cursor.callproc(
            "GetFriends",
            [
                player_id,
                event_id,
                settings.REGISTRATION_EVENT_ID,
                settings.PREVIOUS_REGISTRATION_EVENT_ID,
            ],
        )
        players = fetch_all_as_dictionary(cursor)

    return Response(players, status=200)


@api_view(
    [
        "POST",
    ]
)
@permission_classes((permissions.IsAuthenticated,))
def add_friend(request, player_id):
    player = Player.objects.get(email=request.user.email)
    friend = get_object_or_404(Player, pk=player_id)
    player.favorites.add(friend)
    player.save()
    serializer = PlayerSerializer(
        player.favorites, context={"request": request}, many=True
    )
    return Response(serializer.data)


@api_view(
    [
        "DELETE",
    ]
)
@permission_classes((permissions.IsAuthenticated,))
def remove_friend(request, player_id):
    player = Player.objects.get(email=request.user.email)
    friend = get_object_or_404(Player, pk=player_id)
    player.favorites.remove(friend)
    player.save()
    serializer = PlayerSerializer(
        player.favorites, context={"request": request}, many=True
    )
    return Response(serializer.data)
