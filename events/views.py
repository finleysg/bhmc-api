from datetime import timedelta, date

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

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

#    @method_decorator(cache_page(60 * 60 * 2))
#    def list(self, request, *args, **kwargs):
#        return super().list(request, *args, **kwargs)

#    @method_decorator(cache_page(60 * 30))
#    def retrieve(self, request, *args, **kwargs):
#        return super().retrieve(request, *args, **kwargs)


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

    serializer = EventSerializer(event, context={'request': request})
    return Response(serializer.data)


@api_view(['POST', ])
@permission_classes((permissions.IsAuthenticated,))
def copy_event(request, event_id):
    start_dt = request.query_params.get("start_dt")
    event = Event.objects.get(pk=event_id)
    new_dt = date.fromisoformat(start_dt)
    copy = Event.objects.clone(event, new_dt)

    serializer = EventSerializer(copy, context={'request': request})
    return Response(serializer.data)
