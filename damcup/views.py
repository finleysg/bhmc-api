from rest_framework import viewsets

from damcup.models import DamCup
from damcup.serializers import DamCupSerializer


class DamCupViewSet(viewsets.ModelViewSet):
    serializer_class = DamCupSerializer
    queryset = DamCup.objects.all().order_by("-season")
