# Golf Genius API Integration Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture and Components](#architecture-and-components)
3. [Configuration Requirements](#configuration-requirements)
4. [API Endpoints](#api-endpoints)
5. [Usage Examples](#usage-examples)
6. [Error Handling and Troubleshooting](#error-handling-and-troubleshooting)
7. [Testing](#testing)

## Overview

The Golf Genius API integration system provides seamless synchronization between the BHMC (Bunker Hills Men's Club) application and the Golf Genius platform. This integration allows for automatic mapping of local player records with their corresponding Golf Genius member data, enabling enhanced golf course management and tournament functionality.

### Key Features

- **Player Synchronization**: Automatically sync player records with Golf Genius Master Roster
- **Member Lookup**: Search for members in Golf Genius by email address
- **Batch Processing**: Efficiently process multiple players with configurable batch sizes
- **Dry Run Support**: Test synchronization without making database changes
- **Comprehensive Logging**: Detailed logging with structured output for monitoring and debugging
- **Health Monitoring**: Built-in health checks and statistics tracking
- **Error Resilience**: Robust error handling with detailed error reporting

### Integration Purpose

This system bridges the gap between the BHMC's internal player management system and Golf Genius's tournament management platform. The primary goal is to maintain synchronized player records by linking local player data with Golf Genius member card IDs, enabling:

- Accurate player identification across systems
- Streamlined tournament registration
- Automated handicap synchronization
- Enhanced reporting capabilities

## Architecture and Components

The Golf Genius integration follows a modular architecture with clear separation of concerns:

```
golfgenius/
├── client.py          # Golf Genius API client
├── services.py        # Synchronization business logic
├── views.py          # REST API endpoints
├── urls.py           # URL routing configuration
├── serializers.py    # Data serialization/validation
├── tests.py          # Comprehensive test suite
└── apps.py           # Django app configuration
```

### Core Components

#### 1. Golf Genius Client ([`client.py`](golfgenius/client.py:1))

The [`GolfGeniusClient`](golfgenius/client.py:14) class handles all direct communication with the Golf Genius API:

- **Authentication**: Manages API key authentication
- **HTTP Handling**: Robust request/response handling with timeout management
- **Error Management**: Comprehensive error handling with custom exceptions
- **Health Checks**: API connectivity verification

Key methods:
- [`get_master_roster_member(email)`](golfgenius/client.py:115): Retrieve member data by email
- [`get_master_roster(page, include_photo)`](golfgenius/client.py:156): Get paginated roster data
- [`health_check()`](golfgenius/client.py:179): Verify API connectivity

#### 2. Synchronization Service ([`services.py`](golfgenius/services.py:1))

The [`PlayerSynchronizationService`](golfgenius/services.py:42) handles the business logic for player synchronization:

- **Batch Processing**: Processes players in configurable batches
- **Smart Filtering**: Only processes players that need synchronization
- **Result Tracking**: Detailed statistics and error reporting
- **Transaction Safety**: Database operations with proper error handling

Key methods:
- [`sync_players(player_ids, force, dry_run)`](golfgenius/services.py:59): Main synchronization method
- [`sync_single_player_by_id(player_id, force)`](golfgenius/services.py:237): Sync individual player
- [`get_sync_statistics()`](golfgenius/services.py:264): Retrieve synchronization statistics

#### 3. REST API Views ([`views.py`](golfgenius/views.py:1))

The API views provide HTTP endpoints for integration functionality:

- **Authentication**: All endpoints require user authentication
- **Caching**: Strategic caching for performance optimization
- **Error Handling**: Consistent error response formatting
- **Logging**: Comprehensive request/response logging

#### 4. Data Serializers ([`serializers.py`](golfgenius/serializers.py:1))

Serializers handle data validation and formatting:

- **Request Validation**: Input parameter validation
- **Response Formatting**: Consistent response structure
- **Documentation**: Built-in API documentation support

## Configuration Requirements

### Environment Variables

The following environment variables must be configured for the Golf Genius integration:

#### Required Settings

```bash
# Golf Genius API Configuration
GOLF_GENIUS_API_KEY=your_golf_genius_api_key_here
```

#### Optional Settings

```bash
# Golf Genius API Base URL (defaults to production)
GOLF_GENIUS_BASE_URL=https://www.golfgenius.com

# Request timeout in seconds (default: 30)
GOLF_GENIUS_TIMEOUT=30
```

### Django Settings Configuration

The Golf Genius app is automatically included in [`INSTALLED_APPS`](bhmc/settings.py:113) and logging is configured in [`settings.py`](bhmc/settings.py:250-253):

```python
INSTALLED_APPS = (
    # ... other apps
    "golfgenius",
    # ... other apps
)

# Logging configuration for Golf Genius
"golfgenius": {
    "handlers": ["console", "flat_line_file"],
    "level": "INFO",
},
```

### URL Configuration

The Golf Genius API endpoints are mounted at `/api/golfgenius/` in the main URL configuration ([`bhmc/urls.py`](bhmc/urls.py:54)):

```python
urlpatterns = [
    # ... other patterns
    path("api/golfgenius/", include("golfgenius.urls")),
    # ... other patterns
]
```

### Database Requirements

The integration requires the following database setup:

1. **Player Model**: Must have `gg_id` field for storing Golf Genius member card IDs
2. **Email Field**: Players must have email addresses for lookup
3. **Database Permissions**: Write access for updating player records

## API Endpoints

All endpoints require authentication via Token Authentication. Include the token in the Authorization header:

```
Authorization: Token your_api_token_here
```

### Player Synchronization

#### Sync Players with Golf Genius

**Endpoint**: `POST /api/golfgenius/sync-members/`

Synchronizes player records with Golf Genius Master Roster.

**Request Parameters**:
```json
{
  "force": false,           // Update gg_id even if already set
  "dry_run": false,         // Perform sync without saving to database
  "player_ids": [1, 2, 3]   // Optional: specific player IDs to sync
}
```

**Response**:
```json
{
  "total_players": 100,
  "processed_players": 100,
  "updated_players": 85,
  "skipped_players": 10,
  "failed_players": 5,
  "success_rate": "85.0%",
  "errors": [
    "Player 123 (john@example.com): API error - Member not found"
  ],
  "updated_player_ids": [1, 2, 3],
  "skipped_player_ids": [4, 5],
  "failed_player_ids": [6, 7]
}
```

**Example Usage**:
```bash
# Sync all players (dry run)
curl -X POST \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}' \
  https://api.bhmc.org/api/golfgenius/sync-members/

# Force sync specific players
curl -X POST \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{"force": true, "player_ids": [1, 2, 3]}' \
  https://api.bhmc.org/api/golfgenius/sync-members/
```

#### Sync Single Player

**Endpoint**: `POST /api/golfgenius/players/{player_id}/sync/`

Synchronizes a single player by ID.

**Request Parameters**:
```json
{
  "force": false  // Update gg_id even if already set
}
```

**Response**:
```json
{
  "message": "Successfully updated player 123",
  "success": true
}
```

### Statistics and Monitoring

#### Get Synchronization Statistics

**Endpoint**: `GET /api/golfgenius/sync-stats/`

Returns current synchronization statistics.

**Response**:
```json
{
  "total_players": 500,
  "players_with_gg_id": 450,
  "players_without_gg_id": 50,
  "players_with_email": 480,
  "players_without_email": 20,
  "sync_percentage": "90.0%"
}
```

#### Health Check

**Endpoint**: `GET /api/golfgenius/health/`

Verifies Golf Genius API connectivity.

**Response** (Healthy):
```json
{
  "status": "healthy",
  "golf_genius_api": true,
  "timestamp": "2023-12-01T10:30:00.000Z"
}
```

**Response** (Degraded):
```json
{
  "status": "degraded",
  "golf_genius_api": false,
  "timestamp": "2023-12-01T10:30:00.000Z",
  "message": "Golf Genius API is not accessible"
}
```

### Player Management

#### Get Player Details

**Endpoint**: `GET /api/golfgenius/players/{player_id}/`

Returns player details with Golf Genius sync status.

**Response**:
```json
{
  "id": 123,
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "email": "john@example.com",
  "gg_id": "GG12345",
  "sync_status": "synced",  // "synced", "not_synced", "no_email"
  "is_member": true,
  "ghin": "1234567"
}
```

#### List Unsynced Players

**Endpoint**: `GET /api/golfgenius/players/unsynced/`

Returns list of players without Golf Genius IDs (limited to 100 results).

**Response**:
```json
{
  "count": 25,
  "players": [
    {
      "id": 124,
      "first_name": "Jane",
      "last_name": "Smith",
      "full_name": "Jane Smith",
      "email": "jane@example.com",
      "gg_id": null,
      "sync_status": "not_synced",
      "is_member": true,
      "ghin": "7654321"
    }
  ]
}
```

### Golf Genius Member Lookup

#### Look Up Member by Email

**Endpoint**: `GET /api/golfgenius/member/{email}/`

Directly queries Golf Genius Master Roster for member data.

**Response**:
```json
{
  "member_card_id": "GG12345",
  "name": "John Doe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "deleted": false,
  "waitlist": false,
  "waitlist_type": "regular",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-12-01T10:00:00Z",
  "external_id": null,
  "handicap": {
    "index": 12.5,
    "type": "USGA"
  },
  "custom_fields": {}
}
```

## Usage Examples

### Python SDK Usage

#### Basic Synchronization

```python
from golfgenius.client import GolfGeniusClient
from golfgenius.services import PlayerSynchronizationService

# Initialize client
client = GolfGeniusClient(api_key="your_api_key")

# Initialize synchronization service
sync_service = PlayerSynchronizationService(api_client=client)

# Perform dry run sync
result = sync_service.sync_players(dry_run=True)
print(f"Would update {result.updated_players} players")

# Actual sync
result = sync_service.sync_players()
print(f"Updated {result.updated_players} of {result.total_players} players")
```

#### Single Player Lookup

```python
from golfgenius.client import GolfGeniusClient

client = GolfGeniusClient()

# Look up member by email
member_data = client.get_master_roster_member("john@example.com")
if member_data:
    print(f"Found member: {member_data['name']} (ID: {member_data['member_card_id']})")
else:
    print("Member not found")
```

#### Error Handling

```python
from golfgenius.client import GolfGeniusClient, GolfGeniusAPIError

try:
    client = GolfGeniusClient()
    result = client.get_master_roster_member("test@example.com")
except GolfGeniusAPIError as e:
    print(f"API Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Command Line Examples

#### Using curl for API Calls

```bash
# Set your token
TOKEN="your_api_token_here"
BASE_URL="https://api.bhmc.org"

# Health check
curl -H "Authorization: Token $TOKEN" \
     $BASE_URL/api/golfgenius/health/

# Get sync statistics
curl -H "Authorization: Token $TOKEN" \
     $BASE_URL/api/golfgenius/sync-stats/

# Dry run sync
curl -X POST \
     -H "Authorization: Token $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"dry_run": true}' \
     $BASE_URL/api/golfgenius/sync-members/

# Look up specific member
curl -H "Authorization: Token $TOKEN" \
     $BASE_URL/api/golfgenius/member/john@example.com/

# Get unsynced players
curl -H "Authorization: Token $TOKEN" \
     $BASE_URL/api/golfgenius/players/unsynced/
```

### Management Commands

While no custom management commands are currently implemented, you can create them for common tasks:

```python
# Example management command structure
from django.core.management.base import BaseCommand
from golfgenius.services import PlayerSynchronizationService

class Command(BaseCommand):
    help = 'Sync players with Golf Genius'
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--force', action='store_true')
    
    def handle(self, *args, **options):
        service = PlayerSynchronizationService()
        result = service.sync_players(
            dry_run=options['dry_run'],
            force=options['force']
        )
        self.stdout.write(f"Sync completed: {result.updated_players} updated")
```

## Error Handling and Troubleshooting

### Common Error Types

#### 1. Authentication Errors

**Error**: `GolfGeniusAPIError: Invalid API key or unauthorized`

**Causes**:
- Missing or incorrect `GOLF_GENIUS_API_KEY`
- API key has been revoked or expired
- API key lacks necessary permissions

**Solutions**:
- Verify API key in environment variables
- Contact Golf Genius support to verify key status
- Ensure key has Master Roster read permissions

#### 2. Network Connectivity Issues

**Error**: `GolfGeniusAPIError: Failed to connect to Golf Genius API`

**Causes**:
- Network connectivity issues
- Golf Genius API server downtime
- Firewall blocking outbound connections

**Solutions**:
- Check network connectivity
- Verify firewall rules allow HTTPS to golfgenius.com
- Check Golf Genius status page for service issues

#### 3. Rate Limiting

**Error**: `GolfGeniusAPIError: Rate limit exceeded`

**Causes**:
- Too many API requests in short time period
- Multiple processes making concurrent requests

**Solutions**:
- Implement request throttling
- Use batch processing with delays
- Contact Golf Genius to discuss rate limits

#### 4. Timeout Issues

**Error**: `GolfGeniusAPIError: Request timed out after 30 seconds`

**Causes**:
- Slow network connection
- Golf Genius API performance issues
- Large batch requests

**Solutions**:
- Increase `GOLF_GENIUS_TIMEOUT` setting
- Reduce batch sizes
- Retry failed requests with exponential backoff

### Debugging Steps

#### 1. Enable Debug Logging

Update logging configuration in settings:

```python
"golfgenius": {
    "handlers": ["console", "flat_line_file"],
    "level": "DEBUG",  # Change from INFO to DEBUG
},
```

#### 2. Test API Connectivity

Use the health check endpoint:

```bash
curl -H "Authorization: Token your_token" \
     https://api.bhmc.org/api/golfgenius/health/
```

#### 3. Verify Configuration

Check environment variables:

```python
from django.conf import settings
print(f"API Key configured: {bool(getattr(settings, 'GOLF_GENIUS_API_KEY', None))}")
print(f"Base URL: {getattr(settings, 'GOLF_GENIUS_BASE_URL', 'default')}")
print(f"Timeout: {getattr(settings, 'GOLF_GENIUS_TIMEOUT', 30)}")
```

#### 4. Test Individual Components

```python
# Test client initialization
from golfgenius.client import GolfGeniusClient
try:
    client = GolfGeniusClient()
    print("Client initialized successfully")
except Exception as e:
    print(f"Client initialization failed: {e}")

# Test API call
try:
    result = client.health_check()
    print(f"Health check: {'Pass' if result else 'Fail'}")
except Exception as e:
    print(f"Health check failed: {e}")
```

### Performance Optimization

#### 1. Batch Size Tuning

The default batch size is 50 players. Adjust based on your needs:

```python
# In services.py, modify batch_size
batch_size = 25  # Reduce for slower networks
batch_size = 100  # Increase for faster processing
```

#### 2. Selective Synchronization

Only sync players that need updates:

```python
# Sync only players without gg_id
result = sync_service.sync_players(force=False)

# Sync specific players
result = sync_service.sync_players(player_ids=[1, 2, 3])
```

#### 3. Caching Strategy

API responses are cached where appropriate:

- Sync statistics: 5 minutes
- Unsynced players list: 10 minutes

### Monitoring and Alerting

#### 1. Health Check Monitoring

Set up automated monitoring of the health check endpoint:

```bash
# Example monitoring script
#!/bin/bash
HEALTH_URL="https://api.bhmc.org/api/golfgenius/health/"
TOKEN="your_token"

RESPONSE=$(curl -s -H "Authorization: Token $TOKEN" $HEALTH_URL)
STATUS=$(echo $RESPONSE | jq -r '.status')

if [ "$STATUS" != "healthy" ]; then
    echo "Golf Genius integration unhealthy: $RESPONSE"
    # Send alert
fi
```

#### 2. Log Monitoring

Monitor application logs for errors:

```bash
# Monitor for API errors
tail -f /path/to/bhmc.log | grep "golfgenius.*ERROR"

# Monitor sync operations
tail -f /path/to/bhmc.log | grep "Player synchronization"
```

#### 3. Sync Statistics Tracking

Regularly check sync statistics:

```python
from golfgenius.services import PlayerSynchronizationService

service = PlayerSynchronizationService()
stats = service.get_sync_statistics()

# Alert if sync percentage drops below threshold
if float(stats['sync_percentage'].rstrip('%')) < 85.0:
    print(f"Warning: Sync percentage is {stats['sync_percentage']}")
```

## Testing

The Golf Genius integration includes comprehensive tests covering all major functionality.

### Test Structure

The test suite is located in [`golfgenius/tests.py`](golfgenius/tests.py:1) and includes:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test API endpoints with authentication
- **Mock Tests**: Test external API interactions using mocks

### Test Categories

#### 1. Client Tests ([`GolfGeniusClientTestCase`](golfgenius/tests.py:14))

Tests the Golf Genius API client functionality:

```python
class GolfGeniusClientTestCase(TestCase):
    def test_get_master_roster_member_success(self):
        # Tests successful member lookup
    
    def test_get_master_roster_member_not_found(self):
        # Tests handling of member not found
    
    def test_health_check_no_api_key(self):
        # Tests error handling for missing API key
```

#### 2. Service Tests ([`PlayerSynchronizationServiceTestCase`](golfgenius/tests.py:63))

Tests the synchronization service business logic:

```python
class PlayerSynchronizationServiceTestCase(TestCase):
    def test_sync_statistics(self):
        # Tests statistics calculation
    
    def test_sync_players_dry_run(self):
        # Tests dry run functionality
    
    def test_sync_players_force_update(self):
        # Tests force update functionality
```

#### 3. API Tests ([`GolfGeniusAPITestCase`](golfgenius/tests.py:137))

Tests REST API endpoints with authentication:

```python
class GolfGeniusAPITestCase(APITestCase):
    def test_health_check_endpoint(self):
        # Tests health check API endpoint
    
    def test_sync_members_endpoint(self):
        # Tests player synchronization endpoint
    
    def test_member_lookup_endpoint(self):
        # Tests member lookup endpoint
```

### Running Tests

#### Run All Golf Genius Tests

```bash
# Run all tests for the golfgenius app
python manage.py test golfgenius

# Run with verbose output
python manage.py test golfgenius --verbosity=2

# Run with coverage
coverage run --source='.' manage.py test golfgenius
coverage report -m
```

#### Run Specific Test Classes

```bash
# Run only client tests
python manage.py test golfgenius.tests.GolfGeniusClientTestCase

# Run only service tests
python manage.py test golfgenius.tests.PlayerSynchronizationServiceTestCase

# Run only API tests
python manage.py test golfgenius.tests.GolfGeniusAPITestCase
```

#### Run Individual Tests

```bash
# Run specific test method
python manage.py test golfgenius.tests.GolfGeniusClientTestCase.test_get_master_roster_member_success
```

### Test Environment Setup

#### 1. Test Database

Tests use Django's test database, which is automatically created and destroyed:

```python
# Test models are created automatically
def setUp(self):
    self.player = Player.objects.create(
        first_name="Test",
        last_name="Player",
        email="test@example.com"
    )
```

#### 2. Mock External APIs

External API calls are mocked to ensure reliable testing:

```python
@patch('golfgenius.client.requests.Session.request')
def test_api_call(self, mock_request):
    # Mock the external API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'member': {'member_card_id': '12345'}}
    mock_request.return_value = mock_response
    
    # Test the functionality
    result = self.client.get_master_roster_member('test@example.com')
    self.assertEqual(result['member_card_id'], '12345')
```

#### 3. Authentication Testing

API tests include proper authentication setup:

```python
def setUp(self):
    # Create test user and token
    self.user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass'
    )
    self.token = Token.objects.create(user=self.user)
    self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
```

### Test Coverage

The test suite aims for comprehensive coverage of:

- **Happy Path**: Normal operation scenarios
- **Error Handling**: Various error conditions
- **Edge Cases**: Boundary conditions and unusual inputs
- **Authentication**: Proper access control
- **Data Validation**: Input validation and serialization

### Continuous Integration

For CI/CD pipelines, include Golf Genius tests:

```yaml
# Example GitHub Actions workflow
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run Golf Genius tests
        run: |
          python manage.py test golfgenius
        env:
          GOLF_GENIUS_API_KEY: "test-key"
          DATABASE_URL: "sqlite:///test.db"
```

### Manual Testing Checklist

For manual testing and verification:

#### Pre-deployment Testing

- [ ] Health check endpoint returns expected status
- [ ] Sync statistics endpoint returns current data
- [ ] Player sync with dry_run=true works without database changes
- [ ] Member lookup finds existing Golf Genius members
- [ ] Error handling works for invalid API keys
- [ ] Authentication is required for all endpoints

#### Post-deployment Testing

- [ ] Production health check passes
- [ ] Sync statistics reflect production data
- [ ] Small batch sync works correctly
- [ ] Monitoring and logging are functioning
- [ ] Performance is within acceptable limits

---

This documentation provides comprehensive coverage of the Golf Genius API integration system. For additional support or questions, please contact the development team or refer to the Golf Genius API documentation.