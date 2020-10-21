from .models import Announcement
from events.serializers import SimpleEventSerializer
from documents.serializers import DocumentSerializer
from rest_framework import serializers


class AnnouncementSerializer(serializers.HyperlinkedModelSerializer):

    event = SimpleEventSerializer(required=False)
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Announcement
        fields = ("url", "id", "text", "starts", "expires", "event", "documents", "name", 'visibility', )


# class ContactSerializer(serializers.ModelSerializer):
#
#     class Meta:
#         model = Contact
#         fields = ("president_name", "president_phone", "vice_president_name", "vice_president_phone",
#                   "secretary_name", "secretary_phone", "treasurer_name", "treasurer_phone",
#                   "directors", "committees", "staff", )
