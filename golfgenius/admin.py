from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseRedirect

from register.models import Player
from events.models import Event
from .services import PlayerSyncService, EventSyncService, EventSyncResult
from .client import GolfGeniusAPIClient, GolfGeniusAPIError


# Note: Player model is already registered in register.admin
# We'll extend the existing admin instead of creating a new registration

def sync_selected_players_with_golf_genius(modeladmin, request, queryset):
    """Admin action to sync selected players with Golf Genius"""
    try:
        sync_service = PlayerSyncService()
        total_updated = 0
        total_errors = 0
        
        for player in queryset:
            result = sync_service.sync_single_player(player.pk, force_update=False)
            total_updated += result.updated_players
            total_errors += len(result.errors)
        
        if total_updated > 0:
            modeladmin.message_user(
                request,
                f"Successfully synced {total_updated} players with Golf Genius.",
                messages.SUCCESS
            )
        
        if total_errors > 0:
            modeladmin.message_user(
                request,
                f"Encountered {total_errors} errors during sync. Check logs for details.",
                messages.WARNING
            )
        
        if total_updated == 0 and total_errors == 0:
            modeladmin.message_user(
                request,
                "No players needed syncing (all already have Golf Genius IDs).",
                messages.INFO
            )
            
    except Exception as e:
        modeladmin.message_user(
            request,
            f"Sync failed: {str(e)}",
            messages.ERROR
        )

sync_selected_players_with_golf_genius.short_description = "Sync selected players with Golf Genius"

# Add the action to the existing PlayerAdmin
try:
    from register.admin import PlayerAdmin
    if hasattr(PlayerAdmin, 'actions'):
        if PlayerAdmin.actions is None:
            PlayerAdmin.actions = [sync_selected_players_with_golf_genius]
        else:
            # Convert tuple to list, add action, convert back to tuple
            actions = list(PlayerAdmin.actions)
            if sync_selected_players_with_golf_genius not in actions:
                actions.append(sync_selected_players_with_golf_genius)
            PlayerAdmin.actions = actions
    else:
        PlayerAdmin.actions = [sync_selected_players_with_golf_genius]
        
    # Add Golf Genius status to list display if not already there
    if hasattr(PlayerAdmin, 'list_display'):
        list_display = list(PlayerAdmin.list_display)
        if 'gg_id' not in list_display:
            list_display.append('gg_id')
            PlayerAdmin.list_display = tuple(list_display)
            
except ImportError:
    # Register app might not be available during initial setup
    pass


class GolfGeniusIntegrationAdmin:
    """
    Custom admin views for Golf Genius integration management
    """
    
    def __init__(self):
        self.sync_service = PlayerSyncService()
    
    def get_sync_dashboard_context(self):
        """Get context data for sync dashboard"""
        try:
            status = self.sync_service.get_sync_status()
            
            # Test Golf Genius connection
            try:
                client = GolfGeniusAPIClient()
                seasons = client.get_seasons()
                connection_status = "Connected"
                api_info = {
                    "seasons_count": len(seasons) if seasons else 0,
                    "base_url": client.base_url
                }
            except GolfGeniusAPIError as e:
                connection_status = f"Connection Error: {str(e)}"
                api_info = None
            
            return {
                "sync_status": status,
                "connection_status": connection_status,
                "api_info": api_info,
                "recent_synced_players": Player.objects.filter(
                    gg_id__isnull=False
                ).exclude(gg_id='').order_by('-id')[:10]
            }
            
        except Exception as e:
            return {
                "error": f"Failed to get dashboard data: {str(e)}"
            }


