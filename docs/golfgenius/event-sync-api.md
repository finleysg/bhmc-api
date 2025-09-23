# Golf Genius Event Synchronization API

This document describes the Golf Genius event synchronization API endpoints that allow BHMC administrators to sync events between the BHMC database and Golf Genius platform.

## Overview

The event synchronization system matches BHMC events with Golf Genius events based on:
- Season filtering (current or specified season)
- Category filtering (Men's Club events only)
- Date-based matching with priority for exact date matches over overlapping ranges
- End date calculation: `end_date = start_date + (rounds - 1) days`

## Authentication

All endpoints require admin user authentication (`IsAdminUser` permission).

## Endpoints

### 1. Sync Events

**POST** `/api/golfgenius/sync-events/`

Synchronizes BHMC events with Golf Genius events for a specified or current season.

#### Request Body

```json
{
  "season_override": 2024,  // Optional: Override season detection
  "force_update": false     // Optional: Update events with existing gg_id
}
```

#### Parameters

- `season_override` (integer, optional): Specific season to sync. If not provided, uses current active season.
- `force_update` (boolean, optional): Whether to update events that already have Golf Genius IDs. Default: `false`.

#### Response

**Success (200 OK)**
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
    "error_count": 1,
    "unmatched_bhmc_count": 7,
    "unmatched_gg_count": 4,
    "errors": [
      {
        "event": "Event Name",
        "error": "Error description"
      }
    ],
    "matches": [
      {
        "bhmc_event_id": 123,
        "bhmc_event_name": "Spring Tournament",
        "bhmc_start_date": "2024-05-15",
        "gg_event_id": "789",
        "gg_event_name": "Spring Tournament",
        "gg_start_date": "2024-05-15",
        "gg_end_date": "2024-05-15",
        "match_type": "exact_date"
      }
    ],
    "unmatched_bhmc_events": [
      {
        "id": 456,
        "name": "BHMC Only Event",
        "start_date": "2024-06-01",
        "rounds": 1,
        "season": 2024
      }
    ],
    "unmatched_gg_events": [
      {
        "id": "999",
        "name": "Golf Genius Only Event",
        "start_date": "2024-07-01",
        "end_date": "2024-07-01"
      }
    ]
  }
}
```

**Partial Success (207 Multi-Status)**
```json
{
  "success": true,
  "message": "Event sync completed",
  "results": {
    // Same structure as 200, but with some errors
  }
}
```

**Error (400 Bad Request)**
```json
{
  "success": false,
  "message": "season_override must be a valid integer",
  "results": null
}
```

**Error (500 Internal Server Error)**
```json
{
  "success": false,
  "message": "Event sync failed: Detailed error message",
  "results": null
}
```

#### Match Types

- `exact_date`: BHMC event start date exactly matches Golf Genius event start date
- `date_overlap`: BHMC event date range overlaps with Golf Genius event date range

### 2. Sync Single Event

**POST** `/api/golfgenius/sync-event/<int:event_id>/`

Synchronizes a single BHMC event by its database ID with Golf Genius events.

#### URL Parameters

- `event_id` (integer, required): The database ID of the BHMC event to sync.

#### Request Body

```json
{
  "force_update": false     // Optional: Update event with existing gg_id
}
```

#### Parameters

- `force_update` (boolean, optional): Whether to update the event if it already has a Golf Genius ID. Default: `false`.

#### Response

**Success (200 OK)**
```json
{
  "success": true,
  "message": "Single event sync completed",
  "results": {
    "event_id": 123,
    "matched_events": 1,
    "updated_events": 1,
    "error_count": 0,
    "errors": [],
    "matches": [
      {
        "bhmc_event_id": 123,
        "bhmc_event_name": "Spring Tournament",
        "bhmc_start_date": "2024-05-15",
        "gg_event_id": "789",
        "gg_event_name": "Spring Tournament",
        "gg_start_date": "2024-05-15",
        "gg_end_date": "2024-05-15",
        "match_type": "exact_date"
      }
    ]
  }
}
```

**No Match Found (200 OK)**
```json
{
  "success": true,
  "message": "Single event sync completed",
  "results": {
    "event_id": 123,
    "matched_events": 0,
    "updated_events": 0,
    "error_count": 0,
    "errors": [],
    "matches": []
  }
}
```

**Event Already Synced (200 OK)**
```json
{
  "success": true,
  "message": "Event skipped - already has Golf Genius ID",
  "results": {
    "event_id": 123,
    "matched_events": 0,
    "updated_events": 0,
    "error_count": 0,
    "errors": [],
    "matches": [],
    "skipped_reason": "Already has Golf Genius ID existing_123"
  }
}
```

**Error (400 Bad Request)**
```json
{
  "success": false,
  "message": "BHMC event with ID 99999 not found",
  "results": null
}
```

**Error (400 Bad Request)**
```json
{
  "success": false,
  "message": "BHMC event 'No Season Event' has no season assigned",
  "results": null
}
```

**Error (500 Internal Server Error)**
```json
{
  "success": false,
  "message": "Single event sync failed: Detailed error message",
  "results": null
}
```

### 3. Event Sync Status

**GET** `/api/golfgenius/event-sync-status/`

Returns current event synchronization status across all events.

#### Response

**Success (200 OK)**
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

**Error (500 Internal Server Error)**
```json
{
  "success": false,
  "message": "Failed to get event sync status: Error details",
  "status": null
}
```

## Event Matching Logic

### 1. Season Detection

The system determines the target season in the following order:
1. `season_override` parameter if provided
2. Active season from `SeasonSettings.is_active = True`
3. Latest season from existing events

### 2. Category Filtering

Only Golf Genius events in the "Men's Club" category are considered for matching. The system searches for categories containing both "men" and "club" (case-insensitive).

### 3. Date Calculation

For BHMC events:
- Single round events: `end_date = start_date`
- Multi-round events: `end_date = start_date + (rounds - 1) days`

### 4. Matching Priority

1. **Exact Date Matches**: BHMC start date = Golf Genius start date
2. **Date Range Overlaps**: BHMC date range overlaps with Golf Genius date range

### 5. Idempotent Operations

- Events with existing `gg_id` are skipped unless `force_update=true`
- Duplicate Golf Genius IDs are detected and prevented
- Safe to run multiple times without side effects

## Admin Interface Integration

The event sync functionality is integrated into the Django admin interface with the following actions:

### Event Admin Actions

1. **Sync selected events with Golf Genius**: Syncs only the selected events
2. **Sync all events in selected seasons with Golf Genius**: Syncs all events in the same season(s) as selected events

### Event List Display

The `gg_id` field is automatically added to the Event admin list display to show synchronization status.

## Error Handling

Common error scenarios:

1. **No Season Found**: Cannot determine target season
2. **No Men's Club Category**: Golf Genius account doesn't have Men's Club category
3. **API Connection Issues**: Network or authentication problems with Golf Genius API
4. **Duplicate IDs**: Attempting to assign same Golf Genius ID to multiple BHMC events
5. **Invalid Season**: Provided season_override is not a valid integer

## Usage Examples

### Sync Current Season Events

```bash
curl -X POST "https://your-domain.com/api/golfgenius/sync-events/" \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Sync Specific Season with Force Update

