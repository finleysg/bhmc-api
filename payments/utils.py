import re
from datetime import timedelta, datetime, date
from decimal import Decimal

from django.db.models.aggregates import Sum
from rest_framework.exceptions import APIException

from events.models import EventFee
from payments.models import Payment
from register.models import RegistrationFee

DEFAULT_INTERVAL = 10


def get_start(event, registration, slot):
    if event.start_type == "TT":
        return get_starting_time(event, registration, slot)
    elif event.start_type == "SG":
        return get_starting_hole(event, registration, slot)
    else:
        return "N/A"


def get_starting_time(event, registration, slot):
    if event.can_choose:
        course_name = registration.course.name
        hours = parse_hours(event.start_time)
        minutes = parse_minutes(event.start_time)
        start_date = datetime.combine(event.start_date, datetime.min.time())
        first_time = start_date + timedelta(hours=hours, minutes=minutes)
        start_time = get_starting_time_offset(first_time, slot.starting_order, event.tee_time_splits)
        return "{} {}".format(course_name, start_time.strftime("%-I:%M %p"))

    return "Tee times"


def get_starting_time_offset(first_time, starting_order, tee_time_splits):
    intervals = [int(i) for i in tee_time_splits.split(',')] if tee_time_splits is not None else [DEFAULT_INTERVAL]
    return first_time + timedelta(minutes=get_offset(starting_order, intervals))


def get_offset(starting_order, intervals):
    if starting_order == 0:
        return 0
    elif len(intervals) == 1:
        return starting_order * intervals[0]
    elif starting_order % 2 == 0:
        return (starting_order // 2) * (intervals[0] + intervals[1])
    else:
        return (starting_order // 2) * (intervals[0] + intervals[1]) + intervals[0]


def get_starting_hole(event, registration, slot):
    if event.can_choose:
        course_name = registration.course.name
        if slot.starting_order == 0:
            return "{} {}A".format(course_name, slot.hole.hole_number)
        else:
            return "{} {}B".format(course_name, slot.hole.hole_number)

    return "Shotgun"


def get_required_fees(event, payment_details):
    required = Decimal("0.0")
    for detail in payment_details:
        event_fee = next((f for f in event.fees.all() if f == detail.event_fee), None)
        if event_fee.is_required:
            required = required + event_fee.amount

    return required


def get_optional_fees(event, payment_details):
    optional = Decimal("0.0")
    for detail in payment_details:
        event_fee = next((f for f in event.fees.all() if f == detail.event_fee), None)
        if not event_fee.is_required:
            optional = optional + event_fee.amount

    return optional


def get_players(event, slots, payment_details):
    players = []
    for slot in slots:
        if slot.player is not None:
            players.append({
                "name": "{} {}".format(slot.player.first_name, slot.player.last_name),
                "email": slot.player.email,
                "fees": get_fees(event, filter(lambda fee: fee.registration_slot == slot, payment_details))
            })
    return players


def get_fees(event, payment_details):
    player_fees = []
    for fee in payment_details:
        event_fee = next((f for f in event.fees.all() if f == fee.event_fee), None)
        player_fees.append({
            "description": event_fee.fee_type.name,
            "amount": "${:,.2f}".format(fee.amount)
        })
    return player_fees


# Get emails for the rest of the group
def get_recipients(user, slots):
    recipients = []
    for slot in slots:
        if slot.player is not None and slot.player.email != user.email:
            recipients.append(slot.player.email)

    return recipients


def get_event_url(base_url, event):
    return "{}/event/{}/{}".format(base_url, event.start_date.strftime("%Y-%m-%d"), slugify(event.name))


def slugify(text):
    slug = re.sub("--+", "-", re.sub("[^\\w-]+", "", re.sub("\\s+", "-", text.lower().strip().replace("/", "-"))))
    return slug


# expected 3:00 PM, 7:30 AM, etc.
def parse_hours(time_text):
    parts = re.split("[ :]", time_text)
    hours = int(parts[0])
    return hours if parts[2].lower() == "am" else hours + 12


def parse_minutes(time_text):
    parts = re.split("[ :]", time_text)
    return int(parts[1])


def create_admin_payment(event, slot, fee_ids, is_money_owed, user):
    """Create a payment record for the given event and slot."""
    event_fees = event.fees.filter(pk__in=fee_ids)
    payment_amount = Decimal(event_fees.aggregate(total=Sum("amount"))["total"]) if is_money_owed else Decimal("0.00")
    payment_code = "collect from player" if is_money_owed else "no charge"

    payment = Payment.objects.create(event=event,
                                     user=user,
                                     payment_code=payment_code,
                                     payment_key="n/a",
                                     payment_amount=payment_amount,
                                     transaction_fee=0,
                                     confirmed=True,
                                     confirm_date=date.today(),
                                     notification_type="A")
    payment.save()

    for _, fee in enumerate(event_fees):
        registration_fee = RegistrationFee(event_fee=fee,
                                           registration_slot=slot,
                                           is_paid=False,
                                           payment=payment)
        registration_fee.save()

    return payment


def calculate_refund_amount(payment, refund_fees):
    event_fees = EventFee.objects.filter(event=payment.event)
    refund_amount = 0.0
    for fee in refund_fees:
        event_fee = next((ef for ef in event_fees if ef.id == fee.get("event_fee_id", 0)), None)
        amount_paid = fee.get("amount_paid", 0)
        if amount_paid != event_fee.amount and amount_paid != event_fee.override_amount:
            raise APIException("Refund amount does not match the event fee amount")
        refund_amount += amount_paid

    return refund_amount
