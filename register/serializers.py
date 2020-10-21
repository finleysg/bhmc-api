from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from courses.models import Course
from events.models import Event
from .exceptions import EventFullError, EventRegistrationNotOpenError, CourseRequiredError
from .models import Player, Registration, RegistrationSlot, RegistrationFee


class PlayerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Player
        fields = ("id", "first_name", "last_name", "email", "phone_number", "ghin", "tee")

    def validate(self, attrs):
        view = self.context.get("view")
        if view.action == "update":
            user = self.context.get('request').user
            player = Player.objects.get(email=user.email)
            if player.id != view.request.data["id"]:
                # A player can only update self through the api
                raise ValidationError("To update a player, use the admin website.")

        return attrs


class RegistrationFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationFee
        fields = ("id", "event_fee", "registration_slot", "payment", )


class RegistrationSlotSerializer(serializers.ModelSerializer):
    # We need to identify elements in the list using their primary key,
    # so use a writable field here, rather than the default which would be read-only.
    id = serializers.IntegerField()

    class Meta:
        model = RegistrationSlot
        fields = ("id", "event", "hole", "registration", "starting_order", "slot", "status", "player")
        order_by = ("hole", "starting_order", )


class RegistrationSerializer(serializers.ModelSerializer):

    # course = CourseSerializer()
    slots = RegistrationSlotSerializer(many=True)

    class Meta:
        model = Registration
        fields = ("id", "event", "course", "signed_up_by", "starting_hole", "starting_order", "notes",
                  "slots", "expires")

    def create(self, validated_data):
        slots = validated_data.pop("slots")

        event_id = validated_data.pop("event")
        event = Event.objects.get(pk=event_id)

        # TODO: other validations?
        validate_registration_is_open(event)
        validate_event_is_not_full(event)
        course = validate_course_for_event(event, validated_data.pop("course", None))

        return Registration.objects.create_and_reserve(event, course, slots, **validated_data)

    def update(self, instance, validated_data):
        slots = validated_data.pop("slots")
        for slot in slots:
            player = slot.pop('player')
            if player is not None:
                RegistrationSlot.objects \
                    .select_for_update() \
                    .filter(pk=slot["id"]) \
                    .update(**{"player": player})
            else:
                RegistrationSlot.objects\
                    .select_for_update()\
                    .filter(pk=slot["id"])\
                    .update(**{"status": "A", "player": None})

        instance.notes = validated_data.get("notes", instance.notes)
        instance.save()

        return instance


def validate_event_is_not_full(event):
    if event.registration_maximum is not None and event.registration_maximum != 0:
        registrations = RegistrationSlot.objects.filter(status="R").count()
        if registrations >= event.registration_maximum:
            raise EventFullError()


def validate_registration_is_open(event):
    if event.registration_window != "registration":
        raise EventRegistrationNotOpenError()


def validate_course_for_event(event, course_id):
    course = None  # not required for most events
    if event.can_choose:
        if course_id is None:
            raise CourseRequiredError()
        course = Course.objects.get(pk=course_id)

    return course
