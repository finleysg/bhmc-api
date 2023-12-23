from register.models import Player
from .models import *
from rest_framework import serializers


class DocumentEventSerializer(serializers.ModelSerializer):

    class Meta:
        model = Event
        fields = ("id", "name", "event_type", )


class PhotoTagSerializer(serializers.ModelSerializer):

    tag = serializers.CharField(source="tag.name")

    class Meta:
        model = PhotoTag
        fields = ("id", "tag", )


class DocumentSerializer(serializers.ModelSerializer):

    # event = DocumentEventSerializer(required=False)
    event_type = serializers.ReadOnlyField(source="event.event_type")
    created_by = serializers.CharField(read_only=True)
    last_update = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Document
        fields = ("id", "year", "title", "document_type", "file", "event", "event_type", "created_by", "last_update", )

    def validate(self, data):
        if self.context["request"].method == "PUT" and not data.get("file"):
            data.pop("file", None)
        elif self.context["request"].method == "POST" and not data.get("file"):
            raise Exception("A file is required.")
        return data

    def create(self, validated_data):
        event = validated_data.get("event", None)
        year = validated_data.pop("year")
        title = validated_data.pop("title")
        document_type = validated_data.pop("document_type")
        file = validated_data.pop("file")
        created_by = self.context["request"].user

        doc = Document(year=year, title=title, document_type=document_type, file=file, event=event,
                       created_by=created_by)
        doc.save()

        return doc

    def update(self, instance, validated_data):
        instance.event = validated_data.get("event", instance.event)
        instance.year = validated_data.get("year", instance.year)
        instance.title = validated_data.get("title", instance.title)
        instance.document_type = validated_data.get("document_type", instance.document_type)
        new_file = validated_data.get("file", None)
        if new_file is not None:
            instance.file = new_file

        instance.save()

        return instance


class PhotoSerializer(serializers.ModelSerializer):

    mobile_url = serializers.ReadOnlyField(source="mobile_image.url")
    web_url = serializers.ReadOnlyField(source="web_image.url")
    image_url = serializers.ReadOnlyField(source="raw_image.url")
    tags = PhotoTagSerializer(many=True, required=False)
    created_by = serializers.CharField(read_only=True)
    last_update = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Photo
        fields = ("id", "year", "caption", "mobile_url", "web_url", "image_url", "raw_image", "player_id",
                  "created_by", "last_update", "tags", )

    def create(self, validated_data):
        tags = self.context["request"].data.get("tags", None)
        year = validated_data.pop("year")
        player_id = validated_data.get("player_id", None)
        caption = validated_data.get("caption", None)
        raw_image = validated_data.pop("raw_image")
        created_by = self.context["request"].user

        pic = Photo(year=year, player_id=player_id, caption=caption, raw_image=raw_image, created_by=created_by)
        pic.save()

        if tags is not None:
            for tag in tags.split("|"):
                t, created = Tag.objects.get_or_create(name=tag)
                pt = PhotoTag(document=pic, tag=t)
                pt.save()

        if player_id is not None:
            player = Player.objects.get(pk=player_id)
            player.profile_picture = pic
            player.save()

        return pic

    def update(self, instance, validated_data):
        tags = self.context["request"].data.get("tags", None)

        instance.year = validated_data.get("year", instance.year)
        instance.caption = validated_data.get("caption", instance.caption)
        instance.save()

        # Delete and recreate tags.
        PhotoTag.objects.filter(document=instance).delete()
        if tags is not None:
            for tag in tags:
                t, created = Tag.objects.get_or_create(name=tag.get("name"))
                pt = PhotoTag(document=instance, tag=t)
                pt.save()

        return instance


class StaticDocumentSerializer(serializers.ModelSerializer):

    document = DocumentSerializer(read_only=True)

    class Meta:
        model = StaticDocument
        fields = ("id", "code", "document", )


class UpdatableStaticDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = StaticDocument
        fields = ("id", "code", "document", )
