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


class GolfGeniusResultsParser:
    """
    Base parser for Golf Genius tournament results API responses.

    Handles common structure extraction (event -> scopes -> aggregates -> member_cards).
    Provides validation and safe access to nested response data.
    """

    @staticmethod
    def validate_response(gg_results: Dict[str, Any]) -> Optional[str]:
        """
        Validate Golf Genius results response structure.

        Args:
            gg_results: Raw API response

        Returns:
            Error message if invalid, None if valid
        """
        if not gg_results or "event" not in gg_results:
            return "Invalid or empty results data from Golf Genius"

        event_data = gg_results.get("event", {})
        if "scopes" not in event_data:
            return "No scopes found in results data"

        return None

    @staticmethod
    def extract_scopes(gg_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract scopes (flights) from Golf Genius results.

        Args:
            gg_results: Raw API response

        Returns:
            List of scope dictionaries
        """
        return gg_results.get("event", {}).get("scopes", [])

    @staticmethod
    def extract_aggregates(scope: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract aggregates (player results) from a scope.

        Args:
            scope: Scope dictionary from API response

        Returns:
            List of aggregate dictionaries
        """
        return scope.get("aggregates", [])

    @staticmethod
    def extract_member_cards(aggregate: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract member cards from an aggregate.

        Args:
            aggregate: Aggregate dictionary from API response

        Returns:
            List of member card dictionaries
        """
        return aggregate.get("member_cards", [])

    @staticmethod
    def extract_flight_name(scope: Dict[str, Any], default: str = "N/A") -> str:
        """
        Extract flight name from scope with fallback.

        Args:
            scope: Scope dictionary from API response
            default: Default value if name is missing or empty

        Returns:
            Flight name or default
        """
        name = scope.get("name")
        return name if name else default


class StrokePlayResultParser(GolfGeniusResultsParser):
    """Parser for stroke play tournament results"""

    @staticmethod
    def parse_player_data(
        aggregate: Dict[str, Any], member_card: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract stroke play specific data from aggregate and member card.

        Args:
            aggregate: Player aggregate from API
            member_card: First member card from aggregate

        Returns:
            Dictionary with parsed stroke play data
        """
        return {
            "purse": aggregate.get("purse", "$0.00"),
            "position_str": aggregate.get("position", ""),
            "total_str": aggregate.get("total", ""),
            "member_card_id": str(member_card.get("member_card_id", "")),
            "player_name": aggregate.get("name", "Unknown"),
        }


class PointsResultParser(GolfGeniusResultsParser):
    """Parser for points tournament results"""

    @staticmethod
    def parse_player_data(
        aggregate: Dict[str, Any], member_card: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract points specific data from aggregate and member card.

        Args:
            aggregate: Player aggregate from API
            member_card: First member card from aggregate

        Returns:
            Dictionary with parsed points data
        """
        return {
            "rank_str": aggregate.get("rank", ""),
            "points_str": aggregate.get("points", ""),
            "position_text": aggregate.get("position", ""),
            "total_str": aggregate.get("total", ""),
            "member_card_id": str(member_card.get("member_card_id", "")),
            "player_name": aggregate.get("name", "Unknown"),
        }


class SkinsResultParser(GolfGeniusResultsParser):
    """Parser for skins tournament results"""

    @staticmethod
    def parse_player_data(
        aggregate: Dict[str, Any], member_card: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract skins specific data from aggregate and member card.

        Args:
            aggregate: Player aggregate from API
            member_card: First member card from aggregate

        Returns:
            Dictionary with parsed skins data
        """
        return {
            "purse": aggregate.get("purse", "$0.00"),
            "total_str": aggregate.get("total", ""),
            "details": aggregate.get("details"),
            "member_card_id": str(member_card.get("member_card_id", "")),
            "player_name": aggregate.get("name", "Unknown"),
        }


class UserScoredResultParser(GolfGeniusResultsParser):
    """Parser for user-scored tournament results"""

    @staticmethod
    def parse_player_data(
        aggregate: Dict[str, Any], member_card: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract user-scored specific data from aggregate and member card.

        Args:
            aggregate: Player aggregate from API
            member_card: First member card from aggregate

        Returns:
            Dictionary with parsed user-scored data
        """
        return {
            "purse": aggregate.get("purse", "$0.00"),
            "rank_str": aggregate.get("rank", ""),
            "member_card_id": str(member_card.get("member_card_id", "")),
            "player_name": aggregate.get("name", "Unknown"),
        }


class ResultsImportService:
    """
    Service for importing tournament results from Golf Genius
    """

    def __init__(self, api_client: Optional[GolfGeniusAPIClient] = None):
        self.api_client = api_client or GolfGeniusAPIClient()

    # ========== Helper Methods (High Priority Refactoring) ==========

    def _validate_tournament_for_import(
        self, tournament: Tournament, result: ResultsImportResult
    ) -> bool:
        """
        Validate tournament has required Golf Genius IDs.

        Args:
            tournament: The tournament to validate
            result: ResultsImportResult to add errors to

        Returns:
            True if valid, False if validation failed (errors added to result)
        """
        if not tournament.event.gg_id:
            result.add_error(
                "Event must first be synced with Golf Genius. Run Event Sync process."
            )
            return False

        if not tournament.round or not tournament.round.gg_id:
            result.add_error(
                "Round must first be synced with Golf Genius. Run Event Sync process."
            )
            return False

        if not tournament.gg_id:
            result.add_error(
                "Tournament must first be synced with Golf Genius. Run Event Sync process."
            )
            return False

        return True

    def _parse_purse_amount(
        self, purse_str: str, context: Dict[str, Any]
    ) -> Optional[Decimal]:
        """
        Parse purse string to Decimal amount.

        Args:
            purse_str: Purse string from Golf Genius (e.g., "$100.00")
            context: Context dict for logging (tournament_id, player_name, etc.)

        Returns:
            Decimal amount if valid and > 0, None otherwise
        """
        if not purse_str or purse_str.strip() == "":
            return None

        try:
            cleaned = purse_str.replace("$", "").replace(",", "").strip()
            if not cleaned:
                return None

            amount = Decimal(cleaned)
            return amount if amount > Decimal("0.00") else None

        except (ValueError, TypeError, decimal.InvalidOperation):
            logger.warning(
                "Failed to parse purse amount", purse_str=purse_str, **context
            )
            return None

    def _resolve_player_from_member_cards(
        self,
        member_card: Dict[str, Any],
        result: ResultsImportResult,
    ) -> Optional[Player]:
        """
        Resolve player from Golf Genius member card ID.

        Args:
            member_cards: List of member cards from aggregate
            result: ResultsImportResult to add errors to

        Returns:
            Player instance if found, None otherwise (errors added to result)
        """
        member_card_id = str(member_card.get("member_card_id", ""))
        try:
            return Player.objects.get(gg_id=member_card_id)
        except Player.DoesNotExist:
            result.add_error(
                f"Player not found with Golf Genius ID {member_card_id}"
            )
            return None
        except Player.MultipleObjectsReturned:
            result.add_error(
                f"Multiple players found with Golf Genius ID {member_card_id}"
            )
            return None

    def _delete_existing_results(self, tournament: Tournament) -> int:
        """
        Delete existing results for a tournament (idempotent operation).

        Args:
            tournament: The tournament to delete results for

        Returns:
            Number of deleted results
        """
        with transaction.atomic():
            deleted_count = TournamentResult.objects.filter(
                tournament=tournament
            ).delete()[0]
            logger.info(
                "Deleted existing tournament results",
                tournament_id=tournament.id,
                deleted_count=deleted_count,
            )
            return deleted_count

    def _fetch_gg_results(
        self, tournament: Tournament, result: ResultsImportResult
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch tournament results from Golf Genius API.

        Args:
            tournament: The tournament to fetch results for
            result: ResultsImportResult to add errors to

        Returns:
            Results dict from API if successful, None otherwise (errors added to result)
        """
        try:
            return self.api_client.get_tournament_results(
                event_id=tournament.event.gg_id,
                round_id=tournament.round.gg_id,
                tournament_id=tournament.gg_id,
            )
        except Exception as e:
            result.add_error(f"Failed to fetch results from Golf Genius API: {str(e)}")
            return None

    def _map_member_id_to_name(
        self, individual_results: List[Dict[str, Any]]
    ) -> Dict[int, str]:
        """
        Build a mapping of member_id -> name from an individual_results collection.

        Args:
            individual_results: List of individual result dicts from an aggregate

        Returns:
            Dict where the key is member_id (int) and the value is the member's name (str).
        """
        mapping: Dict[int, str] = {}
        if not individual_results:
            return mapping

        for item in individual_results:
            member_id = item.get("member_id")
            name = item.get("name") or ""
            try:
                mapping[int(member_id)] = name
            except (ValueError, TypeError):
                # If member_id cannot be coerced to int, skip it
                continue

        return mapping

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

    def import_skins(self, event_id: int) -> List[ResultsImportResult]:
        """
        Import skins tournament results from Golf Genius for tournaments with format == 'skins' in a specific event

        Args:
            event_id: The database ID of the event to import results for

        Returns:
            List of ResultsImportResult objects containing success/error information
        """
        results: List[ResultsImportResult] = []

        # Get all skins tournaments for the specified event
        tournaments = Tournament.objects.filter(
            event_id=event_id, format="skins"
        ).select_related("event", "round")

        if not tournaments.exists():
            logger.warning("No skins tournaments found for event", event_id=event_id)
            return results

        for tournament in tournaments:
            result = self._import_skins_tournament_results(tournament)
            results.append(result)

        return results

    def import_user_scored_results(self, event_id: int) -> List[ResultsImportResult]:
        """
        Import user-scored (proxy/similar) tournament results from Golf Genius for tournaments with format == 'user_scored' in a specific event

        Args:
            event_id: The database ID of the event to import results for

        Returns:
            List of ResultsImportResult objects containing success/error information
        """
        results: List[ResultsImportResult] = []

        # Get all user_scored tournaments for the specified event
        tournaments = Tournament.objects.filter(
            event_id=event_id, format="user_scored"
        ).select_related("event", "round")

        if not tournaments.exists():
            logger.warning(
                "No user_scored tournaments found for event", event_id=event_id
            )
            return results

        for tournament in tournaments:
            result = self._import_user_scored_tournament_results(tournament)
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
            # Validate tournament has Golf Genius IDs
            if not self._validate_tournament_for_import(tournament, result):
                return result

            # Delete existing results for this tournament (idempotent operation)
            self._delete_existing_results(tournament)

            # Get tournament results from Golf Genius API
            gg_results = self._fetch_gg_results(tournament, result)
            if not gg_results:
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

    def _process_user_scored_tournament_results(
        self,
        tournament: Tournament,
        gg_results: Dict[str, Any],
        result: ResultsImportResult,
    ):
        """
        Process the Golf Genius user_scored results data and create TournamentResult records

        Args:
            tournament: The Tournament instance
            gg_results: Raw results data from Golf Genius API
            result: ResultsImportResult to track errors and success count
        """
        # Validate response structure using parser
        error = UserScoredResultParser.validate_response(gg_results)
        if error:
            result.add_error(error)
            return

        # Extract scopes (flights) using parser
        scopes = UserScoredResultParser.extract_scopes(gg_results)

        # Process each scope (flight)
        for scope in scopes:
            flight_name = UserScoredResultParser.extract_flight_name(scope)
            aggregates = UserScoredResultParser.extract_aggregates(scope)

            # Process each aggregate (player result)
            for aggregate in aggregates:
                try:
                    self._process_user_scored_player_result(
                        tournament, aggregate, flight_name, result
                    )
                except Exception as e:
                    result.add_error(
                        f"Error processing user_scored player result: {str(e)}"
                    )
                    logger.exception(
                        "Error processing user_scored player result",
                        tournament_id=tournament.id,
                    )

    def _process_user_scored_player_result(
        self,
        tournament: Tournament,
        aggregate: Dict[str, Any],
        flight: str,
        result: ResultsImportResult,
    ):
        """
        Process a single player user_scored result and create TournamentResult record

        Mapping rules:
        - position comes from `rank` attribute
        - amount comes from `purse` attribute (save only if > $0.00)
        - flight defaults to "N/A"
        - points, details, and score set to NULL

        Args:
            tournament: The Tournament instance
            aggregate: Player result data from Golf Genius
            flight: Flight name from scope
            result: ResultsImportResult to track errors and success count
        """
        # Extract member cards and get first member card
        member_cards = UserScoredResultParser.extract_member_cards(aggregate)
        if not member_cards:
            result.add_error(
                f"No member cards found for aggregate {aggregate.get('name', 'Unknown')}"
            )
            return

        # Parse player data using parser
        player_data = UserScoredResultParser.parse_player_data(
            aggregate, member_cards[0]
        )

        # Extract purse amount using helper - skip if $0.00 or less
        purse_amount = self._parse_purse_amount(
            player_data["purse"],
            {
                "tournament_id": tournament.id,
                "player_name": player_data["player_name"],
            },
        )
        if not purse_amount:
            return

        # Resolve player using helper
        player = self._resolve_player_from_member_cards(member_cards[0], result)
        if not player:
            return

        # Extract position from rank attribute
        rank_str = player_data["rank_str"]
        try:
            position = int(rank_str) if rank_str.isdigit() else 0
        except (ValueError, TypeError):
            position = 0

        # Create new tournament result (points, details, score NULL)
        TournamentResult.objects.create(
            tournament=tournament,
            player=player,
            flight=flight if flight else "N/A",
            position=position,
            score=None,
            points=None,
            amount=purse_amount,
            details=None,
        )

        result.results_imported += 1
        logger.debug(
            "User-scored tournament result created",
            tournament_id=tournament.id,
            player_id=player.id,
            position=position,
            amount=purse_amount,
        )

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
            # Validate tournament has Golf Genius IDs
            if not self._validate_tournament_for_import(tournament, result):
                return result

            # Delete existing results for this tournament (idempotent operation)
            self._delete_existing_results(tournament)

            # Get tournament results from Golf Genius API
            gg_results = self._fetch_gg_results(tournament, result)
            if not gg_results:
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

    def _import_skins_tournament_results(
        self, tournament: Tournament
    ) -> ResultsImportResult:
        """
        Import skins results for a single tournament

        Args:
            tournament: The Tournament instance to import results for

        Returns:
            ResultsImportResult with import status and any errors
        """
        result = ResultsImportResult(tournament)

        try:
            # Validate tournament has Golf Genius IDs
            if not self._validate_tournament_for_import(tournament, result):
                return result

            # Delete existing results for this tournament (idempotent operation)
            self._delete_existing_results(tournament)

            # Get tournament results from Golf Genius API
            gg_results = self._fetch_gg_results(tournament, result)
            if not gg_results:
                return result

            # Process the skins results data
            self._process_skins_tournament_results(tournament, gg_results, result)

        except Exception as e:
            result.add_error(f"Unexpected error importing skins results: {str(e)}")
            logger.exception(
                "Unexpected error in tournament skins results import",
                tournament_id=tournament.id,
            )

        return result

    def _import_user_scored_tournament_results(
        self, tournament: Tournament
    ) -> ResultsImportResult:
        """
        Import user_scored results for a single tournament

        Args:
            tournament: The Tournament instance to import results for

        Returns:
            ResultsImportResult with import status and any errors
        """
        result = ResultsImportResult(tournament)

        try:
            # Validate tournament has Golf Genius IDs
            if not self._validate_tournament_for_import(tournament, result):
                return result

            # Delete existing results for this tournament (idempotent operation)
            self._delete_existing_results(tournament)

            # Get tournament results from Golf Genius API
            gg_results = self._fetch_gg_results(tournament, result)
            if not gg_results:
                return result

            # Process the user_scored results data
            self._process_user_scored_tournament_results(tournament, gg_results, result)

        except Exception as e:
            result.add_error(
                f"Unexpected error importing user_scored results: {str(e)}"
            )
            logger.exception(
                "Unexpected error in tournament user_scored results import",
                tournament_id=tournament.id,
            )

        return result

    def _process_skins_tournament_results(
        self,
        tournament: Tournament,
        gg_results: Dict[str, Any],
        result: ResultsImportResult,
    ):
        """
        Process the Golf Genius skins results data and create TournamentResult records

        Args:
            tournament: The Tournament instance
            gg_results: Raw results data from Golf Genius API
            result: ResultsImportResult to track errors and success count
        """
        # Validate response structure using parser
        error = SkinsResultParser.validate_response(gg_results)
        if error:
            result.add_error(error)
            return

        # Extract scopes (flights) using parser
        scopes = SkinsResultParser.extract_scopes(gg_results)

        # Process each scope (flight)
        for scope in scopes:
            flight_name = SkinsResultParser.extract_flight_name(scope)
            aggregates = SkinsResultParser.extract_aggregates(scope)

            # Process each aggregate (player result)
            for aggregate in aggregates:
                try:
                    self._process_skins_player_result(
                        tournament, aggregate, flight_name, result
                    )
                except Exception as e:
                    result.add_error(f"Error processing skins player result: {str(e)}")
                    logger.exception(
                        "Error processing skins player result",
                        tournament_id=tournament.id,
                    )

    def _process_skins_player_result(
        self,
        tournament: Tournament,
        aggregate: Dict[str, Any],
        flight: str,
        result: ResultsImportResult,
    ):
        """
        Process a single player skins result and create TournamentResult record

        Mapping rules:
        - position comes from `total` attribute (number of skins won)
        - amount comes from `purse` attribute (save only if > $0.00)
        - details copied from `details` attribute
        - points and score set to NULL

        Args:
            tournament: The Tournament instance
            aggregate: Player result data from Golf Genius
            flight: Flight name from scope
            result: ResultsImportResult to track errors and success count
        """
        # Extract member cards and get first member card
        member_cards = SkinsResultParser.extract_member_cards(aggregate)
        if not member_cards:
            result.add_error(
                f"No member cards found for aggregate {aggregate.get('name', 'Unknown')}"
            )
            return

        # Parse player data using parser
        player_data = SkinsResultParser.parse_player_data(aggregate, member_cards[0])

        # Extract purse amount using helper - skip if $0.00 or less
        purse_amount = self._parse_purse_amount(
            player_data["purse"],
            {
                "tournament_id": tournament.id,
                "player_name": player_data["player_name"],
            },
        )
        if not purse_amount:
            return

        # Resolve player using helper
        player = self._resolve_player_from_member_cards(member_cards[0], result)
        if not player:
            return

        # Extract position from total attribute (number of skins won)
        total_str = player_data["total_str"]
        try:
            position = int(total_str) if total_str.isdigit() else 0
        except (ValueError, TypeError):
            position = 0

        # Details copied from details attribute
        details = player_data["details"]

        # Create new tournament result (points and score NULL)
        TournamentResult.objects.create(
            tournament=tournament,
            player=player,
            flight=flight if flight else "N/A",
            position=position,
            score=None,
            points=None,
            amount=purse_amount,
            details=details,
        )

        result.results_imported += 1
        logger.debug(
            "Skins tournament result created",
            tournament_id=tournament.id,
            player_id=player.id,
            position=position,
            amount=purse_amount,
        )

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
        # Validate response structure using parser
        error = StrokePlayResultParser.validate_response(gg_results)
        if error:
            result.add_error(error)
            return

        # Extract scopes (flights) using parser
        scopes = StrokePlayResultParser.extract_scopes(gg_results)

        # Process each scope (flight)
        for scope in scopes:
            flight_name = StrokePlayResultParser.extract_flight_name(scope, default="")
            aggregates = StrokePlayResultParser.extract_aggregates(scope)

            # Identify if this is a team event
            is_team_event = len(StrokePlayResultParser.extract_member_cards(aggregates[0])) > 1

            # Process each aggregate (player result)
            for aggregate in aggregates:
                try:
                    if is_team_event:
                        self._process_team_result(
                            tournament, aggregate, flight_name, result
                        )
                    else:
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
        # Validate response structure using parser
        error = PointsResultParser.validate_response(gg_results)
        if error:
            result.add_error(error)
            return

        # Extract scopes (flights) using parser
        scopes = PointsResultParser.extract_scopes(gg_results)

        # Process each scope (flight)
        for scope in scopes:
            flight_name = PointsResultParser.extract_flight_name(scope)
            aggregates = PointsResultParser.extract_aggregates(scope)

            # Process each aggregate (player result)
            for aggregate in aggregates:
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
        # Extract member cards and get first member card
        member_cards = StrokePlayResultParser.extract_member_cards(aggregate)
        if not member_cards:
            result.add_error(
                f"No member cards found for aggregate {aggregate.get('name', 'Unknown')}"
            )
            return

        # Parse player data using parser
        player_data = StrokePlayResultParser.parse_player_data(
            aggregate, member_cards[0]
        )

        # Extract purse amount using helper - skip if $0.00 or less
        purse_amount = self._parse_purse_amount(
            player_data["purse"],
            {
                "tournament_id": tournament.id,
                "player_name": player_data["player_name"],
            },
        )
        if not purse_amount:
            return

        # Resolve player using helper
        player = self._resolve_player_from_member_cards(member_cards[0], result)
        if not player:
            return

        # Extract result data
        position_str = player_data["position_str"]
        try:
            position = int(position_str) if position_str.isdigit() else 0
        except (ValueError, TypeError):
            position = 0

        # Parse score (total strokes)
        total_str = player_data["total_str"]
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
            points=None,
            amount=purse_amount,
            details=None,
        )

        result.results_imported += 1
        logger.debug(
            "Tournament result created",
            tournament_id=tournament.id,
            player_id=player.id,
            position=position,
            amount=purse_amount,
        )

    def _process_team_result(
        self,
        tournament: Tournament,
        aggregate: Dict[str, Any],
        flight: str,
        result: ResultsImportResult,
    ):
        """
        Process team results and create/update TournamentResult records for each team member

        Args:
            tournament: The Tournament instance
            aggregate: Player result data from Golf Genius
            flight: Flight name from scope
            result: ResultsImportResult to track errors and success count
        """
        team = aggregate.get("name")

        # Extract purse amount using helper - skip if $0.00 or less
        purse_amount = self._parse_purse_amount(
            aggregate.get("purse", "$0.00"),
            {
                "tournament_id": tournament.id,
                "team_name": team,
            },
        )
        if not purse_amount:
            return

        team_id = aggregate.get("id_str")
        position = int(aggregate.get("rank"))
        score = int(aggregate.get("total"))

        member_cards = StrokePlayResultParser.extract_member_cards(aggregate)
        member_map = self._map_member_id_to_name(aggregate.get("individual_results", []))

        for member_card in member_cards:
            # Don't include blinds
            member_id = int(member_card.get("member_id"))
            member_name = member_map.get(member_id)
            if member_name.startswith("Bl[") and member_name.endswith("]"):
                continue

            player = self._resolve_player_from_member_cards(member_card, result)

            # Create new tournament result
            TournamentResult.objects.create(
                tournament=tournament,
                player=player,
                flight=flight if flight else "N/A",
                team_id=team_id,
                position=position,
                score=score,
                points=None,
                amount=purse_amount,
                details=team,
            )

            result.results_imported += 1

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
        # Extract member cards and get first member card
        member_cards = PointsResultParser.extract_member_cards(aggregate)
        if not member_cards:
            result.add_error(
                f"No member cards found for aggregate {aggregate.get('name', 'Unknown')}"
            )
            return

        # Parse player data using parser
        player_data = PointsResultParser.parse_player_data(aggregate, member_cards[0])

        # Resolve player using helper
        player = self._resolve_player_from_member_cards(member_cards[0], result)
        if not player:
            return

        # Extract position from rank attribute
        rank_str = player_data["rank_str"]
        try:
            position = int(rank_str) if rank_str.isdigit() else 0
        except (ValueError, TypeError):
            position = 0

        # Parse points and convert to whole number with proper rounding
        points_str = player_data["points_str"]
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
                    player_name=player_data["player_name"],
                )
                points = None

        # Convert position to details text if not already set
        if details is None:
            position_text = player_data["position_text"]
            details = self._format_position_details(position_text)

        # Parse score (total strokes) if available
        total_str = player_data["total_str"]
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
