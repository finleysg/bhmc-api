from rest_framework import serializers

from courses.serializers import HoleSerializer, CourseSerializer, TeeSerializer
from scores.models import EventScore


class EventScoreSerializer(serializers.ModelSerializer):

    hole = HoleSerializer()
    course = CourseSerializer(read_only=True)
    tee = TeeSerializer(read_only=True)

    class Meta:
        model = EventScore
        fields = ("id", "event", "player", "course", "tee", "hole", "score", "is_net",)
