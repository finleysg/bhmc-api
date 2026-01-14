from rest_framework import serializers

from courses.serializers import HoleSerializer, CourseSerializer, SimpleCourseSerializer, TeeSerializer
from scores.models import EventScore, EventScoreCard


class EventScoreSerializer(serializers.ModelSerializer):

    hole = HoleSerializer()

    class Meta:
        model = EventScore
        fields = ("id", "hole", "score", "is_net",)


class EventScoreCardSerializer(serializers.ModelSerializer):

    scores = EventScoreSerializer(many=True)
    course = SimpleCourseSerializer()
    tee = TeeSerializer()

    class Meta:
        model = EventScoreCard
        fields = ("id", "event", "player", "course", "tee", "handicap_index", 
                  "course_handicap", "scores", )
