import structlog
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from golfgenius.event_sync_service import EventSyncService
from golfgenius.player_sync_service import PlayerSyncService

logger = structlog.get_logger(__name__)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def sync_players(request):
    """
    Admin-only endpoint to sync all BHMC players with Golf Genius master roster

    POST /api/golfgenius/sync-players/

    Body parameters:
    - force_update (bool): Whether to update players that already have gg_id (default: False)

    Returns:
        JSON response with sync results
    """
    try:
        force_update = request.data.get("force_update", False)

        logger.info(
            "Player sync requested by admin",
            user=request.user.username,
            force_update=force_update,
        )

        # Initialize sync service and perform sync
        sync_service = PlayerSyncService()
        result = sync_service.sync_all_players(force_update=force_update)

        # Determine response status based on results
        if len(result.errors) == 0:
            response_status = status.HTTP_200_OK
        elif result.updated_players > 0:
            # Some success, some errors
            response_status = status.HTTP_207_MULTI_STATUS
        else:
            # All errors
            response_status = status.HTTP_500_INTERNAL_SERVER_ERROR

        response_data = {
            "success": True,
            "message": "Player sync completed",
            "results": result.to_dict(),
        }

        logger.info(
            "Player sync completed",
            user=request.user.username,
            total=result.total_players,
            updated=result.updated_players,
            errors=len(result.errors),
        )

        return Response(response_data, status=response_status)

    except Exception as e:
        error_msg = f"Player sync failed: {str(e)}"
        logger.error("Player sync failed", user=request.user.username, error=str(e))

        return Response(
            {"success": False, "message": error_msg, "results": None},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def sync_single_player(request, player_id):
    """
    Admin-only endpoint to sync a single player with Golf Genius

    POST /api/golfgenius/sync-player/{player_id}/

    Body parameters:
    - force_update (bool): Whether to update if player already has gg_id (default: False)

    Returns:
        JSON response with sync result
    """
    try:
        force_update = request.data.get("force_update", False)

        logger.info(
            "Single player sync requested",
            user=request.user.username,
            player_id=player_id,
            force_update=force_update,
        )

        # Initialize sync service and sync single player
        sync_service = PlayerSyncService()
        result = sync_service.sync_single_player(player_id, force_update=force_update)

        # Determine response status
        if len(result.errors) == 0 and result.updated_players > 0:
            response_status = status.HTTP_200_OK
        elif len(result.errors) == 0 and result.skipped_players > 0:
            response_status = status.HTTP_200_OK
        else:
            response_status = status.HTTP_400_BAD_REQUEST

        response_data = {
            "success": len(result.errors) == 0,
            "message": "Single player sync completed",
            "results": result.to_dict(),
        }

        return Response(response_data, status=response_status)

    except Exception as e:
        error_msg = f"Single player sync failed: {str(e)}"
        logger.error(
            "Single player sync failed",
            user=request.user.username,
            player_id=player_id,
            error=str(e),
        )

        return Response(
            {"success": False, "message": error_msg, "results": None},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def sync_event(request, event_id):
    """
    Admin-only endpoint to sync a single BHMC event with Golf Genius events

    POST /api/golfgenius/sync-event/{event_id}/

    Returns:
        JSON response with sync result for the single event
    """
    try:
        # Validate event_id
        try:
            event_id = int(event_id)
        except (ValueError, TypeError):
            return Response(
                {
                    "success": False,
                    "message": "Invalid event ID",
                    "error": "Event ID must be a valid integer",
                    "results": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "Single event sync requested", user=request.user.username, event_id=event_id
        )

        # Initialize sync service and sync single event
        sync_service = EventSyncService()
        result = sync_service.sync_event(event_id=event_id)

        response_data = {
            "success": len(result.errors) == 0,
            "message": "Single event sync completed",
            "results": result.to_dict(),
        }

        return Response(response_data, status=200 if len(result.errors) == 0 else 500)

    except Exception as e:
        error_msg = f"Single event sync failed: {str(e)}"
        logger.error(
            "Single event sync failed",
            user=request.user.username,
            event_id=event_id,
            error=str(e),
        )

        return Response(
            {"success": False, "message": error_msg, "results": None},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
