from datetime import timedelta

from django.test import TestCase
from django.utils import timezone as tz
from unittest import mock

from events.models import Event
from register.exceptions import EventRegistrationWaveError
from register.serializers import get_current_wave, get_starting_wave, validate_wave_is_available


class WaveLogicTests(TestCase):
    def setUp(self):
        # Create a test event with wave configuration
        self.event = Event.objects.create(
            name="Test Event",
            start_date=tz.now().date() + timedelta(days=7),
            signup_start=tz.now() - timedelta(days=1),
            signup_end=tz.now() + timedelta(days=6),
            priority_signup_start=tz.now() - timedelta(hours=2),
            signup_waves=4,
            total_groups=40,
            can_choose=True,
            registration_type="M"  # Enable registration
        )

    def test_get_current_wave_before_priority_start(self):
        """Test that get_current_wave returns 0 before priority signup starts."""
        # Set priority start to future
        self.event.priority_signup_start = tz.now() + timedelta(hours=1)
        self.event.save()

        current_wave = get_current_wave(self.event)
        self.assertEqual(current_wave, 0)

    def test_get_current_wave_during_priority_window_wave_1(self):
        """Test wave 1 calculation (first 25% of priority window)."""
        # Set priority window: 4 hours ago to 0 hours from now (so current time is at end of priority window)
        self.event.priority_signup_start = tz.now() - timedelta(hours=4)
        self.event.signup_start = tz.now()
        self.event.save()

        # Mock time to be 1 hour into 4-hour window (25% elapsed) - should be wave 1
        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = self.event.priority_signup_start + timedelta(hours=1)
            current_wave = get_current_wave(self.event)
            self.assertEqual(current_wave, 1)

    def test_get_current_wave_during_priority_window_wave_2(self):
        """Test wave 2 calculation (25-50% of priority window)."""
        # Set priority window: 2 hours ago to 2 hours from now (4 hour window)
        self.event.priority_signup_start = tz.now() - timedelta(hours=2)
        self.event.signup_start = tz.now() + timedelta(hours=2)
        self.event.save()

        # Mock time to be 75 minutes into 4-hour window (31.25% elapsed) - should be wave 2
        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = self.event.priority_signup_start + timedelta(minutes=75)
            current_wave = get_current_wave(self.event)
            self.assertEqual(current_wave, 2)

    def test_get_current_wave_during_priority_window_wave_4(self):
        """Test wave 4 calculation (last wave before general signup)."""
        # Set priority window: 2 hours ago to 2 hours from now (4 hour window)
        self.event.priority_signup_start = tz.now() - timedelta(hours=2)
        self.event.signup_start = tz.now() + timedelta(hours=2)
        self.event.save()

        # Mock time to be 210 minutes into 4-hour window (87.5% elapsed) - should be wave 4
        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = self.event.priority_signup_start + timedelta(minutes=210)
            current_wave = get_current_wave(self.event)
            self.assertEqual(current_wave, 4)

    def test_get_current_wave_after_priority_window(self):
        """Test that get_current_wave returns signup_waves + 1 after priority window."""
        # Set priority window to past
        self.event.priority_signup_start = tz.now() - timedelta(hours=4)
        self.event.signup_start = tz.now() - timedelta(hours=2)
        self.event.save()

        current_wave = get_current_wave(self.event)
        self.assertEqual(current_wave, 5)  # 4 + 1

    def test_get_current_wave_edge_cases(self):
        """Test edge cases for get_current_wave."""
        # Test with None signup_waves
        self.event.signup_waves = None
        self.event.save()
        self.assertEqual(get_current_wave(self.event), 999)

        # Test with zero signup_waves
        self.event.signup_waves = 0
        self.event.save()
        self.assertEqual(get_current_wave(self.event), 999)

        # Test with None priority_signup_start
        self.event.signup_waves = 4
        self.event.priority_signup_start = None
        self.event.save()
        self.assertEqual(get_current_wave(self.event), 999)

        # Test with None signup_start
        self.event.priority_signup_start = tz.now() - timedelta(hours=2)
        self.event.signup_start = None
        self.event.save()
        self.assertEqual(get_current_wave(self.event), 999)

    def test_get_starting_wave_even_distribution(self):
        """Test slot distribution with even division (40 groups / 4 waves = 10 per wave)."""
        # Wave 1: slots 0-9
        self.assertEqual(get_starting_wave(self.event, 0), 1)
        self.assertEqual(get_starting_wave(self.event, 9), 1)

        # Wave 2: slots 10-19
        self.assertEqual(get_starting_wave(self.event, 10), 2)
        self.assertEqual(get_starting_wave(self.event, 19), 2)

        # Wave 3: slots 20-29
        self.assertEqual(get_starting_wave(self.event, 20), 3)
        self.assertEqual(get_starting_wave(self.event, 29), 3)

        # Wave 4: slots 30-39
        self.assertEqual(get_starting_wave(self.event, 30), 4)
        self.assertEqual(get_starting_wave(self.event, 39), 4)

    def test_get_starting_wave_uneven_distribution(self):
        """Test slot distribution with uneven division (42 groups / 4 waves)."""
        # New logic: distribute remainder evenly among first waves
        # base = 42 // 4 = 10, remainder = 42 % 4 = 2
        # First 2 waves get 11 slots each, last 2 waves get 10 slots each
        self.event.total_groups = 42
        self.event.save()

        # Wave 1: slots 0-10 (11 slots)
        self.assertEqual(get_starting_wave(self.event, 0), 1)
        self.assertEqual(get_starting_wave(self.event, 10), 1)

        # Wave 2: slots 11-21 (11 slots)
        self.assertEqual(get_starting_wave(self.event, 11), 2)
        self.assertEqual(get_starting_wave(self.event, 21), 2)

        # Wave 3: slots 22-31 (10 slots)
        self.assertEqual(get_starting_wave(self.event, 22), 3)
        self.assertEqual(get_starting_wave(self.event, 31), 3)

        # Wave 4: slots 32-41 (10 slots)
        self.assertEqual(get_starting_wave(self.event, 32), 4)
        self.assertEqual(get_starting_wave(self.event, 41), 4)

    def test_get_starting_wave_edge_cases(self):
        """Test edge cases for get_starting_wave."""
        # Test with None signup_waves
        self.event.signup_waves = None
        self.event.save()
        self.assertEqual(get_starting_wave(self.event, 5), 1)

        # Test with zero signup_waves
        self.event.signup_waves = 0
        self.event.save()
        self.assertEqual(get_starting_wave(self.event, 5), 1)

        # Test with None total_groups
        self.event.signup_waves = 4
        self.event.total_groups = None
        self.event.save()
        self.assertEqual(get_starting_wave(self.event, 5), 1)

        # Test with zero total_groups
        self.event.total_groups = 0
        self.event.save()
        self.assertEqual(get_starting_wave(self.event, 5), 1)

    def test_get_starting_wave_boundary_conditions(self):
        """Test boundary conditions for wave assignment."""
        # Test with 5 waves
        self.event.signup_waves = 5
        self.event.total_groups = 37  # New logic: base=7, remainder=2, first 2 waves get 8 slots each, last 3 get 7
        self.event.save()

        # Wave 1: 0-7 (8 slots), Wave 2: 8-15 (8 slots), Wave 3: 16-22 (7 slots), Wave 4: 23-29 (7 slots), Wave 5: 30-36 (7 slots)
        self.assertEqual(get_starting_wave(self.event, 7), 1)
        self.assertEqual(get_starting_wave(self.event, 8), 2)
        self.assertEqual(get_starting_wave(self.event, 15), 2)
        self.assertEqual(get_starting_wave(self.event, 16), 3)
        self.assertEqual(get_starting_wave(self.event, 22), 3)
        self.assertEqual(get_starting_wave(self.event, 23), 4)
        self.assertEqual(get_starting_wave(self.event, 29), 4)
        self.assertEqual(get_starting_wave(self.event, 30), 5)
        self.assertEqual(get_starting_wave(self.event, 36), 5)

    def test_validate_wave_is_available_success(self):
        """Test successful validation when current_wave >= slot_wave."""
        # Mock current wave to be 2
        with mock.patch('register.serializers.get_current_wave', return_value=2):
            # Slot in wave 1 should be allowed
            validate_wave_is_available(self.event, 5)  # wave 1 slot
            # Slot in wave 2 should be allowed
            validate_wave_is_available(self.event, 15)  # wave 2 slot

    def test_validate_wave_is_available_failure(self):
        """Test that EventRegistrationWaveError is raised when current_wave < slot_wave."""
        # Ensure event is in priority window
        self.event.priority_signup_start = tz.now() - timedelta(hours=1)
        self.event.signup_start = tz.now() + timedelta(hours=1)
        self.event.save()

        # Mock current wave to be 2
        with mock.patch('register.serializers.get_current_wave', return_value=2):
            # Slot in wave 3 should fail
            with self.assertRaises(EventRegistrationWaveError):
                validate_wave_is_available(self.event, 25)  # wave 3 slot

            # Slot in wave 4 should fail
            with self.assertRaises(EventRegistrationWaveError):
                validate_wave_is_available(self.event, 35)  # wave 4 slot

    def test_validate_wave_is_available_non_priority_window(self):
        """Test that validation passes when not in priority window."""
        # Change to regular registration window by setting times so we're in registration window
        self.event.priority_signup_start = tz.now() - timedelta(hours=4)
        self.event.signup_start = tz.now() - timedelta(hours=2)
        self.event.signup_end = tz.now() + timedelta(hours=2)
        self.event.save()

        # Should not perform wave validation
        validate_wave_is_available(self.event, 35)  # Would be wave 4

    def test_validate_wave_is_available_not_can_choose(self):
        """Test that validation passes when event doesn't allow choosing."""
        self.event.can_choose = False
        self.event.save()

        # Should not perform wave validation
        validate_wave_is_available(self.event, 35)  # Would be wave 4

    def test_validate_wave_is_available_no_waves(self):
        """Test that validation passes when signup_waves is None."""
        self.event.signup_waves = None
        self.event.save()

        # Should not perform wave validation
        validate_wave_is_available(self.event, 35)

    def test_integration_wave_logic(self):
        """Integration test combining all wave logic functions."""
        # Set up a 3-wave event with 30 groups over 90 minutes
        self.event.signup_waves = 3
        self.event.total_groups = 30
        self.event.priority_signup_start = tz.now() - timedelta(minutes=30)  # Started 30 min ago
        self.event.signup_start = tz.now() + timedelta(minutes=60)  # Ends in 60 min
        self.event.save()

        # At 30 minutes in (33% elapsed), should be wave 1
        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = self.event.priority_signup_start + timedelta(minutes=30)
            current_wave = get_current_wave(self.event)
            self.assertEqual(current_wave, 1)

            # Slots 0-9 should be available (wave 1)
            validate_wave_is_available(self.event, 0)
            validate_wave_is_available(self.event, 9)

            # Slots 10-19 should not be available (wave 2)
            with self.assertRaises(EventRegistrationWaveError):
                validate_wave_is_available(self.event, 10)

        # At 60 minutes in (67% elapsed), should be wave 2
        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = self.event.priority_signup_start + timedelta(minutes=60)
            current_wave = get_current_wave(self.event)
            self.assertEqual(current_wave, 2)

            # Slots 0-19 should be available (waves 1-2)
            validate_wave_is_available(self.event, 0)
            validate_wave_is_available(self.event, 19)

            # Slots 20-29 should not be available (wave 3)
            with self.assertRaises(EventRegistrationWaveError):
                validate_wave_is_available(self.event, 20)

    def test_validate_wave_is_available_with_hole_number(self):
        """Test that validate_wave_is_available correctly uses hole_number for shotgun starts."""
        # Set up event for priority window and shotgun start
        self.event.start_type = "SG"
        self.event.priority_signup_start = tz.now() - timedelta(hours=1)
        self.event.signup_start = tz.now() + timedelta(hours=1)
        self.event.can_choose = True
        self.event.signup_waves = 4
        self.event.total_groups = 40
        self.event.save()

        # Mock time to be in priority window and current wave to be 2
        mock_now = tz.now() - timedelta(minutes=30)  # Between priority_signup_start and signup_start
        with mock.patch('django.utils.timezone.now', return_value=mock_now), \
             mock.patch('register.serializers.get_current_wave', return_value=2):
            # For hole 1, starting_order 0: effective_order = (1-1)*2 + 0 = 0, wave = (0//10) + 1 = 1 (should pass)
            validate_wave_is_available(self.event, 0, hole_number=1)

            # For hole 10, starting_order 0: effective_order = (10-1)*2 + 0 = 18, wave = (18//10) + 1 = 2 (should pass)
            validate_wave_is_available(self.event, 0, hole_number=10)

            # For hole 15, starting_order 0: effective_order = (15-1)*2 + 0 = 28, wave = (28//10) + 1 = 3 (should fail)
            with self.assertRaises(EventRegistrationWaveError):
                validate_wave_is_available(self.event, 0, hole_number=15)

    def test_shotgun_wave_assignment(self):
        """Test wave assignment behavior for shotgun starts where starting_order may be low/repeated."""
        # Simulate a shotgun event with 36 groups (18 holes * 2 groups per hole)
        self.event.start_type = "SG"  # Shotgun
        self.event.total_groups = 36
        self.event.signup_waves = 4
        self.event.save()

        # For shotgun starts, starting_order is often 0 for "A" groups and 1 for "B" groups
        # But this would put ALL groups in Wave 1 (since 0//9=0, 1//9=0)
        self.assertEqual(get_starting_wave(self.event, 0), 1)  # A groups -> Wave 1
        self.assertEqual(get_starting_wave(self.event, 1), 1)  # B groups -> Wave 1

        # To have effective wave distribution for shotgun, starting_order needs to be unique across the event
        # e.g., 0-35 for 36 groups
        self.assertEqual(get_starting_wave(self.event, 0), 1)   # First group -> Wave 1
        self.assertEqual(get_starting_wave(self.event, 8), 1)   # 9th group -> Wave 1
        self.assertEqual(get_starting_wave(self.event, 9), 2)   # 10th group -> Wave 2
        self.assertEqual(get_starting_wave(self.event, 17), 2)  # 18th group -> Wave 2
        self.assertEqual(get_starting_wave(self.event, 18), 3)  # 19th group -> Wave 3
        self.assertEqual(get_starting_wave(self.event, 26), 3)  # 27th group -> Wave 3
        self.assertEqual(get_starting_wave(self.event, 27), 4)  # 28th group -> Wave 4
        self.assertEqual(get_starting_wave(self.event, 35), 4)  # 36th group -> Wave 4
