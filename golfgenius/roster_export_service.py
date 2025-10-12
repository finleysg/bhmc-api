import time
import structlog
from typing import Dict, List, Optional, Any

from register.models import RegistrationSlot
from events.models import Event
from payments.utils import get_start
from .client import GolfGeniusAPIClient

logger = structlog.get_logger(__name__)


class RosterExportResult:
    """Container for roster export operation results"""

    def __init__(self):
        self.total_players = 0
        self.processed_players = 0
        self.exported_players = 0
        self.created_players = 0
        self.updated_players = 0
        self.skipped_players = 0
        self.errors = []
        self.exports = []
        self.api_responses = []

    def add_error(self, player_name: str, error: str):
        """Add an error for a specific player"""
        self.errors.append({"player": player_name, "error": error})
        logger.error("Roster export error", player=player_name, error=error)

    def add_success(
        self,
        player_name: str,
        gg_member_id: str,
        api_response: Dict,
        operation: str = "created",
    ):
        """Record a successful export and whether it was a create or update"""
        entry = {
            "player": player_name,
            "gg_member_id": gg_member_id,
            "operation": operation,
            "api_response": api_response,
        }
        self.exports.append(entry)
        self.api_responses.append(api_response)
        self.exported_players += 1

        if operation == "created":
            self.created_players += 1
        elif operation == "updated":
            self.updated_players += 1

        logger.info(
            "Player exported successfully",
            player=player_name,
            gg_member_id=gg_member_id,
            operation=operation,
        )

    def add_skip(self, player_name: str, reason: str):
        """Record a skipped player"""
        self.skipped_players += 1
        logger.info("Player skipped", player=player_name, reason=reason)

    def to_dict(self) -> Dict:
        """Convert results to dictionary for API response"""
        return {
            "total_players": self.total_players,
            "processed_players": self.processed_players,
            "exported_players": self.exported_players,
            "created_players": self.created_players,
            "updated_players": self.updated_players,
            "skipped_players": self.skipped_players,
            "error_count": len(self.errors),
            "export_count": len(self.exports),
            "errors": self.errors,
            "exports": self.exports,
            "api_responses": self.api_responses,
        }


