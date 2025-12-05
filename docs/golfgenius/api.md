# Golf Genius API Integration

This document describes the Golf Genius API integration for the BHMC (Bunker Hills Men's Club) Django application. The integration provides two-way synchronization between BHMC and Golf Genius systems.

## Overview

The Golf Genius integration provides:
- **Player Synchronization**: Sync BHMC players with Golf Genius Master Roster using email matching
- **Event Synchronization**: Match BHMC events with Golf Genius events based on dates, seasons, and categories
- **Admin Interface**: Django admin actions for bulk operations
- **API Endpoints**: RESTful endpoints for programmatic access
- **Rate Limiting**: Built-in protection against API rate limits with exponential backoff

## Authentication

All API endpoints require admin user authentication (`IsAdminUser` permission).

## Core Endpoints

### Connection & Status

#### Test Connection
**GET** `/api/golfgenius/test-connection/`

Tests the connection to Golf Genius API.

**Response:**
```json
{
  "success": true,
  "message": "Successfully connected to Golf Genius API"
}
```

#### Account Information
**GET** `/api/golfgenius/info/`

Retrieves Golf Genius account information including seasons, categories, and directories.

**Response:**
```json
{
  "success": true,
  "account_info": {
    "seasons": [...],
    "categories": [...],
    "directories": [...]
  }
}
```

### Player Synchronization

#### Sync Players
**POST** `/api/golfgenius/sync-players/`

Synchronizes BHMC players with Golf Genius Master Roster.

**Request Body:**
```json
{
  "force_update": false  // Optional: Update existing member_card_ids
}
```

**Response:**
```json
{
  "success": true,
  "message": "Player sync completed",
  "results": {
    "total_players": 150,
    "matched_players": 140,
    "updated_players": 135,
    "skipped_players": 5,
    "unmatched_players": 10
  }
}
```

#### Player Sync Status
**GET** `/api/golfgenius/sync-status/`

Returns current player synchronization status.

**Response:**
```json
{
  "success": true,
  "message": "Player sync status retrieved",
  "status": {
    "total_players": 150,
    "synced_players": 140,
    "unsynced_players": 10,
    "sync_percentage": 93.33
  }
}
```

### Event Synchronization

#### Sync Events
**POST** `/api/golfgenius/sync-events/`

Synchronizes BHMC events with Golf Genius events for a specified or current season.

**Request Body:**
```json
{
  "season_override": 2024,  // Optional: Override season detection
  "force_update": false     // Optional: Update events with existing gg_id
}
```

**Response:**
```json
{
  "success": true,
  "message": "Event sync completed",
  "results": {
    "total_bhmc_events": 15,
    "total_gg_events": 12,
    "matched_events": 8,
    "updated_events": 6,
    "skipped_events": 2,
    "unmatched_bhmc_count": 7,
    "unmatched_gg_count": 4,
    "matches": [...],
    "unmatched_bhmc_events": [...],
    "unmatched_gg_events": [...]
  }
}
```

#### Event Sync Status
**GET** `/api/golfgenius/event-sync-status/`

Returns current event synchronization status.

**Response:**
```json
{
  "success": true,
  "message": "Event sync status retrieved",
  "status": {
    "total_events": 50,
    "synced_events": 35,
    "unsynced_events": 15,
    "sync_percentage": 70.0
  }
}
```

## Detailed Documentation

### Player Synchronization
For detailed information about player synchronization, including:
- Email-based matching logic
- Member card ID updates
- Force update behavior
- Error handling scenarios

See: [Player Sync API Documentation](player-sync-api.md)

### Event Synchronization
For detailed information about event synchronization, including:
- Date-based matching algorithms
- Season and category filtering
- End date calculations
- Match types and priorities

See: [Event Sync API Documentation](event-sync-api.md)

## Admin Interface Integration

### Player Admin Actions
- **Sync selected players with Golf Genius**: Sync only selected players
- **Force sync selected players with Golf Genius**: Update existing member_card_ids

### Event Admin Actions
- **Sync selected events with Golf Genius**: Sync only selected events
- **Sync all events in selected seasons with Golf Genius**: Sync entire seasons

### List Display Enhancements
- Player admin shows `member_card_id` field
- Event admin shows `gg_id` field for sync status visibility

## Error Handling

Common error scenarios across all endpoints:

### Authentication Errors
```json
{
  "success": false,
  "message": "Authentication failed: Invalid API key",
  "results": null
}
```

### Rate Limiting
The integration includes automatic retry with exponential backoff for 429 responses:
- Initial retry after 1 second
- Exponential backoff up to 32 seconds
- Maximum 5 retry attempts

### Connection Errors
```json
{
  "success": false,
  "message": "Failed to connect to Golf Genius API: Connection timeout",
  "results": null
}
```

### Validation Errors
```json
{
  "success": false,
  "message": "Invalid request: season_override must be a valid integer",
  "results": null
}
```

## Configuration

### Environment Variables
```bash
GOLF_GENIUS_API_KEY=your_api_key_here
GOLF_GENIUS_BASE_URL=https://www.golfgenius.com/api_v2
```

### Django Settings
```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    # ... other apps
    'golfgenius',
]

# URL Configuration
urlpatterns = [
    # ... other patterns
    path('api/golfgenius/', include('golfgenius.urls')),
]
```

## Usage Examples

### Sync Current Season Players
```bash
curl -X POST "https://your-domain.com/api/golfgenius/sync-players/" \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Sync Specific Season Events
```bash
curl -X POST "https://your-domain.com/api/golfgenius/sync-events/" \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "season_override": 2024,
    "force_update": false
  }'
