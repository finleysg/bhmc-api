import structlog
from typing import Dict, List, Any, Optional
from django.core.exceptions import ObjectDoesNotExist

from events.models import Event, Round
from scores.models import EventScore
from register.models import Player
from courses.models import Hole, Course, Tee
from .client import GolfGeniusAPIClient

logger = structlog.get_logger(__name__)


class ScoreImportError(Exception):
    """Custom exception for score import errors"""
    pass


class ScoreImportResult:
    def __init__(self):
        self.success_count = 0
        self.errors = {}  # {player_name: error_message}

    def add_error(self, player_name: str, error: str):
        self.errors[player_name] = error

    def add_success(self):
        self.success_count += 1

    def to_dict(self):
        return {
            "success_count": self.success_count,
            "errors": self.errors
        }


class ScoreImportService:
    def __init__(self, api_client=None):
        self.api_client = api_client or GolfGeniusAPIClient()

    def import_scores(self, event_id: int, round_id: int) -> ScoreImportResult:
        """
        Import scores for an event round from Golf Genius

        Args:
            event_id: Local event ID
            round_id: Local round ID

        Returns:
            ImportResult with success count and errors dict

        Raises:
            ScoreImportError: If event/round sync required or API errors
        """
        result = ScoreImportResult()

        # Validate prerequisites
        event, round_obj = self._validate_prerequisites(event_id, round_id)

        # Get event holes for mapping
        holes = self._get_event_holes(event)

        try:
            # Fetch tee sheet data from Golf Genius
            tee_sheet_data = self._get_tee_sheet_data(event.gg_id, round_obj.gg_id)

            # Process each pairing group
            for pairing_group in tee_sheet_data:
                players = pairing_group.get("pairing_group", {}).get("players", [])
                for player_data in players:
                    try:
                        self._process_player_scores(event, round_obj, player_data, holes)
                        result.add_success()
                    except Exception as e:
                        player_name = player_data.get("name", "Unknown Player")
                        result.add_error(player_name, str(e))
                        logger.warning(
                            "Failed to import scores for player",
                            player_name=player_name,
                            error=str(e),
                            event_id=event_id,
                            round_id=round_id
                        )

            # Debug logging if no scores were processed
            if result.success_count == 0 and len(result.errors) == 0:
                logger.warning(
                    "No scores processed - debugging tee sheet data",
                    event_id=event_id,
                    round_id=round_id,
                    pairing_count=len(tee_sheet_data),
                    sample_data=tee_sheet_data[:1] if tee_sheet_data else None
                )

            logger.info(
                "Score import completed",
                event_id=event_id,
                round_id=round_id,
                success_count=result.success_count,
                error_count=len(result.errors)
            )

        except Exception as e:
            logger.error(
                "Score import failed",
                event_id=event_id,
                round_id=round_id,
                error=str(e)
            )
            raise ScoreImportError(f"Failed to import scores: {str(e)}")

        return result

    def _validate_prerequisites(self, event_id: int, round_id: int):
        """Validate event has gg_id and round exists"""
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            raise ScoreImportError("Event not found")

        if not event.gg_id:
            raise ScoreImportError("You must first run the Event Sync process to sync this event with Golf Genius")

        try:
            round_obj = Round.objects.get(event=event, id=round_id)
        except ObjectDoesNotExist:
            raise ScoreImportError("You must first run the Event Sync process to sync this round with Golf Genius")

        return event, round_obj

    def _get_event_holes(self, event: Event) -> Dict[int, Dict[int, Hole]]:
        """Get holes for the event mapped by course_id -> {hole_number: hole}"""
        holes = {}
        for course in event.courses.all():
            course_holes = {}
            for hole in course.holes.all():
                course_holes[hole.hole_number] = hole
            holes[course.id] = course_holes
        return holes

    def _get_tee_sheet_data(self, event_gg_id: str, round_gg_id: str) -> List[Dict[str, Any]]:
        """Fetch tee sheet data from Golf Genius API"""
        return self.api_client.get_round_tee_sheet(event_gg_id, round_gg_id)

    def _process_player_scores(self, event: Event, round_obj: Round, player_data: Dict[str, Any], holes: Dict[int, Dict[int, Hole]]):
        """Process individual player's gross and net scores"""
        # Find player by external_id
        external_id = player_data.get("external_id")
        if not external_id:
            raise ValueError("Player missing external_id")

        try:
            # Convert external_id to int since Player.id is an integer field
            player_id = int(external_id)
            player = Player.objects.get(id=player_id)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid external_id format: {external_id}")
        except ObjectDoesNotExist:
            raise ValueError(f"Player with external_id {external_id} not found in system")

        # Find course and tee for this player
        course = self._find_player_course(player_data)
        tee = self._find_player_tee(player_data, course)

        # Delete existing scores for this player/event to ensure idempotency
        self._delete_existing_scores(event, player, holes)

        # Process gross scores
        gross_scores = player_data.get("score_array", [])
        logger.debug(
            "Processing player scores",
            player_name=player_data.get("name", "Unknown"),
            external_id=external_id,
            course_name=course.name if course else None,
            tee_name=tee.name if tee else None,
            gross_scores_count=len(gross_scores) if gross_scores else 0,
            has_gross_scores=bool(gross_scores)
        )

        if gross_scores:
            self._import_scores_for_holes(event, player, course, tee, gross_scores, False, holes)

        # Process net scores
        handicap_dots = player_data.get("handicap_dots_by_hole", [])
        if handicap_dots and gross_scores:
            net_scores = self._calculate_net_scores(gross_scores, handicap_dots)
            self._import_scores_for_holes(event, player, course, tee, net_scores, True, holes)

    def _delete_existing_scores(self, event: Event, player: Player, holes: Dict[int, Dict[int, Hole]]):
        """Delete existing scores for the player in this event"""
        hole_ids = []
        for course_holes in holes.values():
            hole_ids.extend([hole.id for hole in course_holes.values()])
        EventScore.objects.filter(
            event=event,
            player=player,
            hole_id__in=hole_ids
        ).delete()

    def _calculate_net_scores(self, gross_scores: List[int], handicap_dots: List[int]) -> List[int]:
        """Calculate net scores using handicap dots"""
        net_scores = []
        for gross, dots in zip(gross_scores, handicap_dots):
            if gross is not None and dots is not None:
                net_scores.append(gross - dots)
            else:
                net_scores.append(None)
        return net_scores

    def _find_player_course(self, player_data: Dict[str, Any]) -> Optional[Course]:
        """Find the course for a player using Golf Genius course_id"""
        tee_data = player_data.get("tee", {})
        course_id = tee_data.get("course_id")
        if course_id:
            try:
                return Course.objects.get(gg_id=course_id)
            except ObjectDoesNotExist:
                logger.warning(
                    "Course not found for gg_id",
                    gg_id=course_id,
                    player_name=player_data.get("name", "Unknown")
                )
        return None

    def _find_player_tee(self, player_data: Dict[str, Any], course: Optional[Course]) -> Optional[Tee]:
        """Find the tee for a player using Golf Genius tee_id"""
        tee_data = player_data.get("tee", {})
        tee_id = tee_data.get("id")
        if tee_id:
            try:
                # First try to find tee by gg_id only
                tee = Tee.objects.get(gg_id=tee_id)
                # If course is provided, verify it matches (optional validation)
                if course and tee.course != course:
                    logger.warning(
                        "Tee course mismatch",
                        tee_gg_id=tee_id,
                        tee_course=tee.course.name,
                        player_course=course.name if course else None,
                        player_name=player_data.get("name", "Unknown")
                    )
                return tee
            except ObjectDoesNotExist:
                logger.warning(
                    "Tee not found for gg_id",
                    gg_id=tee_id,
                    player_name=player_data.get("name", "Unknown")
                )
        return None

    def _import_scores_for_holes(self, event: Event, player: Player, course: Optional[Course], tee: Optional[Tee], scores: List[Optional[int]], is_net: bool, holes: Dict[int, Dict[int, Hole]]):
        """Import scores for all holes"""
        score_objects = []

        # Get holes for this player's course
        course_holes = {}
        if course and course.id in holes:
            course_holes = holes[course.id]

        for hole_number, score in enumerate(scores, 1):
            if score is not None and hole_number in course_holes:
                hole = course_holes[hole_number]
                score_objects.append(EventScore(
                    event=event,
                    player=player,
                    course=course,
                    tee=tee,
                    hole=hole,
                    score=score,
                    is_net=is_net
                ))

        # Bulk create scores
        if score_objects:
            EventScore.objects.bulk_create(score_objects)
