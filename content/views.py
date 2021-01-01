from rest_framework import viewsets

from .models import PageContent
from .serializers import PageContentSerializer


class PageContentViewSet(viewsets.ModelViewSet):

    serializer_class = PageContentSerializer

    def get_queryset(self):
        """ Optionally filter by year
        """
        queryset = PageContent.objects.all()
        key = self.request.query_params.get('key', None)

        if key is not None:
            queryset = queryset.filter(key=key)

        return queryset
