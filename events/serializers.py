from courses.serializers import CourseSerializer
from documents.serializers import DocumentSerializer
from register.serializers import RegistrationSlotSerializer
from .models import Event, EventFee, FeeType
from rest_framework import serializers


class FeeTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = FeeType
        fields = ("id", "name", )


class EventFeeSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventFee
        fields = ("id", "fee_type", "amount", "display_order", )


class EventSerializer(serializers.ModelSerializer):

    class Meta:
        model = Event
        fields = ("id", "name", "rounds", "ghin_required", "total_groups",
                  "minimum_signup_group_size", "maximum_signup_group_size", "group_size", "start_type",
                  "can_choose", "registration_window", "external_url",
                  "notes", "event_type", "skins_type", "season_points", "portal_url", "registration_maximum",
                  "start_date", "start_time", "registration_type", "signup_start", "signup_end", "payments_end",)


class EventDetailSerializer(serializers.ModelSerializer):

    courses = CourseSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    registrations = RegistrationSlotSerializer(many=True)
    fees = EventFeeSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = ("id", "name", "rounds", "ghin_required", "total_groups",
                  "minimum_signup_group_size", "maximum_signup_group_size", "group_size", "start_type",
                  "can_choose", "registration_window", "external_url",
                  "notes", "event_type", "skins_type", "season_points", "portal_url",
                  "start_date", "start_time", "registration_type", "signup_start", "signup_end", "payments_end",
                  "registration_maximum", "courses", "documents", "fees", "registrations",)


class SimpleEventSerializer(serializers.ModelSerializer):

    class Meta:
        model = Event
        fields = ("id", "name", "event_type", "start_date", "registration_type", )
