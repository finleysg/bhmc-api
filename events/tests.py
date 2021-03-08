from datetime import date
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from courses.models import Course
from payments.models import Payment
from payments.utils import get_event_url, get_start, get_required_fees, get_optional_fees, get_players, get_recipients
from register.models import Registration, Player, RegistrationSlot, RegistrationFee
from .models import Event, EventFee


class EventModelTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee", "course", "hole"]

    def test_weeknight_teetimes_is_valid(self):
        event = Event.objects.get(pk=3)
        event.clean()
        self.assertTrue(True)

    def test_weeknight_teetimes_must_have_total_groups(self):
        event = Event.objects.get(pk=3)
        event.total_groups = 0
        with self.assertRaises(ValidationError, msg='You must include the number of groups per course when players are '
                                                    'choosing their own tee times'):
            event.clean()

    def test_weeknight_shotgun_is_valid(self):
        event = Event.objects.get(pk=6)
        event.clean()
        self.assertTrue(True)

    def test_weeknight_can_choose_must_have_group_size(self):
        event = Event.objects.get(pk=3)
        event.group_size = 0
        with self.assertRaises(ValidationError, msg='A group size is required if players are choosing their starting '
                                                    'hole or tee time'):
            event.clean()

    def test_weeknight_registration_signup_end(self):
        event = Event.objects.get(pk=3)
        event.signup_end = None
        with self.assertRaises(ValidationError, msg='When an event requires registration, both signup start and '
                                                    'signup end are required'):
            event.clean()

    def test_weeknight_registration_signup_start(self):
        event = Event.objects.get(pk=3)
        event.signup_start = None
        with self.assertRaises(ValidationError, msg='When an event requires registration, both signup start and '
                                                    'signup end are required'):
            event.clean()

    def test_weeknight_registration_signup_start_before_end(self):
        event = Event.objects.get(pk=3)
        event.signup_start = event.signup_end + timedelta(hours=1)
        with self.assertRaises(ValidationError, msg='The signup start must be earlier than signup end'):
            event.clean()

    def test_can_clone(self):
        event = Event.objects.get(pk=1)
        new_dt = date.fromisoformat('2020-12-04')
        copy = Event.objects.clone(event, new_dt)
        self.assertNotEqual(event.id, copy.id)
        self.assertEqual(event.name, copy.name)
        self.assertGreater(copy.signup_start, event.signup_start)

    def test_clone_includes_registration_slots(self):
        event = Event.objects.get(pk=3)
        new_dt = date.fromisoformat('2020-12-04')
        copy = Event.objects.clone(event, new_dt)
        self.assertEqual(len(copy.registrations.all()), 0)

    def test_clone_includes_fees(self):
        event = Event.objects.get(pk=4)
        new_dt = date.fromisoformat('2020-12-31')
        copy = Event.objects.clone(event, new_dt)
        self.assertGreater(len(copy.fees.all()), 0)


class EmailUtilsTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee", "course", "hole"]

    def test_weeknight_url_is_valid(self):
        event = Event.objects.get(pk=3)
        event_url = get_event_url("http://localhost", event)
        self.assertEqual("http://localhost/event/2020-11-04/low-gross-low-net", event_url)

    def test_major_url_is_valid(self):
        event = Event.objects.get(pk=4)
        event_url = get_event_url("http://localhost", event)
        self.assertEqual("http://localhost/event/2020-11-14/2-man-best-ball", event_url)

    def test_get_start_shotgun_a_group(self):
        event = Event.objects.get(pk=6)
        course = Course.objects.get(pk=1)
        registration = Registration(event=event, course=course, starting_hole=2, starting_order=0)
        start = get_start(event, registration)
        self.assertEqual("East 2A", start)

    def test_get_start_shotgun_b_group(self):
        event = Event.objects.get(pk=6)
        course = Course.objects.get(pk=1)
        registration = Registration(event=event, course=course, starting_hole=9, starting_order=1)
        start = get_start(event, registration)
        self.assertEqual("East 9B", start)

    def test_get_start_teetimes_first_group(self):
        event = Event.objects.get(pk=3)
        course = Course.objects.get(pk=1)
        registration = Registration(event=event, course=course, starting_hole=1, starting_order=0)
        start = get_start(event, registration)
        self.assertEqual("East 3:00 PM", start)

    def test_get_start_teetimes_third_group(self):
        event = Event.objects.get(pk=3)
        course = Course.objects.get(pk=1)
        registration = Registration(event=event, course=course, starting_hole=1, starting_order=2)
        start = get_start(event, registration)
        self.assertEqual("East 3:16 PM", start)

    def test_get_start_teetimes_tenth_group(self):
        event = Event.objects.get(pk=3)
        course = Course.objects.get(pk=1)
        registration = Registration(event=event, course=course, starting_hole=1, starting_order=9)
        start = get_start(event, registration)
        self.assertEqual("East 4:12 PM", start)

    def test_get_fee_amounts(self):
        event = Event.objects.get(pk=6)
        course = Course.objects.get(pk=1)
        holes = list(course.holes.all())
        event_fees = list(EventFee.objects.filter(event=6).all())
        registration = Registration(event=event, course=course, starting_hole=2, starting_order=0)
        player1 = Player(id=1, email="player1@test.com")
        player2 = Player(id=2, email="player2@test.com")
        user1 = User(id=1, email="player1@test.com")
        slot1 = RegistrationSlot(event=event, registration=registration, hole=holes[0], player=player1,
                                 starting_order=0, slot=0, status="R")
        slot2 = RegistrationSlot(event=event, registration=registration, hole=holes[0], player=player2,
                                 starting_order=0, slot=1, status="R")
        payment = Payment(event=event, user=user1, payment_code="test", notification_type="C", confirmed=1)
        payment_details = [RegistrationFee(id=1, event_fee=event_fees[0], registration_slot=slot1, payment=payment),
                           RegistrationFee(id=2, event_fee=event_fees[1], registration_slot=slot1, payment=payment),
                           RegistrationFee(id=3, event_fee=event_fees[3], registration_slot=slot1, payment=payment),
                           RegistrationFee(id=4, event_fee=event_fees[0], registration_slot=slot2, payment=payment),
                           RegistrationFee(id=5, event_fee=event_fees[2], registration_slot=slot2, payment=payment)]

        required_fees = get_required_fees(event, payment_details)
        optional_fees = get_optional_fees(event, payment_details)

        self.assertEqual(Decimal(10), required_fees)
        self.assertEqual(Decimal(29), optional_fees)

    def test_get_players(self):
        event = Event.objects.get(pk=6)
        course = Course.objects.get(pk=1)
        holes = list(course.holes.all())
        event_fees = list(EventFee.objects.filter(event=6).all())
        registration = Registration(event=event, course=course, starting_hole=2, starting_order=0)
        user1 = User(id=1, email="player1@test.com")
        player1 = Player(id=1, email="player1@test.com")
        player2 = Player(id=2, email="player2@test.com")
        slot1 = RegistrationSlot(event=event, registration=registration, hole=holes[0], player=player1,
                                 starting_order=0, slot=0, status="R")
        slot2 = RegistrationSlot(event=event, registration=registration, hole=holes[0], player=player2,
                                 starting_order=0, slot=1, status="R")
        slot3 = RegistrationSlot(event=event, registration=registration, hole=holes[0], player=None,
                                 starting_order=0, slot=2, status="P")
        payment = Payment(event=event, user=user1, payment_code="test", notification_type="C", confirmed=1)
        payment_details = [RegistrationFee(id=1, event_fee=event_fees[0], registration_slot=slot1, payment=payment),
                           RegistrationFee(id=2, event_fee=event_fees[1], registration_slot=slot1, payment=payment),
                           RegistrationFee(id=3, event_fee=event_fees[3], registration_slot=slot1, payment=payment),
                           RegistrationFee(id=4, event_fee=event_fees[0], registration_slot=slot2, payment=payment),
                           RegistrationFee(id=5, event_fee=event_fees[2], registration_slot=slot2, payment=payment)]

        players = get_players(event, [slot1, slot2, slot3], payment_details)

        self.assertEqual(2, len(players))
        self.assertEqual(3, len(players[0]["fees"]))
        self.assertEqual(2, len(players[1]["fees"]))

    def test_get_email_recipients(self):
        event = Event.objects.get(pk=6)
        course = Course.objects.get(pk=1)
        holes = list(course.holes.all())
        registration = Registration(event=event, course=course, starting_hole=2, starting_order=0)
        user1 = User(id=1, email="player1@test.com")
        player1 = Player(id=1, email="player1@test.com")
        player2 = Player(id=2, email="player2@test.com")
        slot1 = RegistrationSlot(event=event, registration=registration, hole=holes[0], player=player1,
                                 starting_order=0, slot=0, status="R")
        slot2 = RegistrationSlot(event=event, registration=registration, hole=holes[0], player=player2,
                                 starting_order=0, slot=1, status="R")
        slot3 = RegistrationSlot(event=event, registration=registration, hole=holes[0], player=None,
                                 starting_order=0, slot=2, status="P")

        emails = get_recipients(user1, [slot1, slot2, slot3])

        self.assertEqual(1, len(emails))
        self.assertEqual("player2@test.com", emails[0])
