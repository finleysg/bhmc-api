from datetime import timedelta, date

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from payments.utils import create_admin_payment
from register.models import RegistrationSlot, Player, Registration
from register.serializers import RegistrationSlotSerializer, RegistrationSerializer
from .models import Event, FeeType
from .serializers import EventSerializer, FeeTypeSerializer


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer

    def get_queryset(self):
        """ Optionally filter by year and month
        """
        queryset = Event.objects.all()
        year = self.request.query_params.get('year', None)
        month = self.request.query_params.get('month', None)
        active = self.request.query_params.get('active', None)
        season = self.request.query_params.get('season', None)

        if year is not None:
            queryset = queryset.filter(start_date__year=year)
        if month is not None:
            queryset = queryset.filter(start_date__month=month)
        if season is not None and season != '0':
            queryset = queryset.filter(season=season)
        if active is not None:
            today = timezone.now()
            end_dt = today + timedelta(days=float(active))
            queryset = queryset.exclude(registration_type='N')
            queryset = queryset.filter(signup_start__lte=today, signup_end__gt=end_dt)

        return queryset.order_by('start_date')

    @transaction.atomic()
    @action(detail=True, methods=['put'], permission_classes=[IsAdminUser])
    def append_teetime(self, request, pk):
        event = Event.objects.get(pk=pk)
        if not event.can_choose:
            raise ValidationError("This event does not allow tee time selection")

        last_start = RegistrationSlot.objects.append_teetime(event)
        event.total_groups = last_start + 1
        event.save()

        serializer = EventSerializer(event, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def copy_event(self, request, pk):
        start_dt = request.query_params.get("start_dt")
        event = Event.objects.get(pk=pk)
        new_dt = date.fromisoformat(start_dt)
        copy = Event.objects.clone(event, new_dt)

        serializer = EventSerializer(copy, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def create_slots(self, request, pk):
        event = Event.objects.get(pk=pk)

        RegistrationSlot.objects.remove_slots_for_event(event)
        slots = RegistrationSlot.objects.create_slots_for_event(event)

        serializer = RegistrationSlotSerializer(slots, many=True, context={'request': request})
        return Response(serializer.data)

    @transaction.atomic()
    @action(detail=True, methods=['put'], permission_classes=[IsAdminUser])
    def add_player(self, request, pk):
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


class FeeTypeViewSet(viewsets.ModelViewSet):
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer
