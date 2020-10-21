from rest_framework import viewsets

from .models import Policy
from .serializers import PolicySerializer


class PolicyViewSet(viewsets.ModelViewSet):

    serializer_class = PolicySerializer
    queryset = Policy.objects.all()
