from datetime import date

from factory.django import DjangoModelFactory

from events.models import Event


class WeeknightEventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    event_type = "N"
    name = "Weeknight Test Event"
    start_date = date.today()
    start_time = "2:00 PM"
    start_type = "TT"
    status = "S"
    registration_type = "M"
    can_choose = True
    tee_time_splits = "10"
    season = 2024
