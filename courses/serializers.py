from .models import Course, Hole
from rest_framework import serializers


class HoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Hole
        fields = ("id", "course", "hole_number", "par", )


class CourseSerializer(serializers.ModelSerializer):
    holes = HoleSerializer(many=True)

    class Meta:
        model = Course
        fields = ("id", "name", "number_of_holes", "holes", )
