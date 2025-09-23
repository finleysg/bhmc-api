import time
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from django.db import models, transaction
from django.core.exceptions import ValidationError

from register.models import Player
from events.models import Event
from core.models import SeasonSettings
from .client import GolfGeniusAPIClient, GolfGeniusAPIError, GolfGeniusRateLimitError

logger = structlog.get_logger(__name__)


class PlayerSyncResult:
    """Container for player sync operation results"""
    
    def __init__(self):
        self.total_players = 0
        self.processed_players = 0
        self.updated_players = 0
        self.skipped_players = 0
        self.errors = []
        self.matched_emails = []
        self.unmatched_emails = []
    
    def add_error(self, email: str, error: str):
        """Add an error for a specific email"""
        self.errors.append({"email": email, "error": error})
        logger.error("Player sync error", email=email, error=error)
    
    def add_match(self, email: str, member_card_id: str):
        """Record a successful match"""
        self.matched_emails.append({"email": email, "member_card_id": member_card_id})
        self.updated_players += 1
        logger.info("Player matched and updated", email=email, member_card_id=member_card_id)
    
    def add_skip(self, email: str, reason: str):
        """Record a skipped player"""
        self.skipped_players += 1
        logger.info("Player skipped", email=email, reason=reason)
    
    def add_unmatched(self, email: str):
        """Record an unmatched player"""
        self.unmatched_emails.append(email)
        logger.info("Player not found in Golf Genius", email=email)
    
    def to_dict(self) -> Dict:
        """Convert results to dictionary for API response"""
        return {
            "total_players": self.total_players,
            "processed_players": self.processed_players,
            "updated_players": self.updated_players,
            "skipped_players": self.skipped_players,
            "error_count": len(self.errors),
            "matched_count": len(self.matched_emails),
            "unmatched_count": len(self.unmatched_emails),
            "errors": self.errors,
            "matched_emails": self.matched_emails,
            "unmatched_emails": self.unmatched_emails
        }


