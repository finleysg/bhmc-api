import structlog
import decimal
from decimal import Decimal
from typing import Dict, List, Optional, Any
from django.db import transaction
from events.models import Tournament, TournamentResult
from register.models import Player
from .client import GolfGeniusAPIClient

logger = structlog.get_logger(__name__)


class ResultsImportResult:
    """Container for results import operation results"""

    def __init__(self, tournament: Tournament):
        self.tournament_id = tournament.id
        self.tournament_name = tournament.name
        self.event_name = tournament.event.name
        self.errors = []
        self.results_imported = 0

    def add_error(self, error: str):
        """Add an error for a specific tournament"""
        self.errors.append(error)
        logger.error(
            "Results import error", tournament_id=self.tournament_id, error=error
        )

    def to_dict(self) -> Dict:
        """Convert results to dictionary for API response"""
        return {
            "tournament": f"{self.event_name} - {self.tournament_name}",
            "results_imported": self.results_imported,
            "errors": self.errors,
        }


class ResultsImportService:
    """
    Service for importing tournament results from Golf Genius
    """

    def __init__(self, api_client: Optional[GolfGeniusAPIClient] = None):
        self.api_client = api_client or GolfGeniusAPIClient()

    def import_stroke_play_results(self, event_id: int) -> List[ResultsImportResult]:
        """
        Import stroke play tournament results from Golf Genius for tournaments with format == 'stroke' in a specific event

        Args:
            event_id: The database ID of the event to import results for

        Returns:
            List of ResultsImportResult objects containing success/error information
        """
        results = []

        # Get all stroke play tournaments for the specified event
        tournaments = Tournament.objects.filter(
            event_id=event_id, format="stroke"
        ).select_related("event", "round")

        if not tournaments.exists():
            logger.warning(
                "No stroke play tournaments found for event", event_id=event_id
            )
            return results

        for tournament in tournaments:
            result = self._import_tournament_results(tournament)
            results.append(result)

        return results

    def import_points(self, event_id: int) -> List[ResultsImportResult]:
        """
        Import points tournament results from Golf Genius for tournaments with format == 'points' in a specific event

        Args:
            event_id: The database ID of the event to import results for

        Returns:
            List of ResultsImportResult objects containing success/error information
        """
        results = []

        # Get all points tournaments for the specified event
        tournaments = Tournament.objects.filter(
            event_id=event_id, format="points"
        ).select_related("event", "round")

        if not tournaments.exists():
            logger.warning("No points tournaments found for event", event_id=event_id)
            return results

        for tournament in tournaments:
            result = self._import_points_tournament_results(tournament)
            results.append(result)

        return results

    def _import_tournament_results(self, tournament: Tournament) -> ResultsImportResult:
        """
        Import results for a single tournament

        Args:
            tournament: The Tournament instance to import results for

        Returns:
            ResultsImportResult with import status and any errors
        """
        result = ResultsImportResult(tournament)

        try:
            # Check if event has Golf Genius ID
            if not tournament.event.gg_id:
                result.add_error(
                    "Event must first be synced with Golf Genius. Run Event Sync process."
                )
                return result

            # Check if round has Golf Genius ID
            if not tournament.round.gg_id:
                result.add_error(
                    "Round must first be synced with Golf Genius. Run Event Sync process."
                )
                return result

            # Check if tournament has Golf Genius ID
            if not tournament.gg_id:
                result.add_error(
                    "Tournament must first be synced with Golf Genius. Run Event Sync process."
                )
                return result

            # Delete existing results for this tournament (idempotent operation)
            with transaction.atomic():
                deleted_count = TournamentResult.objects.filter(
                    tournament=tournament
                ).delete()[0]
                logger.info(
                    "Deleted existing tournament results",
                    tournament_id=tournament.id,
                    deleted_count=deleted_count,
                )

            # Get tournament results from Golf Genius API
            try:
                gg_results = self.api_client.get_tournament_results(
                    event_id=tournament.event.gg_id,
                    round_id=tournament.round.gg_id,
                    tournament_id=tournament.gg_id,
                )
            except Exception as e:
                result.add_error(
                    f"Failed to fetch results from Golf Genius API: {str(e)}"
                )
                return result

            # Process the results data
            self._process_tournament_results(tournament, gg_results, result)

        except Exception as e:
            result.add_error(f"Unexpected error importing results: {str(e)}")
            logger.exception(
                "Unexpected error in tournament results import",
                tournament_id=tournament.id,
            )

        return result

    def _import_points_tournament_results(
        self, tournament: Tournament
    ) -> ResultsImportResult:
        """
        Import points results for a single tournament

        Args:
            tournament: The Tournament instance to import results for

        Returns:
            ResultsImportResult with import status and any errors
        """
        result = ResultsImportResult(tournament)

        try:
            # Check if event has Golf Genius ID
            if not tournament.event.gg_id:
                result.add_error(
                    "Event must first be synced with Golf Genius. Run Event Sync process."
                )
                return result

            # Check if round has Golf Genius ID
            if not tournament.round.gg_id:
                result.add_error(
                    "Round must first be synced with Golf Genius. Run Event Sync process."
                )
                return result

            # Check if tournament has Golf Genius ID
            if not tournament.gg_id:
                result.add_error(
                    "Tournament must first be synced with Golf Genius. Run Event Sync process."
                )
                return result

            # Delete existing results for this tournament (idempotent operation)
            with transaction.atomic():
                deleted_count = TournamentResult.objects.filter(
                    tournament=tournament
                ).delete()[0]
                logger.info(
                    "Deleted existing tournament results",
                    tournament_id=tournament.id,
                    deleted_count=deleted_count,
                )

            # Get tournament results from Golf Genius API
            try:
                gg_results = self.api_client.get_tournament_results(
                    event_id=tournament.event.gg_id,
                    round_id=tournament.round.gg_id,
                    tournament_id=tournament.gg_id,
                )
            except Exception as e:
                result.add_error(
                    f"Failed to fetch results from Golf Genius API: {str(e)}"
                )
                return result

            # Process the points results data
            self._process_points_tournament_results(tournament, gg_results, result)

        except Exception as e:
            result.add_error(f"Unexpected error importing points results: {str(e)}")
            logger.exception(
                "Unexpected error in tournament points results import",
                tournament_id=tournament.id,
            )

        return result

    def _process_tournament_results(
        self,
        tournament: Tournament,
        gg_results: Dict[str, Any],
        result: ResultsImportResult,
    ):
        """
        Process the Golf Genius results data and create TournamentResult records

        Args:
            tournament: The Tournament instance
            gg_results: Raw results data from Golf Genius API
            result: ResultsImportResult to track errors and success count
        """
        if not gg_results or "event" not in gg_results:
            result.add_error("Invalid or empty results data from Golf Genius")
            return

        event_data = gg_results["event"]
        if "scopes" not in event_data:
            result.add_error("No scopes found in results data")
            return

        # Process each scope (flight)
        for scope in event_data["scopes"]:
            flight_name = scope.get("name", "")

            if "aggregates" not in scope:
                continue

            # Process each aggregate (player result)
            for aggregate in scope["aggregates"]:
                try:
                    self._process_player_result(
                        tournament, aggregate, flight_name, result
                    )
                except Exception as e:
                    result.add_error(f"Error processing player result: {str(e)}")
                    logger.exception(
                        "Error processing player result", tournament_id=tournament.id
                    )

    def _process_points_tournament_results(
        self,
        tournament: Tournament,
        gg_results: Dict[str, Any],
        result: ResultsImportResult,
    ):
        """
        Process the Golf Genius points results data and create TournamentResult records

        Args:
            tournament: The Tournament instance
            gg_results: Raw results data from Golf Genius API
            result: ResultsImportResult to track errors and success count
        """
        if not gg_results or "event" not in gg_results:
            result.add_error("Invalid or empty results data from Golf Genius")
            return

        event_data = gg_results["event"]
        if "scopes" not in event_data:
            result.add_error("No scopes found in results data")
            return

        # Process each scope (flight)
        for scope in event_data["scopes"]:
            flight_name = scope.get("name", "N/A") if scope.get("name") else "N/A"

            if "aggregates" not in scope:
                continue

            # Process each aggregate (player result)
            for aggregate in scope["aggregates"]:
                try:
                    self._process_points_player_result(
                        tournament, aggregate, flight_name, result
                    )
                except Exception as e:
                    result.add_error(f"Error processing player result: {str(e)}")
                    logger.exception(
                        "Error processing player result", tournament_id=tournament.id
                    )

    def _process_player_result(
        self,
        tournament: Tournament,
        aggregate: Dict[str, Any],
        flight: str,
        result: ResultsImportResult,
    ):
        """
        Process a single player result and create/update TournamentResult record

        Args:
            tournament: The Tournament instance
            aggregate: Player result data from Golf Genius
            flight: Flight name from scope
            result: ResultsImportResult to track errors and success count
        """
        # Extract purse amount and skip if $0.00 or less
        purse_str = aggregate.get("purse", "$0.00")
        try:
            # Handle empty string or None values
            if not purse_str or purse_str.strip() == "":
                return  # Skip results with no prize money

            # Remove $ and convert to decimal
            cleaned_purse = purse_str.replace("$", "").replace(",", "").strip()
            if not cleaned_purse:
                return  # Skip if empty after cleaning

            purse_amount = Decimal(cleaned_purse)
            if purse_amount <= 0:
                return  # Skip results with no prize money
        except (ValueError, TypeError, decimal.InvalidOperation):
            logger.warning(
                "Failed to parse purse amount",
                tournament_id=tournament.id,
                purse_str=purse_str,
                player_name=aggregate.get("name", "Unknown"),
            )
            return  # Skip if purse can't be parsed

        # Get member card ID to find player
        member_cards = aggregate.get("member_cards", [])
        if not member_cards:
            result.add_error(
                f"No member cards found for aggregate {aggregate.get('name', 'Unknown')}"
            )
            return

        member_card_id = str(member_cards[0].get("member_card_id", ""))
        if not member_card_id:
            result.add_error(
                f"No member card ID found for {aggregate.get('name', 'Unknown')}"
            )
            return

        # Find player by Golf Genius ID
        try:
            player = Player.objects.get(gg_id=member_card_id)
        except Player.DoesNotExist:
            result.add_error(
                f"Player not found with Golf Genius ID {member_card_id} for {aggregate.get('name', 'Unknown')}"
            )
            return
        except Player.MultipleObjectsReturned:
            result.add_error(
                f"Multiple players found with Golf Genius ID {member_card_id}"
            )
            return

        # Extract result data
        position_str = aggregate.get("position", "")
        try:
            position = int(position_str) if position_str.isdigit() else 0
        except (ValueError, TypeError):
            position = 0

        # Parse score (total strokes)
        total_str = aggregate.get("total", "")
        try:
            score = int(total_str) if total_str.isdigit() else None
        except (ValueError, TypeError):
            score = None

        # Create new tournament result
        TournamentResult.objects.create(
            tournament=tournament,
            player=player,
            flight=flight if flight else "N/A",
            position=position,
            score=score,
            points=None,  # Set to NULL as specified
            amount=purse_amount,
            details=None,  # Set to NULL as specified
        )

        result.results_imported += 1
        logger.debug(
            "Tournament result created",
            tournament_id=tournament.id,
            player_id=player.id,
            position=position,
            amount=purse_amount,
        )

    def _process_points_player_result(
        self,
        tournament: Tournament,
        aggregate: Dict[str, Any],
        flight: str,
        result: ResultsImportResult,
    ):
        """
        Process a single player points result and create/update TournamentResult record

        Args:
            tournament: The Tournament instance
            aggregate: Player result data from Golf Genius
            flight: Flight name from scope
            result: ResultsImportResult to track errors and success count
        """
        # Get member card ID to find player
        member_cards = aggregate.get("member_cards", [])
        if not member_cards:
            result.add_error(
                f"No member cards found for aggregate {aggregate.get('name', 'Unknown')}"
            )
            return

        member_card_id = str(member_cards[0].get("member_card_id", ""))
        if not member_card_id:
            result.add_error(
                f"No member card ID found for {aggregate.get('name', 'Unknown')}"
            )
            return

        # Find player by Golf Genius ID
        try:
            player = Player.objects.get(gg_id=member_card_id)
        except Player.DoesNotExist:
            result.add_error(
                f"Player not found with Golf Genius ID {member_card_id} for {aggregate.get('name', 'Unknown')}"
            )
            return
        except Player.MultipleObjectsReturned:
            result.add_error(
                f"Multiple players found with Golf Genius ID {member_card_id}"
            )
            return

        # Extract position from rank attribute
        rank_str = aggregate.get("rank", "")
        try:
            position = int(rank_str) if rank_str.isdigit() else 0
        except (ValueError, TypeError):
            position = 0

        # Parse points and convert to whole number with proper rounding
        points_str = aggregate.get("points", "")
        points = None
        details = None

        if points_str == "0.00":
            details = "No points awarded"
            points = Decimal("0")
        else:
            try:
                points_decimal = Decimal(points_str)
                # Round to whole number: up for .5 or greater, down otherwise
                points = points_decimal.quantize(Decimal("1"), rounding="ROUND_HALF_UP")
            except (ValueError, TypeError, decimal.InvalidOperation):
                logger.warning(
                    "Failed to parse points",
                    tournament_id=tournament.id,
                    points_str=points_str,
                    player_name=aggregate.get("name", "Unknown"),
                )
                points = None

        # Convert position to details text if not already set
        if details is None:
            position_text = aggregate.get("position", "")
            details = self._format_position_details(position_text)

        # Parse score (total strokes) if available
        total_str = aggregate.get("total", "")
        try:
            score = int(total_str) if total_str.isdigit() else None
        except (ValueError, TypeError):
            score = None

        # Create new tournament result
        TournamentResult.objects.create(
            tournament=tournament,
            player=player,
            flight=flight if flight else "N/A",
            position=position,
            score=score,
            points=points,
            amount=0,  # Set to 0 for points tournaments
            details=details,
        )

        result.results_imported += 1
        logger.debug(
            "Tournament result created",
            tournament_id=tournament.id,
            player_id=player.id,
            position=position,
            points=points,
            details=details,
        )

    def _format_position_details(self, position_text: str) -> str:
        """
        Format position text into descriptive details for points tournaments
        
        Args:
            position_text: Position string from Golf Genius (e.g., "T1", "4", "21")
            
        Returns:
            Formatted details string (e.g., "Tied for first place points", "21st place points")
        """
        if not position_text:
            return "No points awarded"
            
        if position_text.startswith("T"):
            # Handle tied positions like "T1", "T16", "T21"
            try:
                tie_position = int(position_text[1:])
                ordinal = self._get_ordinal_suffix(tie_position)
                return f"Tied for {tie_position}{ordinal} place points"
            except (ValueError, IndexError):
                return "No points awarded"
        else:
            # Handle regular positions like "4", "16", "21"
            try:
                pos_num = int(position_text)
                ordinal = self._get_ordinal_suffix(pos_num)
                return f"{pos_num}{ordinal} place points"
            except (ValueError, TypeError):
                return "No points awarded"
    
    def _get_ordinal_suffix(self, number: int) -> str:
        """
        Get the correct ordinal suffix for a number
        
        Args:
            number: Integer position number
            
        Returns:
            Ordinal suffix ("st", "nd", "rd", or "th")
        """
        # Handle special cases for 11th, 12th, 13th
        if 10 <= number % 100 <= 20:
            return "th"
        
        # Handle regular cases
        last_digit = number % 10
        if last_digit == 1:
            return "st"
        elif last_digit == 2:
            return "nd"
        elif last_digit == 3:
            return "rd"
        else:
            return "th"
