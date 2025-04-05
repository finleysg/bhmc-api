from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, permissions
from rest_framework.decorators import permission_classes

from .models import PageContent, Tag
from .serializers import PageContentSerializer, TagSerializer


class PageContentViewSet(viewsets.ModelViewSet):

    serializer_class = PageContentSerializer

    def get_queryset(self):
        queryset = PageContent.objects.all()
        key = self.request.query_params.get('key', None)

        if key is not None:
            queryset = queryset.filter(key=key)

        return queryset

    @method_decorator(cache_page(60 * 60 * 4))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@permission_classes((permissions.IsAuthenticatedOrReadOnly,))
class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer

    def get_queryset(self):
        queryset = Tag.objects.all()
        pattern = self.request.query_params.get('pattern', None)

        if pattern is not None:
            queryset = queryset.filter(name__icontains=pattern)

        return queryset
