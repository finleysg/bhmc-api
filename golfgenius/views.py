import structlog
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .services import PlayerSyncService
from .client import GolfGeniusAPIClient, GolfGeniusAPIError

logger = structlog.get_logger(__name__)


@api_view(['POST'])
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
        force_update = request.data.get('force_update', False)
        
        logger.info("Player sync requested by admin", 
                   user=request.user.username,
                   force_update=force_update)
        
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
            "results": result.to_dict()
        }
        
        logger.info("Player sync completed", 
                   user=request.user.username,
                   total=result.total_players,
                   updated=result.updated_players,
                   errors=len(result.errors))
        
        return Response(response_data, status=response_status)
        
    except Exception as e:
        error_msg = f"Player sync failed: {str(e)}"
        logger.error("Player sync failed", 
                    user=request.user.username,
                    error=str(e))
        
        return Response({
            "success": False,
            "message": error_msg,
            "results": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
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
        force_update = request.data.get('force_update', False)
        
        logger.info("Single player sync requested", 
                   user=request.user.username,
                   player_id=player_id,
                   force_update=force_update)
        
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
            "results": result.to_dict()
        }
        
        return Response(response_data, status=response_status)
        
    except Exception as e:
        error_msg = f"Single player sync failed: {str(e)}"
        logger.error("Single player sync failed", 
                    user=request.user.username,
                    player_id=player_id,
                    error=str(e))
        
        return Response({
            "success": False,
            "message": error_msg,
            "results": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def sync_status(request):
    """
    Admin-only endpoint to get current player sync status
    
    GET /api/golfgenius/sync-status/
    
    Returns:
        JSON response with sync status information
    """
    try:
        logger.info("Sync status requested", user=request.user.username)
        
        sync_service = PlayerSyncService()
        status_info = sync_service.get_sync_status()
        
        return Response({
            "success": True,
            "message": "Sync status retrieved",
            "status": status_info
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        error_msg = f"Failed to get sync status: {str(e)}"
        logger.error("Sync status request failed", 
                    user=request.user.username,
                    error=str(e))
        
        return Response({
            "success": False,
            "message": error_msg,
            "status": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def test_connection(request):
    """
    Admin-only endpoint to test Golf Genius API connection
    
    GET /api/golfgenius/test-connection/
    
    Returns:
        JSON response with connection test results
    """
    try:
        logger.info("Golf Genius connection test requested", user=request.user.username)
        
        client = GolfGeniusAPIClient()
        
        # Test connection by getting seasons (lightweight endpoint)
        seasons = client.get_seasons()
        
        response_data = {
            "success": True,
            "message": "Golf Genius API connection successful",
            "api_info": {
                "base_url": client.base_url,
                "has_api_key": bool(client.api_key),
                "seasons_count": len(seasons) if seasons else 0
            }
        }
        
        logger.info("Golf Genius connection test successful", 
                   user=request.user.username,
                   seasons_count=len(seasons) if seasons else 0)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except GolfGeniusAPIError as e:
        error_msg = f"Golf Genius API error: {str(e)}"
        logger.error("Golf Genius connection test failed", 
                    user=request.user.username,
                    error=str(e))
        
        return Response({
            "success": False,
            "message": error_msg,
            "api_info": None
        }, status=status.HTTP_502_BAD_GATEWAY)
        
    except Exception as e:
        error_msg = f"Connection test failed: {str(e)}"
        logger.error("Golf Genius connection test failed", 
                    user=request.user.username,
                    error=str(e))
        
        return Response({
            "success": False,
            "message": error_msg,
            "api_info": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def golf_genius_info(request):
    """
    Admin-only endpoint to get basic Golf Genius account information
    
    GET /api/golfgenius/info/
    
    Returns:
        JSON response with Golf Genius account info
    """
    try:
        logger.info("Golf Genius info requested", user=request.user.username)
        
        client = GolfGeniusAPIClient()
        
        # Get basic account information
        seasons = client.get_seasons()
        categories = client.get_categories()
        
        # Get a small sample of master roster for info
        try:
            roster_sample = client.get_master_roster(page=1)
        except:
            roster_sample = []
        
        response_data = {
            "success": True,
            "message": "Golf Genius account information retrieved",
            "info": {
                "api_base_url": client.base_url,
                "seasons": seasons,
                "categories": categories,
                "master_roster_sample_size": len(roster_sample) if roster_sample else 0
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except GolfGeniusAPIError as e:
        error_msg = f"Golf Genius API error: {str(e)}"
        logger.error("Golf Genius info request failed", 
                    user=request.user.username,
                    error=str(e))
        
        return Response({
            "success": False,
            "message": error_msg,
            "info": None
        }, status=status.HTTP_502_BAD_GATEWAY)
        
    except Exception as e:
        error_msg = f"Info request failed: {str(e)}"
        logger.error("Golf Genius info request failed", 
                    user=request.user.username,
                    error=str(e))
        
        return Response({
            "success": False,
            "message": error_msg,
            "info": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
