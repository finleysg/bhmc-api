import os
import json
from unittest.mock import patch, Mock
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from register.models import Player
from .client import GolfGeniusAPIClient, GolfGeniusAPIError, GolfGeniusAuthError
from .services import PlayerSyncService


class GolfGeniusAPIClientTestCase(TestCase):
    """
    Test cases for Golf Genius API client
    """
    
    def setUp(self):
        self.api_key = "test_api_key"
        self.client = GolfGeniusAPIClient(api_key=self.api_key)
    
    def test_client_initialization(self):
        """Test client initializes correctly"""
        self.assertEqual(self.client.api_key, self.api_key)
        self.assertEqual(self.client.base_url, "https://www.golfgenius.com")
        self.assertIsNotNone(self.client.session)
    
    def test_client_initialization_without_api_key(self):
        """Test client raises error without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(GolfGeniusAuthError):
                GolfGeniusAPIClient()
    
    @patch('golfgenius.client.requests.Session.request')
    def test_successful_api_request(self, mock_request):
        """Test successful API request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_request.return_value = mock_response
        
        result = self.client._make_request("GET", "/test")
        
        self.assertEqual(result, {"test": "data"})
        mock_request.assert_called_once()
    
    @patch('golfgenius.client.requests.Session.request')
    def test_api_authentication_error(self, mock_request):
        """Test API authentication error handling"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response
        
        with self.assertRaises(GolfGeniusAuthError):
            self.client._make_request("GET", "/test")
    
    @patch('golfgenius.client.requests.Session.request')
    def test_api_rate_limit_error(self, mock_request):
        """Test API rate limit error handling"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_request.return_value = mock_response
        
        with self.assertRaises(Exception):  # Should raise GolfGeniusRateLimitError
            self.client._make_request("GET", "/test")
    
    @patch.object(GolfGeniusAPIClient, '_make_request')
    def test_get_master_roster(self, mock_request):
        """Test getting master roster"""
        mock_request.return_value = [{"member": {"id": "123", "email": "test@example.com"}}]
        
        result = self.client.get_master_roster(page=1, photo=True)
        
        self.assertEqual(len(result), 1)
        mock_request.assert_called_once_with(
            "GET", 
            f"/api_v2/{self.api_key}/master_roster", 
            params={"page": 1, "photo": "true"}
        )
    
    @patch.object(GolfGeniusAPIClient, '_make_request')
    def test_get_master_roster_member(self, mock_request):
        """Test getting specific master roster member"""
        mock_request.return_value = {"member": {"id": "123", "email": "test@example.com"}}
        
        result = self.client.get_master_roster_member("test@example.com")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["email"], "test@example.com")


class PlayerSyncServiceTestCase(TestCase):
    """
    Test cases for Player sync service
    """
    
    def setUp(self):
        self.mock_client = Mock(spec=GolfGeniusAPIClient)
        self.service = PlayerSyncService(api_client=self.mock_client)
        
        # Create test players
        self.player1 = Player.objects.create(
            first_name="John",
            last_name="Doe", 
            email="john@example.com"
        )
        self.player2 = Player.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            gg_id="existing_id"
        )
    
    def test_get_sync_status(self):
        """Test getting sync status"""
        status = self.service.get_sync_status()
        
        self.assertEqual(status["total_players"], 2)
        self.assertEqual(status["synced_players"], 1)
        self.assertEqual(status["unsynced_players"], 1)
        self.assertEqual(status["sync_percentage"], 50.0)
    
    def test_sync_single_player_success(self):
        """Test successful single player sync"""
        # Mock Golf Genius response
        self.mock_client.get_master_roster_member.return_value = {
            "member_card_id": "gg_123",
            "email": "john@example.com"
        }
        
        result = self.service.sync_single_player(self.player1.pk)
        
        self.assertEqual(result.updated_players, 1)
        self.assertEqual(len(result.errors), 0)
        
        # Check player was updated
        self.player1.refresh_from_db()
        self.assertEqual(self.player1.gg_id, "gg_123")
    
    def test_sync_single_player_not_found(self):
        """Test single player sync when not found in Golf Genius"""
        self.mock_client.get_master_roster_member.return_value = None
        
        result = self.service.sync_single_player(self.player1.pk)
        
        self.assertEqual(result.updated_players, 0)
        self.assertEqual(result.unmatched_emails, ["john@example.com"])
    
    def test_sync_player_already_has_gg_id(self):
        """Test sync skips player that already has gg_id"""
        result = self.service.sync_single_player(self.player2.pk, force_update=False)
        
        self.assertEqual(result.skipped_players, 1)
        self.assertEqual(result.updated_players, 0)
    
    def test_sync_all_players(self):
        """Test syncing all players"""
        # Mock Golf Genius responses
        def mock_get_member(email):
            if email == "john@example.com":
                return {"member_card_id": "gg_123", "email": email}
            return None
        
        self.mock_client.get_master_roster_member.side_effect = mock_get_member
        
        result = self.service.sync_all_players()
        
        self.assertEqual(result.total_players, 1)  # Only player without gg_id
        self.assertEqual(result.updated_players, 1)
        self.assertEqual(result.unmatched_emails, [])