```

### Get Overall Status
```bash
# Player sync status
curl -X GET "https://your-domain.com/api/golfgenius/sync-status/" \
  -H "Authorization: Bearer your-admin-token"

# Event sync status
curl -X GET "https://your-domain.com/api/golfgenius/event-sync-status/" \
  -H "Authorization: Bearer your-admin-token"
```

## Testing

The integration includes comprehensive test suites:

### Player Sync Tests
- `golfgenius/tests/test_player_sync.py`
- Email matching logic validation
- Member card ID update scenarios
- Error handling verification

### Event Sync Tests
- `golfgenius/tests/test_event_sync.py`
- Date matching algorithm validation
- Season detection logic
- Category filtering verification

### Integration Tests
- `golfgenius/tests/test_integration.py`
- End-to-end workflow testing
- API client functionality
- Rate limiting behavior

## Monitoring and Logging

All operations are logged with structured logging:

```python
import logging
logger = logging.getLogger('golfgenius')

# Example log output
logger.info("Player sync completed", extra={
    'total_players': 150,
    'matched_players': 140,
    'sync_duration': 45.2
})
```

## Security Considerations

- All endpoints require admin authentication
- API keys are stored securely in environment variables
- Rate limiting prevents API abuse
- Idempotent operations prevent data corruption
- Database transactions ensure data consistency

## Troubleshooting

### Common Issues

1. **No Golf Genius API Key**: Ensure `GOLF_GENIUS_API_KEY` environment variable is set
2. **Rate Limit Exceeded**: The system handles this automatically with retries
3. **No Season Found**: Create active season in `SeasonSettings` or use `season_override`
4. **No Men's Club Category**: Ensure Golf Genius account has a category containing "men" and "club"
5. **Email Mismatches**: Verify player email addresses match between systems

### Debug Mode
Enable detailed logging:
```python
LOGGING = {
    'loggers': {
        'golfgenius': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

## API Versioning

Current API version: v1

All endpoints are prefixed with `/api/golfgenius/` and maintain backward compatibility.

## Support

For technical support or questions about the Golf Genius integration:
1. Check the detailed documentation links above
2. Review the test files for usage examples
3. Enable debug logging for troubleshooting
4. Contact the development team with specific error messages