```bash
curl -X POST "https://your-domain.com/api/golfgenius/sync-events/" \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "season_override": 2024,
    "force_update": true
  }'
```

### Get Sync Status

```bash
curl -X GET "https://your-domain.com/api/golfgenius/event-sync-status/" \
  -H "Authorization: Bearer your-admin-token"
```

### Sync Single Event

```bash
curl -X POST "https://your-domain.com/api/golfgenius/sync-event/123/" \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Sync Single Event with Force Update

```bash
curl -X POST "https://your-domain.com/api/golfgenius/sync-event/123/" \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "force_update": true
  }'
```

## Related Endpoints

- `GET /api/golfgenius/sync-status/` - Player sync status
- `POST /api/golfgenius/sync-players/` - Player synchronization
- `POST /api/golfgenius/sync-event/<int:event_id>/` - Single event synchronization
- `GET /api/golfgenius/test-connection/` - Test Golf Genius API connection
- `GET /api/golfgenius/info/` - Golf Genius account information

## Technical Implementation

The event synchronization is implemented using:

- **Service Layer**: `GolfGeniusEventService` for business logic
- **Result Container**: `EventSyncResult` for operation results
- **API Client**: `GolfGeniusAPIClient` with rate limiting protection
- **Database Transactions**: Atomic updates for data consistency
- **Comprehensive Logging**: Detailed operation logging with structured logs