class GolfGeniusAPIViewsTestCase(TestCase):
    """
    Test cases for Golf Genius API views
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass",
            is_staff=True,
            is_superuser=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username="user",
            email="user@example.com", 
            password="testpass"
        )
        
        # Create test player
        self.player = Player.objects.create(
            first_name="Test",
            last_name="Player",
            email="test@example.com"
        )
    
    def test_sync_players_requires_admin(self):
        """Test that sync players endpoint requires admin permissions"""
        self.client.force_authenticate(user=self.regular_user)
        
        response = self.client.post('/api/golfgenius/sync-players/', {})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_sync_status_requires_admin(self):
        """Test that sync status endpoint requires admin permissions"""
        self.client.force_authenticate(user=self.regular_user)
        
        response = self.client.get('/api/golfgenius/sync-status/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    @patch('golfgenius.services.PlayerSyncService.sync_all_players')
    def test_sync_players_success(self, mock_sync):
        """Test successful player sync via API"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Mock successful sync result
        mock_result = Mock()
        mock_result.total_players = 1
        mock_result.updated_players = 1
        mock_result.errors = []
        mock_result.to_dict.return_value = {
            "total_players": 1,
            "updated_players": 1,
            "error_count": 0
        }
        mock_sync.return_value = mock_result
        
        response = self.client.post('/api/golfgenius/sync-players/', {
            "force_update": False
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["results"]["updated_players"], 1)
    
    @patch('golfgenius.services.PlayerSyncService.get_sync_status')
    def test_sync_status_success(self, mock_status):
        """Test successful sync status retrieval"""
        self.client.force_authenticate(user=self.admin_user)
        
        mock_status.return_value = {
            "total_players": 10,
            "synced_players": 7,
            "unsynced_players": 3,
            "sync_percentage": 70.0
        }
        
        response = self.client.get('/api/golfgenius/sync-status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["status"]["total_players"], 10)
    
    @patch('golfgenius.client.GolfGeniusAPIClient.get_seasons')
    def test_test_connection_success(self, mock_get_seasons):
        """Test successful connection test"""
        self.client.force_authenticate(user=self.admin_user)
        
        mock_get_seasons.return_value = [{"season": {"id": "1", "name": "2024"}}]
        
        response = self.client.get('/api/golfgenius/test-connection/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["api_info"]["seasons_count"], 1)
    
    @patch('golfgenius.services.PlayerSyncService.sync_single_player')
    def test_sync_single_player(self, mock_sync):
        """Test single player sync via API"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Mock successful sync result
        mock_result = Mock()
        mock_result.updated_players = 1
        mock_result.errors = []
        mock_result.to_dict.return_value = {
            "updated_players": 1,
            "error_count": 0
        }
        mock_sync.return_value = mock_result
        
        response = self.client.post(f'/api/golfgenius/sync-player/{self.player.pk}/', {
            "force_update": False
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
