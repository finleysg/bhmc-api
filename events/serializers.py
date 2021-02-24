from courses.serializers import CourseSerializer
from .models import Event, EventFee, FeeType
from rest_framework import serializers


class FeeTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = FeeType
        fields = ("id", "name", "code", "restriction", )


class EventFeeSerializer(serializers.ModelSerializer):

    fee_type = FeeTypeSerializer(read_only=True)

    class Meta:
        model = EventFee
        fields = ("id", "event", "fee_type", "amount", "is_required", "display_order", )


class EventSerializer(serializers.ModelSerializer):

    courses = CourseSerializer(many=True, read_only=True)
    fees = EventFeeSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = ("id", "name", "rounds", "ghin_required", "total_groups",
                  "minimum_signup_group_size", "maximum_signup_group_size", "group_size", "start_type",
                  "can_choose", "registration_window", "external_url", "season",
                  "notes", "event_type", "skins_type", "season_points", "portal_url",
                  "start_date", "start_time", "registration_type", "signup_start", "signup_end", "payments_end",
                  "registration_maximum", "courses", "fees", )
