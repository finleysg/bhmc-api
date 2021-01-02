from rest_framework import viewsets, permissions
from rest_framework.decorators import permission_classes

from .serializers import *


@permission_classes((permissions.IsAuthenticatedOrReadOnly,))
class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer

    def get_queryset(self):
        queryset = Tag.objects.all()
        pattern = self.request.query_params.get('pattern', None)

        if pattern is not None:
            queryset = queryset.filter(name__icontains=pattern)

        return queryset


@permission_classes((permissions.IsAuthenticatedOrReadOnly,))
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        queryset = Document.objects.all()
        year = self.request.query_params.get('year', None)
        event_id = self.request.query_params.get('event_id', None)
        doc_type = self.request.query_params.get('type', None)

        if year is not None:
            queryset = queryset.filter(year=year)
        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if doc_type is not None:
            queryset = queryset.filter(document_type=doc_type)

        return queryset


@permission_classes((permissions.IsAuthenticatedOrReadOnly,))
class PhotoViewSet(viewsets.ModelViewSet):
    serializer_class = PhotoSerializer

    def get_queryset(self):
        queryset = Photo.objects.all()
        year = self.request.query_params.get('year', None)
        player_id = self.request.query_params.get('player', None)

        if year is not None:
            queryset = queryset.filter(year=year)
        if player_id is not None:
            queryset = queryset.filter(player_id=player_id)

        return queryset


# @api_view(("GET",))
# @permission_classes((permissions.AllowAny,))
# def random_photo(request, tournament):
#     photo = Photo.objects.random(tournament)
#     serializer = PhotoSerializer(photo, context={"request": request})
#     return Response(serializer.data)
