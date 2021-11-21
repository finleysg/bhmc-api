from .models import PageContent, Tag
from rest_framework import serializers


class PageContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageContent
        fields = ("id", "key", "title", "content", )


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ("id", "name", )
