from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.db import transaction

from events.models import Event
from core.models import SeasonSettings
from golfgenius.services import GolfGeniusEventService, EventSyncResult
from golfgenius.client import GolfGeniusAPIClient, GolfGeniusAPIError


class TestEventSyncResult(TestCase):
    """Test EventSyncResult container class"""
    
    def test_init(self):
        result = EventSyncResult()
        self.assertEqual(result.total_bhmc_events, 0)
        self.assertEqual(result.total_gg_events, 0)
        self.assertEqual(result.matched_events, 0)
        self.assertEqual(result.updated_events, 0)
        self.assertEqual(result.skipped_events, 0)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.matches), 0)
        self.assertEqual(len(result.unmatched_bhmc_events), 0)
        self.assertEqual(len(result.unmatched_gg_events), 0)
    
    def test_to_dict(self):
        result = EventSyncResult()
        result.total_bhmc_events = 5
        result.total_gg_events = 3
        result.matched_events = 2
        result.updated_events = 1
        
        data = result.to_dict()
        
        self.assertEqual(data['total_bhmc_events'], 5)
        self.assertEqual(data['total_gg_events'], 3)
        self.assertEqual(data['matched_events'], 2)
        self.assertEqual(data['updated_events'], 1)
        self.assertIn('errors', data)
        self.assertIn('matches', data)


