import logging
from datetime import timedelta, datetime

import structlog
from django.db import IntegrityError
from django.utils import timezone as tz
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth.models import User

from courses.models import Course
from documents.serializers import PhotoSerializer
from events.serializers import EventFeeSerializer
from payments.utils import get_offset, DEFAULT_INTERVAL
from .exceptions import (
    EventFullError,
    EventRegistrationNotOpenError,
    CourseRequiredError,
    PlayerConflictError, EventRegistrationWaveError,
)
from .models import Player, Registration, RegistrationSlot, RegistrationFee, PlayerHandicap

logger = structlog.getLogger(__name__)


class SimplePlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "ghin",
            "tee",
            "birth_date",
            "is_member",
            "last_season",
        )


class PlayerSerializer(serializers.ModelSerializer):

    profile_picture = PhotoSerializer(read_only=True)

    class Meta:
        model = Player
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "ghin",
            "tee",
            "birth_date",
            "save_last_card",
            "profile_picture",
            "is_member",
            "last_season",
        )

    def create(self, validated_data):
        ghin = validated_data.pop("ghin", None)
        if ghin is not None:
            if ghin.strip() == "":
                ghin = None

        player = Player(ghin=ghin, **validated_data)
        player.save()

        return player

    def update(self, instance, validated_data):
        user = User.objects.get(email=instance.email)
        ghin = validated_data["ghin"]
        if ghin is not None:
            if ghin.strip() == "":
                ghin = None
            else:
                exists = (
                    Player.objects.filter(ghin=ghin).exclude(email=user.email).exists()
                )
                if exists:
                    raise ValidationError("ghin is already associated with a player")

        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.email = validated_data.get("email", instance.email)
        instance.phone_number = validated_data.get(
            "phone_number", instance.phone_number
        )
        instance.ghin = ghin
        instance.tee = validated_data.get("tee", instance.tee)
        instance.birth_date = validated_data.get("birth_date", instance.birth_date)
        instance.save_last_card = validated_data.get(
            "save_last_card", instance.save_last_card
        )
        instance.profile_picture = validated_data.get(
            "profile_picture", instance.profile_picture
        )
        instance.save()

        user.email = validated_data.get("email", instance.email)
        user.first_name = validated_data.get("first_name", instance.first_name)
        user.last_name = validated_data.get("last_name", instance.last_name)
        user.save()

        return instance

    def validate(self, attrs):
        view = self.context.get("view")
        if view.action == "update":
            user = self.context.get("request").user
            player = Player.objects.get(email=user.email)
            if player.id != view.request.data["id"]:
                # A player can only update self through the api
                raise ValidationError("To update a player, use the admin website.")

        return attrs


class RegistrationFeeSerializer(serializers.ModelSerializer):

    class Meta:
        model = RegistrationFee
        fields = (
            "id",
            "event_fee",
            "registration_slot",
            "payment",
            "is_paid",
            "amount",
        )


class RegistrationSlotSerializer(serializers.ModelSerializer):
    # We need to identify elements in the list using their primary key,
    # so use a writable field here, rather than the default which would be read-only.
    id = serializers.IntegerField()
    player = SimplePlayerSerializer(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = RegistrationSlot
        fields = (
            "id",
            "event",
            "hole",
            "registration",
            "starting_order",
            "slot",
            "status",
            "player",
        )
        order_by = (
            "hole",
            "starting_order",
        )


class UpdatableRegistrationSlotSerializer(serializers.ModelSerializer):
    # We need to identify elements in the list using their primary key,
    # so use a writable field here, rather than the default which would be read-only.
    id = serializers.IntegerField()

    class Meta:
        model = RegistrationSlot
        fields = (
            "id",
            "event",
            "hole",
            "registration",
            "starting_order",
            "slot",
            "status",
            "player",
        )

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except Exception as ex:
            if isinstance(ex, IntegrityError):
                raise PlayerConflictError()


class PaymentDetailSerializer(serializers.ModelSerializer):

    event_fee = EventFeeSerializer()
    registration_slot = RegistrationSlotSerializer()

    class Meta:
        model = RegistrationFee
        fields = (
            "id",
            "event_fee",
            "registration_slot",
        )


class RegistrationSerializer(serializers.ModelSerializer):

    # course = CourseSerializer()
    slots = RegistrationSlotSerializer(many=True)

    class Meta:
        model = Registration
        fields = (
            "id",
            "event",
            "course",
            "signed_up_by",
            "starting_hole",
            "starting_order",
            "notes",
            "slots",
            "expires",
            "created_date",
        )

    def create(self, validated_data):
        user = None
        signed_up_by = None

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user

        signed_up_by = validated_data.get("signed_up_by", None)
        is_admin = signed_up_by == "admin"

        course = validated_data.pop("course", None)
        slots = validated_data.pop("slots")
        event = validated_data.pop("event")

        player = None if is_admin else Player.objects.get(email=user.email)
        signed_up_by = user.get_full_name()

        if not is_admin:
            logger.info("Creating a registration")
            validate_registration_is_open(event)
            if event.can_choose and len(slots) > 0:
                validate_wave_is_available(event, slots[0].get("starting_order"))
            validate_event_is_not_full(event)

        return Registration.objects.create_and_reserve(user, player, event, course, slots, signed_up_by)

    def update(self, instance, validated_data):
        logger.info("Updating a registration")
        instance.notes = validated_data.get("notes", instance.notes)
        instance.save()

        return instance


class PlayerHandicapSerializer(serializers.ModelSerializer):

    class Meta:
        model = PlayerHandicap
        fields = (
            "season",
            "player",
            "handicap",
        )


def validate_event_is_not_full(event):
    if event.registration_maximum is not None and event.registration_maximum != 0:
        registrations = (
            RegistrationSlot.objects.filter(event=event).filter(status="R").count()
        )
        if registrations >= event.registration_maximum:
            raise EventFullError()


def validate_registration_is_open(event):
    if event.registration_window != "registration" and event.registration_window != "priority":
        raise EventRegistrationNotOpenError()


def validate_course_for_event(event, course_id):
    course = None  # not required if event != "can_choose"
    if event.can_choose:
        if course_id is None:
            raise CourseRequiredError()
        course = Course.objects.get(pk=course_id)

    return course


def validate_wave_is_available(event, starting_order):
    if event.registration_window == "priority" and event.can_choose:
        this_wave = get_starting_wave(event.tee_time_splits, starting_order) # 1-4: wave based on the given starting order
        current_wave = get_current_wave() # 1-4: wave based on the current time
        if this_wave > current_wave:
            raise EventRegistrationWaveError(this_wave)


def get_current_wave():
    current_time = datetime.now()
    if current_time.minute < 15:
        return 1
    elif current_time.minute < 30:
        return 2
    elif current_time.minute < 45:
        return 3
    else:
        return 4


def get_starting_wave(tee_time_splits, starting_order):
    intervals = [int(i) for i in tee_time_splits.split(',')] if tee_time_splits is not None else [DEFAULT_INTERVAL]
    delta = get_offset(int(starting_order), intervals)
    if delta < 60:
        return 1
    elif delta < 120:
        return 2
    elif delta < 180:
        return 3
    else:
        return 4
