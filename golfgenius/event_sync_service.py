import os
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.conf import settings
from courses.models import Course
from events.models import Event, Round
from .client import GolfGeniusAPIClient

logger = structlog.get_logger(__name__)


class EventSyncResult:
    """Container for event sync operation results"""

    def __init__(self, event: Event):
        self.event_id = event.id
        self.event_name = event.name
        self.start_date = event.start_date
        self.errors = []

    def add_error(self, error: str):
        """Add an error for a specific event"""
        self.errors.append(error)
        logger.error("Event sync error", event_id=self.event_id, error=error)

    def to_dict(self) -> Dict:
        """Convert results to dictionary for API response"""
        return {
            "event": self.event_name + f" ({self.start_date})",
            "errors": self.errors,
        }


class EventSyncService:
    """
    Service for synchronizing BHMC events with Golf Genius events
    """

    def __init__(self, api_client: Optional[GolfGeniusAPIClient] = None):
        self.api_client = api_client or GolfGeniusAPIClient()
        self.api_delay = 0.05  # Delay between API calls to prevent rate limiting

    def sync_event(self, event_id: int) -> EventSyncResult:
        """
        Sync a single BHMC event with Golf Genius events based on date matching

        Args:
            event_id: The database ID of the BHMC event to sync

        Returns:
            EventSyncResult containing sync results for the single event
        """
        try:
            logger.info("Starting single event sync operation", event_id=event_id)

            # Get the specific BHMC event
            try:
                from events.models import Event

                bhmc_event = Event.objects.get(id=event_id)
                result = EventSyncResult(bhmc_event)
            except Event.DoesNotExist:
                # Create a dummy result for error reporting
                dummy_event = Event(
                    id=event_id,
                    name=f"Event {event_id}",
                    start_date=datetime.now().date(),
                )
                result = EventSyncResult(dummy_event)
                error_msg = f"BHMC event with ID {event_id} not found"
                result.add_error(error_msg)
                return result

            # Get Golf Genius events for the season
            gg_events = self._get_golf_genius_events(bhmc_event.season)
            result.total_gg_events = len(gg_events)

            if not gg_events:
                result.add_error(
                    "No Golf Genius events found for season " + str(bhmc_event.season)
                )
                return result

            # Try to match this single event with Golf Genius events
            event_matched = self._update_event_ggid(bhmc_event, gg_events)
            if not event_matched:
                result.add_error("No matching Golf Genius event found")
                return result

            # Sync courses, tees, and holes for the event
            self._sync_event_courses(bhmc_event, result)

            # Sync rounds and tournaments for the event
            self._sync_event_rounds_and_tournaments(bhmc_event, result)

            logger.info("Single event sync operation completed", event_id=event_id)
            return result

        except Exception as e:
            error_msg = f"Single event sync failed: {str(e)}"
            result.add_error(error_msg)
            return result

    def _get_golf_genius_events(self, season: int) -> List[Dict]:
        """
        Get Golf Genius events for the season, filtered by Men's Club category

        Args:
            season: Target season

        Returns:
            List of Golf Genius event dictionaries
        """
        try:
            # Get seasons to find the target season
            seasons = self.api_client.get_seasons()
            target_season_id = None

            for season_data in seasons:
                season_info = season_data.get("season", {})
                # Try to match by name (assuming season name contains the year)
                if str(season) in season_info.get("name", ""):
                    target_season_id = season_info.get("id")
                    break

            if not target_season_id:
                logger.warning(
                    "Could not find target season in Golf Genius", season=season
                )
                return []

            logger.info(
                "Found target season in Golf Genius",
                season=season,
                gg_season_id=target_season_id,
            )

            # Get events for the season and category
            events = self.api_client.get_events(
                season_id=target_season_id,
                category_id=settings.GOLF_GENIUS_CATEGORY_ID,
            )

            # Extract event data from the response format
            gg_events = []
            for event_data in events:
                event_info = event_data.get("event", {})
                if event_info:
                    gg_events.append(event_info)

            logger.info(
                "Retrieved Golf Genius events", season=season, count=len(gg_events)
            )

            return gg_events

        except Exception as e:
            logger.error(
                "Failed to get Golf Genius events", season=season, error=str(e)
            )
            return []

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
        gg_start_date = gg_event.get("start_date")
        if not gg_start_date:
            return False

        try:
            # Parse the GG date string (format: YYYY-MM-DD)
            gg_start = datetime.strptime(gg_start_date, "%Y-%m-%d").date()
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
        gg_start_date = gg_event.get("start_date")
        gg_end_date = gg_event.get("end_date")

        if not gg_start_date:
            return False

        try:
            # Parse GG dates
            gg_start = datetime.strptime(gg_start_date, "%Y-%m-%d").date()
            gg_end = gg_start  # Default to start date

            if gg_end_date:
                gg_end = datetime.strptime(gg_end_date, "%Y-%m-%d").date()

            # Calculate BHMC event end date
            bhmc_start = bhmc_event.start_date
            bhmc_end = self._calculate_end_date(bhmc_event)

            # Check for overlap: events overlap if one starts before the other ends
            return bhmc_start <= gg_end and gg_start <= bhmc_end

        except (ValueError, TypeError):
            return False

    def _update_event_ggid(self, bhmc_event: Event, gg_events: List[Dict]):
        """
        Match BHMC events with Golf Genius events and update database

        Args:
           bhmc_event: The BHMC Event object to update
           gg_events: List of Golf Genius event dictionaries

        Returns:
           True if a match was found and gg_id updated, False otherwise
        """
        for gg_event in gg_events:
            gg_id = str(gg_event.get("id", ""))

            if self._events_exact_match(bhmc_event, gg_event):
                bhmc_event.gg_id = gg_id
                bhmc_event.save(update_fields=["gg_id"])
                return True
            elif self._events_overlap(bhmc_event, gg_event):
                bhmc_event.gg_id = gg_id
                bhmc_event.save(update_fields=["gg_id"])
                return True

        return False

    def _sync_event_courses(self, bhmc_event: Event, result: EventSyncResult):
        """
        Sync courses, tees, and holes for a BHMC event from Golf Genius

        Args:
            bhmc_event: BHMC Event object with gg_id set
            result: EventSyncResult for error reporting
        """
        try:
            # Get courses from Golf Genius
            gg_courses = self.api_client.get_event_courses(bhmc_event.gg_id)

            if not gg_courses:
                logger.info(
                    "No courses found for event",
                    event_id=bhmc_event.id,
                    gg_event_id=bhmc_event.gg_id,
                )
                return

            # Process each course
            for gg_course in gg_courses:
                try:
                    self._sync_course(gg_course, result)
                except Exception as e:
                    course_name = gg_course.get("name", "Unknown")
                    error_msg = f"Failed to sync course '{course_name}': {str(e)}"
                    result.add_error(error_msg)

            logger.info("Course sync completed", event_id=bhmc_event.id)

        except Exception as e:
            error_msg = f"Course sync failed: {str(e)}"
            result.add_error(error_msg)

    def _sync_course(self, gg_course: Dict, result: EventSyncResult):
        """
        Sync a single course from Golf Genius

        Args:
            bhmc_event: BHMC Event object
            gg_course: Golf Genius course dictionary
            result: EventSyncResult for error reporting
        """

        gg_course_id = str(gg_course.get("id", ""))
        course_name = gg_course.get("name", "").strip()

        if not course_name:
            result.add_error("Course sync failed: missing course name")
            return

        # Find or create course
        course = self._find_or_create_course(course_name, gg_course_id, result)
        if not course:
            return

        # Ensure our course record has the gg_id populated
        if not course.gg_id and gg_course_id:
            course.gg_id = gg_course_id
            course.save(update_fields=["gg_id"])
            logger.info(
                "Updated course with gg_id", course_name=course.name, gg_id=gg_course_id
            )

        # Sync tees for this course
        self._sync_course_tees(course, gg_course, result)

        # Sync holes for this course
        self._sync_course_holes(course, gg_course, result)

    def _find_or_create_course(
        self, course_name: str, gg_course_id: str, result: EventSyncResult
    ) -> Optional[Course]:
        """
        Find existing course or create new one

        Args:
            course_name: Name of the course
            gg_course_id: Golf Genius course ID
            result: EventSyncResult for error reporting

        Returns:
            Course object or None if failed
        """
        from courses.models import Course

        try:
            # First try to find by gg_id
            if gg_course_id:
                try:
                    course = Course.objects.get(gg_id=gg_course_id)
                    logger.info(
                        "Found course by gg_id",
                        course_name=course.name,
                        gg_id=gg_course_id,
                    )
                    return course
                except Course.DoesNotExist:
                    pass

            # Try to find by name (case-insensitive)
            try:
                course = Course.objects.get(name__iexact=course_name)
                logger.info("Found course by name", course_name=course.name)

                # Update gg_id if missing
                if not course.gg_id and gg_course_id:
                    course.gg_id = gg_course_id
                    course.save(update_fields=["gg_id"])
                    logger.info(
                        "Updated course with gg_id",
                        course_name=course.name,
                        gg_id=gg_course_id,
                    )

                return course

            except Course.DoesNotExist:
                pass

            # Create new course
            course = Course.objects.create(
                name=course_name,
                gg_id=gg_course_id,
                number_of_holes=18,  # Default to 18 holes
            )
            logger.info(
                "Created new course", course_name=course.name, gg_id=gg_course_id
            )
            return course

        except Exception as e:
            error_msg = f"Failed to find/create course '{course_name}': {str(e)}"
            result.add_error(error_msg)
            return None

    def _sync_course_tees(
        self, course: "Course", gg_course: Dict, result: EventSyncResult
    ):
        """
        Sync tees for a course from Golf Genius

        Args:
            course: BHMC Course object
            gg_course: Golf Genius course dictionary
            result: EventSyncResult for error reporting
        """
        from courses.models import Tee

        gg_tees = gg_course.get("tees", [])
        if not gg_tees:
            logger.info("No tees found for course", course_name=course.name)
            return

        for gg_tee in gg_tees:
            try:
                tee_name = gg_tee.get("name", "").strip()
                gg_tee_id = str(gg_tee.get("id", ""))

                if not tee_name:
                    logger.warning(
                        "Skipping tee with missing name", course_name=course.name
                    )
                    continue

                # Check if tee already exists
                try:
                    Tee.objects.get(course=course, name=tee_name)
                    logger.debug(
                        "Tee already exists, skipping",
                        course_name=course.name,
                        tee_name=tee_name,
                    )
                    continue
                except Tee.DoesNotExist:
                    pass

                # Create new tee
                tee = Tee.objects.create(course=course, name=tee_name, gg_id=gg_tee_id)
                logger.info(
                    "Created tee",
                    course_name=course.name,
                    tee_name=tee.name,
                    gg_id=gg_tee_id,
                )

            except Exception as e:
                tee_name = gg_tee.get("name", "Unknown")
                error_msg = f"Failed to sync tee '{tee_name}' for course '{course.name}': {str(e)}"
                result.add_error(error_msg)

    def _sync_course_holes(
        self, course: "Course", gg_course: Dict, result: EventSyncResult
    ):
        """
        Sync holes for a course from Golf Genius

        Args:
            course: BHMC Course object
            gg_course: Golf Genius course dictionary
            result: EventSyncResult for error reporting
        """
        from courses.models import Hole

        # Check if holes already exist
        if Hole.objects.filter(course=course).exists():
            logger.debug(
                "Holes already exist for course, skipping", course_name=course.name
            )
            return

        # Get par data from the first tee
        gg_tees = gg_course.get("tees", [])
        if not gg_tees:
            logger.warning("No tees available for hole sync", course_name=course.name)
            return

        first_tee = gg_tees[0]
        hole_data = first_tee.get("hole_data", {})
        par_data = hole_data.get("par", [])

        if not par_data or len(par_data) != 18:
            logger.warning(
                "Invalid or missing par data for holes",
                course_name=course.name,
                par_count=len(par_data),
            )
            return

        try:
            holes_to_create = []
            for hole_number in range(1, 19):
                par = par_data[hole_number - 1]  # par_data is 0-indexed
                if par is None or par <= 0:
                    logger.warning(
                        "Invalid par for hole",
                        course_name=course.name,
                        hole_number=hole_number,
                        par=par,
                    )
                    continue

                holes_to_create.append(
                    Hole(course=course, hole_number=hole_number, par=par)
                )

            # Bulk create holes
            Hole.objects.bulk_create(holes_to_create)
            logger.info(
                "Created holes",
                course_name=course.name,
                hole_count=len(holes_to_create),
            )

        except Exception as e:
            error_msg = f"Failed to create holes for course '{course.name}': {str(e)}"
            result.add_error(error_msg)
            logger.error("Hole creation failed", course_name=course.name, error=str(e))

    def _sync_event_rounds_and_tournaments(
        self, bhmc_event: Event, result: EventSyncResult
    ):
        """
        Sync rounds and tournaments for a BHMC event from Golf Genius

        Args:
            bhmc_event: BHMC Event object with gg_id set
            result: EventSyncResult for error reporting
        """
        try:
            # Get rounds from Golf Genius
            gg_rounds = self.api_client.get_event_rounds(bhmc_event.gg_id)

            if not gg_rounds:
                logger.info(
                    "No rounds found for event",
                    event_id=bhmc_event.id,
                    gg_event_id=bhmc_event.gg_id,
                )
                return

            # Process each round
            for gg_round in gg_rounds:
                try:
                    self._sync_round(bhmc_event, gg_round, result)
                except Exception as e:
                    round_number = gg_round.get("round", {}).get("index", "Unknown")
                    error_msg = f"Failed to sync round '{round_number}': {str(e)}"
                    result.add_error(error_msg)

            logger.info("Round and tournament sync completed", event_id=bhmc_event.id)

        except Exception as e:
            error_msg = f"Round and tournament sync failed: {str(e)}"
            result.add_error(error_msg)

    def _sync_round(self, bhmc_event: Event, gg_round: Dict, result: EventSyncResult):
        """
        Sync a single round from Golf Genius, including its tournaments

        Args:
            bhmc_event: BHMC Event object
            gg_round: Golf Genius round dictionary
            result: EventSyncResult for error reporting
        """
        from events.models import Round
        from django.db import IntegrityError

        gg_round_id = str(gg_round.get("round", {}).get("id", ""))
        round_number = gg_round.get("round", {}).get("index")
        round_date_str = gg_round.get("round", {}).get("date")

        if not gg_round_id:
            result.add_error("Round sync failed: missing round ID")
            return

        if round_number is None:
            result.add_error(
                f"Round sync failed: missing round number for round {gg_round_id}"
            )
            return

        if not round_date_str:
            result.add_error(
                f"Round sync failed: missing round date for round {gg_round_id}"
            )
            return

        try:
            # Parse round date
            round_date = datetime.strptime(round_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            result.add_error(
                f"Round sync failed: invalid round date '{round_date_str}' for round {gg_round_id}"
            )
            return

        # Check if round already exists
        try:
            existing_round = Round.objects.get(event=bhmc_event, gg_id=gg_round_id)

            # Delete existing round (this will CASCADE delete related tournaments)
            try:
                existing_round.delete()
                logger.info(
                    "Deleted existing round and tournaments",
                    event_id=bhmc_event.id,
                    round_number=round_number,
                    gg_round_id=gg_round_id,
                )
            except IntegrityError as e:
                # Foreign key constraint error - hard stop as requested
                error_msg = f"Foreign key constraint error deleting round {round_number} (GG ID: {gg_round_id}): {str(e)}"
                result.add_error(error_msg)
                return

        except Round.DoesNotExist:
            # Round doesn't exist, proceed with creation
            pass

        # Create new round
        try:
            new_round = Round.objects.create(
                event=bhmc_event,
                round_number=round_number,
                round_date=round_date,
                gg_id=gg_round_id,
            )
            logger.info(
                "Created round",
                event_id=bhmc_event.id,
                round_number=round_number,
                round_date=round_date,
                gg_round_id=gg_round_id,
            )
        except Exception as e:
            error_msg = f"Failed to create round {round_number}: {str(e)}"
            result.add_error(error_msg)
            return

        # Sync tournaments for this round
        self._sync_round_tournaments(bhmc_event, new_round, gg_round, result)

    def _sync_round_tournaments(
        self,
        bhmc_event: Event,
        round_obj: Round,
        gg_round: Dict,
        result: EventSyncResult,
    ):
        """
        Sync tournaments for a specific round from Golf Genius

        Args:
            bhmc_event: BHMC Event object
            round_obj: BHMC Round object
            gg_round: Golf Genius round dictionary
            result: EventSyncResult for error reporting
        """

        gg_round_id = str(gg_round.get("round", {}).get("id", ""))

        try:
            # Get tournaments for this round from Golf Genius
            gg_tournaments = self.api_client.get_round_tournaments(
                bhmc_event.gg_id, gg_round_id
            )

            if not gg_tournaments:
                logger.info(
                    "No tournaments found for round",
                    event_id=bhmc_event.id,
                    round_number=round_obj.round_number,
                    gg_round_id=gg_round_id,
                )
                return

            # Process each tournament
            for gg_tournament in gg_tournaments:
                try:
                    self._sync_tournament(bhmc_event, round_obj, gg_tournament, result)
                except Exception as e:
                    tournament_name = gg_tournament.get("name", "Unknown")
                    error_msg = f"Failed to sync tournament '{tournament_name}' for round {round_obj.round_number}: {str(e)}"
                    result.add_error(error_msg)

        except Exception as e:
            error_msg = f"Failed to get tournaments for round {round_obj.round_number}: {str(e)}"
            result.add_error(error_msg)

    def _sync_tournament(
        self,
        bhmc_event: Event,
        round_obj: "Round",
        gg_tournament: Dict,
        result: EventSyncResult,
    ):
        """
        Sync a single tournament from Golf Genius

        Args:
            bhmc_event: BHMC Event object
            round_obj: BHMC Round object
            gg_tournament: Golf Genius tournament dictionary
            result: EventSyncResult for error reporting
        """
        from events.models import Tournament

        gg_tournament_id = str(gg_tournament.get("event", {}).get("id", ""))
        tournament_name = gg_tournament.get("event", {}).get("name", "").strip()
        tournament_format = gg_tournament.get("event", {}).get("score_format", "")
        handicap_format = gg_tournament.get("event", {}).get("handicap_format", "")

        if not gg_tournament_id:
            result.add_error("Tournament sync failed: missing tournament ID")
            return

        if not tournament_name:
            result.add_error(
                f"Tournament sync failed: missing name for tournament {gg_tournament_id}"
            )
            return

        # Determine if tournament is net
        is_net = self._determine_is_net(handicap_format)

        # Create tournament
        try:
            Tournament.objects.create(
                event=bhmc_event,
                round=round_obj,
                name=tournament_name,
                format=tournament_format,
                is_net=is_net,
                gg_id=gg_tournament_id,
            )
            logger.info(
                "Created tournament",
                event_id=bhmc_event.id,
                round_number=round_obj.round_number,
                tournament_name=tournament_name,
                is_net=is_net,
                gg_tournament_id=gg_tournament_id,
            )
        except Exception as e:
            error_msg = f"Failed to create tournament '{tournament_name}': {str(e)}"
            result.add_error(error_msg)

    def _determine_is_net(self, handicap_format: str) -> bool:
        """
        Determine if a tournament is net based on handicap_format

        Args:
            handicap_format: Golf Genius handicap format string

        Returns:
            True if tournament is net, False if gross
        """
        if not handicap_format:
            return False

        handicap_format_lower = handicap_format.lower()

        # Check for net indicators
        net_indicators = ["net", "usga_net"]
        return any(indicator in handicap_format_lower for indicator in net_indicators)