class TestGolfGeniusEventService(TestCase):
    """Test GolfGeniusEventService functionality"""
    
    def setUp(self):
        self.mock_client = Mock(spec=GolfGeniusAPIClient)
        self.service = GolfGeniusEventService(api_client=self.mock_client)
        
        # Create test data
        self.test_event = Event.objects.create(
            name="Test Event",
            start_date=date(2024, 6, 15),
            rounds=2,
            season=2024,
            event_type="N"
        )
        
        self.test_season_settings = SeasonSettings.objects.create(
            season=2024,
            is_active=True,
            member_event_id=self.test_event.id,
            match_play_event_id=self.test_event.id
        )
    
    def test_get_target_season_with_override(self):
        """Test season detection with override"""
        season = self.service._get_target_season(2023)
        self.assertEqual(season, 2023)
    
    def test_get_target_season_from_active_settings(self):
        """Test season detection from active SeasonSettings"""
        season = self.service._get_target_season(None)
        self.assertEqual(season, 2024)
    
    def test_calculate_end_date_single_round(self):
        """Test end date calculation for single round event"""
        event = Event(start_date=date(2024, 6, 15), rounds=1)
        end_date = self.service._calculate_end_date(event)
        self.assertEqual(end_date, date(2024, 6, 15))
    
    def test_calculate_end_date_multiple_rounds(self):
        """Test end date calculation for multi-round event"""
        event = Event(start_date=date(2024, 6, 15), rounds=3)
        end_date = self.service._calculate_end_date(event)
        self.assertEqual(end_date, date(2024, 6, 17))  # start + 2 days
    
    def test_calculate_end_date_no_rounds(self):
        """Test end date calculation when rounds is None"""
        event = Event(start_date=date(2024, 6, 15), rounds=None)
        end_date = self.service._calculate_end_date(event)
        self.assertEqual(end_date, date(2024, 6, 15))
    
    def test_events_exact_match(self):
        """Test exact date matching between events"""
        bhmc_event = Event(start_date=date(2024, 6, 15))
        gg_event = {"start_date": "2024-06-15"}
        
        self.assertTrue(self.service._events_exact_match(bhmc_event, gg_event))
    
    def test_events_exact_match_different_dates(self):
        """Test exact date matching with different dates"""
        bhmc_event = Event(start_date=date(2024, 6, 15))
        gg_event = {"start_date": "2024-06-16"}
        
        self.assertFalse(self.service._events_exact_match(bhmc_event, gg_event))
    
    def test_events_overlap_single_day(self):
        """Test date overlap for single day events"""
        bhmc_event = Event(start_date=date(2024, 6, 15), rounds=1)
        gg_event = {"start_date": "2024-06-15", "end_date": "2024-06-15"}
        
        self.assertTrue(self.service._events_overlap(bhmc_event, gg_event))
    
    def test_events_overlap_multi_day(self):
        """Test date overlap for multi-day events"""
        bhmc_event = Event(start_date=date(2024, 6, 15), rounds=3)  # June 15-17
        gg_event = {"start_date": "2024-06-16", "end_date": "2024-06-18"}  # June 16-18
        
        self.assertTrue(self.service._events_overlap(bhmc_event, gg_event))
    
    def test_events_no_overlap(self):
        """Test no overlap between events"""
        bhmc_event = Event(start_date=date(2024, 6, 15), rounds=1)  # June 15
        gg_event = {"start_date": "2024-06-17", "end_date": "2024-06-17"}  # June 17
        
        self.assertFalse(self.service._events_overlap(bhmc_event, gg_event))
    
    @patch('golfgenius.services.Event.objects')
    def test_get_bhmc_events_force_update(self, mock_events):
        """Test getting BHMC events with force update"""
        mock_queryset = Mock()
        mock_events.filter.return_value = mock_queryset
        mock_queryset.order_by.return_value = [self.test_event]
        
        events = self.service._get_bhmc_events(2024, force_update=True)
        
        mock_events.filter.assert_called_once_with(season=2024)
        self.assertEqual(len(events), 1)
    
    @patch('golfgenius.services.Event.objects')
    def test_get_bhmc_events_no_force_update(self, mock_events):
        """Test getting BHMC events without force update"""
        mock_queryset = Mock()
        mock_filter_queryset = Mock()
        mock_events.filter.return_value = mock_queryset
        mock_queryset.filter.return_value = mock_filter_queryset
        mock_filter_queryset.order_by.return_value = [self.test_event]
        
        events = self.service._get_bhmc_events(2024, force_update=False)
        
        mock_events.filter.assert_called_once_with(season=2024)
        # Should filter for events without gg_id
        mock_queryset.filter.assert_called_once()
        self.assertEqual(len(events), 1)
    
    def test_get_golf_genius_events_success(self):
        """Test successful retrieval of Golf Genius events"""
        # Mock API responses
        self.mock_client.get_categories.return_value = [
            {"category": {"id": "123", "name": "Men's Club"}}
        ]
        self.mock_client.get_seasons.return_value = [
            {"season": {"id": "456", "name": "2024"}}
        ]
        self.mock_client.get_events.return_value = [
            {"event": {"id": "789", "name": "Test GG Event", "start_date": "2024-06-15"}}
        ]
        
        events = self.service._get_golf_genius_events(2024)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["id"], "789")
        self.assertEqual(events[0]["name"], "Test GG Event")
    
    def test_get_golf_genius_events_no_mens_club_category(self):
        """Test handling when Men's Club category is not found"""
        self.mock_client.get_categories.return_value = [
            {"category": {"id": "123", "name": "Other Category"}}
        ]
        
        events = self.service._get_golf_genius_events(2024)
        
        self.assertEqual(len(events), 0)
    
    def test_get_golf_genius_events_no_season(self):
        """Test handling when target season is not found"""
        self.mock_client.get_categories.return_value = [
            {"category": {"id": "123", "name": "Men's Club"}}
        ]
        self.mock_client.get_seasons.return_value = [
            {"season": {"id": "456", "name": "2023"}}  # Different year
        ]
        
        events = self.service._get_golf_genius_events(2024)
        
        self.assertEqual(len(events), 0)
    
    def test_get_mens_club_category_id_success(self):
        """Test successful retrieval of Men's Club category ID"""
        self.mock_client.get_categories.return_value = [
            {"category": {"id": "123", "name": "Men's Club"}},
            {"category": {"id": "456", "name": "Women's League"}}
        ]
        
        category_id = self.service._get_mens_club_category_id()
        
        self.assertEqual(category_id, "123")
    
    def test_get_mens_club_category_id_case_insensitive(self):
        """Test Men's Club category matching is case insensitive"""
        self.mock_client.get_categories.return_value = [
            {"category": {"id": "123", "name": "MENS CLUB"}}
        ]
        
        category_id = self.service._get_mens_club_category_id()
        
        self.assertEqual(category_id, "123")
    
    def test_get_mens_club_category_id_not_found(self):
        """Test handling when Men's Club category is not found"""
        self.mock_client.get_categories.return_value = [
            {"category": {"id": "123", "name": "Other Category"}}
        ]
        
        category_id = self.service._get_mens_club_category_id()
        
        self.assertIsNone(category_id)
    
    @patch('golfgenius.services.Event.objects')
    def test_update_event_match_success(self, mock_events):
        """Test successful event update"""
        result = EventSyncResult()
        gg_event = {"id": "789", "name": "Test GG Event"}
        
        # Mock the filter to return no existing events with this gg_id
        mock_filter = Mock()
        mock_filter.exclude.return_value.first.return_value = None
        mock_events.filter.return_value = mock_filter
        
        self.service._update_event_match(self.test_event, gg_event, "exact_date", result)
        
        self.assertEqual(self.test_event.gg_id, "789")
        self.assertEqual(result.updated_events, 1)
        self.assertEqual(result.matched_events, 1)
    
    @patch('golfgenius.services.Event.objects')
    def test_update_event_match_duplicate_gg_id(self, mock_events):
        """Test handling duplicate Golf Genius ID"""
        result = EventSyncResult()
        gg_event = {"id": "789", "name": "Test GG Event"}
        
        # Mock existing event with same gg_id
        existing_event = Event(name="Existing Event", gg_id="789")
        mock_filter = Mock()
        mock_filter.exclude.return_value.first.return_value = existing_event
        mock_events.filter.return_value = mock_filter
        
        self.service._update_event_match(self.test_event, gg_event, "exact_date", result)
        
        # Should not update the event
        self.assertIsNone(self.test_event.gg_id)
        self.assertEqual(result.updated_events, 0)
        self.assertEqual(len(result.errors), 1)
    
    def test_get_sync_status(self):
        """Test sync status calculation"""
        # Create another event with gg_id
        Event.objects.create(
            name="Synced Event",
            start_date=date(2024, 7, 1),
            season=2024,
            event_type="N",
            gg_id="123"
        )
        
        status = self.service.get_sync_status()
        
        self.assertEqual(status['total_events'], 2)
        self.assertEqual(status['synced_events'], 1)
        self.assertEqual(status['unsynced_events'], 1)
        self.assertEqual(status['sync_percentage'], 50.0)
    
    @patch.object(GolfGeniusEventService, '_get_golf_genius_events')
    @patch.object(GolfGeniusEventService, '_get_bhmc_events')
    @patch.object(GolfGeniusEventService, '_get_target_season')
    def test_sync_events_success(self, mock_get_season, mock_get_bhmc, mock_get_gg):
        """Test successful event synchronization"""
        # Setup mocks
        mock_get_season.return_value = 2024
        mock_get_bhmc.return_value = [self.test_event]
        mock_get_gg.return_value = [
            {"id": "789", "name": "Test GG Event", "start_date": "2024-06-15"}
        ]
        
        result = self.service.sync_events()
        
        self.assertEqual(result.total_bhmc_events, 1)
        self.assertEqual(result.total_gg_events, 1)
        self.assertTrue(result.matched_events > 0 or len(result.unmatched_bhmc_events) > 0)
    
    @patch.object(GolfGeniusEventService, '_get_target_season')
    def test_sync_events_no_season(self, mock_get_season):
        """Test sync when no season can be determined"""
        mock_get_season.return_value = None
        
        result = self.service.sync_events()
        
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Could not determine target season", result.errors[0]["error"])
    
    @patch.object(GolfGeniusEventService, '_get_golf_genius_events')
    @patch.object(GolfGeniusEventService, '_get_bhmc_events')
    @patch.object(GolfGeniusEventService, '_get_target_season')
    def test_sync_events_no_bhmc_events(self, mock_get_season, mock_get_bhmc, mock_get_gg):
        """Test sync when no BHMC events are found"""
        mock_get_season.return_value = 2024
        mock_get_bhmc.return_value = []
        
        result = self.service.sync_events()
        
        self.assertEqual(result.total_bhmc_events, 0)
        # Should return early without calling Golf Genius API
        mock_get_gg.assert_not_called()
    
    @patch.object(GolfGeniusEventService, '_get_golf_genius_events')
    @patch.object(GolfGeniusEventService, '_get_bhmc_events')
    @patch.object(GolfGeniusEventService, '_get_target_season')
    def test_sync_events_no_gg_events(self, mock_get_season, mock_get_bhmc, mock_get_gg):
        """Test sync when no Golf Genius events are found"""
        mock_get_season.return_value = 2024
        mock_get_bhmc.return_value = [self.test_event]
        mock_get_gg.return_value = []
        
        result = self.service.sync_events()
        
        self.assertEqual(result.total_bhmc_events, 1)
        self.assertEqual(result.total_gg_events, 0)
        self.assertEqual(len(result.unmatched_bhmc_events), 1)


