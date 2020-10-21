from rest_framework import viewsets, permissions
from rest_framework.decorators import permission_classes, api_view
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

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
        """ Optionally filter by code
        """
        queryset = Document.objects.all()
        year = self.request.query_params.get('year', None)
        tournament = self.request.query_params.get('tournament', None)
        doc_types = self.request.query_params.get('type', None)
        tags = self.request.query_params.get('tags', None)

        if year is not None:
            queryset = queryset.filter(year=year)
        if tournament is not None:
            queryset = queryset.filter(tournament=tournament)
        if doc_types is not None:
            queryset = queryset.filter(document_type__icontains=doc_types)
        if tags is not None and tags != "":
            tag_set = tags.split(",")
            for tag in tag_set:
                queryset = queryset.filter(tags__tag__name__icontains=tag)

        return queryset


@permission_classes((permissions.IsAuthenticatedOrReadOnly,))
class PhotoViewSet(viewsets.ModelViewSet):
    serializer_class = PhotoSerializer
    # parser_classes = (MultiPartParser, FormParser, )

    def get_queryset(self):
        """ Optionally filter by code
        """
        queryset = Photo.objects.all()
        year = self.request.query_params.get('year', None)
        tournament = self.request.query_params.get('tournament', None)
        pic_type = self.request.query_params.get('type', None)

        if year is not None:
            queryset = queryset.filter(year=year)
        if tournament is not None:
            queryset = queryset.filter(tournament=tournament)
        if pic_type is not None:
            queryset = queryset.filter(photo_type=pic_type)

        return queryset


# @api_view(("GET",))
# @permission_classes((permissions.AllowAny,))
# def random_photo(request, tournament):
#     photo = Photo.objects.random(tournament)
#     serializer = PhotoSerializer(photo, context={"request": request})
#     return Response(serializer.data)
