from rest_framework import viewsets

from .models import Course, Hole
from .serializers import CourseSerializer, HoleSerializer


class CourseViewSet(viewsets.ModelViewSet):

    queryset = Course.objects.all()
    serializer_class = CourseSerializer


class HoleViewSet(viewsets.ModelViewSet):

    queryset = Hole.objects.all()
    serializer_class = HoleSerializer
