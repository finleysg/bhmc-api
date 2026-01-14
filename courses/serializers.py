from .models import Course, Hole, Tee
from rest_framework import serializers


class HoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Hole
        fields = ("id", "course", "hole_number", "par", )


class TeeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tee
        fields = ("id", "course", "name", "gg_id", )


class CourseSerializer(serializers.ModelSerializer):
    holes = HoleSerializer(many=True, read_only=True)
    tees = TeeSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ("id", "name", "number_of_holes", "gg_id", "holes", "tees", )


class SimpleCourseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Course
        fields = ("id", "name", "number_of_holes", )