class RosterService:
    """
    Service for exporting BHMC event rosters to Golf Genius
    """

    def __init__(self, api_client: Optional[GolfGeniusAPIClient] = None):
        self.api_client = api_client or GolfGeniusAPIClient()
        self.api_delay = (
            0.5  # Delay between API calls in seconds to prevent rate limiting
        )

    def export_roster(self, event_id: int) -> RosterExportResult:
        """
        Export roster for a BHMC event to Golf Genius by creating member registrations

        Args:
            event_id: BHMC Event database ID

        Returns:
            RosterExportResult with operation details
        """
        result = RosterExportResult()

        logger.info("Starting roster export operation", event_id=event_id)

        try:
            # Get the BHMC event
            try:
                event = Event.objects.get(id=event_id)
                logger.info(
                    "Found BHMC event for roster export",
                    event_id=event_id,
                    event_name=event.name,
                    start_date=str(event.start_date),
                )
            except Event.DoesNotExist:
                result.add_error("SYSTEM", f"BHMC event with ID {event_id} not found")
                return result

            # Verify event has Golf Genius ID
            if not event.gg_id:
                result.add_error(
                    "SYSTEM", f"BHMC event '{event.name}' has no Golf Genius ID"
                )
                return result

            # Grab and validate rounds
            if not event.gg_rounds.exists():
                result.add_error("SYSTEM", f"Event {event.name} has no rounds")
                return result
            rounds = list(event.gg_rounds.values_list("gg_id", flat=True))

            # Get all registration slots for the event with players
            registration_slots = (
                RegistrationSlot.objects.filter(
                    event=event, status="R", player__isnull=False
                )
                .select_related("player", "registration", "event")
                .prefetch_related("fees__event_fee")
            )

            result.total_players = registration_slots.count()

            if result.total_players == 0:
                logger.info("No players registered for event", event_name=event.name)
                return result

            logger.info(
                "Found players to export",
                event_name=event.name,
                total_players=result.total_players,
            )

            # Fetch existing roster from Golf Genius to make export idempotent.
            roster_map = {}
            try:
                gg_members = self.api_client.get_event_roster(event.gg_id)
                for member in gg_members:
                    ext_id = member.get("external_id")
                    member_id = member.get("member_id") or member.get("id")
                    if ext_id and member_id:
                        roster_map[str(ext_id)] = str(member_id)
                logger.info(
                    "Built roster external_id -> member_id map",
                    event_name=event.name,
                    mapped_count=len(roster_map),
                )
            except Exception as e:
                logger.warning(
                    "Failed to fetch event roster from Golf Genius, proceeding with creates",
                    event_name=event.name,
                    error=str(e),
                )
                roster_map = {}

            # Process each player (use roster_map to decide create vs update)
            for slot in registration_slots:
                result.processed_players += 1
                self._export_player(slot, rounds, result, roster_map)

            logger.info(
                "Roster export operation completed",
                event_name=event.name,
                total=result.total_players,
                exported=result.exported_players,
                skipped=result.skipped_players,
                errors=len(result.errors),
            )

            return result

        except Exception as e:
            logger.error(
                "Roster export operation failed", error=str(e), event_id=event_id
            )
            result.add_error("SYSTEM", f"Roster export failed: {str(e)}")
            return result

    def export_single_player(self, event_id: int, player_id: int) -> RosterExportResult:
        """
        Export a single player (by player_id) for a BHMC event to Golf Genius.

        Args:
            event_id: BHMC Event database ID
            player_id: Player database ID

        Returns:
            RosterExportResult containing the outcome for this single player
        """
        result = RosterExportResult()

        logger.info(
            "Starting single player export", event_id=event_id, player_id=player_id
        )

        try:
            # Get the BHMC event
            try:
                event = Event.objects.get(id=event_id)
                logger.info(
                    "Found BHMC event for single player export",
                    event_id=event_id,
                    event_name=event.name,
                    start_date=str(event.start_date),
                )
            except Event.DoesNotExist:
                result.add_error("SYSTEM", f"BHMC event with ID {event_id} not found")
                return result

            # Verify event has Golf Genius ID
            if not event.gg_id:
                result.add_error(
                    "SYSTEM", f"BHMC event '{event.name}' has no Golf Genius ID"
                )
                return result

            # Grab and validate rounds
            if not event.gg_rounds.exists():
                result.add_error("SYSTEM", f"Event {event.name} has no rounds")
                return result
            rounds = list(event.gg_rounds.values_list("gg_id", flat=True))

            # Find registration slot for player
            slot = (
                RegistrationSlot.objects.filter(
                    event=event, player__id=player_id, status="R"
                )
                .select_related("player", "registration", "event")
                .prefetch_related("fees__event_fee")
                .first()
            )

            if not slot:
                result.add_error(
                    "SYSTEM",
                    f"No registration slot found for player {player_id} in event {event_id}",
                )
                return result

            # Build roster_map for idempotency
            roster_map: Dict[str, str] = {}
            try:
                gg_members = self.api_client.get_event_roster(event.gg_id)
                for member in gg_members:
                    ext_id = member.get("external_id")
                    member_id = member.get("member_id") or member.get("id")
                    if ext_id and member_id:
                        roster_map[str(ext_id)] = str(member_id)
                logger.info(
                    "Built roster external_id -> member_id map for single export",
                    event_id=event_id,
                    mapped_count=len(roster_map),
                )
            except Exception as e:
                logger.warning(
                    "Failed to fetch event roster from Golf Genius for single export, proceeding with create",
                    event_id=event_id,
                    error=str(e),
                )
                roster_map = {}

            # Perform the single export
            result.total_players = 1
            result.processed_players = 1
            self._export_player(slot, rounds, result, roster_map)

            logger.info(
                "Single player export operation completed",
                event_id=event_id,
                player_id=player_id,
                exported=result.exported_players,
                errors=len(result.errors),
            )

            return result

        except Exception as e:
            logger.error(
                "Single player export operation failed",
                error=str(e),
                event_id=event_id,
                player_id=player_id,
            )
            result.add_error("SYSTEM", f"Single player export failed: {str(e)}")
            return result

    def _export_player(
        self,
        slot: RegistrationSlot,
        rounds: List[str],
        result: RosterExportResult,
        roster_map: Optional[Dict[str, str]] = None,
    ):
        """
        Export a single player to Golf Genius. Uses roster_map to decide between creating
        a new member registration or updating an existing one to make exports idempotent.

        Args:
            slot: RegistrationSlot with player data
            round_id: Golf Genius round ID
            result: RosterExportResult to update
            roster_map: Mapping of external_id -> Golf Genius member_id
        """
        player = slot.player
        player_name = player.player_name()

        try:
            # Validate required data
            if not player.email:
                result.add_skip(player_name, "Missing email address")
                return

            if not player.ghin:
                result.add_skip(player_name, "Missing GHIN number")
                return

            # Build member registration data
            member_data = self._build_member_data(slot, rounds)

            # Add delay between API calls
            if result.processed_players > 1:
                time.sleep(self.api_delay)

            external_id = str(player.id)

            # Decide create vs update
            gg_member_id = None
            api_response = None

            if roster_map and roster_map.get(external_id):
                # Update existing member
                gg_member_id = roster_map.get(external_id)
                api_response = self.api_client.update_member_registration(
                    slot.event.gg_id, gg_member_id, member_data
                )
                result.add_success(
                    player_name, str(gg_member_id), api_response, operation="updated"
                )
            else:
                # Create new member registration
                api_response = self.api_client.create_member_registration(
                    slot.event.gg_id, member_data
                )
                gg_member_id = api_response.get("member_id") or api_response.get("id")
                result.add_success(
                    player_name, str(gg_member_id), api_response, operation="created"
                )

        except Exception as e:
            result.add_error(player_name, f"Export failed: {str(e)}")

    def _build_member_data(
        self, slot: RegistrationSlot, rounds: List[str]
    ) -> Dict[str, Any]:
        """
        Build the member registration data for Golf Genius API

        Args:
            slot: RegistrationSlot with player data
            round_id: Golf Genius round ID

        Returns:
            Dictionary containing member registration data
        """
        player = slot.player

        # Calculate team ID
        team_id = self._calculate_group(slot)

        # Get skins amounts
        gross_skins, net_skins = self._get_skins_amounts(slot)

        # Build custom fields
        custom_fields = {
            "Tee": player.tee or "Club",
            "Date of Birth": player.birth_date.strftime("%Y-%m-%d")
            if player.birth_date
            else "",
            "Team Id": team_id,
            "Entry Number": str(slot.id),
            "Course": slot.registration.course.name
            if slot.registration.course
            else "Unknown",
            "Full Name": player.player_name(),
            "Gross Skins": str(gross_skins),
            "Net Skins": str(net_skins),
        }

        return {
            "external_id": str(player.id),
            "last_name": player.last_name,
            "first_name": player.first_name,
            "email": player.email,
            "gender": "M",  # Always "M" as specified
            "handicap_network_id": player.ghin,
            "rounds": rounds,
            "custom_fields": custom_fields,
        }

    def _calculate_group(self, slot: RegistrationSlot) -> str:
        """
        Calculate the group for a registration slot

        Args:
            slot: RegistrationSlot object

        Returns:
            Group as string (e.g., "East 5:10 PM")
        """
        try:
            # Use the get_start utility function from payments.utils
            return get_start(slot.event, slot.registration, slot)
        except Exception as e:
            logger.warning(
                "Failed to calculate start time, using default",
                slot_id=slot.id,
                error=str(e),
            )
            return "12:00 PM"  # Default fallback

    def _get_skins_amounts(self, slot: RegistrationSlot) -> tuple[int, int]:
        """
        Get gross and net skins amounts from registration fees

        Args:
            slot: RegistrationSlot object

        Returns:
            Tuple of (gross_skins, net_skins) amounts
        """
        gross_skins = 0
        net_skins = 0

        try:
            # Get fees where fee code is "S" (skins)
            skins_fees = slot.fees.filter(event_fee__fee_type__code="S")

            for fee in skins_fees:
                amount = int(fee.amount)  # Convert Decimal to int
                fee_name = fee.event_fee.fee_type.name.lower()

                # Distinguish gross vs net based on fee type name
                if "net" in fee_name:
                    net_skins += amount
                else:
                    # Default to gross (includes "gross" and any other skins fees)
                    gross_skins += amount

        except Exception as e:
            logger.warning("Failed to get skins amounts", slot_id=slot.id, error=str(e))

        return gross_skins, net_skins
