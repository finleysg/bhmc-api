import re
from datetime import timedelta, datetime, date
from decimal import Decimal


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
        start_time = first_time + timedelta(minutes=(8 * slot.starting_order))
        return "{} {}".format(course_name, start_time.strftime("%-I:%M %p"))

    return "Tee times"


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
            "amount": "${:,.2f}".format(event_fee.amount)
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


# expected 3:00 PM or 7:30 AM, et al
def parse_hours(time_text):
    parts = re.split("[ :]", time_text)
    hours = int(parts[0])
    return hours if parts[2].lower() == "am" else hours + 12


def parse_minutes(time_text):
    parts = re.split("[ :]", time_text)
    return int(parts[1])
