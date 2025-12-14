from datetime import timedelta, date

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from courses.models import Course
from payments.utils import create_admin_payment
from register.models import RegistrationSlot, Player, Registration
from register.serializers import (
    RegistrationSlotSerializer,
    RegistrationSerializer,
    get_starting_wave,
    get_current_wave,
)
from .models import Event, FeeType, TournamentResult
from .serializers import (
    EventSerializer,
    FeeTypeSerializer,
    TournamentResultSerializer,
)


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer

    def get_queryset(self):
        """
        Return Event objects filtered by optional query parameters and ordered by start_date.

        Filters:
        - Uses `year` to match Event.start_date year.
        - Uses `month` to match Event.start_date month.
        - Uses `season` to match Event.season; a value of "0" is ignored.
        - Uses `active` as a number of days to compute an end datetime (now + active days), excludes events with registration_type == "N", and keeps events whose signup_start <= now and signup_end > computed end datetime.

        Returns:
            QuerySet: Event queryset filtered according to provided query parameters and ordered by `start_date`.
        """
        queryset = Event.objects.all()
        year = self.request.query_params.get("year", None)
        month = self.request.query_params.get("month", None)
        active = self.request.query_params.get("active", None)
        season = self.request.query_params.get("season", None)

        if year is not None:
            queryset = queryset.filter(start_date__year=year)
        if month is not None:
            queryset = queryset.filter(start_date__month=month)
        if season is not None and season != "0":
            queryset = queryset.filter(season=season)
        if active is not None:
            today = timezone.now()
            end_dt = today + timedelta(days=float(active))
            queryset = queryset.exclude(registration_type="N")
            queryset = queryset.filter(signup_start__lte=today, signup_end__gt=end_dt)

        return queryset.order_by("start_date")

    def list(self, request, *args, **kwargs):
        """
        Return a list of events using the view's queryset, applied request filters, and pagination.

        Returns:
            Response: DRF response containing the serialized page or list of Event objects.
        """
        return super().list(request, *args, **kwargs)

    @transaction.atomic()
    @action(detail=True, methods=["put"], permission_classes=[IsAdminUser])
    def append_teetime(self, request, pk):
        """
        Append a new tee time (registration slot) to the event identified by `pk` and return the updated event.

        If the event does not allow tee time selection, a ValidationError is raised.

        Parameters:
            pk (int): Primary key of the Event to modify.

        Returns:
            rest_framework.response.Response: Serialized Event data reflecting the updated total_groups.

        Raises:
            rest_framework.exceptions.ValidationError: If the event's `can_choose` is False.
        """
        event = Event.objects.get(pk=pk)
        if not event.can_choose:
            raise ValidationError("This event does not allow tee time selection")

        last_start = RegistrationSlot.objects.append_teetime(event)
        event.total_groups = last_start + 1
        event.save()

        serializer = EventSerializer(event, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def copy_event(self, request, pk):
        """
        Clone an existing Event to a new start date and return the cloned event's serialized data.

        Expects the query parameter `start_dt` in ISO format (YYYY-MM-DD). Retrieves the Event identified by `pk`, clones it with the provided start date, and returns the serialized clone.

        Parameters:
            request: DRF request; must include `start_dt` in `request.query_params`.
            pk: Primary key of the Event to clone.

        Returns:
            Serialized data of the newly cloned Event.
        """
        start_dt = request.query_params.get("start_dt")
        event = Event.objects.get(pk=pk)
        new_dt = date.fromisoformat(start_dt)
        copy = Event.objects.clone(event, new_dt)

        serializer = EventSerializer(copy, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def create_slots(self, request, pk):
        """
        Create registration slots for the specified event and return their serialized representation.

        Parameters:
            request: The HTTP request object (used to build serializer context).
            pk (int | str): Primary key of the event for which slots will be recreated.

        Returns:
            list: Serialized list of the created RegistrationSlot objects.
        """
        event = Event.objects.get(pk=pk)

        RegistrationSlot.objects.remove_slots_for_event(event)
        slots = RegistrationSlot.objects.create_slots_for_event(event)

        serializer = RegistrationSlotSerializer(
            slots, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @transaction.atomic()
    @action(detail=True, methods=["put"], permission_classes=[IsAdminUser])
    def add_player(self, request, pk):
        """
        Add a player to an event registration, create or assign the corresponding slot, and create any associated admin payment.

        Creates a Registration record for the player and, depending on the event's configuration, either assigns that registration to an existing RegistrationSlot (when the event allows choosing) or creates a new slot linked to the registration. Also creates an administrative payment record for the provided fees and returns the serialized registration.

        Parameters:
                pk (int | str): Primary key of the Event to which the player is being added.

        Returns:
                serialized_registration (dict): The Registration serialized by RegistrationSerializer.

        Raises:
                ValidationError: If no `player_id` is provided in the request data.
        """
        player_id = request.data.get("player_id", None)
        slot_id = request.data.get("slot_id", None)
        fee_ids = request.data.get("fees", [])
        is_money_owed = request.data.get("is_money_owed", False)
        notes = request.data.get("notes", "")

        if player_id is None:
            raise ValidationError("A player is required.")

        event = Event.objects.get(pk=pk)
        player = Player.objects.get(pk=player_id)
        user = User.objects.get(email=player.email)

        if event.can_choose:
            # a slot_id is expected for this kind of event
            slot = RegistrationSlot.objects.get(pk=slot_id)
            registration = Registration.objects.create(
                event=event,
                course=slot.hole.course,
                user=user,
                signed_up_by=request.user.get_full_name(),
                notes=notes,
            )
            slot.status = "R"
            slot.player = player
            slot.registration = registration
            slot.save()
        else:
            registration = Registration.objects.create(
                event=event,
                user=user,
                signed_up_by=request.user.get_full_name(),
                notes=notes,
            )
            slot = event.registrations.create(
                event=event,
                player=player,
                registration=registration,
                status="R",
                starting_order=0,
                slot=0,
            )

        create_admin_payment(event, slot, fee_ids, is_money_owed, user)

        serializer = RegistrationSerializer(registration, context={"request": request})
        return Response(serializer.data, status=200)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def available_groups(self, request, pk):
        """
        Return available tee times (TT) or starting holes (SG) for registration.

        Query params:
            course_id: Required - course to check
            player_count: Required - number of players needing slots
        """
        event = Event.objects.get(pk=pk)

        if not event.can_choose:
            raise ValidationError(
                "This event does not allow tee time/starting hole selection"
            )

        course_id = request.query_params.get("course_id")
        player_count = request.query_params.get("player_count")

        if not course_id:
            raise ValidationError("course_id is required")
        if not player_count:
            raise ValidationError("player_count is required")

        try:
            player_count = int(player_count)
            if player_count < 1:
                raise ValueError()
        except ValueError:
            raise ValidationError("player_count must be a positive integer")

        # Validate course association with event first
        if not event.courses.filter(pk=course_id).exists():
            raise ValidationError("Course is not associated with this event")

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise ValidationError("Invalid course_id")

        grouped = RegistrationSlot.objects.get_available_groups(
            event, course, player_count
        )

        # Filter by wave availability during priority signup
        current_wave = get_current_wave(event)
        result = []
        for (hole_number, starting_order), slots in grouped.items():
            group_wave = get_starting_wave(event, starting_order, hole_number)
            if group_wave <= current_wave:
                result.append(
                    {
                        "hole_number": hole_number,
                        "starting_order": starting_order,
                        "slots": RegistrationSlotSerializer(
                            slots, many=True, context={"request": request}
                        ).data,
                    }
                )

        # Sort by hole number then starting_order
        result.sort(
            key=lambda x: (
                x["hole_number"] if x["hole_number"] is not None else 0,
                x["starting_order"],
            )
        )

        return Response(result)


class FeeTypeViewSet(viewsets.ModelViewSet):
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer


class TournamentResultViewSet(viewsets.ModelViewSet):
    queryset = TournamentResult.objects.all()
    serializer_class = TournamentResultSerializer
