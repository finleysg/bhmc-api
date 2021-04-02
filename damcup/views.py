from rest_framework import viewsets

from damcup.models import DamCup, SeasonLongPoints
from damcup.serializers import DamCupSerializer, SeasonLongPointsSerializer


class DamCupViewSet(viewsets.ModelViewSet):
    serializer_class = DamCupSerializer
    queryset = DamCup.objects.all().order_by("-season")


class SeasonLongPointsViewSet(viewsets.ModelViewSet):
    serializer_class = SeasonLongPointsSerializer
    queryset = SeasonLongPoints.objects.all()
