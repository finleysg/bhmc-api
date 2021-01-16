from rest_framework import serializers

from points.models import PlayerPoints
from register.serializers import SimplePlayerSerializer


class PlayerPointsSerializer(serializers.ModelSerializer):

    player = SimplePlayerSerializer()

    class Meta:
        model = PlayerPoints
        fields = ("id", "event", "player", "points1", "points2", "group")


class SeasonPointsSerializer(serializers.ModelSerializer):

    player = SimplePlayerSerializer()
    total_points1 = serializers.IntegerField()
    total_points2 = serializers.IntegerField()

    class Meta:
        model = PlayerPoints
        fields = ("season", "player", "total_points1", "total_points2")
