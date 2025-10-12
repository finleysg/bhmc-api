from django.contrib import messages

from .player_sync_service import PlayerSyncService

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
                messages.SUCCESS,
            )

        if total_errors > 0:
            modeladmin.message_user(
                request,
                f"Encountered {total_errors} errors during sync. Check logs for details.",
                messages.WARNING,
            )

        if total_updated == 0 and total_errors == 0:
            modeladmin.message_user(
                request,
                "No players needed syncing (all already have Golf Genius IDs).",
                messages.INFO,
            )

    except Exception as e:
        modeladmin.message_user(request, f"Sync failed: {str(e)}", messages.ERROR)


sync_selected_players_with_golf_genius.short_description = (
    "Sync selected players with Golf Genius"
)

# Add the action to the existing PlayerAdmin
try:
    from register.admin import PlayerAdmin

    if hasattr(PlayerAdmin, "actions"):
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
    if hasattr(PlayerAdmin, "list_display"):
        list_display = list(PlayerAdmin.list_display)
        if "gg_id" not in list_display:
            list_display.append("gg_id")
            PlayerAdmin.list_display = tuple(list_display)

except ImportError:
    # Register app might not be available during initial setup
    pass
