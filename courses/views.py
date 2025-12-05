from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets

from .models import Course, Hole, Tee
from .serializers import CourseSerializer, HoleSerializer, TeeSerializer


class CourseViewSet(viewsets.ModelViewSet):

    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    @method_decorator(cache_page(60 * 60 * 24))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class HoleViewSet(viewsets.ModelViewSet):

    queryset = Hole.objects.all()
    serializer_class = HoleSerializer

    @method_decorator(cache_page(60 * 60 * 24))
    def list(self, request, *args, **kwargs):
        """
        Return a list response of serialized model instances for this viewset (honors the view's caching decorator).
        
        Returns:
            rest_framework.response.Response: Response containing the serialized queryset, respecting pagination and any applied filters.
        """
        return super().list(request, *args, **kwargs)


class TeeViewSet(viewsets.ModelViewSet):

    queryset = Tee.objects.all()
    serializer_class = TeeSerializer

    @method_decorator(cache_page(60 * 60 * 24))
    def list(self, request, *args, **kwargs):
        """
        Return a list response of serialized model instances for this viewset (honors the view's caching decorator).
        
        Returns:
            rest_framework.response.Response: Response containing the serialized queryset, respecting pagination and any applied filters.
        """
        return super().list(request, *args, **kwargs)