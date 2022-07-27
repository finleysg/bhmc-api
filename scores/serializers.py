from rest_framework import serializers

from courses.serializers import HoleSerializer
from scores.models import EventScore


class EventScoreSerializer(serializers.ModelSerializer):

    hole = HoleSerializer()

    class Meta:
        model = EventScore
        fields = ("id", "event", "player", "hole", "score", "is_net",)