class PlayerSyncService:
    """
    Service for synchronizing BHMC players with Golf Genius master roster
    """
    
    def __init__(self, api_client: Optional[GolfGeniusAPIClient] = None):
        self.api_client = api_client or GolfGeniusAPIClient()
        self.api_delay = 0.5  # Delay between API calls in seconds to prevent rate limiting
        
    def sync_all_players(self, force_update: bool = False) -> PlayerSyncResult:
        """
        Sync all BHMC players with Golf Genius master roster
        
        Args:
            force_update: If True, update players even if they already have gg_id
            
        Returns:
            PlayerSyncResult with operation details
        """
        result = PlayerSyncResult()
        
        logger.info("Starting player sync operation", force_update=force_update)
        
        try:
            # Get players that need syncing
            if force_update:
                players = Player.objects.filter(is_member=True).all()
            else:
                # Only sync players without gg_id
                players = Player.objects.filter(is_member=True).filter(gg_id__isnull=True) \
                  | Player.objects.filter(is_member=True).filter(gg_id='')
            
            result.total_players = players.count()
            
            logger.info("Found players to sync", 
                       total_players=result.total_players, 
                       force_update=force_update)
            
            if result.total_players == 0:
                logger.info("No players need syncing")
                return result
            
            # Process players in batches to avoid memory issues
            batch_size = 50
            for i in range(0, result.total_players, batch_size):
                batch_players = players[i:i + batch_size]
                self._sync_player_batch(batch_players, result, force_update)
            
            logger.info("Player sync operation completed", 
                       total=result.total_players,
                       updated=result.updated_players,
                       skipped=result.skipped_players,
                       errors=len(result.errors))
            
            return result
            
        except Exception as e:
            logger.error("Player sync operation failed", error=str(e))
            result.add_error("SYSTEM", f"Sync operation failed: {str(e)}")
            return result
    
    def _sync_player_batch(self, players: List[Player], result: PlayerSyncResult, force_update: bool):
        """
        Sync a batch of players with rate limiting protection
        
        Args:
            players: List of Player objects to sync
            result: PlayerSyncResult to update
            force_update: Whether to force update existing gg_id values
        """
        for i, player in enumerate(players):
            result.processed_players += 1
            
            try:
                # Skip if player already has gg_id and not forcing update
                if not force_update and player.gg_id:
                    result.add_skip(player.email, "Already has Golf Genius ID")
                    continue
                
                # Validate email
                if not player.email or not player.email.strip():
                    result.add_error(player.email or "EMPTY", "No email address")
                    continue
                
                # Add delay between API calls (except for first player)
                if i > 0:
                    time.sleep(self.api_delay)
                
                # Try to find player in Golf Genius
                gg_member = self._find_golf_genius_member(player.email.strip().lower())
                
                if gg_member:
                    # Update player with Golf Genius member_card_id
                    self._update_player_gg_id(player, gg_member, result)
                else:
                    result.add_unmatched(player.email)
                    
            except GolfGeniusRateLimitError as e:
                # If we still hit rate limits despite client retries, back off more
                logger.warning("Rate limit error in batch processing",
                             player_email=player.email,
                             error=str(e))
                result.add_error(player.email, f"Rate limit error: {str(e)}")
                
                # Increase delay for remaining players in this batch
                self.api_delay = min(self.api_delay * 2, 5.0)
                time.sleep(self.api_delay)
                
            except Exception as e:
                result.add_error(player.email, f"Processing error: {str(e)}")
    
    def _find_golf_genius_member(self, email: str) -> Optional[Dict]:
        """
        Find member in Golf Genius master roster by email
        
        Args:
            email: Email address to search for
            
        Returns:
            Golf Genius member dictionary if found, None otherwise
        """
        try:
            # First try the specific member endpoint
            member = self.api_client.get_master_roster_member(email)
            if member:
                return member
            
            # If not found with specific endpoint, could try master roster pagination
            # but for now we'll just return None
            return None
            
        except GolfGeniusAPIError as e:
            logger.warning("Error searching for Golf Genius member", 
                          email=email, error=str(e))
            return None
    
    @transaction.atomic
    def _update_player_gg_id(self, player: Player, gg_member: Dict, result: PlayerSyncResult):
        """
        Update player with Golf Genius member_card_id
        
        Args:
            player: BHMC Player object
            gg_member: Golf Genius member data
            result: PlayerSyncResult to update
        """
        try:
            # Extract member_card_id from Golf Genius response
            member_card_id = None
            
            # The API documentation shows different possible locations for the ID
            if 'member_card_id' in gg_member:
                member_card_id = gg_member['member_card_id']
            elif 'id' in gg_member:
                member_card_id = gg_member['id']
            
            if not member_card_id:
                result.add_error(player.email, "No member_card_id found in Golf Genius response")
                return
            
            # Convert to string to ensure consistency
            member_card_id = str(member_card_id)
            
            # Check if another player already has this gg_id
            existing_player = Player.objects.filter(gg_id=member_card_id).exclude(pk=player.pk).first()
            if existing_player:
                result.add_error(player.email, 
                               f"Golf Genius ID {member_card_id} already assigned to {existing_player.email}")
                return
            
            # Update the player
            old_gg_id = player.gg_id
            player.gg_id = member_card_id
            player.save(update_fields=['gg_id'])
            
            result.add_match(player.email, member_card_id)
            
            logger.info("Updated player Golf Genius ID",
                       player_id=player.pk,
                       email=player.email,
                       old_gg_id=old_gg_id,
                       new_gg_id=member_card_id)
            
        except ValidationError as e:
            result.add_error(player.email, f"Validation error: {str(e)}")
        except Exception as e:
            result.add_error(player.email, f"Update error: {str(e)}")
    
    def sync_single_player(self, player_id: int, force_update: bool = False) -> PlayerSyncResult:
        """
        Sync a single player with Golf Genius
        
        Args:
            player_id: ID of the player to sync
            force_update: Whether to force update existing gg_id
            
        Returns:
            PlayerSyncResult with operation details
        """
        result = PlayerSyncResult()
        
        try:
            player = Player.objects.get(pk=player_id)
            result.total_players = 1
            
            self._sync_player_batch([player], result, force_update)
            
            logger.info("Single player sync completed",
                       player_id=player_id,
                       email=player.email,
                       updated=result.updated_players > 0)
            
            return result
            
        except Player.DoesNotExist:
            result.add_error("SYSTEM", f"Player with ID {player_id} not found")
            return result
        except Exception as e:
            result.add_error("SYSTEM", f"Single player sync failed: {str(e)}")
            return result
    
    def get_sync_status(self) -> Dict:
        """
        Get current synchronization status
        
        Returns:
            Dictionary with sync status information
        """
        total_players = Player.objects.count()
        synced_players = Player.objects.filter(gg_id__isnull=False).exclude(gg_id='').count()
        unsynced_players = total_players - synced_players
        
        return {
            "total_players": total_players,
            "synced_players": synced_players,
            "unsynced_players": unsynced_players,
            "sync_percentage": round((synced_players / total_players * 100) if total_players > 0 else 0, 2)
        }


