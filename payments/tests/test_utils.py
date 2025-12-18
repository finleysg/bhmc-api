from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from rest_framework.exceptions import APIException

from courses.models import Course, Hole
from events.models import Event
from payments.models import Payment
from payments.utils import (
    calculate_payment_amount,
    calculate_refund_amount,
    derive_notification_type,
    get_amount_due,
    get_event_url,
    get_fees,
    get_offset,
    get_optional_fees,
    get_payment_slots,
    get_players,
    get_recipients,
    get_required_fees,
    get_start,
    get_starting_hole,
    get_starting_time,
    get_starting_time_offset,
    has_required_fees,
    parse_hours,
    parse_minutes,
    round_half_up,
    slugify,
    update_to_unpaid,
)
from register.models import Registration, RegistrationFee, RegistrationSlot, Player
from django.contrib.auth.models import User


class PaymentCalculationTests(TestCase):
    def test_calculate_payment_amount_zero(self):
        total, fee = calculate_payment_amount(Decimal("0.00"))
        # Formula: (0 + 0.30) / (1 - 0.029) = 0.30 / 0.971 = 0.309...
        self.assertAlmostEqual(float(total), 0.31, places=2)
        self.assertAlmostEqual(float(fee), 0.31, places=2)

    def test_calculate_payment_amount_ten_dollars(self):
        total, fee = calculate_payment_amount(Decimal("10.00"))
        # Formula: (10 + 0.30) / (1 - 0.029) = 10.30 / 0.971 = 10.608...
        self.assertAlmostEqual(float(total), 10.61, places=2)
        self.assertAlmostEqual(float(fee), 0.61, places=2)

    def test_calculate_payment_amount_hundred_dollars(self):
        total, fee = calculate_payment_amount(Decimal("100.00"))
        # Formula: (100 + 0.30) / (1 - 0.029) = 100.30 / 0.971 = 103.29...
        self.assertAlmostEqual(float(total), 103.30, places=2)
        self.assertAlmostEqual(float(fee), 3.30, places=2)

    def test_round_half_up_basic(self):
        self.assertEqual(round_half_up(Decimal("2.5")), 3)
        self.assertEqual(round_half_up(Decimal("2.4")), 2)
        self.assertEqual(round_half_up(Decimal("2.6")), 3)

    def test_round_half_up_with_decimals(self):
        self.assertAlmostEqual(
            float(round_half_up(Decimal("2.555"), 2)), 2.56, places=2
        )
        self.assertAlmostEqual(
            float(round_half_up(Decimal("2.554"), 2)), 2.55, places=2
        )

    def test_round_half_up_negative(self):
        self.assertEqual(round_half_up(Decimal("-2.5")), -2)
        self.assertEqual(round_half_up(Decimal("-2.6")), -3)


class NotificationTypeTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee"]

    def setUp(self):
        self.event = Event.objects.get(pk=1)  # Season registration event (type R)
        self.match_play_event = Event.objects.get(
            pk=2
        )  # Match play (type S in fixture is O but we'll mock)
        self.regular_event = Event.objects.get(pk=3)  # Normal event (type N)

    @mock.patch("payments.utils.current_season")
    def test_derive_notification_type_returning_member(self, mock_season):
        mock_season.return_value = 2021

        class MockPlayer:
            last_season = 2020

        class MockDetail:
            pass

        result = derive_notification_type(self.event, MockPlayer(), [])
        self.assertEqual(result, "R")

    @mock.patch("payments.utils.current_season")
    def test_derive_notification_type_new_member(self, mock_season):
        mock_season.return_value = 2021

        class MockPlayer:
            last_season = 2019

        result = derive_notification_type(self.event, MockPlayer(), [])
        self.assertEqual(result, "N")

    @mock.patch("payments.utils.current_season")
    def test_derive_notification_type_new_member_no_previous_season(self, mock_season):
        mock_season.return_value = 2021

        class MockPlayer:
            last_season = None

        result = derive_notification_type(self.event, MockPlayer(), [])
        self.assertEqual(result, "N")

    def test_derive_notification_type_match_play(self):
        # Create an event with type S (match play)
        event = Event.objects.create(
            event_type="S",
            name="Match Play",
            start_date=date.today(),
        )

        class MockPlayer:
            last_season = 2020

        result = derive_notification_type(event, MockPlayer(), [])
        self.assertEqual(result, "M")

    def test_derive_notification_type_regular_event_with_required_fees(self):
        class MockPlayer:
            last_season = 2020

        event_fee = self.regular_event.fees.filter(is_required=True).first()
        payment_details = [{"event_fee": event_fee}]

        result = derive_notification_type(
            self.regular_event, MockPlayer(), payment_details
        )
        self.assertEqual(result, "C")

    def test_derive_notification_type_regular_event_without_required_fees(self):
        class MockPlayer:
            last_season = 2020

        event_fee = self.regular_event.fees.filter(is_required=False).first()
        payment_details = [{"event_fee": event_fee}]

        result = derive_notification_type(
            self.regular_event, MockPlayer(), payment_details
        )
        self.assertEqual(result, "U")


class FeeCalculationTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee"]

    def setUp(self):
        self.event = Event.objects.get(pk=3)  # Low Gross / Low Net

    def test_has_required_fees_true(self):
        required_fee = self.event.fees.filter(is_required=True).first()
        payment_details = [{"event_fee": required_fee}]
        self.assertTrue(has_required_fees(self.event, payment_details))

    def test_has_required_fees_false(self):
        optional_fee = self.event.fees.filter(is_required=False).first()
        payment_details = [{"event_fee": optional_fee}]
        self.assertFalse(has_required_fees(self.event, payment_details))

    def test_has_required_fees_empty(self):
        payment_details = []
        self.assertFalse(has_required_fees(self.event, payment_details))

    def test_get_amount_due_single(self):
        class MockDetail:
            amount = Decimal("10.00")

        result = get_amount_due(self.event, [MockDetail()])
        self.assertEqual(result, Decimal("10.00"))

    def test_get_amount_due_multiple(self):
        class MockDetail1:
            amount = Decimal("10.00")

        class MockDetail2:
            amount = Decimal("5.00")

        class MockDetail3:
            amount = Decimal("7.50")

        result = get_amount_due(
            self.event, [MockDetail1(), MockDetail2(), MockDetail3()]
        )
        self.assertEqual(result, Decimal("22.50"))

    def test_get_amount_due_empty(self):
        result = get_amount_due(self.event, [])
        self.assertEqual(result, Decimal("0.0"))

    def test_get_required_fees(self):
        required_fee = self.event.fees.filter(is_required=True).first()

        class MockDetail:
            event_fee = required_fee

        result = get_required_fees(self.event, [MockDetail()])
        self.assertEqual(result, required_fee.amount)

    def test_get_optional_fees(self):
        optional_fee = self.event.fees.filter(is_required=False).first()

        class MockDetail:
            event_fee = optional_fee

        result = get_optional_fees(self.event, [MockDetail()])
        self.assertEqual(result, optional_fee.amount)


class StartingPositionTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee", "course", "hole"]

    def setUp(self):
        self.tee_time_event = Event.objects.get(pk=3)  # TT start type, can_choose=True
        self.shotgun_event = Event.objects.get(pk=6)  # SG start type, can_choose=True
        self.course = Course.objects.get(pk=1)
        self.hole = Hole.objects.get(pk=1)

    def test_get_start_tee_time(self):
        class MockRegistration:
            course = Course.objects.get(pk=1)

        class MockSlot:
            starting_order = 0

        result = get_start(self.tee_time_event, MockRegistration(), MockSlot())
        self.assertIn("East", result)
        self.assertIn("3:00 PM", result)

    def test_get_start_shotgun(self):
        class MockRegistration:
            course = Course.objects.get(pk=1)

        class MockSlot:
            starting_order = 0
            hole = Hole.objects.get(pk=1)

        result = get_start(self.shotgun_event, MockRegistration(), MockSlot())
        self.assertIn("East", result)
        self.assertIn("1A", result)

    def test_get_start_unknown_type(self):
        event = Event.objects.create(
            event_type="N",
            name="Unknown Start",
            start_date=date.today(),
            start_type="XX",
        )

        result = get_start(event, None, None)
        self.assertEqual(result, "N/A")

    def test_get_starting_time_can_choose(self):
        class MockRegistration:
            course = Course.objects.get(pk=1)

        class MockSlot:
            starting_order = 0

        result = get_starting_time(self.tee_time_event, MockRegistration(), MockSlot())
        self.assertEqual(result, "East 3:00 PM")

    def test_get_starting_time_cannot_choose(self):
        event = Event.objects.get(pk=4)  # can_choose=False

        result = get_starting_time(event, None, None)
        self.assertEqual(result, "Tee times")

    def test_get_starting_time_with_offset(self):
        class MockRegistration:
            course = Course.objects.get(pk=1)

        class MockSlot:
            starting_order = 1

        result = get_starting_time(self.tee_time_event, MockRegistration(), MockSlot())
        self.assertEqual(result, "East 3:10 PM")

    def test_get_starting_hole_can_choose_first(self):
        class MockRegistration:
            course = Course.objects.get(pk=1)

        class MockSlot:
            starting_order = 0
            hole = Hole.objects.get(pk=1)

        result = get_starting_hole(self.shotgun_event, MockRegistration(), MockSlot())
        self.assertEqual(result, "East 1A")

    def test_get_starting_hole_can_choose_second(self):
        class MockRegistration:
            course = Course.objects.get(pk=1)

        class MockSlot:
            starting_order = 1
            hole = Hole.objects.get(pk=1)

        result = get_starting_hole(self.shotgun_event, MockRegistration(), MockSlot())
        self.assertEqual(result, "East 1B")

    def test_get_starting_hole_cannot_choose(self):
        event = Event.objects.get(pk=4)  # can_choose=False

        result = get_starting_hole(event, None, None)
        self.assertEqual(result, "Shotgun")


class TeeTimeOffsetTests(TestCase):
    def test_get_offset_zero_order(self):
        result = get_offset(0, [10])
        self.assertEqual(result, 0)

    def test_get_offset_single_interval(self):
        result = get_offset(1, [10])
        self.assertEqual(result, 10)
        result = get_offset(2, [10])
        self.assertEqual(result, 20)
        result = get_offset(5, [10])
        self.assertEqual(result, 50)

    def test_get_offset_dual_interval_even_order(self):
        # With [8, 10], even orders: 0->0, 2->(1*(8+10))=18, 4->(2*(8+10))=36
        result = get_offset(2, [8, 10])
        self.assertEqual(result, 18)
        result = get_offset(4, [8, 10])
        self.assertEqual(result, 36)

    def test_get_offset_dual_interval_odd_order(self):
        # With [8, 10], odd orders: 1->(0*(8+10))+8=8, 3->(1*(8+10))+8=26
        result = get_offset(1, [8, 10])
        self.assertEqual(result, 8)
        result = get_offset(3, [8, 10])
        self.assertEqual(result, 26)

    def test_get_starting_time_offset_no_splits(self):
        first_time = datetime(2021, 6, 15, 15, 0)
        result = get_starting_time_offset(first_time, 0, None)
        self.assertEqual(result, first_time)

    def test_get_starting_time_offset_with_splits(self):
        first_time = datetime(2021, 6, 15, 15, 0)
        result = get_starting_time_offset(first_time, 2, "8,10")
        expected = first_time + timedelta(minutes=18)
        self.assertEqual(result, expected)


class TimeParsingTests(TestCase):
    def test_parse_hours_pm(self):
        self.assertEqual(parse_hours("3:00 PM"), 15)
        self.assertEqual(parse_hours("1:00 PM"), 13)
        self.assertEqual(parse_hours("12:00 PM"), 24)  # Note: 12 PM adds 12

    def test_parse_hours_am(self):
        self.assertEqual(parse_hours("7:30 AM"), 7)
        self.assertEqual(parse_hours("9:00 AM"), 9)
        self.assertEqual(parse_hours("12:00 AM"), 12)  # Note: 12 AM doesn't subtract

    def test_parse_minutes(self):
        self.assertEqual(parse_minutes("3:00 PM"), 0)
        self.assertEqual(parse_minutes("7:30 AM"), 30)
        self.assertEqual(parse_minutes("5:45 PM"), 45)


