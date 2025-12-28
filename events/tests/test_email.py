from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from courses.models import Course, Hole
from events.tests.factories import WeeknightEventFactory
from payments.models import Payment
from payments.utils import (
    get_event_url,
    get_start,
    get_required_fees,
    get_optional_fees,
    get_players,
    get_recipients,
)
from register.models import Registration, Player, RegistrationSlot, RegistrationFee
from events.models import Event, EventFee


def create_teetime_event(splits):
    """
    Create a WeeknightEvent configured for teetimes with a 3:00 PM start.
    
    Parameters:
        splits (str|None): Tee time split configuration (e.g., "8", "8,9") or None to use the default split.
    
    Returns:
        WeeknightEvent: A WeeknightEvent instance with start_time "3:00 PM", start_type "TT", and tee_time_splits set to `splits`.
    """
    event = WeeknightEventFactory()
    event.start_time = "3:00 PM"
    event.start_type = "TT"
    event.tee_time_splits = splits
    return event


def create_shotgun_event():
    event = WeeknightEventFactory()
    event.start_time = "5:00 PM"
    event.start_type = "SG"
    return event


class EmailUtilsTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee", "course", "hole"]

    def test_weeknight_url_is_valid(self):
        event = Event.objects.get(pk=3)
        event_url = get_event_url("http://localhost", event)
        self.assertEqual(
            "http://localhost/event/2020-11-04/low-gross-low-net", event_url
        )

    def test_major_url_is_valid(self):
        event = Event.objects.get(pk=4)
        event_url = get_event_url("http://localhost", event)
        self.assertEqual("http://localhost/event/2020-11-14/2-man-best-ball", event_url)

    def test_get_start_shotgun_a_group(self):
        event = create_shotgun_event()
        course = Course.objects.get(pk=1)
        hole = Hole.objects.get(pk=2)
        registration = Registration(event=event, course=course)
        slot = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=0
        )
        start = get_start(event, registration, slot)
        self.assertEqual("East 2A", start)

    def test_get_start_shotgun_b_group(self):
        event = create_shotgun_event()
        course = Course.objects.get(pk=1)
        hole = Hole.objects.get(pk=9)
        registration = Registration(event=event, course=course)
        slot = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=1
        )
        start = get_start(event, registration, slot)
        self.assertEqual("East 9B", start)

    def test_get_start_teetimes_first_group_default_split(self):
        event = create_teetime_event(None)
        course = Course.objects.get(pk=1)
        hole = course.holes.first()
        registration = Registration(event=event, course=course)
        slot = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=0
        )

        start = get_start(event, registration, slot)
        self.assertEqual("East 3:00 PM", start)

    def test_get_start_teetimes_third_group_default_split(self):
        event = create_teetime_event(None)
        course = Course.objects.get(pk=1)
        hole = course.holes.first()
        registration = Registration(event=event, course=course)
        slot = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=2
        )

        start = get_start(event, registration, slot)
        self.assertEqual("East 3:20 PM", start)

    def test_get_start_teetimes_tenth_group_default_split(self):
        event = create_teetime_event(None)
        course = Course.objects.get(pk=1)
        hole = course.holes.first()
        registration = Registration(event=event, course=course)
        slot = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=9
        )

        start = get_start(event, registration, slot)
        self.assertEqual("East 4:30 PM", start)

    def test_get_start_teetimes_first_group_defined_split(self):
        event = create_teetime_event("9")
        course = Course.objects.get(pk=1)
        hole = course.holes.first()
        registration = Registration(event=event, course=course)
        slot = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=0
        )

        start = get_start(event, registration, slot)
        self.assertEqual("East 3:00 PM", start)

    def test_get_start_teetimes_third_group_defined_split(self):
        event = create_teetime_event("9")
        course = Course.objects.get(pk=1)
        hole = course.holes.first()
        registration = Registration(event=event, course=course)
        slot = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=2
        )

        start = get_start(event, registration, slot)
        self.assertEqual("East 3:18 PM", start)

    def test_get_start_teetimes_tenth_group_defined_split(self):
        event = create_teetime_event("9")
        course = Course.objects.get(pk=1)
        hole = course.holes.first()
        registration = Registration(event=event, course=course)
        slot = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=9
        )

        start = get_start(event, registration, slot)
        self.assertEqual("East 4:21 PM", start)

    def test_get_start_teetimes_first_group_alternating_split(self):
        event = create_teetime_event("8,9")
        course = Course.objects.get(pk=1)
        hole = course.holes.first()
        registration = Registration(event=event, course=course)
        slot = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=0
        )

        start = get_start(event, registration, slot)
        self.assertEqual("East 3:00 PM", start)

    def test_get_start_teetimes_third_group_alternating_split(self):
        event = create_teetime_event("8,9")
        course = Course.objects.get(pk=1)
        hole = course.holes.first()
        registration = Registration(event=event, course=course)
        slot1 = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=1
        )
        slot2 = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=2
        )

        self.assertEqual("East 3:08 PM", get_start(event, registration, slot1))
        self.assertEqual("East 3:17 PM", get_start(event, registration, slot2))

    def test_get_start_teetimes_tenth_group_alternating_split(self):
        event = create_teetime_event("8,9")
        course = Course.objects.get(pk=1)
        hole = course.holes.first()
        registration = Registration(event=event, course=course)
        slot = RegistrationSlot(
            event=event, registration=registration, hole=hole, starting_order=9
        )

        start = get_start(event, registration, slot)
        print(start)
        self.assertEqual("East 4:16 PM", start)

    def test_get_fee_amounts(self):
        event = Event.objects.get(pk=6)
        course = Course.objects.get(pk=1)
        holes = list(course.holes.all())
        event_fees = list(EventFee.objects.filter(event=6).all())
        registration = Registration(
            event=event, course=course
        )
        player1 = Player(id=1, email="player1@test.com")
        player2 = Player(id=2, email="player2@test.com")
        user1 = User(id=1, email="player1@test.com")
        slot1 = RegistrationSlot(
            event=event,
            registration=registration,
            hole=holes[0],
            player=player1,
            starting_order=0,
            slot=0,
            status="R",
        )
        slot2 = RegistrationSlot(
            event=event,
            registration=registration,
            hole=holes[0],
            player=player2,
            starting_order=0,
            slot=1,
            status="R",
        )
        payment = Payment(
            event=event,
            user=user1,
            payment_code="test",
            notification_type="C",
            confirmed=1,
        )
        payment_details = [
            RegistrationFee(
                id=1, event_fee=event_fees[0], registration_slot=slot1, payment=payment
            ),
            RegistrationFee(
                id=2, event_fee=event_fees[1], registration_slot=slot1, payment=payment
            ),
            RegistrationFee(
                id=3, event_fee=event_fees[3], registration_slot=slot1, payment=payment
            ),
            RegistrationFee(
                id=4, event_fee=event_fees[0], registration_slot=slot2, payment=payment
            ),
            RegistrationFee(
                id=5, event_fee=event_fees[2], registration_slot=slot2, payment=payment
            ),
        ]

        required_fees = get_required_fees(event, payment_details)
        optional_fees = get_optional_fees(event, payment_details)

        self.assertEqual(Decimal(10), required_fees)
        self.assertEqual(Decimal(29), optional_fees)

    def test_get_players(self):
        event = Event.objects.get(pk=6)
        course = Course.objects.get(pk=1)
        holes = list(course.holes.all())
        event_fees = list(EventFee.objects.filter(event=6).all())
        registration = Registration(
            event=event, course=course
        )
        user1 = User(id=1, email="player1@test.com")
        player1 = Player(id=1, email="player1@test.com")
        player2 = Player(id=2, email="player2@test.com")
        slot1 = RegistrationSlot(
            event=event,
            registration=registration,
            hole=holes[0],
            player=player1,
            starting_order=0,
            slot=0,
            status="R",
        )
        slot2 = RegistrationSlot(
            event=event,
            registration=registration,
            hole=holes[0],
            player=player2,
            starting_order=0,
            slot=1,
            status="R",
        )
        slot3 = RegistrationSlot(
            event=event,
            registration=registration,
            hole=holes[0],
            player=None,
            starting_order=0,
            slot=2,
            status="P",
        )
        payment = Payment(
            event=event,
            user=user1,
            payment_code="test",
            notification_type="C",
            confirmed=1,
        )
        payment_details = [
            RegistrationFee(
                id=1, event_fee=event_fees[0], registration_slot=slot1, payment=payment
            ),
            RegistrationFee(
                id=2, event_fee=event_fees[1], registration_slot=slot1, payment=payment
            ),
            RegistrationFee(
                id=3, event_fee=event_fees[3], registration_slot=slot1, payment=payment
            ),
            RegistrationFee(
                id=4, event_fee=event_fees[0], registration_slot=slot2, payment=payment
            ),
            RegistrationFee(
                id=5, event_fee=event_fees[2], registration_slot=slot2, payment=payment
            ),
        ]

        players = get_players(event, [slot1, slot2, slot3], payment_details)

        self.assertEqual(2, len(players))
        self.assertEqual(3, len(players[0]["fees"]))
        self.assertEqual(2, len(players[1]["fees"]))

    def test_get_email_recipients(self):
        event = Event.objects.get(pk=6)
        course = Course.objects.get(pk=1)
        holes = list(course.holes.all())
        registration = Registration(
            event=event, course=course
        )
        user1 = User(id=1, email="player1@test.com")
        player1 = Player(id=1, email="player1@test.com")
        player2 = Player(id=2, email="player2@test.com")
        slot1 = RegistrationSlot(
            event=event,
            registration=registration,
            hole=holes[0],
            player=player1,
            starting_order=0,
            slot=0,
            status="R",
        )
        slot2 = RegistrationSlot(
            event=event,
            registration=registration,
            hole=holes[0],
            player=player2,
            starting_order=0,
            slot=1,
            status="R",
        )
        slot3 = RegistrationSlot(
            event=event,
            registration=registration,
            hole=holes[0],
            player=None,
            starting_order=0,
            slot=2,
            status="P",
        )

        emails = get_recipients(user1, [slot1, slot2, slot3])

        self.assertEqual(1, len(emails))
        self.assertEqual("player2@test.com", emails[0])