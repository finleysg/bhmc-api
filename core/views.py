from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import SeasonSettings, BoardMember
from .serializers import SettingsSerializer, BoardMemberSerializer


@api_view(['GET', ])
def current_settings(request):
    cs = SeasonSettings.objects.current_settings()
    serializer = SettingsSerializer(cs, context={'request': request})
    return Response(serializer.data)


class BoardMemberViewSet(viewsets.ModelViewSet):
    serializer_class = BoardMemberSerializer
    queryset = BoardMember.objects.all()
