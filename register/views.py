from django.conf import settings
from django.db import connection, transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from events.models import Event
from reporting.views import fetch_all_as_dictionary
from .models import Registration, RegistrationSlot, Player, RegistrationFee
from .serializers import (
    RegistrationSlotSerializer,
    RegistrationSerializer,
    PlayerSerializer,
    SimplePlayerSerializer,
    UpdatableRegistrationSlotSerializer, RegistrationFeeSerializer,
)
from .utils import get_start


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
        ghin = self.request.query_params.get("ghin", None)

        if email is not None:
            queryset = queryset.filter(email=email)
        if ghin is not None:
            queryset = queryset.filter(ghin=ghin)

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
            queryset = queryset.filter(event=event_id).prefetch_related("slots")
        if player_id is not None:
            queryset = queryset.filter(slots__player_id=player_id).prefetch_related("slots")
        if seasons:
            queryset = queryset.filter(event__season__in=seasons)
        if is_self == "me":
            queryset = queryset.filter(user=self.request.user.id).prefetch_related("slots")

        return queryset

    # def perform_create(self, serializer):
    #     signed_up_by = self.request.user.get_full_name()
    #     serializer.save(signed_up_by=signed_up_by, **self.request.data)


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
            # queryset = queryset.filter(player__isnull=True)
            queryset = queryset.filter(status="A")
        return queryset


class RegistrationFeeViewsSet(viewsets.ModelViewSet):

    serializer_class = RegistrationFeeSerializer

    def get_queryset(self):
        queryset = RegistrationFee.objects.all()
        registration_id = self.request.query_params.get("registration_id", None)
        event_id = self.request.query_params.get("event_id", None)
        confirmed = self.request.query_params.get("confirmed", "false")

        if event_id is not None:
            queryset = queryset.filter(event_fee__event=event_id)
        if registration_id is not None:
            queryset = queryset.filter(registration_slot__registration=registration_id)
        if confirmed == "true":
            queryset = queryset.filter(payment__confirmed=1)
        return queryset


@api_view(["PUT", ])
@permission_classes((permissions.IsAuthenticated,))
def cancel_reserved_slots(request, registration_id):

    if registration_id == 0:
        raise ValidationError("Missing registration_id")

    payment_id = int(request.query_params.get("payment_id", "0"))
    Registration.objects.cancel_registration(registration_id, payment_id, True)

    return Response(status=204)


@api_view(['POST', ])
@permission_classes((permissions.IsAuthenticated,))
def create_event_slots(request, event_id):
    event = Event.objects.get(pk=event_id)

    RegistrationSlot.objects.remove_slots_for_event(event)
    slots = RegistrationSlot.objects.create_slots_for_event(event)

    serializer = RegistrationSlotSerializer(slots, many=True, context={'request': request})
    return Response(serializer.data)


# @api_view(["GET", ])
# @permission_classes((permissions.AllowAny,))
# def cancel_expired(request):
#     Registration.objects.clean_up_expired()
#
#     return Response(status=204)


@api_view(("GET",))
@permission_classes((permissions.IsAuthenticated,))
def player_search(request):
    event_id = request.query_params.get("event_id", 0)
    player_id = request.query_params.get("player_id", 0)
    pattern = request.query_params.get("pattern", "")

    with connection.cursor() as cursor:
        cursor.callproc(
            "SearchPlayers",
            [
                pattern,
                player_id,
                event_id,
                settings.REGISTRATION_EVENT_ID,
                settings.PREVIOUS_REGISTRATION_EVENT_ID,
            ],
        )
        players = fetch_all_as_dictionary(cursor)

    return Response(players, status=200)


@api_view(["GET", ])
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


@api_view(["POST", ])
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


@api_view(["DELETE", ])
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


@api_view(["PUT", ])
@transaction.atomic()
@permission_classes((permissions.IsAuthenticated,))
def move_players(request, registration_id):
    # TODO: validate that len(source) == len(destination)
    # TODO: validate that destination is open
    source_slots = request.data.get("source_slots", [])
    destination_slots = request.data.get("destination_slots", [])

    registration = Registration.objects.filter(pk=registration_id).get()

    for index, slot_id in enumerate(source_slots):
        source = registration.slots.get(pk=slot_id)
        destination = RegistrationSlot.objects.get(pk=destination_slots[index])

        user_name = request.user.get_full_name()
        player_name = "{} {}".format(source.player.first_name, source.player.last_name)
        source_start = get_start(source)
        destination_start = get_start(destination)
        message = "\n{} moved from {} to {} by {}".format(player_name, source_start, destination_start, user_name)
        if registration.notes is None:
            registration.notes = message
        else:
            registration.notes = registration.notes + "\n" + message
        registration.save()

        for fee in source.fees.all():
            fee.registration_slot = destination
            fee.save()

        player_ref = source.player
        source.registration = None
        source.player = None
        source.status = "A"
        source.save()

        destination.registration = registration
        destination.player = player_ref
        destination.status = "R"
        destination.save()

    return Response(status=204)


@api_view(["DELETE", ])
@transaction.atomic()
@permission_classes((permissions.IsAuthenticated,))
def drop_players(request, registration_id):
    source_slots = request.data.get("source_slots", [])
    registration = Registration.objects.filter(pk=registration_id).get()

    for slot_id in source_slots:
        source = registration.slots.get(pk=slot_id)

        user_name = request.user.get_full_name()
        player_name = "{} {}".format(source.player.first_name, source.player.last_name)
        message = "\n{} dropped from the event by {}".format(player_name, user_name)
        if registration.notes is None:
            registration.notes = message
        else:
            registration.notes = registration.notes + "\n" + message
        registration.save()

        for fee in source.fees.all():
            fee.registration_slot = None
            fee.save()

        if registration.event.can_choose:
            source.registration = None
            source.player = None
            source.status = "A"
            source.save()
        else:
            source.delete()

    return Response(status=204)
