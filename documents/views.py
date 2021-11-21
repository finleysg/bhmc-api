from rest_framework import viewsets, permissions
from rest_framework.decorators import permission_classes, api_view
from rest_framework.response import Response

from .serializers import *


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

        if year is None:
            queryset = queryset.order_by("-year")

        return queryset


@permission_classes((permissions.IsAuthenticatedOrReadOnly,))
class PhotoViewSet(viewsets.ModelViewSet):
    serializer_class = PhotoSerializer

    def get_queryset(self):
        queryset = Photo.objects.all()
        year = self.request.query_params.get('year', None)
        player_id = self.request.query_params.get('player', None)
        tags = self.request.query_params.get('tags', None)

        if year is not None:
            queryset = queryset.filter(year=year)
        if player_id is not None:
            queryset = queryset.filter(player_id=player_id)
        if tags is not None and tags != "":
            tag_set = tags.split(",")
            for tag in tag_set:
                queryset = queryset.filter(tags__tag__name__icontains=tag)

        return queryset


@permission_classes((permissions.IsAuthenticatedOrReadOnly,))
class StaticDocumentViewSet(viewsets.ModelViewSet):

    def get_serializer_class(self):
        if self.action == "create":
            return UpdatableStaticDocumentSerializer
        else:
            return StaticDocumentSerializer

    def get_queryset(self):
        queryset = StaticDocument.objects.all()
        code = self.request.query_params.get('code', None)

        if code is not None:
            queryset = queryset.filter(code=code)

        return queryset


@api_view(("GET",))
@permission_classes((permissions.AllowAny,))
def random_photos(request):
    tag = request.query_params.get("tag", None)
    take = request.query_params.get("take", "1")
    photo = Photo.objects.random(tag, int(take))
    serializer = PhotoSerializer(photo, context={"request": request}, many=True)
    return Response(serializer.data)
