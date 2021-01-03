from django.contrib.auth.models import User, Group
from rest_framework.exceptions import ValidationError

from register.models import Player
from register.serializers import SimplePlayerSerializer
from .models import BoardMember
from rest_framework import serializers


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("name",)


class UserDetailSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email",
                  "is_authenticated", "is_staff", "is_active", "groups", )
        read_only_fields = ("id", "is_authenticated", "is_staff", "is_active", )

    def update(self, instance, validated_data):
        player = Player.objects.get(email=instance.email)

        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.username = validated_data.get("username", instance.username)
        instance.email = validated_data.get("email", instance.email)
        instance.save()

        player.email = validated_data.get("email", instance.email)
        player.first_name = validated_data.get("first_name", instance.first_name)
        player.last_name = validated_data.get("last_name", instance.last_name)
        player.save()

        return instance


class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    ghin = serializers.CharField(max_length=8, required=False, allow_blank=True)
    password = serializers.CharField(max_length=128)

    class Meta:
        fields = ("email", "password", "first_name", "last_name", "ghin", )

    def create(self, validated_data):
        email = validated_data["email"]
        ghin = validated_data["ghin"].strip()
        exists = User.objects.filter(email=email).exists()
        if exists:
            raise ValidationError("user already exists")
        elif ghin is not None:
            if ghin == "":
                ghin = None
            else:
                exists = Player.objects.filter(ghin=ghin).exists()
                if exists:
                    raise ValidationError("ghin is already associated with a player")

        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            is_active=False,
        )

        Player.objects.create(first_name=user.first_name, last_name=user.last_name, email=user.email, ghin=ghin)

        return user


class BoardMemberSerializer(serializers.ModelSerializer):

    player = SimplePlayerSerializer()

    class Meta:
        model = BoardMember
        fields = ("player", "role", "term_expires", )