class UrlAndSlugTests(TestCase):
    def test_slugify_basic(self):
        self.assertEqual(slugify("Hello World"), "hello-world")
        self.assertEqual(slugify("Low Gross / Low Net"), "low-gross-low-net")

    def test_slugify_special_chars(self):
        self.assertEqual(slugify("Test! Event @2021"), "test-event-2021")
        self.assertEqual(slugify("Event (Special)"), "event-special")

    def test_slugify_multiple_spaces(self):
        self.assertEqual(slugify("Multiple   Spaces"), "multiple-spaces")

    def test_slugify_leading_trailing_spaces(self):
        self.assertEqual(slugify("  Trimmed  "), "trimmed")

    def test_get_event_url(self):
        class MockEvent:
            start_date = date(2021, 6, 15)
            name = "Low Gross / Low Net"

        result = get_event_url("https://example.com", MockEvent())
        self.assertEqual(
            result, "https://example.com/event/2021-06-15/low-gross-low-net"
        )


class PaymentHelperTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee", "course", "hole", "user", "player"]

    def setUp(self):
        self.event = Event.objects.get(pk=3)
        self.user = User.objects.get(pk=1)

    def test_get_fees(self):
        event_fee = self.event.fees.first()

        class MockDetail:
            amount = Decimal("10.00")

        detail = MockDetail()
        detail.event_fee = event_fee

        result = get_fees(self.event, [detail])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["description"], event_fee.fee_type.name)
        self.assertEqual(result[0]["amount"], "$10.00")

    def test_get_fees_multiple(self):
        fees = list(self.event.fees.all()[:2])

        class MockDetail1:
            event_fee = fees[0]
            amount = Decimal("5.00")

        class MockDetail2:
            event_fee = fees[1]
            amount = Decimal("10.00")

        result = get_fees(self.event, [MockDetail1(), MockDetail2()])
        self.assertEqual(len(result), 2)

    def test_get_recipients_excludes_user(self):
        player1 = Player.objects.get(pk=2)
        player2 = Player.objects.get(pk=3)

        class MockSlot1:
            player = player1

        class MockSlot2:
            player = player2

        result = get_recipients(self.user, [MockSlot1(), MockSlot2()])
        self.assertEqual(len(result), 2)
        self.assertIn(player1.email, result)
        self.assertIn(player2.email, result)
        self.assertNotIn(self.user.email, result)

    def test_get_recipients_handles_none_player(self):
        player1 = Player.objects.get(pk=2)

        class MockSlot1:
            player = player1

        class MockSlot2:
            player = None

        result = get_recipients(self.user, [MockSlot1(), MockSlot2()])
        self.assertEqual(len(result), 1)
        self.assertIn(player1.email, result)

    def test_get_recipients_excludes_same_email(self):
        # Player with same email as user
        player = Player.objects.get(pk=1)  # This should be the admin user's player

        class MockSlot:
            pass

        slot = MockSlot()
        slot.player = player

        result = get_recipients(self.user, [slot])
        self.assertNotIn(self.user.email, result)


class PaymentSlotTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee", "course", "hole", "user", "player"]

    def setUp(self):
        self.event = Event.objects.get(pk=3)
        self.user = User.objects.get(pk=1)
        self.course = Course.objects.get(pk=1)
        self.hole = Hole.objects.get(pk=1)

        # Create a registration with slots
        self.registration = Registration.objects.create(
            event=self.event,
            course=self.course,
            user=self.user,
            signed_up_by=self.user,
        )
        self.slot1 = RegistrationSlot.objects.create(
            event=self.event,
            registration=self.registration,
            hole=self.hole,
            player=Player.objects.get(pk=1),
            starting_order=0,
            slot=0,
        )
        self.slot2 = RegistrationSlot.objects.create(
            event=self.event,
            registration=self.registration,
            hole=self.hole,
            player=Player.objects.get(pk=2),
            starting_order=0,
            slot=1,
        )

    def test_get_payment_slots_single(self):
        class MockFee:
            registration_slot_id = self.slot1.pk

        result = get_payment_slots(self.registration, [MockFee()])
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.slot1)

    def test_get_payment_slots_multiple(self):
        class MockFee1:
            registration_slot_id = self.slot1.pk

        class MockFee2:
            registration_slot_id = self.slot2.pk

        result = get_payment_slots(self.registration, [MockFee1(), MockFee2()])
        self.assertEqual(result.count(), 2)

    def test_get_payment_slots_deduplicates(self):
        class MockFee1:
            registration_slot_id = self.slot1.pk

        class MockFee2:
            registration_slot_id = self.slot1.pk

        result = get_payment_slots(self.registration, [MockFee1(), MockFee2()])
        self.assertEqual(result.count(), 1)


class RefundTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee", "course", "hole", "user", "player"]

    def setUp(self):
        self.event = Event.objects.get(pk=3)
        self.user = User.objects.get(pk=1)
        self.course = Course.objects.get(pk=1)
        self.hole = Hole.objects.get(pk=1)
        self.event_fee = self.event.fees.first()

        # Create payment
        self.payment = Payment.objects.create(
            event=self.event,
            user=self.user,
            payment_code="test",
            payment_key="test-key",
            payment_amount=Decimal("10.00"),
            transaction_fee=Decimal("0.50"),
            confirmed=True,
        )

        # Create registration and slot
        self.registration = Registration.objects.create(
            event=self.event,
            course=self.course,
            user=self.user,
            signed_up_by=self.user,
        )
        self.slot = RegistrationSlot.objects.create(
            event=self.event,
            registration=self.registration,
            hole=self.hole,
            player=Player.objects.get(pk=1),
            starting_order=0,
            slot=0,
        )

        # Create registration fee
        self.reg_fee = RegistrationFee.objects.create(
            event_fee=self.event_fee,
            registration_slot=self.slot,
            is_paid=True,
            payment=self.payment,
        )

    def test_calculate_refund_amount(self):
        refund_fees = [
            {
                "event_fee_id": self.event_fee.id,
                "amount_paid": str(self.event_fee.amount),
            }
        ]
        result = calculate_refund_amount(self.payment, refund_fees)
        self.assertEqual(result, self.event_fee.amount)

    def test_calculate_refund_amount_multiple(self):
        event_fee2 = self.event.fees.all()[1]
        refund_fees = [
            {
                "event_fee_id": self.event_fee.id,
                "amount_paid": str(self.event_fee.amount),
            },
            {"event_fee_id": event_fee2.id, "amount_paid": str(event_fee2.amount)},
        ]
        result = calculate_refund_amount(self.payment, refund_fees)
        self.assertEqual(result, self.event_fee.amount + event_fee2.amount)

    def test_calculate_refund_amount_invalid_amount(self):
        refund_fees = [{"event_fee_id": self.event_fee.id, "amount_paid": "999.99"}]
        with self.assertRaises(APIException):
            calculate_refund_amount(self.payment, refund_fees)

    def test_update_to_unpaid(self):
        self.assertTrue(self.reg_fee.is_paid)
        refund_fees = [{"fee_id": self.reg_fee.pk}]
        update_to_unpaid(refund_fees)
        self.reg_fee.refresh_from_db()
        self.assertFalse(self.reg_fee.is_paid)

    def test_update_to_unpaid_multiple(self):
        # Create another registration fee
        event_fee2 = self.event.fees.all()[1]
        reg_fee2 = RegistrationFee.objects.create(
            event_fee=event_fee2,
            registration_slot=self.slot,
            is_paid=True,
            payment=self.payment,
        )

        refund_fees = [{"fee_id": self.reg_fee.pk}, {"fee_id": reg_fee2.pk}]
        update_to_unpaid(refund_fees)

        self.reg_fee.refresh_from_db()
        reg_fee2.refresh_from_db()
        self.assertFalse(self.reg_fee.is_paid)
        self.assertFalse(reg_fee2.is_paid)


class GetPlayersTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee", "course", "hole", "user", "player"]

    def setUp(self):
        self.event = Event.objects.get(pk=3)
        self.player1 = Player.objects.get(pk=1)
        self.player2 = Player.objects.get(pk=2)
        self.event_fee = self.event.fees.first()

    def test_get_players_single(self):
        class MockSlot:
            player = self.player1

        class MockDetail:
            registration_slot = MockSlot()
            event_fee = self.event_fee
            amount = Decimal("5.00")

        slots = [MockSlot()]
        result = get_players(self.event, slots, [MockDetail()])

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["name"], f"{self.player1.first_name} {self.player1.last_name}"
        )
        self.assertEqual(result[0]["email"], self.player1.email)

    def test_get_players_skips_none(self):
        class MockSlot1:
            player = self.player1

        class MockSlot2:
            player = None

        slots = [MockSlot1(), MockSlot2()]
        result = get_players(self.event, slots, [])

        self.assertEqual(len(result), 1)
