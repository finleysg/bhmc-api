from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, permissions, pagination
from rest_framework.decorators import permission_classes, api_view, action
from rest_framework.response import Response

from .serializers import *


class GalleryPagination(pagination.PageNumberPagination):
    page_size = 15
    page_size_query_param = "size"


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
    pagination_class = GalleryPagination

    def get_queryset(self):
        queryset = Photo.objects.all()
        year = self.request.query_params.get('year', None)
        player_id = self.request.query_params.get('player', None)
        tags = self.request.query_params.get('tags', None)

        if player_id is not None:
            queryset = queryset.filter(player_id=player_id)
        else:
            queryset = queryset.exclude(year=0)

        if year is not None:
            queryset = queryset.filter(year=year)
        if tags is not None and tags != "":
            tag_set = tags.split(",")
            for tag in tag_set:
                queryset = queryset.filter(tags__tag__name__icontains=tag)

        queryset = queryset.order_by("-year", "caption")
        return queryset

    @method_decorator(cache_page(timeout=60 * 60 * 4, cache="file"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def random(self, request):
        try:
            tag = request.query_params.get("tag", None)
            take = request.query_params.get("take", "1")
            photo = Photo.objects.random(tag, int(take))
            serializer = PhotoSerializer(photo, context={"request": request}, many=True)
            return Response(serializer.data)
        except:
            return Response(status=204)


@permission_classes((permissions.IsAuthenticatedOrReadOnly,))
class StaticDocumentViewSet(viewsets.ModelViewSet):

    def get_serializer_class(self):
        if self.action == "create" or self.action == "update":
            return UpdatableStaticDocumentSerializer
        else:
            return StaticDocumentSerializer

    def get_queryset(self):
        queryset = StaticDocument.objects.all()
        code = self.request.query_params.get('code', None)

        if code is not None:
            queryset = queryset.filter(code=code)

        return queryset

    @method_decorator(cache_page(60 * 60 * 2))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
