import logging
from datetime import timedelta

from django.utils import timezone as tz
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import Max
from courses.models import Hole
from register.exceptions import SlotConflictError, MissingSlotsError

logger = logging.getLogger('register-manager')


class RegistrationManager(models.Manager):

    def clean_up_expired(self):
        registrations = self.filter(expires__lt=tz.now()).filter(slots__status="P")
        count = len(registrations)

        for reg in registrations:
            # Make can_choose slots available
            reg.slots.filter(event__can_choose=True).update(**{"status": "A", "registration": None, "player": None})

            # Delete other slots
            reg.slots.exclude(event__can_choose=True).delete()

            reg.delete()

        return count

    @transaction.atomic()
    def create_and_reserve(self, event, course, registration_slots, **registration_data):
        reg = self.create(event=event, course=course, **registration_data)
        reg.expires = tz.now() + timedelta(minutes=10)
        reg.save()

        if event.can_choose:
            slot_ids = [slot["id"] for slot in registration_slots]
            slots = list(event.registrations.select_for_update(nowait=True).filter(pk__in=slot_ids))

            if slots is None or len(slots) == 0:
                raise MissingSlotsError()

            for s in slots:
                if s.status != "A":
                    raise SlotConflictError()

            for i, slot in enumerate(slots):
                slot.status = "P"
                slot.registration = reg
                slot.save()
        else:
            for s in range(0, event.maximum_signup_group_size):
                slot = event.registrations.create(event=event, registration=reg, status="P", starting_order=0, slot=s)
                slot.save()

        return reg

    @transaction.atomic()
    def cancel_registration(self, registration_id):
        try:
            reg = self.filter(pk=registration_id).get()

            if reg.event.can_choose:
                reg.slots.update(**{"status": "A", "registration": None, "player": None})
            else:
                reg.slots.all().delete()

            reg.delete()

        except ObjectDoesNotExist:
            logger.warning("Could not find and cancel a registration with id {}".format(registration_id),)


class RegistrationSlotManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('player')

    def is_registered(self, event_id, player_id):
        try:
            self.filter(event__id=event_id).filter(player__id=player_id).filter(status='R').get()
            return True
        except ObjectDoesNotExist:
            return False

    def players(self, event_id):
        return self.filter(event__id=event_id).values_list('player', flat=True)

    def update_slots_for_hole(self, slots):
        for slot in slots:
            if type(slot["player"]) is dict:
                player_id = slot["player"]["id"]
            else:
                player_id = slot.get("player", 0)
            # If a player is assigned, reserve for that player, otherwise make available
            if player_id > 0:
                player = self.player_set.objects.get(pk=player_id)
                self.objects \
                    .select_for_update() \
                    .filter(pk=slot["id"]) \
                    .update(**{
                        "player": player,
                        "status": "R"
                    })
            else:
                self.objects.select_for_update().filter(pk=slot["id"]).update(**{"status": "A"})

    def remove_slots_for_event(self, event):
        self.filter(event=event).delete()

    def create_slots_for_event(self, event):
        slots = []

        if event.can_choose and event.start_type == "SG":
            for course in event.courses.all():
                # for each hole in course setup, create an A and B group
                holes = Hole.objects.filter(course=course)
                for hole in holes:
                    for s in range(0, event.group_size):
                        slot = self.create(event=event, hole=hole, starting_order=0, slot=s)
                        slots.append(slot)
                    # Only add 2nd group on par 4s and 5s
                    if hole.par != 3:
                        for s in range(0, event.group_size):
                            slot = self.create(event=event, hole=hole, starting_order=1, slot=s)
                            slots.append(slot)
        elif event.can_choose and event.start_type == "TT":
            for course in event.courses.all():
                hole = Hole.objects.filter(course=course).filter(hole_number=1).get()
                for i in range(event.total_groups):
                    for s in range(0, event.group_size):
                        slot = self.create(event=event, hole=hole, starting_order=i, slot=s)
                        slots.append(slot)

        return slots

    def remove_hole(self, event, hole, starting_order):
        self.filter(event=event, hole=hole, starting_order=starting_order).delete()

    def add_slots_for_hole(self, event, hole):
        slots = []
        start = 0

        # get max starting order and increment 1
        previous = self.filter(event=event, hole=hole).aggregate(Max("starting_order"))
        if len(previous):
            start = previous["starting_order__max"] + 1

        for s in range(0, event.maximum_signup_group_size):
            slot = self.create(event=event, hole=hole, starting_order=start, slot=s)
            slots.append(slot)

        return slots

    def update_slots_for_payment(self, payment, fee_ids):
        registration_fees = list(self.fees.filter(pk_in=fee_ids))
        for fee in registration_fees:
            fee.status = "R"
            fee.payment = payment
            fee.save()
