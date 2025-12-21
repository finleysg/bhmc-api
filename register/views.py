import csv

from collections import defaultdict
from decimal import Decimal

from django.db import connection, transaction, models
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from documents.models import Document
from events.models import Event
from payments.models import Payment, Refund
from payments.utils import get_start
from reporting.views import fetch_all_as_dictionary
from .models import (
    Registration,
    RegistrationSlot,
    Player,
    RegistrationFee,
    PlayerHandicap,
)
from .serializers import (
    RegistrationSlotSerializer,
    RegistrationSerializer,
    PlayerSerializer,
    SimplePlayerSerializer,
    UpdatableRegistrationSlotSerializer,
    RegistrationFeeSerializer,
    PlayerHandicapSerializer,
    validate_registration_is_open,
)
from .exceptions import RegistrationFullError, EventFullError, PlayerConflictError


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

    # @method_decorator(cache_page(60 * 60 * 4))
    # def list(self, request, *args, **kwargs):
    #     return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def search(self, request):
        player_id = request.query_params.get("player_id", 0)
        pattern = request.query_params.get("pattern", "")

        with connection.cursor() as cursor:
            cursor.callproc(
                "SearchPlayers",
                [
                    pattern,
                    player_id,
                ],
            )
            players = fetch_all_as_dictionary(cursor)

        return Response(players, status=200)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def friends(self, request, pk):
        player_id = pk
        with connection.cursor() as cursor:
            cursor.callproc(
                "GetFriends",
                [
                    player_id,
                ],
            )
            players = fetch_all_as_dictionary(cursor)

        return Response(players, status=200)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def add_friend(self, request, pk):
        player = Player.objects.get(email=request.user.email)
        friend = get_object_or_404(Player, pk=pk)
        player.favorites.add(friend)
        player.save()
        serializer = PlayerSerializer(
            player.favorites, context={"request": request}, many=True
        )
        return Response(serializer.data)

    @action(detail=True, methods=["delete"], permission_classes=[IsAuthenticated])
    def remove_friend(self, request, pk):
        player = Player.objects.get(email=request.user.email)
        friend = get_object_or_404(Player, pk=pk)
        player.favorites.remove(friend)
        player.save()
        serializer = PlayerSerializer(
            player.favorites, context={"request": request}, many=True
        )
        return Response(serializer.data)


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
            queryset = queryset.filter(slots__player_id=player_id).prefetch_related(
                "slots"
            )
        if seasons:
            queryset = queryset.filter(event__season__in=seasons)
        if is_self == "me":
            queryset = queryset.filter(user=self.request.user.id).prefetch_related(
                "slots"
            )

        return queryset

    @action(detail=True, methods=["put"], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk):
        if pk == 0:
            raise ValidationError("Missing registration_id")

        payment_id = int(request.query_params.get("payment_id", "0"))
        reason = request.query_params.get("reason", "user")  # user, timeout, navigation

        Registration.objects.cancel_registration(pk, payment_id, reason)

        return Response(status=204)

    @transaction.atomic()
    @action(detail=True, methods=["put"], permission_classes=[IsAuthenticated])
    def move(self, request, pk):
        """
        Move one or more players from specified source registration slots to corresponding destination slots within the same registration.
        
        This action reassigns player ownership and registration fees from each source slot to the matching destination slot (by index), updates slot statuses, optionally updates the registration's course when moving to a different tee, and appends a note to the registration describing the move.
        
        Parameters:
            request: DRF Request containing JSON keys:
                - "source_slots" (list[int]): ordered list of source RegistrationSlot IDs to move.
                - "destination_slots" (list[int]): ordered list of destination RegistrationSlot IDs to receive players; must match length of "source_slots" and share the same tee time/hole.
            pk (int): ID of the Registration being modified.
        
        Returns:
            dict: On success, a response payload with key "destination" containing the computed destination start information.
            Error behavior: Returns an HTTP 400 response if provided destination slots do not share the same tee time/hole.
        """
        source_slot_ids = request.data.get("source_slots", [])
        destination_slot_ids = request.data.get("destination_slots", [])

        registration = Registration.objects.filter(pk=pk).get()
        event = registration.event

        # Load all slots upfront
        source_slots = list(
            registration.slots.filter(pk__in=source_slot_ids).select_related(
                "player", "hole"
            )
        )
        destination_slots = list(
            RegistrationSlot.objects.filter(pk__in=destination_slot_ids).select_related(
                "hole", "hole__course"
            )
        )

        # Validate destination slots are same tee time/hole
        if len(destination_slots) > 1:
            first = destination_slots[0]
            for dest in destination_slots[1:]:
                if (
                    dest.hole_id != first.hole_id
                    or dest.starting_order != first.starting_order
                ):
                    return Response(
                        {"error": "Destination slots must be same tee time/hole"},
                        status=400,
                    )

        # Build note message before loop
        user_name = request.user.get_full_name()
        source_start = get_start(event, registration, source_slots[0])
        # Temporarily set registration course to destination for get_start
        dest_course = (
            destination_slots[0].hole.course if destination_slots[0].hole else None
        )
        original_course = registration.course
        registration.course = dest_course
        destination_start = get_start(event, registration, destination_slots[0])
        registration.course = original_course

        player_names = ", ".join(
            f"{s.player.first_name} {s.player.last_name}" for s in source_slots
        )
        message = f"\n{player_names} moved from {source_start} to {destination_start} by {user_name}"
        if registration.notes is None:
            registration.notes = message
        else:
            registration.notes = registration.notes + "\n" + message

        # Update course if different
        if dest_course and dest_course != original_course:
            registration.course = dest_course

        registration.save()

        # Create lookup for destination slots by index
        dest_by_id = {slot.id: slot for slot in destination_slots}
        source_by_id = {slot.id: slot for slot in source_slots}

        for index, slot_id in enumerate(source_slot_ids):
            source = source_by_id[slot_id]
            destination = dest_by_id[destination_slot_ids[index]]

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

        return Response({"destination": destination_start}, status=200)

    @transaction.atomic()
    @action(detail=True, methods=["delete"], permission_classes=[IsAuthenticated])
    def drop(self, request, pk):
        source_slot_ids = request.data.get("source_slots", [])
        registration = Registration.objects.filter(pk=pk).get()
        user_name = request.user.get_full_name()

        # 1. Load all source slots in one query
        source_slots_qs = (
            registration.slots.filter(pk__in=source_slot_ids)
            .select_related("player")
            .prefetch_related("fees", "fees__payment")
        )
        source_slots_list = list(source_slots_qs)

        # 2. Group fees by payment and issue refunds
        fees_by_payment = defaultdict(list)
        for slot in source_slots_list:
            for fee in slot.fees.all():
                if fee.is_paid and fee.payment and fee.payment.confirmed:
                    # Skip payments without a Stripe payment intent
                    if not fee.payment.payment_code.startswith("pi_"):
                        continue
                    fees_by_payment[fee.payment_id].append(fee)

        for payment_id, fees in fees_by_payment.items():
            payment = Payment.objects.get(pk=payment_id)
            refund_amount = sum(fee.amount for fee in fees)
            player_names = ", ".join(
                set(
                    f"{f.registration_slot.player.first_name} {f.registration_slot.player.last_name}"
                    for f in fees
                    if f.registration_slot and f.registration_slot.player
                )
            )
            notes = f"Dropped: {player_names} by {user_name}"
            # This will raise if Stripe fails, rolling back the transaction
            Refund.objects.create_refund(request.user, payment, refund_amount, notes)
            for fee in fees:
                fee.is_paid = False
                fee.save()

        # 3. Record action
        all_players = ", ".join(
            f"{s.player.first_name} {s.player.last_name}" for s in source_slots_list
        )
        message = f"{all_players} dropped from event by {user_name}"
        if registration.notes is None:
            registration.notes = message
        else:
            registration.notes = registration.notes + "\n" + message
        registration.save()

        # 4. Drop players
        for source in source_slots_list:
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

    @action(detail=False, methods=["put"], permission_classes=[IsAdminUser])
    def cancel_expired(self, request):
        cleaned = Registration.objects.clean_up_expired()
        return Response(
            "Cleaned up " + str(cleaned) + " registration slots", status=204
        )

    @action(detail=True, methods=["put"], permission_classes=[IsAdminUser])
    def move_registration(self, request, pk):
        target_event_id = request.data.get("target_event_id", None)
        if target_event_id is None:
            raise ValidationError("Missing target_event_id")

        registration = Registration.objects.get(pk=pk)
        source_event = registration.event
        target_event = Event.objects.get(pk=target_event_id)

        registration.event = target_event
        registration.slots.all().update(event=target_event)
        registration.notes = (
            f"Moved player(s) from {source_event.name} to {target_event.name}."
        )
        registration.save()

        # Find any related payments and move them to the target event
        payment_ids = []
        for slot in registration.slots.all():
            fees = slot.fees.all()
            for fee in fees:
                if fee.payment_id not in payment_ids:
                    payment_ids.append(fee.payment_id)
                # The fees will be orphaned if we don't assign them to the target event
                target_event_fee = get_target_event_fee(fee, source_event, target_event)
                fee.event_fee_id = target_event_fee.id
                fee.save()

        for payment_id in payment_ids:
            payment = Payment.objects.get(pk=payment_id)
            payment.event = target_event
            payment.save()

        return Response(status=204)

    @transaction.atomic()
    @action(detail=True, methods=["put"], permission_classes=[IsAuthenticated])
    def add_players(self, request, pk):
        """
        Add one or more players to an existing registration, reserving or creating slots and creating a pending payment for required fees.
        
        Adds the provided players to the registration identified by `pk` after validating the registration window, ensuring none of the players are already registered for the event, and enforcing event and group capacity rules. If the event allows choosing slots, available open slots in the registration's group are assigned; otherwise new registration slots are created. The registration expiry is extended by 10 minutes and a pending Payment is created with RegistrationFee records for all required event fees.
        
        Parameters:
            request: DRF request with JSON body containing a `players` list of objects with `id` keys.
            pk (int): Primary key of the Registration to update.
        
        Returns:
            Response containing:
              - `registration`: serialized registration data (updated slots and expiry)
              - `payment_id`: ID of the created Payment
        
        Raises:
            ValidationError: when no players are provided or one or more players are not found.
            PlayerConflictError: when one or more players are already registered (excluding status "A").
            RegistrationFullError: when the registration's group cannot accommodate the new players.
            EventFullError: when the event's overall capacity is exceeded.
        """
        from datetime import timedelta
        from django.utils import timezone as tz

        player_ids = [p["id"] for p in request.data.get("players", [])]
        if not player_ids:
            raise ValidationError("No players provided")

        registration = get_object_or_404(Registration, pk=pk)
        event = registration.event

        # Validate registration window
        validate_registration_is_open(event)

        # Validate players not already registered
        existing = (
            RegistrationSlot.objects.filter(event=event, player_id__in=player_ids)
            .exclude(status="A")
            .select_for_update()
            .values_list("player_id", flat=True)
        )
        if existing:
            raise PlayerConflictError()

        players = list(Player.objects.filter(id__in=player_ids))
        if len(players) != len(player_ids):
            raise ValidationError("One or more players not found")

        # Validate space and reserve slots
        if event.can_choose:
            # Find available slots in same group (hole/starting_order)
            first_slot = registration.slots.first()
            available = list(
                RegistrationSlot.objects.select_for_update()
                .filter(
                    event=event,
                    hole=first_slot.hole,
                    starting_order=first_slot.starting_order,
                    status="A",
                )
                .order_by("slot")[: len(players)]
            )
            if len(available) < len(players):
                raise RegistrationFullError()
            for i, slot in enumerate(available):
                slot.player = players[i]
                slot.status = "P"
                slot.registration = registration
                slot.save()
            new_slots = available
        else:
            # Check event capacity
            reserved_count = RegistrationSlot.objects.filter(
                event=event, status__in=["R", "P"]
            ).count()
            if (
                event.registration_maximum
                and reserved_count + len(players) > event.registration_maximum
            ):
                raise EventFullError()
            # Check registration group capacity
            current_slots = registration.slots.count()
            if current_slots + len(players) > event.maximum_signup_group_size:
                raise RegistrationFullError()
            # Create new slots
            max_slot = (
                registration.slots.aggregate(models.Max("slot"))["slot__max"] or -1
            )
            new_slots = []
            for i, player in enumerate(players):
                slot = RegistrationSlot.objects.create(
                    event=event,
                    registration=registration,
                    player=player,
                    status="P",
                    starting_order=0,
                    slot=max_slot + 1 + i,
                )
                new_slots.append(slot)

        # Reset expiry - give the user 10 minutes to complete payment
        registration.expires = tz.now() + timedelta(minutes=10)
        registration.save()

        # Create payment for required fees
        required_fees = list(event.fees.filter(is_required=True))
        payment = Payment.objects.create(
            event=event,
            user=request.user,
            payment_code="pending",
            notification_type="U",
        )
        for slot in new_slots:
            for fee in required_fees:
                RegistrationFee.objects.create(
                    event_fee=fee,
                    registration_slot=slot,
                    payment=payment,
                    amount=fee.amount,
                )

        serializer = RegistrationSerializer(registration, context={"request": request})
        return Response(
            {"registration": serializer.data, "payment_id": payment.id}, status=200
        )


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
        hole_id = self.request.query_params.get("hole_id", None)
        starting_order = self.request.query_params.get("starting_order", None)

        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if player_id is not None:
            queryset = queryset.filter(player=player_id)
        if seasons:
            queryset = queryset.filter(event__season__in=seasons)
        if is_open:
            queryset = queryset.filter(status="A")
        if hole_id is not None:
            queryset = queryset.filter(hole=hole_id)
        if starting_order is not None:
            queryset = queryset.filter(starting_order=starting_order)
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


@api_view(("POST",))
@permission_classes((permissions.AllowAny,))
def import_handicaps(request):
    season = request.data.get("season", 0)
    document_id = request.data.get("document_id", 0)

    document = Document.objects.get(pk=document_id)
    players = Player.objects.all()
    player_map = {player.ghin: player for player in players}

    with document.file.open("r") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        next(reader)  # skip header

        for row in reader:
            player = player_map.get(row[2])

            if player is None:
                continue

            player_hcp = PlayerHandicap(
                season=season, player=player, handicap=get_index(row[1])
            )
            player_hcp.save()

    return Response(status=204)


def get_index(cell):
    idx = str(cell)
    if idx.startswith("+"):
        return Decimal(idx[1:]) * -1
    else:
        return Decimal(idx)
    

def get_target_event_fee(source_fee, source_event, target_event):
    fee_type_id = source_event.fees.filter(pk=source_fee.event_fee_id)[0].fee_type_id
    return target_event.fees.filter(fee_type_id=fee_type_id)[0]
