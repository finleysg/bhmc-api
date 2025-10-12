import time
import structlog
from typing import Dict, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError

from register.models import Player
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
        logger.info(
            "Player matched and updated", email=email, member_card_id=member_card_id
        )

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
            "unmatched_emails": self.unmatched_emails,
        }


class PlayerSyncService:
    """
    Service for synchronizing BHMC players with Golf Genius master roster
    """

    def __init__(self, api_client: Optional[GolfGeniusAPIClient] = None):
        self.api_client = api_client or GolfGeniusAPIClient()
        self.api_delay = (
            0.5  # Delay between API calls in seconds to prevent rate limiting
        )

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
                players = Player.objects.filter(is_member=True).filter(
                    gg_id__isnull=True
                ) | Player.objects.filter(is_member=True).filter(gg_id="")

            result.total_players = players.count()

            logger.info(
                "Found players to sync",
                total_players=result.total_players,
                force_update=force_update,
            )

            if result.total_players == 0:
                logger.info("No players need syncing")
                return result

            # Process players in batches to avoid memory issues
            batch_size = 50
            for i in range(0, result.total_players, batch_size):
                batch_players = players[i : i + batch_size]
                self._sync_player_batch(batch_players, result, force_update)

            logger.info(
                "Player sync operation completed",
                total=result.total_players,
                updated=result.updated_players,
                skipped=result.skipped_players,
                errors=len(result.errors),
            )

            return result

        except Exception as e:
            logger.error("Player sync operation failed", error=str(e))
            result.add_error("SYSTEM", f"Sync operation failed: {str(e)}")
            return result

    def sync_single_player(
        self, player_id: int, force_update: bool = False
    ) -> PlayerSyncResult:
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

            logger.info(
                "Single player sync completed",
                player_id=player_id,
                email=player.email,
                updated=result.updated_players > 0,
            )

            return result

        except Player.DoesNotExist:
            result.add_error("SYSTEM", f"Player with ID {player_id} not found")
            return result
        except Exception as e:
            result.add_error("SYSTEM", f"Single player sync failed: {str(e)}")
            return result

    def _sync_player_batch(
        self, players: List[Player], result: PlayerSyncResult, force_update: bool
    ):
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
                logger.warning(
                    "Rate limit error in batch processing",
                    player_email=player.email,
                    error=str(e),
                )
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
            logger.warning(
                "Error searching for Golf Genius member", email=email, error=str(e)
            )
            return None

    @transaction.atomic
    def _update_player_gg_id(
        self, player: Player, gg_member: Dict, result: PlayerSyncResult
    ):
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
            if "member_card_id" in gg_member:
                member_card_id = gg_member["member_card_id"]
            elif "id" in gg_member:
                member_card_id = gg_member["id"]

            if not member_card_id:
                result.add_error(
                    player.email, "No member_card_id found in Golf Genius response"
                )
                return

            # Convert to string to ensure consistency
            member_card_id = str(member_card_id)

            # Check if another player already has this gg_id
            existing_player = (
                Player.objects.filter(gg_id=member_card_id)
                .exclude(pk=player.pk)
                .first()
            )
            if existing_player:
                result.add_error(
                    player.email,
                    f"Golf Genius ID {member_card_id} already assigned to {existing_player.email}",
                )
                return

            # Update the player
            old_gg_id = player.gg_id
            player.gg_id = member_card_id
            player.save(update_fields=["gg_id"])

            result.add_match(player.email, member_card_id)

            logger.info(
                "Updated player Golf Genius ID",
                player_id=player.pk,
                email=player.email,
                old_gg_id=old_gg_id,
                new_gg_id=member_card_id,
            )

        except ValidationError as e:
            result.add_error(player.email, f"Validation error: {str(e)}")
        except Exception as e:
            result.add_error(player.email, f"Update error: {str(e)}")
