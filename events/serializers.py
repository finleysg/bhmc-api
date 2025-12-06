from rest_framework import serializers

from courses.serializers import CourseSerializer
from .models import Event, EventFee, FeeType, TournamentResult


class TournamentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TournamentResult
        fields = (
            "id",
            "tournament",
            "player",
            "team_id",
            "position",
            "score",
            "points",
            "is_net",
        )


class FeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeType
        fields = (
            "id",
            "name",
            "code",
            "restriction",
        )


class EventFeeSerializer(serializers.ModelSerializer):
    fee_type = FeeTypeSerializer(read_only=True)

    class Meta:
        model = EventFee
        fields = (
            "id",
            "event",
            "fee_type",
            "amount",
            "is_required",
            "display_order",
            "override_amount",
            "override_restriction",
        )


class EventSerializer(serializers.ModelSerializer):
    courses = CourseSerializer(many=True, read_only=True)
    fees = EventFeeSerializer(many=True, read_only=True)
    default_tag = serializers.CharField(required=False, source="default_tag.name")

    class Meta:
        model = Event
        fields = (
            "id",
            "name",
            "rounds",
            "ghin_required",
            "total_groups",
            "status",
            "minimum_signup_group_size",
            "maximum_signup_group_size",
            "group_size",
            "start_type",
            "can_choose",
            "registration_window",
            "external_url",
            "season",
            "tee_time_splits",
            "notes",
            "event_type",
            "skins_type",
            "season_points",
            "portal_url",
            "priority_signup_start",
            "start_date",
            "start_time",
            "registration_type",
            "signup_start",
            "signup_end",
            "signup_waves",
            "payments_end",
            "registration_maximum",
            "courses",
            "fees",
            "default_tag",
            "starter_time_interval",
            "team_size",
            "age_restriction",
            "age_restriction_type",
        )


class SimpleEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = (
            "id",
            "name",
            "event_type",
            "season",
            "start_date",
        )
