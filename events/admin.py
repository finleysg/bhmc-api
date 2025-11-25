import structlog
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.db.models import QuerySet
from django.http import HttpRequest

from core.util import current_season
from golfgenius.event_sync_service import EventSyncService
from golfgenius.results_import_service import ResultsImportService
from golfgenius.roster_export_service import RosterService
from golfgenius.score_import_service import ScoreImportService
from register.admin import CurrentSeasonFilter

from .models import Event, EventFee, FeeType, Round, Tournament, TournamentResult

logger = structlog.get_logger(__name__)

# Constants
MAX_EVENTS_PER_ACTION = 1
SINGLE_EVENT_WARNING = "Please select exactly one event for this action."

# Service instances
event_sync_service = EventSyncService()
results_import_service = ResultsImportService()
roster_service = RosterService()
score_import_service = ScoreImportService()


class TournamentResultEventFilter(SimpleListFilter):
    """
    Filter tournament results by current season events.

    Shows events from the current season that have tournaments with results.
    Falls back to all current season events if TournamentResult table doesn't exist.
    """

    title = "current season event"
    parameter_name = "event"

    def _get_events_with_results(self, current_season_year: int) -> QuerySet[Event]:
        """Get events from current season that have tournament results"""
        return (
            Event.objects.filter(
                season=current_season_year,
                gg_tournaments__tournament_results__isnull=False,
            )
            .distinct()
            .order_by("start_date", "name")
        )

    def _get_all_current_season_events(
        self, current_season_year: int
    ) -> QuerySet[Event]:
        """Get all events from current season as fallback"""
        return Event.objects.filter(season=current_season_year).order_by(
            "start_date", "name"
        )

    def lookups(self, request, model_admin):
        current_season_year = current_season()
        events = []

        try:
            events_qs = self._get_events_with_results(current_season_year)
        except Exception as e:
            logger.warning("Failed to get events with results", exc_info=e)
            try:
                events_qs = self._get_all_current_season_events(current_season_year)
            except Exception as e:
                logger.error("Failed to get current season events", exc_info=e)
                return []

        for event in events_qs:
            display_name = f"{event.start_date} - {event.name}"
            events.append((event.id, display_name))

        return events

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tournament__event__id=self.value())
        return queryset


class TournamentByEventFilter(SimpleListFilter):
    """
    Filter tournaments by the event selected in TournamentResultEventFilter.

    Reads the selected 'event' GET parameter and shows only tournaments
    belonging to that event. Shows no choices if no event is selected.
    """

    title = "tournament"
    parameter_name = "tournament"

    def lookups(self, request, model_admin):
        event_id = request.GET.get("event")
        if not event_id:
            return []

        try:
            tournaments = (
                Tournament.objects.filter(event_id=event_id)
                .select_related("round")
                .order_by("round__round_date", "name")
            )
        except Exception as e:
            logger.error(
                "Failed to get tournaments for event", event_id=event_id, exc_info=e
            )
            return []

        choices = []
        for tournament in tournaments:
            round_display = str(tournament.round) if tournament.round else "No Round"
            display = f"{round_display} - {tournament.name}"
            choices.append((str(tournament.id), display))

        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tournament__id=self.value())
        return queryset


class CoursesInline(admin.TabularInline):
    model = Event.courses.through
    can_delete = True
    extra = 0
    fields = [
        "name",
    ]


class EventFeesInline(admin.TabularInline):
    model = EventFee
    can_delete = True
    extra = 0
    verbose_name_plural = "Event Fees"
    fields = [
        "display_order",
        "fee_type",
        "is_required",
        "amount",
        "override_amount",
        "override_restriction",
    ]


class FeeTypeAdmin(admin.ModelAdmin):
    fields = [
        "name",
        "code",
        "restriction",
    ]
    list_display = [
        "name",
        "code",
        "restriction",
    ]
    list_display_links = ("name",)
    ordering = [
        "name",
    ]


class EventAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Event Details",
            {
                "fields": (
                    "season",
                    "name",
                    ("event_type", "start_type", "status"),
                    (
                        "rounds",
                        "season_points",
                        "skins_type",
                    ),
                )
            },
        ),
        (
            "Event Date",
            {
                "fields": (
                    "start_date",
                    "start_time",
                    "tee_time_splits",
                    "starter_time_interval",
                )
            },
        ),
        (
            "Registration Settings",
            {
                "fields": (
                    "registration_type",
                    (
                        "signup_start",
                        "signup_end",
                        "payments_end",
                        "priority_signup_start",
                    ),
                    (
                        "group_size",
                        "team_size",
                        "total_groups",
                        "registration_maximum",
                        "minimum_signup_group_size",
                        "maximum_signup_group_size",
                    ),
                    (
                        "ghin_required",
                        "can_choose",
                        "age_restriction",
                        "age_restriction_type",
                    ),
                    ("courses",),
                )
            },
        ),
        (
            "Format, Rules, and Notes",
            {
                "classes": ("wide",),
                "fields": ("notes",),
            },
        ),
        (
            "Other",
            {
                "fields": (
                    "external_url",
                    "portal_url",
                    "default_tag",
                )
            },
        ),
    )
    inlines = [
        EventFeesInline,
    ]
    actions = [
        "export_roster_to_golf_genius",
        "sync_event_with_golf_genius",
        "import_tournament_results",
        "import_points_from_golf_genius",
        "import_skins_from_golf_genius",
        "import_user_scored_from_golf_genius",
    ]

    def _validate_single_event_selection(
        self, request: HttpRequest, queryset: QuerySet[Event]
    ) -> bool:
        """Validate that exactly one event is selected for an action.

        Args:
            request: The HTTP request object
            queryset: Selected Event instances

        Returns:
            True if exactly one event is selected, False otherwise
        """
        if queryset.count() != MAX_EVENTS_PER_ACTION:
            logger.warning(
                "invalid_event_selection_count",
                expected=MAX_EVENTS_PER_ACTION,
                actual=queryset.count(),
            )
            messages.error(request, SINGLE_EVENT_WARNING)
            return False
        return True

    def _import_results_base(
        self,
        request: HttpRequest,
        queryset: QuerySet[Event],
        import_method,
        format_name: str,
        success_message_template: str,
        no_results_message: str,
    ) -> None:
        """Base helper method for importing tournament results.

        Args:
            request: The HTTP request object
            queryset: Selected Event instances (must be exactly 1)
            import_method: The import method to call (e.g., import_stroke_play_results)
            format_name: Name of the format being imported (for logging)
            success_message_template: Template for success message with {count} and {tournament}
            no_results_message: Message to show when no results are found
        """
        if not self._validate_single_event_selection(request, queryset):
            return

        event = queryset.first()
        logger.info(
            "importing_tournament_results",
            event_id=event.id,
            event_name=event.name,
            format=format_name,
        )

        try:
            results = import_method(event.id)

            if not results:
                logger.info(
                    "no_tournaments_found",
                    event_id=event.id,
                    format=format_name,
                )
                messages.warning(request, f'Event "{event.name}": {no_results_message}')
                return

            total_imported = 0
            errors_occurred = False

            for tournament_result in results:
                total_imported += tournament_result.results_imported

                if tournament_result.errors:
                    errors_occurred = True
                    logger.warning(
                        "tournament_import_errors",
                        event_id=event.id,
                        tournament=tournament_result.tournament_name,
                        error_count=len(tournament_result.errors),
                    )
                    for error in tournament_result.errors:
                        messages.error(
                            request,
                            f"{event.name} - {tournament_result.tournament_name}: {error}",
                        )
                elif tournament_result.results_imported > 0:
                    logger.info(
                        "tournament_import_successful",
                        event_id=event.id,
                        tournament=tournament_result.tournament_name,
                        count=tournament_result.results_imported,
                    )
                    messages.success(
                        request,
                        success_message_template.format(
                            count=tournament_result.results_imported,
                            tournament=tournament_result.tournament_name,
                        ),
                    )

            if total_imported > 0:
                level = messages.WARNING if errors_occurred else messages.SUCCESS
                logger.info(
                    "import_completed",
                    event_id=event.id,
                    format=format_name,
                    total_imported=total_imported,
                    had_errors=errors_occurred,
                )
                messages.add_message(
                    request,
                    level,
                    f'Event "{event.name}": Imported {total_imported} {format_name} results across all tournaments',
                )

        except Exception as e:
            logger.error(
                "import_failed",
                event_id=event.id,
                format=format_name,
                error=str(e),
                exc_info=True,
            )
            messages.error(
                request,
                f'Event "{event.name}": Import failed - {str(e)}',
            )

    def export_roster_to_golf_genius(
        self, request: HttpRequest, queryset: QuerySet[Event]
    ) -> None:
        """Admin action to export roster to Golf Genius.

        Args:
            request: The HTTP request object
            queryset: Selected Event instances (must be exactly 1)
        """
        if not self._validate_single_event_selection(request, queryset):
            return

        event = queryset.first()
        logger.info(
            "exporting_roster_to_golf_genius", event_id=event.id, event_name=event.name
        )

        try:
            result = roster_service.export_roster(event.id)

            if result.errors:
                logger.warning(
                    "roster_export_completed_with_errors",
                    event_id=event.id,
                    exported_count=result.exported_players,
                    error_count=len(result.errors),
                )
                messages.warning(
                    request,
                    f'Event "{event.name}": Exported {result.exported_players} players with {len(result.errors)} errors',
                )
            else:
                logger.info(
                    "roster_export_successful",
                    event_id=event.id,
                    exported_count=result.exported_players,
                )
                messages.success(
                    request,
                    f'Event "{event.name}": Successfully exported {result.exported_players} players',
                )

        except Exception as e:
            logger.error(
                "roster_export_failed", event_id=event.id, error=str(e), exc_info=True
            )
            messages.error(request, f'Event "{event.name}": Export failed - {str(e)}')

    export_roster_to_golf_genius.short_description = "Export roster to Golf Genius"

    def sync_event_with_golf_genius(
        self, request: HttpRequest, queryset: QuerySet[Event]
    ) -> None:
        """Admin action to sync event with Golf Genius.

        Args:
            request: The HTTP request object
            queryset: Selected Event instances (must be exactly 1)
        """
        if not self._validate_single_event_selection(request, queryset):
            return

        event = queryset.first()
        logger.info(
            "syncing_event_with_golf_genius", event_id=event.id, event_name=event.name
        )

        try:
            result = event_sync_service.sync_event(event.id)

            if result.errors:
                logger.warning(
                    "event_sync_completed_with_errors",
                    event_id=event.id,
                    error_count=len(result.errors),
                )
                for error in result.errors:
                    messages.warning(request, f'Event "{event.name}": {error}')
            else:
                logger.info("event_sync_successful", event_id=event.id)
                messages.success(
                    request,
                    f'Event "{event.name}": Successfully synced with Golf Genius',
                )

        except Exception as e:
            logger.error(
                "event_sync_failed", event_id=event.id, error=str(e), exc_info=True
            )
            messages.error(request, f'Event "{event.name}": Sync failed - {str(e)}')

    sync_event_with_golf_genius.short_description = "Sync event with Golf Genius"

    def import_tournament_results(
        self, request: HttpRequest, queryset: QuerySet[Event]
    ) -> None:
        """Import stroke play tournament results from Golf Genius for selected event.

        Args:
            request: The HTTP request object
            queryset: Selected Event instances (must be exactly 1)
        """
        self._import_results_base(
            request=request,
            queryset=queryset,
            import_method=results_import_service.import_stroke_play_results,
            format_name="stroke play",
            success_message_template="Successfully imported {count} results for {tournament}",
            no_results_message="No stroke play tournaments found (must have prize money > $0.00 and format = 'stroke')",
        )

    import_tournament_results.short_description = (
        "Import tournament results from Golf Genius"
    )

    def import_points_from_golf_genius(
        self, request: HttpRequest, queryset: QuerySet[Event]
    ) -> None:
        """Import points tournament results from Golf Genius for selected event.

        Args:
            request: The HTTP request object
            queryset: Selected Event instances (must be exactly 1)
        """
        self._import_results_base(
            request=request,
            queryset=queryset,
            import_method=results_import_service.import_points,
            format_name="points",
            success_message_template="Successfully imported {count} points for {tournament}",
            no_results_message="No points tournaments found (must have points > 0 and format = 'points')",
        )

    import_points_from_golf_genius.short_description = "Import points from Golf Genius"

    def import_skins_from_golf_genius(
        self, request: HttpRequest, queryset: QuerySet[Event]
    ) -> None:
        """Import skins tournament results from Golf Genius for selected event.

        Args:
            request: The HTTP request object
            queryset: Selected Event instances (must be exactly 1)
        """
        self._import_results_base(
            request=request,
            queryset=queryset,
            import_method=results_import_service.import_skins,
            format_name="skins",
            success_message_template="Successfully imported {count} skins results for {tournament}",
            no_results_message="No skins tournaments found (must have purse > $0.00 and format = 'skins')",
        )

    import_skins_from_golf_genius.short_description = "Import skins from Golf Genius"

    def import_user_scored_from_golf_genius(
        self, request: HttpRequest, queryset: QuerySet[Event]
    ) -> None:
        """Import user-scored tournament results from Golf Genius for selected event.

        Args:
            request: The HTTP request object
            queryset: Selected Event instances (must be exactly 1)
        """
        self._import_results_base(
            request=request,
            queryset=queryset,
            import_method=results_import_service.import_user_scored_results,
            format_name="user_scored",
            success_message_template="Successfully imported {count} results for {tournament}",
            no_results_message="No user_scored tournaments found for this event",
        )

    import_user_scored_from_golf_genius.short_description = (
        "Import user-scored results from Golf Genius"
    )

    import_user_scored_from_golf_genius.short_description = (
        "Import user-scored results from Golf Genius"
    )

    def event_type_display(self, obj):
        return obj.get_event_type_display()

    event_type_display.short_description = "Event Type"
    date_hierarchy = "start_date"
    list_display = [
        "season",
        "name",
        "start_date",
        "event_type_display",
        "gg_id",
    ]
    list_display_links = ("name",)
    list_filter = (
        "season",
        "event_type",
    )
    ordering = [
        "start_date",
    ]
    search_fields = [
        "name",
        "notes",
    ]
    save_on_top = True