class EventSyncResult:
    """Container for event sync operation results"""
    
    def __init__(self):
        self.total_bhmc_events = 0
        self.total_gg_events = 0
        self.matched_events = 0
        self.updated_events = 0
        self.skipped_events = 0
        self.errors = []
        self.matches = []
        self.unmatched_bhmc_events = []
        self.unmatched_gg_events = []
    
    def add_error(self, event_name: str, error: str):
        """Add an error for a specific event"""
        self.errors.append({"event": event_name, "error": error})
        logger.error("Event sync error", event_name=event_name, error=error)
    
    def add_match(self, bhmc_event: Event, gg_event: Dict, match_type: str):
        """Record a successful match"""
        self.matches.append({
            "bhmc_event_id": bhmc_event.id,
            "bhmc_event_name": bhmc_event.name,
            "bhmc_start_date": str(bhmc_event.start_date),
            "gg_event_id": gg_event["id"],
            "gg_event_name": gg_event["name"],
            "gg_start_date": gg_event.get("start_date"),
            "gg_end_date": gg_event.get("end_date"),
            "match_type": match_type
        })
        self.matched_events += 1
        logger.info("Event matched",
                   bhmc_event=bhmc_event.name,
                   gg_event=gg_event["name"],
                   match_type=match_type)
    
    def add_skip(self, event_name: str, reason: str):
        """Record a skipped event"""
        self.skipped_events += 1
        logger.info("Event skipped", event_name=event_name, reason=reason)
    
    def add_unmatched_bhmc(self, event: Event):
        """Record an unmatched BHMC event"""
        self.unmatched_bhmc_events.append({
            "id": event.id,
            "name": event.name,
            "start_date": str(event.start_date),
            "rounds": event.rounds,
            "season": event.season
        })
        logger.info("BHMC event not matched", event_name=event.name)
    
    def add_unmatched_gg(self, gg_event: Dict):
        """Record an unmatched Golf Genius event"""
        self.unmatched_gg_events.append({
            "id": gg_event["id"],
            "name": gg_event["name"],
            "start_date": gg_event.get("start_date"),
            "end_date": gg_event.get("end_date")
        })
        logger.info("Golf Genius event not matched", event_name=gg_event["name"])
    
    def to_dict(self) -> Dict:
        """Convert results to dictionary for API response"""
        return {
            "total_bhmc_events": self.total_bhmc_events,
            "total_gg_events": self.total_gg_events,
            "matched_events": self.matched_events,
            "updated_events": self.updated_events,
            "skipped_events": self.skipped_events,
            "error_count": len(self.errors),
            "unmatched_bhmc_count": len(self.unmatched_bhmc_events),
            "unmatched_gg_count": len(self.unmatched_gg_events),
            "errors": self.errors,
            "matches": self.matches,
            "unmatched_bhmc_events": self.unmatched_bhmc_events,
            "unmatched_gg_events": self.unmatched_gg_events
        }