class TestEventSyncIntegration(TestCase):
    """Integration tests for event synchronization"""
    
    def setUp(self):
        self.service = GolfGeniusEventService()
        
        # Create test events
        self.event1 = Event.objects.create(
            name="Spring Tournament",
            start_date=date(2024, 5, 15),
            rounds=1,
            season=2024,
            event_type="W"
        )
        
        self.event2 = Event.objects.create(
            name="Summer Championship",
            start_date=date(2024, 7, 20),
            rounds=2,
            season=2024,
            event_type="W"
        )
        
        self.event3 = Event.objects.create(
            name="Already Synced Event",
            start_date=date(2024, 8, 10),
            rounds=1,
            season=2024,
            event_type="N",
            gg_id="999"  # Already has Golf Genius ID
        )
    
    def test_match_events_exact_date_priority(self):
        """Test that exact date matches take priority over overlaps"""
        bhmc_events = [self.event1, self.event2]
        gg_events = [
            {"id": "100", "name": "Exact Match", "start_date": "2024-05-15", "end_date": "2024-05-15"},
            {"id": "200", "name": "Overlap Match", "start_date": "2024-05-14", "end_date": "2024-05-16"}
        ]
        
        result = EventSyncResult()
        result.total_bhmc_events = len(bhmc_events)
        result.total_gg_events = len(gg_events)
        
        # Mock the update method to avoid database operations
        with patch.object(self.service, '_update_event_match') as mock_update:
            self.service._match_events(bhmc_events, gg_events, result, force_update=False)
        
        # Should prefer exact match over overlap
        mock_update.assert_called()
        call_args = mock_update.call_args_list[0]
        self.assertEqual(call_args[0][1]["id"], "100")  # Exact match event
        self.assertEqual(call_args[0][2], "exact_date")  # Match type
    
    def test_get_sync_status_integration(self):
        """Test sync status calculation with real data"""
        status = self.service.get_sync_status()
        
        self.assertEqual(status['total_events'], 3)
        self.assertEqual(status['synced_events'], 1)  # Only event3 has gg_id
        self.assertEqual(status['unsynced_events'], 2)
        self.assertAlmostEqual(status['sync_percentage'], 33.33, places=1)