class RoundAdmin(admin.ModelAdmin):
    fields = ["event", "round_number", "round_date", "gg_id"]
    list_display = ["event", "round_number", "round_date", "gg_id"]
    list_display_links = ("round_number",)
    list_filter = (CurrentSeasonFilter, "round_date")
    ordering = ["event", "round_number"]
    search_fields = ["event__name", "gg_id"]
    save_on_top = True
    actions = ["import_scores_from_golf_genius"]

    def import_scores_from_golf_genius(self, request, queryset):
        """Admin action to import scores from Golf Genius"""
        from golfgenius.score_import_service import ScoreImportService

        service = ScoreImportService()
        total_success = 0
        total_errors = 0

        for round_obj in queryset:
            try:
                result = service.import_scores(round_obj.event.id, round_obj.id)

                if result.errors:
                    total_errors += len(result.errors)
                    for player_name, error in result.errors.items():
                        messages.warning(
                            request, f'Round "{round_obj}": {player_name} - {error}'
                        )
                else:
                    total_success += result.success_count
                    messages.success(
                        request,
                        f'Round "{round_obj}": Successfully imported {result.success_count} scores',
                    )

            except Exception as e:
                messages.error(
                    request, f'Round "{round_obj}": Import failed - {str(e)}'
                )
                total_errors += 1

        if total_success > 0:
            messages.success(
                request,
                f"Total: Imported {total_success} scores across {queryset.count()} rounds",
            )

        if total_errors > 0:
            messages.warning(request, f"Completed with {total_errors} errors")

    import_scores_from_golf_genius.short_description = "Import scores from Golf Genius"


class TournamentAdmin(admin.ModelAdmin):
    fields = ["event", "round", "name", "format", "is_net", "gg_id"]
    list_display = ["event", "round", "name", "format", "is_net", "gg_id"]
    list_display_links = ("name",)
    list_filter = (CurrentSeasonFilter, "is_net", "format")
    ordering = ["event", "round", "name"]
    search_fields = ["event__name", "name", "gg_id"]
    save_on_top = True


class TournamentResultAdmin(admin.ModelAdmin):
    fields = [
        "tournament",
        "flight",
        "player",
        "team_id",
        "position",
        "score",
        "amount",
        "details",
    ]
    list_display = [
        "tournament",
        "flight",
        "player",
        "position",
        "score",
        "amount",
    ]
    list_display_links = ("tournament",)
    list_filter = (TournamentResultEventFilter, TournamentByEventFilter, "flight")
    ordering = ["tournament", "position"]
    search_fields = ["tournament__name", "player__first_name", "player__last_name"]
    save_on_top = True


admin.site.register(FeeType, FeeTypeAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Round, RoundAdmin)
admin.site.register(Tournament, TournamentAdmin)
admin.site.register(TournamentResult, TournamentResultAdmin)
