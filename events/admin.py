import structlog
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import QuerySet

from core.util import current_season
from register.admin import CurrentSeasonFilter

from .models import Event, EventFee, FeeType, Round, Tournament, TournamentResult

logger = structlog.get_logger(__name__)


class TournamentResultEventFilter(SimpleListFilter):
    """
    Filter tournament results by current season events.

    Shows events from the current season that have tournaments with results.
    Falls back to all current season events if TournamentResult table doesn't exist.
    """

    title = "current season event"
    parameter_name = "event"

    def _get_events_with_results(self, current_season_year: int) -> QuerySet[Event]:
        """
        Retrieve events in the specified season that have at least one tournament result.
        
        Returns:
            QuerySet[Event]: Events in the given season that have one or more associated tournament results, ordered by start_date then name.
        """
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
        """
        Return all events for the given season ordered by start date and name.
        
        Parameters:
            current_season_year (int): Year of the season to filter events by.
        
        Returns:
            QuerySet[Event]: Events in the specified season ordered by `start_date`, then `name`.
        """
        return Event.objects.filter(season=current_season_year).order_by(
            "start_date", "name"
        )

    def lookups(self, request, model_admin):
        """
        Builds the admin filter choices for current-season events that have associated tournament results.
        
        If retrieving events with results fails, falls back to all events in the current season; if that also fails, returns an empty list.
        
        Returns:
            list[tuple[int, str]]: Tuples of (event_id, "start_date - event_name") suitable for Django admin filter choices, or an empty list if no events could be retrieved.
        """
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
        """
        Filter the provided queryset to tournament results belonging to the selected event.
        
        Returns:
            QuerySet: TournamentResult queryset filtered to the event whose id matches the current filter value, or the original queryset if no event is selected.
        """
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
        """
        Provide tournament choices for the admin filter based on the "event" GET parameter.
        
        Reads the "event" parameter from the provided request and returns a list of tuples suitable for Django admin filter lookups. Each tuple is (tournament_id_as_str, display), where display is formatted as "<Round or 'No Round'> - <tournament name>". If the "event" parameter is missing or an error occurs while fetching tournaments, an empty list is returned.
        
        Parameters:
            request (HttpRequest): The incoming request used to read the "event" GET parameter.
        
        Returns:
            list[tuple[str, str]]: A list of (tournament id, display string) tuples for the given event, or an empty list.
        """
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
        """
        Filter the provided queryset to the tournament selected by the admin filter.
        
        @returns Filtered queryset limited to the selected tournament when a value is set, the original queryset otherwise.
        """
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
                "signup_waves",
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

    def event_type_display(self, obj):
        """
        Return the human-readable label for the event's type.
        
        Parameters:
            obj (Event): The Event model instance whose event type label to retrieve.
        
        Returns:
            label (str): Human-readable label for the event's type.
        """
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
