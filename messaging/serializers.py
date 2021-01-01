from .models import Announcement
from documents.serializers import DocumentSerializer
from rest_framework import serializers


class AnnouncementSerializer(serializers.ModelSerializer):

    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Announcement
        fields = ("id", "text", "starts", "expires", "event", "documents", "title", 'visibility', )
