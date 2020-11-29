from datetime import timedelta, datetime

from django.utils import timezone
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from .models import Event, FeeType
from .serializers import EventSerializer, EventDetailSerializer, FeeTypeSerializer


class EventViewSet(viewsets.ModelViewSet):
    """ API endpoint to view Events
    """
    def get_serializer_class(self):
        if self.action == 'list':
            return EventSerializer
        else:
            return EventDetailSerializer

    def get_queryset(self):
        """ Optionally filter by year and month
        """
        queryset = Event.objects.all()
        year = self.request.query_params.get('year', None)
        month = self.request.query_params.get('month', None)
        active = self.request.query_params.get('active', None)

        if year is not None:
            queryset = queryset.filter(start_date__year=year)
        if month is not None:
            queryset = queryset.filter(start_date__month=month)
        if active is not None:
            today = timezone.now()
            end_dt = today + timedelta(days=float(active))
            queryset = queryset.exclude(registration_type='N')
            queryset = queryset.filter(signup_start__lte=today, signup_end__gt=end_dt)
        if self.action != 'list':
            queryset.prefetch_related('registrations', 'documents', 'fees', 'courses')

        return queryset.order_by('start_date')


class FeeTypeViewSet(viewsets.ModelViewSet):
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer


# TODO: move to patch or put
@api_view(['POST', ])
@permission_classes((permissions.IsAuthenticated,))
def update_portal(request, pk):

    event = get_object_or_404(Event, pk=pk)
    portal = request.data.get("portal", None)
    if portal is None:
        raise ValidationError("A portal url is required")

    event.portal_url = portal
    event.save()

    serializer = EventDetailSerializer(event, context={'request': request})
    return Response(serializer.data)
