from rest_framework import serializers

from scores.models import EventScore
from register.serializers import SimplePlayerSerializer


class EventScoreSerializer(serializers.ModelSerializer):

    player = SimplePlayerSerializer()

    class Meta:
        model = EventScore
        fields = ("id", "event", "player", "hole", "score", "is_net",)
