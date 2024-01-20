import csv

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection, transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from documents.models import Document
from events.models import Event
from payments.utils import create_admin_payment
from reporting.views import fetch_all_as_dictionary
from .models import Registration, RegistrationSlot, Player, RegistrationFee, PlayerHandicap
from .serializers import (
    RegistrationSlotSerializer,
    RegistrationSerializer,
    PlayerSerializer,
    SimplePlayerSerializer,
    UpdatableRegistrationSlotSerializer, RegistrationFeeSerializer, PlayerHandicapSerializer,
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
        members_only = self.request.query_params.get("members-only", None)

        if email is not None:
            queryset = queryset.filter(email=email)
        if ghin is not None:
            queryset = queryset.filter(ghin=ghin)
        if members_only and members_only == "true":
            queryset = queryset.filter(is_member=True)

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


class PlayerHandicapViewsSet(viewsets.ModelViewSet):

    serializer_class = PlayerHandicapSerializer

    def get_queryset(self):
        queryset = PlayerHandicap.objects.all()
        season = self.request.query_params.get("season", None)

        if season is not None:
            queryset = queryset.filter(season=season)
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
@permission_classes((permissions.IsAdminUser,))
def create_event_slots(request, event_id):
    event = Event.objects.get(pk=event_id)

    RegistrationSlot.objects.remove_slots_for_event(event)
    slots = RegistrationSlot.objects.create_slots_for_event(event)

    serializer = RegistrationSlotSerializer(slots, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(["PUT", ])
@permission_classes((permissions.IsAdminUser,))
def cancel_expired(request):
    cleaned = Registration.objects.clean_up_expired()

    return Response("Cleaned up " + str(cleaned) + " registration slots", status=204)


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
            ],
        )
        players = fetch_all_as_dictionary(cursor)

    return Response(players, status=200)


@api_view(["GET", ])
@permission_classes((permissions.IsAuthenticated,))
def friends(request, player_id):
    with connection.cursor() as cursor:
        cursor.callproc(
            "GetFriends",
            [
                player_id,
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
@permission_classes((permissions.IsAdminUser,))
def add_player(request, event_id):
    player_id = request.data.get("player_id", None)
    slot_id = request.data.get("slot_id", None)
    fee_ids = request.data.get("fees", [])
    is_money_owed = request.data.get("is_money_owed", False)
    notes = request.data.get("notes", "")

    if player_id is None:
        raise ValidationError("A player is required.")

    event = Event.objects.get(pk=event_id)
    player = Player.objects.get(pk=player_id)
    user = User.objects.get(email=player.email)

    if event.can_choose:
        # a slot_id is expected for this kind of event
        slot = RegistrationSlot.objects.get(pk=slot_id)
        registration = Registration.objects.create(event=event, course=slot.hole.course, user=user,
                                                   signed_up_by=request.user.get_full_name(), notes=notes)
        slot.status = "R"
        slot.player = player
        slot.registration = registration
        slot.save()
    else:
        registration = Registration.objects.create(event=event, user=user, signed_up_by=request.user.get_full_name(),
                                                   notes=notes)
        slot = event.registrations.create(event=event, player=player, registration=registration, status="R",
                                          starting_order=0, slot=0)

    create_admin_payment(event, slot, fee_ids, is_money_owed, user)

    serializer = RegistrationSerializer(registration, context={"request": request})
    return Response(serializer.data, status=200)


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


@api_view(("POST",))
@permission_classes((permissions.AllowAny,))
def import_handicaps(request):

    season = request.data.get("season", 0)
    document_id = request.data.get("document_id", 0)

    document = Document.objects.get(pk=document_id)
    players = Player.objects.all()
    player_map = {player.ghin: player for player in players}

    with document.file.open("r") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        next(reader)  # skip header

        for row in reader:
            player = player_map.get(row[2])

            if player is None:
                continue

            player_hcp = PlayerHandicap(season=season, player=player, handicap=get_index(row[1]))
            player_hcp.save()

    return Response(status=204)


def get_index(cell):
    idx = str(cell)
    if idx.startswith("+"):
        return Decimal(idx[1:]) * -1
    else:
        return Decimal(idx)
