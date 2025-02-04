try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import stripe
import structlog

from datetime import timedelta

from django.utils import timezone as tz
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import Max, Q

from courses.models import Hole
from payments.models import Payment
from register.exceptions import SlotConflictError, MissingSlotsError, AlreadyRegisteredError

logger = structlog.getLogger(__name__)


class RegistrationManager(models.Manager):

    def clean_up_expired(self):
        current_time = tz.localtime(tz.now(), timezone=ZoneInfo("America/Chicago"))

        registrations = self \
            .filter(expires__lt=current_time) \
            .filter(slots__status="P")
        count = len(registrations)

        for reg in registrations:
            logger.info("Cleaning up expired registration", currentTime=current_time, expiry=reg.expires,
                        registrationId=reg.id, user=reg.signed_up_by)

            # Make can_choose slots available
            reg.slots \
                .filter(status="P") \
                .filter(event__can_choose=True) \
                .update(**{"status": "A", "registration": None, "player": None})

            # Delete other slots
            reg.slots \
                .filter(status="P") \
                .exclude(event__can_choose=True) \
                .delete()

            if len(reg.slots.all()) == 0:
                reg.delete()

        return count

    @transaction.atomic()
    def create_and_reserve(self, user, player, event, course, registration_slots, signed_up_by):

        if event.can_choose:
            slot_ids = [slot["id"] for slot in registration_slots]
            logger.info("Checking slots", eventId=event.id, course=course.name, user=signed_up_by, slots=slot_ids)

            slots = list(event.registrations.select_for_update().filter(pk__in=slot_ids))

            if slots is None or len(slots) == 0:
                raise MissingSlotsError()

            if len(slots) != len(slot_ids):
                raise SlotConflictError()

            for s in slots:
                if s.status != "A":
                    raise SlotConflictError()

            reg = self.create_or_update_registration(event, user, course, signed_up_by)

            logger.info("Reserving slots", eventId=event.id, course=course.name, user=signed_up_by, slots=slot_ids)
            for i, slot in enumerate(slots):
                if i == 0:
                    slot.player = player
                slot.status = "P"
                slot.registration = reg
                slot.save()
        else:
            reg = self.create_or_update_registration(event, user, course, signed_up_by)
            for s in range(0, event.maximum_signup_group_size):
                slot = event.registrations.create(event=event, registration=reg, status="P", starting_order=0, slot=s)
                if slot.slot == 0:
                    slot.player = player
                slot.save()

        return reg

    def create_or_update_registration(self, event, user, course, signed_up_by):
        registration = self.filter(user=user, event=event).first()
        if registration is not None:
            is_duplicate = registration.slots.filter(Q(status="R") | Q(status="X")).exists()
            if is_duplicate:
                raise AlreadyRegisteredError()
            registration.course = course
            registration.signed_up_by = signed_up_by
            registration.slots.filter(status="P").update(**{"status": "A", "player": None, "registration": None})
        else:
            registration = self.create(event=event, course=course, user=user, signed_up_by=signed_up_by)

        if event.can_choose:
            registration.expires = tz.now() + timedelta(minutes=5)
        else:
            registration.expires = tz.now() + timedelta(minutes=15)

        registration.save()

        return registration

    def payment_processing(self, registration_id):
        try:
            reg = self.filter(pk=registration_id).get()
            reg.slots.filter(status="P").filter(player__isnull=False).update(**{"status": "X"})
            # free up or remove slots without players
            if reg.event.can_choose:
                reg.slots\
                    .filter(status="P")\
                    .filter(player__isnull=True)\
                    .update(**{"status": "A", "player": None, "registration": None})
            else:
                reg.slots\
                    .filter(status="P")\
                    .filter(player__isnull=True)\
                    .delete()
        except ObjectDoesNotExist:
            pass

    def payment_confirmed(self, registration_id):
        try:
            reg = self.filter(pk=registration_id).get()
            reg.slots.filter(status="X").update(**{"status": "R"})
            return reg.slots.filter(status="R")
        except ObjectDoesNotExist:
            pass
        
    # Something went wrong on the client side, so we revert the status to Pending
    def undo_payment_processing(self, registration_id):
        try:
            reg = self.filter(pk=registration_id).get()
            logger.info("Undoing payment processing", registration=registration_id, user=reg.signed_up_by)
            reg.slots.filter(status="X").update(**{"status": "P"})
        except ObjectDoesNotExist:
            pass

    @transaction.atomic()
    def cancel_registration(self, registration_id, payment_id, reason):
        try:
            reg = self.filter(pk=registration_id).get()
            logger.info("Canceling registration", registration=registration_id, payment=payment_id,
                        user=reg.signed_up_by, reason=reason)

            if reg.event.can_choose:
                reg.slots.filter(status="P").update(**{"status": "A", "player": None, "registration": None})
            else:
                reg.slots.filter(status="P").delete()

            reg.delete()

            if payment_id is not None and payment_id > 0:
                payment = Payment.objects.get(pk=payment_id)
                payment.payment_details.all().delete()
                if payment.payment_code is not None and payment.payment_code.startswith("pi_"):
                    logger.info("Canceling stripe payment", payment=payment_id, code=payment.payment_code, user=reg.signed_up_by)
                    stripe.PaymentIntent.cancel(payment.payment_code)
                payment.delete()

        except ObjectDoesNotExist:
            pass


class RegistrationSlotManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related("player")

    def is_registered(self, event_id, player_id):
        try:
            self.filter(event__id=event_id).filter(player__id=player_id).filter(status="R").get()
            return True
        except ObjectDoesNotExist:
            return False

    def players(self, event_id):
        return self.filter(event__id=event_id).values_list("player", flat=True)

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
        pass

    def create_slots_for_event(self, event):
        slots = []

        if event.can_choose and event.start_type == "SG":
            for course in event.courses.all():
                # for each hole in course setup, create an A and B group
                holes = Hole.objects.filter(course=course)
                for hole in holes:
                    for s in range(0, event.group_size):
                        a_slot = self.create(event=event, hole=hole, starting_order=0, slot=s)
                        slots.append(a_slot)
                    # Only add 2nd group on par 4s and 5s
                    # if hole.par != 3:
                    # for s in range(0, event.group_size):
                        b_slot = self.create(event=event, hole=hole, starting_order=1, slot=s)
                        slots.append(b_slot)
        elif event.can_choose and event.start_type == "TT":
            for course in event.courses.all():
                hole = Hole.objects.filter(course=course).filter(hole_number=1).get()
                for i in range(event.total_groups):
                    status = "U" if event.starter_time_interval > 0\
                                 and (i + 1) % event.starter_time_interval == 0\
                                 else "A "
                    for s in range(0, event.group_size):
                        slot = self.create(event=event, hole=hole, starting_order=i, slot=s, status=status)
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


class RegistrationFeeManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related("event_fee").selected_related("registration_slot")
