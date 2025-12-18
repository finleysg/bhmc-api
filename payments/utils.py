try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import math
import re

from datetime import timedelta, datetime
from decimal import Decimal, Context

from django.db.models.aggregates import Sum
from django.utils import timezone as tz
from rest_framework.exceptions import APIException

from core.util import current_season
from events.models import EventFee
from payments.models import Payment
from register.models import RegistrationFee

DEFAULT_INTERVAL = 10


def calculate_payment_amount(amount_due):
    transaction_fixed_cost = Decimal(0.3)
    transaction_percentage = Decimal(0.029)
    total = (amount_due + transaction_fixed_cost) / (Decimal(1.0) - transaction_percentage)
    transaction_fee = total - amount_due
    return total, transaction_fee


def derive_notification_type(event, player, payment_details):

    """
    Determine the notification type code for a payment related to an event and player.
    
    Returns one of the notification codes based on event type, player history, and whether required fees are present in the provided payment details:
    - If the event's type is "R": returns "R" when the player is re-registering from the previous season, otherwise "N".
    - If the event's type is "S": returns "M".
    - For other event types: returns "C" when required fees are included in payment_details, otherwise "U".
    
    Parameters:
        event: Event-like object with at least an `event_type` attribute.
        player: Player-like object with at least a `last_season` attribute.
        payment_details: Iterable of payment detail objects used to determine presence of required fees.
    
    Returns:
        str: One of `"R"`, `"N"`, `"M"`, `"C"`, or `"U"` representing the notification type.
    """
    if event.event_type == "R":  # season registration
        season = current_season()
        if player.last_season == (season - 1):
            return "R"
        else:
            return "N"
    elif event.event_type == "S":  # season long match play
        return "M"

    # This is a roundabout way to get this info, but if there are
    # no required fees in the payment details, we know this is an
    # "edit" (skins payment, or other fees, after the initial registration)
    if has_required_fees(event, payment_details):
        return "C"
    else:
        return "U"
    

def get_amount_due(event, payment_details):
    # TODO: verify that the amount_received is a valid override
    """
    Compute the total amount due from a sequence of payment detail entries.
    
    Parameters:
        payment_details (iterable): An iterable of objects each exposing an `amount` (Decimal) to include in the total.
    
    Returns:
        Decimal: Sum of all `amount` values from `payment_details`.
    """
    amount_due = Decimal(0.0)
    amounts = [detail.amount for detail in payment_details]
    for amount in amounts:
        amount_due += amount

    return amount_due


def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n*multiplier + Decimal(0.5)) / multiplier


def has_required_fees(event, payment_details):
    event_fees = event.fees.all()
    event_fee_ids = [detail["event_fee"].id for detail in payment_details]
    required = next(iter([f for f in event_fees if f.is_required and f.id in event_fee_ids]), None)
    return required is not None


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
    """
    Builds a list of fee descriptions and formatted amounts for the given event and payment details.
    
    Parameters:
        event: Event model instance whose fees are used to map fee types.
        payment_details: Iterable of payment detail objects containing `event_fee` and numeric `amount`.
    
    Returns:
        List[dict]: Each dict has keys:
            - "description": the fee type name from the matched event fee.
            - "amount": the fee amount formatted as a currency string (e.g., "$12.34").
    """
    player_fees = []
    for fee in payment_details:
        event_fee = next((f for f in event.fees.all() if f == fee.event_fee), None)
        player_fees.append({
            "description": event_fee.fee_type.name,
            "amount": "${:,.2f}".format(fee.amount)
        })
    return player_fees


# Get slots only for players with payment changes
def get_payment_slots(registration, payment_details):
    """
    Return the registration's slots that are referenced by the provided payment detail records.
    
    Parameters:
        registration: Registration-like object with a `slots` relation supporting `.filter(pk__in=...)`.
        payment_details: Iterable of objects each exposing a `registration_slot_id` attribute or field.
    
    Returns:
        QuerySet: A queryset of registration slots whose primary keys appear in `payment_details`.
    """
    slot_ids = set()
    for fee in payment_details:
        slot_ids.add(fee.registration_slot_id)
        
    return registration.slots.filter(pk__in=slot_ids)


# Get emails for the rest of the group
def get_recipients(user, slots):
    """
    Return a list of email addresses for players in the provided slots excluding the given user's email.
    
    Parameters:
        user: User-like object with an `email` attribute to exclude from recipients.
        slots: Iterable of slot-like objects; each may have a `player` attribute (which may be None) and a `player.email`.
    
    Returns:
        list[str]: Email addresses of slot players that exist and are not the same as `user.email`.
    """
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
                                     confirm_date=tz.localtime(tz.now(), timezone=ZoneInfo("America/Chicago")),
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
    refund_amount = Decimal("0.00")
    for fee in refund_fees:
        event_fee = next((ef for ef in event_fees if ef.id == fee.get("event_fee_id", 0)), None)
        amount_paid = Decimal(fee.get("amount_paid", 0)).quantize(Decimal("0.01"))
        if amount_paid != event_fee.amount and amount_paid != event_fee.override_amount:
            raise APIException(f"Refund amount does not match the event fee amount: {amount_paid} != {event_fee.amount}")
        refund_amount += amount_paid

    return refund_amount


def update_to_unpaid(refund_fees):
    for fee in refund_fees:
        registration_fee = RegistrationFee.objects.get(pk=fee.get("fee_id", 0))
        registration_fee.is_paid = False
        registration_fee.save()