class GolfGeniusEventService:
    """
    Service for synchronizing BHMC events with Golf Genius events
    """
    
    def __init__(self, api_client: Optional[GolfGeniusAPIClient] = None):
        self.api_client = api_client or GolfGeniusAPIClient()
        self.api_delay = 0.5  # Delay between API calls to prevent rate limiting
        
    def sync_single_event(self, event_id: int, force_update: bool = False) -> EventSyncResult:
        """
        Sync a single BHMC event with Golf Genius events based on date matching
        
        Args:
            event_id: The database ID of the BHMC event to sync
            force_update: Whether to update events that already have Golf Genius IDs
            
        Returns:
            EventSyncResult containing sync results for the single event
        """
        result = EventSyncResult()
        
        try:
            logger.info("Starting single event sync operation", event_id=event_id, force_update=force_update)
            
            # Get the specific BHMC event
            try:
                from events.models import Event
                bhmc_event = Event.objects.get(id=event_id)
                logger.info("Found BHMC event for sync",
                           event_id=event_id,
                           event_name=bhmc_event.name,
                           start_date=str(bhmc_event.start_date),
                           season=bhmc_event.season)
            except Event.DoesNotExist:
                error_msg = f"BHMC event with ID {event_id} not found"
                result.add_error("SYSTEM", error_msg)
                logger.error("Single event sync failed", error=error_msg, event_id=event_id)
                return result
            
            # Check if event already has Golf Genius ID and force_update is False
            if bhmc_event.gg_id and not force_update:
                result.add_skip(bhmc_event.name, f"Already has Golf Genius ID {bhmc_event.gg_id}")
                logger.info("Event skipped - already has Golf Genius ID",
                           event_name=bhmc_event.name,
                           gg_id=bhmc_event.gg_id)
                return result
            
            # Determine target season (use event's season)
            target_season = bhmc_event.season
            if not target_season or target_season == 0:
                error_msg = f"BHMC event '{bhmc_event.name}' has no season assigned"
                logger.error("Event sync error", error=error_msg, event_name=bhmc_event.name)
                result.errors.append({
                    "bhmc_event_id": event_id,
                    "event_name": bhmc_event.name,
                    "error": error_msg
                })
                return result
                
            logger.info("Using event's season for sync", season=target_season, event_name=bhmc_event.name)
            
            # Get Golf Genius events for the season
            gg_events = self._get_golf_genius_events(target_season)
            if not gg_events:
                result.add_unmatched_bhmc(bhmc_event)
                logger.info("No Golf Genius events found for season", season=target_season)
                return result
            
            result.total_bhmc_events = 1
            result.total_gg_events = len(gg_events)
            
            # Try to match this single event with Golf Genius events
            self._match_events([bhmc_event], gg_events, result, force_update)
            
            logger.info("Single event sync operation completed",
                       event_id=event_id,
                       matched=result.matched_events,
                       updated=result.updated_events,
                       errors=len(result.errors))
            
            return result
            
        except Exception as e:
            error_msg = f"Single event sync failed: {str(e)}"
            logger.error("Single event sync operation failed", error=str(e), event_id=event_id)
            result.add_error("SYSTEM", error_msg)
            return result
        
    def sync_events(self, season_override: Optional[int] = None, force_update: bool = False) -> EventSyncResult:
        """
        Sync BHMC events with Golf Genius events based on date ranges and season
        
        Args:
            season_override: Override the season detection (use specific season)
            force_update: If True, update events even if they already have gg_id
            
        Returns:
            EventSyncResult with operation details
        """
        result = EventSyncResult()
        
        logger.info("Starting event sync operation",
                   season_override=season_override,
                   force_update=force_update)
        
        try:
            # Determine target season
            target_season = self._get_target_season(season_override)
            if not target_season:
                result.add_error("SYSTEM", "Could not determine target season")
                return result
            
            logger.info("Using target season", season=target_season)
            
            # Get BHMC events for the season
            bhmc_events = self._get_bhmc_events(target_season, force_update)
            result.total_bhmc_events = len(bhmc_events)
            
            if not bhmc_events:
                logger.info("No BHMC events found for season", season=target_season)
                return result
            
            # Get Golf Genius events for the season
            gg_events = self._get_golf_genius_events(target_season)
            result.total_gg_events = len(gg_events)
            
            if not gg_events:
                logger.info("No Golf Genius events found for season", season=target_season)
                # All BHMC events are unmatched
                for event in bhmc_events:
                    result.add_unmatched_bhmc(event)
                return result
            
            # Match events and update database
            self._match_events(bhmc_events, gg_events, result, force_update)
            
            logger.info("Event sync operation completed",
                       total_bhmc=result.total_bhmc_events,
                       total_gg=result.total_gg_events,
                       matched=result.matched_events,
                       updated=result.updated_events,
                       errors=len(result.errors))
            
            return result
            
        except Exception as e:
            logger.error("Event sync operation failed", error=str(e))
            result.add_error("SYSTEM", f"Sync operation failed: {str(e)}")
            return result
    
    def _get_target_season(self, season_override: Optional[int]) -> Optional[int]:
        """
        Get the target season for synchronization
        
        Args:
            season_override: Optional season override
            
        Returns:
            Season number or None if cannot be determined
        """
        if season_override:
            return season_override
        
        # Try to get current active season
        try:
            active_season = SeasonSettings.objects.filter(is_active=True).first()
            if active_season:
                return active_season.season
        except Exception as e:
            logger.warning("Could not get active season from settings", error=str(e))
        
        # Fallback: get the most recent season from events
        try:
            latest_event = Event.objects.order_by('-season').first()
            if latest_event and latest_event.season:
                return latest_event.season
        except Exception as e:
            logger.warning("Could not get latest season from events", error=str(e))
        
        return None
    
    def _get_bhmc_events(self, season: int, force_update: bool) -> List[Event]:
        """
        Get BHMC events that need synchronization
        
        Args:
            season: Target season
            force_update: Whether to include events with existing gg_id
            
        Returns:
            List of Event objects
        """
        events_query = Event.objects.filter(season=season)
        
        if not force_update:
            # Only get events without gg_id
            events_query = events_query.filter(
                models.Q(gg_id__isnull=True) | models.Q(gg_id='')
            )
        
        return list(events_query.order_by('start_date'))
    
    def _get_golf_genius_events(self, season: int) -> List[Dict]:
        """
        Get Golf Genius events for the season, filtered by Men's Club category
        
        Args:
            season: Target season
            
        Returns:
            List of Golf Genius event dictionaries
        """
        try:
            # First, get the "Men's Club" category ID
            mens_club_category_id = self._get_mens_club_category_id()
            if not mens_club_category_id:
                logger.warning("Could not find Men's Club category in Golf Genius")
                return []
            
            # Get seasons to find the target season
            seasons = self.api_client.get_seasons()
            target_season_id = None
            
            for season_data in seasons:
                season_info = season_data.get('season', {})
                # Try to match by name (assuming season name contains the year)
                if str(season) in season_info.get('name', ''):
                    target_season_id = season_info.get('id')
                    break
            
            if not target_season_id:
                logger.warning("Could not find target season in Golf Genius", season=season)
                return []
            
            logger.info("Found target season in Golf Genius",
                       season=season,
                       gg_season_id=target_season_id)
            
            # Get events for the season and category
            events = self.api_client.get_events(
                season_id=target_season_id,
                category_id=mens_club_category_id
            )
            
            # Extract event data from the response format
            gg_events = []
            for event_data in events:
                event_info = event_data.get('event', {})
                if event_info:
                    gg_events.append(event_info)
            
            logger.info("Retrieved Golf Genius events",
                       season=season,
                       count=len(gg_events))
            
            return gg_events
            
        except Exception as e:
            logger.error("Failed to get Golf Genius events", season=season, error=str(e))
            return []
    
    def _get_mens_club_category_id(self) -> Optional[str]:
        """
        Get the category ID for "Men's Club" events
        
        Returns:
            Category ID string or None if not found
        """
        try:
            categories = self.api_client.get_categories()
            
            for category_data in categories:
                category_info = category_data.get('category', {})
                category_name = category_info.get('name', '').lower()
                
                # Look for "men's club" or similar variations
                if 'men' in category_name and 'club' in category_name:
                    category_id = category_info.get('id')
                    logger.info("Found Men's Club category",
                               name=category_info.get('name'),
                               id=category_id)
                    return str(category_id)
            
            logger.warning("Men's Club category not found in Golf Genius categories")
            return None
            
        except Exception as e:
            logger.error("Failed to get Golf Genius categories", error=str(e))
            return None
    
    def _calculate_end_date(self, event: Event):
        """
        Calculate the end date for a BHMC event based on rounds
        
        Args:
            event: BHMC Event object
            
        Returns:
            End date (same as start_date if rounds is None/1, otherwise start_date + rounds - 1 days)
        """
        if not event.rounds or event.rounds <= 1:
            return event.start_date
        
        return event.start_date + timedelta(days=event.rounds - 1)
    
    def _events_exact_match(self, bhmc_event: Event, gg_event: Dict) -> bool:
        """
        Check if events have exact date match
        
        Args:
            bhmc_event: BHMC Event object
            gg_event: Golf Genius event dictionary
            
        Returns:
            True if start dates match exactly
        """
        gg_start_date = gg_event.get('start_date')
        if not gg_start_date:
            return False
        
        try:
            # Parse the GG date string (format: YYYY-MM-DD)
            gg_start = datetime.strptime(gg_start_date, '%Y-%m-%d').date()
            return bhmc_event.start_date == gg_start
        except (ValueError, TypeError):
            return False
    
    def _events_overlap(self, bhmc_event: Event, gg_event: Dict) -> bool:
        """
        Check if events have overlapping date ranges
        
        Args:
            bhmc_event: BHMC Event object
            gg_event: Golf Genius event dictionary
            
        Returns:
            True if date ranges overlap
        """
        gg_start_date = gg_event.get('start_date')
        gg_end_date = gg_event.get('end_date')
        
        if not gg_start_date:
            return False
        
        try:
            # Parse GG dates
            gg_start = datetime.strptime(gg_start_date, '%Y-%m-%d').date()
            gg_end = gg_start  # Default to start date
            
            if gg_end_date:
                gg_end = datetime.strptime(gg_end_date, '%Y-%m-%d').date()
            
            # Calculate BHMC event end date
            bhmc_start = bhmc_event.start_date
            bhmc_end = self._calculate_end_date(bhmc_event)
            
            # Check for overlap: events overlap if one starts before the other ends
            return bhmc_start <= gg_end and gg_start <= bhmc_end
            
        except (ValueError, TypeError):
            return False
    
    def _match_events(self, bhmc_events: List[Event], gg_events: List[Dict],
                     result: EventSyncResult, force_update: bool):
        """
        Match BHMC events with Golf Genius events and update database
        
        Args:
            bhmc_events: List of BHMC Event objects
            gg_events: List of Golf Genius event dictionaries
            result: EventSyncResult to update
            force_update: Whether to force update existing gg_id values
        """
        used_gg_events: Set[str] = set()
        
        # First pass: exact date matches (highest priority)
        for bhmc_event in bhmc_events[:]:  # Use slice to allow modification during iteration
            if bhmc_event.gg_id and not force_update:
                result.add_skip(bhmc_event.name, "Already has Golf Genius ID")
                continue
            
            for gg_event in gg_events:
                gg_id = str(gg_event.get('id', ''))
                
                if gg_id in used_gg_events:
                    continue
                
                if self._events_exact_match(bhmc_event, gg_event):
                    self._update_event_match(bhmc_event, gg_event, "exact_date", result)
                    used_gg_events.add(gg_id)
                    bhmc_events.remove(bhmc_event)
                    break
        
        # Second pass: overlapping date ranges for remaining events
        for bhmc_event in bhmc_events[:]:
            if bhmc_event.gg_id and not force_update:
                result.add_skip(bhmc_event.name, "Already has Golf Genius ID")
                continue
            
            for gg_event in gg_events:
                gg_id = str(gg_event.get('id', ''))
                
                if gg_id in used_gg_events:
                    continue
                
                if self._events_overlap(bhmc_event, gg_event):
                    self._update_event_match(bhmc_event, gg_event, "date_overlap", result)
                    used_gg_events.add(gg_id)
                    bhmc_events.remove(bhmc_event)
                    break
        
        # Record unmatched events
        for bhmc_event in bhmc_events:
            result.add_unmatched_bhmc(bhmc_event)
        
        for gg_event in gg_events:
            gg_id = str(gg_event.get('id', ''))
            if gg_id not in used_gg_events:
                result.add_unmatched_gg(gg_event)
    
    @transaction.atomic
    def _update_event_match(self, bhmc_event: Event, gg_event: Dict,
                           match_type: str, result: EventSyncResult):
        """
        Update BHMC event with Golf Genius event ID
        
        Args:
            bhmc_event: BHMC Event object
            gg_event: Golf Genius event dictionary
            match_type: Type of match ("exact_date" or "date_overlap")
            result: EventSyncResult to update
        """
        try:
            gg_id = str(gg_event.get('id', ''))
            
            if not gg_id:
                result.add_error(bhmc_event.name, "No event ID found in Golf Genius response")
                return
            
            # Check if another event already has this gg_id
            existing_event = Event.objects.filter(gg_id=gg_id).exclude(pk=bhmc_event.pk).first()
            if existing_event:
                result.add_error(bhmc_event.name,
                               f"Golf Genius ID {gg_id} already assigned to {existing_event.name}")
                return
            
            # Update the event
            old_gg_id = bhmc_event.gg_id
            bhmc_event.gg_id = gg_id
            bhmc_event.save(update_fields=['gg_id'])
            
            result.add_match(bhmc_event, gg_event, match_type)
            result.updated_events += 1
            
            logger.info("Updated event Golf Genius ID",
                       event_id=bhmc_event.pk,
                       bhmc_event_name=bhmc_event.name,
                       old_gg_id=old_gg_id,
                       new_gg_id=gg_id,
                       match_type=match_type)
            
        except ValidationError as e:
            result.add_error(bhmc_event.name, f"Validation error: {str(e)}")
        except Exception as e:
            result.add_error(bhmc_event.name, f"Update error: {str(e)}")
    
    def get_sync_status(self) -> Dict:
        """
        Get current event synchronization status
        
        Returns:
            Dictionary with sync status information
        """
        total_events = Event.objects.count()
        synced_events = Event.objects.filter(gg_id__isnull=False).exclude(gg_id='').count()
        unsynced_events = total_events - synced_events
        
        return {
            "total_events": total_events,
            "synced_events": synced_events,
            "unsynced_events": unsynced_events,
            "sync_percentage": round((synced_events / total_events * 100) if total_events > 0 else 0, 2)
        }