from rest_framework import viewsets

from .models import BoardMember
from .serializers import BoardMemberSerializer


class BoardMemberViewSet(viewsets.ModelViewSet):
    serializer_class = BoardMemberSerializer
    queryset = BoardMember.objects.all()
