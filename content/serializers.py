from .models import PageContent
from rest_framework import serializers


class PageContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageContent
        fields = ("id", "key", "title", "content", )