def sync_selected_events_with_golf_genius(modeladmin, request, queryset):
    """Admin action to sync selected events with Golf Genius"""
    try:
        sync_service = EventSyncService()
        total_updated = 0
        total_errors = 0
        
        # Group events by season for more efficient processing
        events_by_season = {}
        for event in queryset:
            season = event.season
            if season not in events_by_season:
                events_by_season[season] = []
            events_by_season[season].append(event)
        
        # Process each season separately
        for season, events in events_by_season.items():
            # Create a proper result object for this season
            temp_result = EventSyncResult()
            
            # Get all events for this season to match against
            season_events = list(Event.objects.filter(season=season))
            
            # Get Golf Genius events for this season
            gg_events = sync_service._get_golf_genius_events(season)
            
            if gg_events:
                # Match only the selected events
                selected_events = [e for e in season_events if e in events]
                sync_service._match_events(selected_events, gg_events, temp_result, force_update=False)
            
            total_updated += temp_result.updated_events
            total_errors += len(temp_result.errors)
        
        if total_updated > 0:
            modeladmin.message_user(
                request,
                f"Successfully synced {total_updated} events with Golf Genius.",
                messages.SUCCESS
            )
        
        if total_errors > 0:
            modeladmin.message_user(
                request,
                f"Encountered {total_errors} errors during sync. Check logs for details.",
                messages.WARNING
            )
        
        if total_updated == 0 and total_errors == 0:
            modeladmin.message_user(
                request,
                "No events needed syncing (all already have Golf Genius IDs or no matches found).",
                messages.INFO
            )
            
    except Exception as e:
        modeladmin.message_user(
            request,
            f"Event sync failed: {str(e)}",
            messages.ERROR
        )

sync_selected_events_with_golf_genius.short_description = "Sync selected events with Golf Genius"


def sync_season_events_with_golf_genius(modeladmin, request, queryset):
    """Admin action to sync all events in the same season(s) as selected events"""
    try:
        sync_service = EventSyncService()
        
        # Get unique seasons from selected events
        seasons = set(event.season for event in queryset if event.season)
        
        if not seasons:
            modeladmin.message_user(
                request,
                "No valid seasons found in selected events.",
                messages.WARNING
            )
            return
        
        total_updated = 0
        total_errors = 0
        
        for season in seasons:
            result = sync_service.sync_events(season_override=season, force_update=False)
            total_updated += result.updated_events
            total_errors += len(result.errors)
        
        if total_updated > 0:
            modeladmin.message_user(
                request,
                f"Successfully synced {total_updated} events across {len(seasons)} season(s) with Golf Genius.",
                messages.SUCCESS
            )
        
        if total_errors > 0:
            modeladmin.message_user(
                request,
                f"Encountered {total_errors} errors during sync. Check logs for details.",
                messages.WARNING
            )
        
        if total_updated == 0 and total_errors == 0:
            modeladmin.message_user(
                request,
                f"No events needed syncing in {len(seasons)} season(s).",
                messages.INFO
            )
            
    except Exception as e:
        modeladmin.message_user(
            request,
            f"Season event sync failed: {str(e)}",
            messages.ERROR
        )

sync_season_events_with_golf_genius.short_description = "Sync all events in selected seasons with Golf Genius"


# Add the actions to the existing EventAdmin
try:
    from events.admin import EventAdmin
    if hasattr(EventAdmin, 'actions'):
        if EventAdmin.actions is None:
            EventAdmin.actions = [sync_selected_events_with_golf_genius, sync_season_events_with_golf_genius]
        else:
            # Convert tuple to list, add actions, convert back to tuple
            actions = list(EventAdmin.actions)
            if sync_selected_events_with_golf_genius not in actions:
                actions.append(sync_selected_events_with_golf_genius)
            if sync_season_events_with_golf_genius not in actions:
                actions.append(sync_season_events_with_golf_genius)
            EventAdmin.actions = actions
    else:
        EventAdmin.actions = [sync_selected_events_with_golf_genius, sync_season_events_with_golf_genius]
        
    # Add Golf Genius ID to list display if not already there
    if hasattr(EventAdmin, 'list_display'):
        list_display = list(EventAdmin.list_display)
        if 'gg_id' not in list_display:
            list_display.append('gg_id')
            EventAdmin.list_display = tuple(list_display)
            
except ImportError:
    # Events app might not be available during initial setup
    pass