class TestSingleEventSync(TestCase):
    """Test single event sync functionality"""

    def setUp(self):
        self.service = GolfGeniusEventService()
        
        # Create test event
        self.test_event = Event.objects.create(
            name="Test Event",
            start_date=date(2024, 6, 15),
            rounds=1,
            season=2024
        )
    
    @patch.object(GolfGeniusEventService, '_get_golf_genius_events')
    def test_sync_single_event_success(self, mock_get_gg_events):
        """Test successful single event sync"""
        # Mock Golf Genius events
        mock_get_gg_events.return_value = [
            {
                "id": "789",
                "name": "Test GG Event",
                "start_date": "2024-06-15",
                "end_date": "2024-06-15"
            }
        ]
        
        # Perform single event sync
        result = self.service.sync_single_event(self.test_event.id)
        
        # Verify results
        self.assertEqual(result.total_bhmc_events, 1)
        self.assertEqual(result.total_gg_events, 1)
        self.assertEqual(result.matched_events, 1)
        self.assertEqual(result.updated_events, 1)
        self.assertEqual(len(result.errors), 0)
        
        # Verify event was updated
        self.test_event.refresh_from_db()
        self.assertEqual(self.test_event.gg_id, "789")
        
        # Verify match details
        self.assertEqual(len(result.matches), 1)
        match = result.matches[0]
        self.assertEqual(match["bhmc_event_id"], self.test_event.id)
        self.assertEqual(match["gg_event_id"], "789")
        self.assertEqual(match["match_type"], "exact_date")
    
    def test_sync_single_event_not_found(self):
        """Test sync when event ID doesn't exist"""
        result = self.service.sync_single_event(99999)  # Non-existent ID
        
        # Verify error handling
        self.assertEqual(result.total_bhmc_events, 0)
        self.assertEqual(result.matched_events, 0)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("not found", result.errors[0]["error"])
    
    def test_sync_single_event_no_season(self):
        """Test sync when event has no season (season=0)"""
        # Create event with season=0 (no season)
        no_season_event = Event.objects.create(
            name="No Season Event",
            start_date=date(2024, 6, 15),
            rounds=1,
            season=0  # Default value indicating no season
        )
        
        result = self.service.sync_single_event(no_season_event.id)
        
        # Verify error handling
        self.assertEqual(result.matched_events, 0)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("no season assigned", result.errors[0]["error"])
    
    def test_sync_single_event_already_has_gg_id(self):
        """Test sync when event already has Golf Genius ID"""
        # Set existing Golf Genius ID
        self.test_event.gg_id = "existing_123"
        self.test_event.save()
        
        result = self.service.sync_single_event(self.test_event.id, force_update=False)
        
        # Verify event was skipped
        self.assertEqual(result.matched_events, 0)
        self.assertEqual(result.skipped_events, 1)
        self.assertEqual(len(result.errors), 0)
    
    @patch.object(GolfGeniusEventService, '_get_golf_genius_events')
    def test_sync_single_event_force_update(self, mock_get_gg_events):
        """Test single event sync with force update"""
        # Mock Golf Genius events
        mock_get_gg_events.return_value = [
            {
                "id": "new_789",
                "name": "New GG Event",
                "start_date": "2024-06-15",
                "end_date": "2024-06-15"
            }
        ]
        
        # Set existing Golf Genius ID
        self.test_event.gg_id = "old_123"
        self.test_event.save()
        
        result = self.service.sync_single_event(self.test_event.id, force_update=True)
        
        # Verify event was updated despite existing ID
        self.assertEqual(result.matched_events, 1)
        self.assertEqual(result.updated_events, 1)
        self.assertEqual(result.skipped_events, 0)
        
        # Verify new Golf Genius ID
        self.test_event.refresh_from_db()
        self.assertEqual(self.test_event.gg_id, "new_789")
    
    @patch.object(GolfGeniusEventService, '_get_golf_genius_events')
    def test_sync_single_event_no_match(self, mock_get_gg_events):
        """Test single event sync when no Golf Genius events match"""
        # Mock Golf Genius events with different dates
        mock_get_gg_events.return_value = [
            {
                "id": "789",
                "name": "Different Date Event",
                "start_date": "2024-07-15",  # Different date
                "end_date": "2024-07-15"
            }
        ]
        
        result = self.service.sync_single_event(self.test_event.id)
        
        # Verify no match
        self.assertEqual(result.matched_events, 0)
        self.assertEqual(result.updated_events, 0)
        self.assertEqual(len(result.unmatched_bhmc_events), 1)
        self.assertEqual(len(result.errors), 0)
    
    @patch.object(GolfGeniusEventService, '_get_golf_genius_events')
    def test_sync_single_event_no_gg_events(self, mock_get_gg_events):
        """Test single event sync when no Golf Genius events found"""
        # Mock no Golf Genius events
        mock_get_gg_events.return_value = []
        
        result = self.service.sync_single_event(self.test_event.id)
        
        # Verify no match
        self.assertEqual(result.total_gg_events, 0)
        self.assertEqual(result.matched_events, 0)
        self.assertEqual(len(result.unmatched_bhmc_events), 1)