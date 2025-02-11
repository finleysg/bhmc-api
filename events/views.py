from datetime import timedelta, date

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from register.models import RegistrationSlot
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

    @action(detail=True, methods=['put'])
    @transaction.atomic()
    def append_teetime(self, request, pk):
        event = Event.objects.get(pk=pk)
        if not event.can_choose:
            raise ValidationError("This event does not allow tee time selection")

        last_start = RegistrationSlot.objects.append_teetime(event)
        event.total_groups = last_start + 1
        event.save()

        serializer = EventSerializer(event, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def copy_event(self, request, pk):
        start_dt = request.query_params.get("start_dt")
        event = Event.objects.get(pk=pk)
        new_dt = date.fromisoformat(start_dt)
        copy = Event.objects.clone(event, new_dt)

        serializer = EventSerializer(copy, context={'request': request})
        return Response(serializer.data)


class FeeTypeViewSet(viewsets.ModelViewSet):
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer
