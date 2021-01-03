import logging
import pytz

from datetime import timedelta
from django.utils import timezone as tz
from django.conf import settings

from .email import *


# def create_event(event):
#
#     if not event.requires_registration:
#         raise ValidationError("{} does not require registration".format(event.name))
#
#     if event.event_type == "L":
#         return LeagueEvent(event)
#     else:
#         return NonLeagueEvent(event)


def is_cash_or_check(payment_code):
    if not payment_code:
        return False
    elif payment_code.startswith("ch_"):
        return False

    return True


def can_update_registration(event, user):

    if user.is_staff:
        return True

    # allow a 10 minute grace period on the deadline
    skins_end = pytz.utc.normalize(event.skins_end)
    padded_now = tz.now() - timedelta(minutes=10)
    return padded_now <= skins_end


def calculate_refund(reg):
    amount = reg.event.event_fee * 100
    if reg.is_greens_fee_paid:
        amount += reg.event.green_fee * 100
    if reg.is_cart_fee_paid:
        amount += reg.event.cart_fee * 100
    if reg.is_gross_skins_paid:
        amount += reg.event.skins_fee * 100
    if reg.is_net_skins_paid:
        amount += reg.event.skins_fee * 100
    return amount

#
# def register_new(user, event, group_tmp, group, amount_due, payment_code, verification_token):
#     if is_cash_or_check(payment_code):
#         group.payment_confirmation_code = payment_code
#         group.payment_amount = amount_due
#         group.payment_confirmation_timestamp = tz.now()
#     else:
#         charge = stripe_charge(user, event, int(amount_due * 100), verification_token)
#         group.payment_amount = amount_due
#         group.card_verification_token = verification_token
#         group.payment_confirmation_code = charge.id
#         group.payment_confirmation_timestamp = tz.now()
#         group.notes = group_tmp["notes"]
#
#     group.save()
#
#     for slot_tmp in group_tmp["slots"]:
#
#         if type(slot_tmp["member"]) is dict:
#             member_id = slot_tmp["member"]["id"]
#         else:
#             member_id = slot_tmp.get("member", 0)
#
#         if member_id > 0:
#             member = Member.objects.get(pk=member_id)
#             RegistrationSlot.objects \
#                 .select_for_update() \
#                 .filter(pk=slot_tmp["id"]) \
#                 .update(**{
#                     "member": member,
#                     "status": "R",
#                     "is_event_fee_paid": slot_tmp.get("is_event_fee_paid", True),
#                     "is_gross_skins_paid": slot_tmp.get("is_gross_skins_paid", False),
#                     "is_net_skins_paid": slot_tmp.get("is_net_skins_paid", False),
#                     "is_greens_fee_paid": slot_tmp.get("is_greens_fee_paid", False),
#                     "is_cart_fee_paid": slot_tmp.get("is_cart_fee_paid", False)
#                 })
#         else:
#             RegistrationSlot.objects.select_for_update().filter(pk=slot_tmp["id"]).update(**{"status": "A"})
#
#     # notification and confirmation/welcome emails
#     try:
#         if group.event == config.reg_event:
#             if user.date_joined.year == config.year:
#                 send_new_member_notification(user, group, config)
#                 send_new_member_welcome(user, config)
#             else:
#                 send_returning_member_welcome(user, config)
#                 send_has_notes_notification(user, group, event)
#         elif group.event == config.match_play_event:
#             send_event_confirmation(user, group, event, config)
#         elif not is_cash_or_check(payment_code):
#             send_event_confirmation(user, group, event, config)
#             send_has_notes_notification(user, group, event)
#     except Exception:
#         logging.exception("failed to send post-registration email(s)")
#
#     return Registration.objects.get(pk=group.id)
#
#
# # updates support paying additional fees like skins (not event fees)
# def register_update(user, event, group_tmp, group, amount_due, payment_code, verification_token):
#
#     # members in the staff role can perform updates past the deadline defined in the event
#     if not can_update_registration(event, user):
#         raise ValidationError("Sorry, online payments for this event have closed")
#
#     # ensure all updated slot records share the same timestamp
#     payment_ts = tz.now()
#     registrar = Member.objects.get(pk=user.member.id)
#
#     if not is_cash_or_check(payment_code):
#         charge = stripe_charge(user, event, int(amount_due * 100), verification_token)
#         payment_code = charge.id
#
#     for slot_tmp in group_tmp["slots"]:
#         RegistrationSlot.objects \
#             .select_for_update() \
#             .filter(pk=slot_tmp["id"]) \
#             .update(**{
#                 "is_gross_skins_paid": slot_tmp.get("is_gross_skins_paid", False),
#                 "is_net_skins_paid": slot_tmp.get("is_net_skins_paid", False),
#                 "is_greens_fee_paid": slot_tmp.get("is_greens_fee_paid", False),
#                 "is_cart_fee_paid": slot_tmp.get("is_cart_fee_paid", False)
#             })
#         # slot payment records repeat the payment info for each updated reg slot,
#         # so that will have to be accounted for at reporting time
#         slot = RegistrationSlot.objects.get(pk=slot_tmp["id"])
#         slot_payment = RegistrationSlotPayment(
#             registration_slot=slot,
#             recorded_by=registrar,
#             card_verification_token=verification_token,
#             payment_code=payment_code,
#             payment_timestamp=payment_ts,
#             payment_amount=amount_due,
#             comment="updated payment"
#         )
#         slot_payment.save()
#
#     return Registration.objects.get(pk=group.id)
#
#
# class LeagueEvent:
#
#     def __init__(self, event):
#         self.event = event
#         self.logger = logging.getLogger(__name__)
#
#     def reserve(self, registrar, member, slot_ids=None, course_setup_hole_id=None, starting_order=0):
#
#         hole = CourseSetupHole.objects.filter(pk=course_setup_hole_id).get()
#         if hole is None:
#             raise ValidationError("Hole id {} is not valid".format(course_setup_hole_id))
#
#         group = Registration(event=self.event, course_setup=hole.course_setup, signed_up_by=registrar,
#                                   starting_hole=hole.hole_number, starting_order=starting_order)
#         group.expires = tz.now() + timedelta(minutes=10)
#         group.save()
#
#         self.logger.info("selecting slots for update for member {} and group {}".format(member.id, group.id))
#         slots = list(RegistrationSlot.objects.select_for_update().filter(pk__in=slot_ids))
#         for s in slots:
#             if s.status != "A":
#                 raise SlotConflictError()
#
#         for i, slot in enumerate(slots):
#             slot.status = "P"
#             slot.registration_group = group
#             slot.course_setup_hole = hole
#             if i == 0:
#                 slot.member = member
#             slot.save()
#
#         self.logger.info("saved slots for member {} and group {}".format(member.id, group.id))
#
#         return group
#
#
# class NonLeagueEvent:
#
#     def __init__(self, event):
#         self.event = event
#
#     def reserve(self, registrar, member, slot_ids=None, course_setup_hole_id=None, starting_order=0):
#
#         if self.event.registration_maximum != 0:
#             registrations = RegistrationSlot.objects.filter(event=self.event).filter(status="R").count()
#             if registrations >= self.event.registration_maximum:
#                 raise EventFullError()
#
#         group = Registration(event=self.event, course_setup=None, signed_up_by=registrar,
#                                   starting_hole=1, starting_order=starting_order)
#         group.expires = tz.now() + timedelta(minutes=10)
#         group.save()
#
#         for s in range(0, self.event.maximum_signup_group_size):
#             slot = RegistrationSlot(event=self.event, starting_order=starting_order, slot=s)
#             slot.status = "P"
#             slot.registration_group = group
#             if s == 0:
#                 slot.member = member
#             slot.save()
#
#         return group
