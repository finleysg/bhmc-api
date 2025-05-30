import re
from datetime import timedelta, datetime


# def get_start(slot):
#     event = slot.event
#     if event.start_type == "TT":
#         return get_starting_time(event, slot)
#     else:
#         return get_starting_hole(event, slot)
#
#
# def get_starting_time(event, slot):
#     if event.can_choose:
#         course_name = slot.hole.course.name
#         hours = parse_hours(event.start_time)
#         minutes = parse_minutes(event.start_time)
#         start_date = datetime.combine(event.start_date, datetime.min.time())
#         first_time = start_date + timedelta(hours=hours, minutes=minutes)
#         start_time = first_time + timedelta(minutes=(event.tee_time_splits * slot.starting_order))
#         return "{} {}".format(course_name, start_time.strftime("%-I:%M %p"))
#
#     return "Tee times"


def get_starting_hole(event, slot):
    if event.can_choose:
        course_name = slot.hole.course.name
        if slot.starting_order == 0:
            return "{} {}A".format(course_name, slot.hole.hole_number)
        else:
            return "{} {}B".format(course_name, slot.hole.hole_number)

    return "Shotgun"


# expected 3:00 PM, 7:30 AM, etc.
def parse_hours(time_text):
    parts = re.split("[ :]", time_text)
    hours = int(parts[0])
    return hours if parts[2].lower() == "am" else hours + 12


def parse_minutes(time_text):
    parts = re.split("[ :]", time_text)
    return int(parts[1])


def get_target_event_fee(source_fee, source_event, target_event):
    fee_type_id = source_event.fees.filter(pk=source_fee.event_fee_id)[0].fee_type_id
    return target_event.fees.filter(fee_type_id=fee_type_id)[0]