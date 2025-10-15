from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import SimpleListFilter

from core.util import current_season
from register.admin import CurrentSeasonFilter

from .models import Event, EventFee, FeeType, Round, Tournament, TournamentResult


class TournamentResultEventFilter(SimpleListFilter):
    """Filter tournament results by current season events"""

    title = "current season event"
    parameter_name = "event"

    def lookups(self, request, model_admin):
        # Get current season events that have tournaments with results
        current_season_year = current_season()
        events = []

        try:
            # Get events from current season that have tournaments with results
            events_with_results = (
                Event.objects.filter(
                    season=current_season_year,
                    gg_tournaments__tournament_results__isnull=False,
                )
                .distinct()
                .order_by("start_date", "name")
            )

            for event in events_with_results:
                display_name = f"{event.start_date} - {event.name}"
                events.append((event.id, display_name))

        except Exception:
            # Handle case where TournamentResult table doesn't exist yet
            # Fall back to showing all current season events
            try:
                all_current_events = Event.objects.filter(
                    season=current_season_year
                ).order_by("start_date", "name")

                for event in all_current_events:
                    display_name = f"{event.start_date} - {event.name}"
                    events.append((event.id, display_name))
            except Exception:
                pass

        return events

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tournament__event__id=self.value())
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

    def export_roster_to_golf_genius(self, request, queryset):
        """Admin action to export roster to Golf Genius"""
        from golfgenius.roster_export_service import RosterService

        service = RosterService()
        total_exported = 0
        total_errors = 0

        for event in queryset:
            try:
                result = service.export_roster(event.id)
                total_exported += result.exported_players
                total_errors += len(result.errors)

                if result.errors:
                    messages.warning(
                        request,
                        f'Event "{event.name}": Exported {result.exported_players} players, '
                        f"{len(result.errors)} errors",
                    )
                else:
                    messages.success(
                        request,
                        f'Event "{event.name}": Successfully exported {result.exported_players} players',
                    )

            except Exception as e:
                messages.error(
                    request, f'Event "{event.name}": Export failed - {str(e)}'
                )
                total_errors += 1

        if total_exported > 0:
            messages.success(
                request,
                f"Total: Exported {total_exported} players across {queryset.count()} events",
            )

        if total_errors > 0:
            messages.warning(request, f"Completed with {total_errors} errors")

    export_roster_to_golf_genius.short_description = "Export roster to Golf Genius"

    def sync_event_with_golf_genius(self, request, queryset):
        """Admin action to sync event with Golf Genius"""
        from golfgenius.event_sync_service import EventSyncService

        service = EventSyncService()
        total_synced = 0
        total_errors = 0

        for event in queryset:
            try:
                result = service.sync_event(event.id)

                if result.errors:
                    total_errors += len(result.errors)
                    for error in result.errors:
                        messages.warning(request, f'Event "{event.name}": {error}')
                else:
                    total_synced += 1
                    messages.success(
                        request,
                        f'Event "{event.name}": Successfully synced with Golf Genius',
                    )

            except Exception as e:
                messages.error(request, f'Event "{event.name}": Sync failed - {str(e)}')
                total_errors += 1

        if total_synced > 0:
            messages.success(
                request, f"Total: Synced {total_synced} events with Golf Genius"
            )

        if total_errors > 0:
            messages.warning(request, f"Completed with {total_errors} errors")

    sync_event_with_golf_genius.short_description = "Sync event with Golf Genius"

    def import_tournament_results(self, request, queryset):
        """Import tournament results from Golf Genius for selected events"""
        from golfgenius.results_import_service import ResultsImportService

        if queryset.count() > 5:
            self.message_user(
                request,
                "Please select 5 or fewer events at a time to avoid timeout issues.",
                level=messages.ERROR,
            )
            return

        results_service = ResultsImportService()
        total_imported = 0
        errors_occurred = False

        for event in queryset:
            try:
                # Import results for this event
                results = results_service.import_stroke_play_results(event.id)

                if not results:
                    self.message_user(
                        request,
                        f"No stroke play tournaments found for event '{event.name}'.",
                        level=messages.WARNING,
                    )
                    continue

                event_imported = 0
                for tournament_result in results:
                    event_imported += tournament_result.results_imported

                    if tournament_result.errors:
                        errors_occurred = True
                        for error in tournament_result.errors:
                            self.message_user(
                                request,
                                f"{event.name} - {tournament_result.tournament_name}: {error}",
                                level=messages.ERROR,
                            )
                    else:
                        if tournament_result.results_imported > 0:
                            self.message_user(
                                request,
                                f"Successfully imported {tournament_result.results_imported} results for {tournament_result.tournament_name}.",
                                level=messages.SUCCESS,
                            )

                total_imported += event_imported

                if event_imported > 0:
                    self.message_user(
                        request,
                        f"Event '{event.name}': Total {event_imported} results imported across all tournaments.",
                        level=messages.SUCCESS,
                    )

            except Exception as e:
                errors_occurred = True
                self.message_user(
                    request,
                    f"Error importing results for event '{event.name}': {str(e)}",
                    level=messages.ERROR,
                )

        # Summary message
        if total_imported > 0:
            level = messages.WARNING if errors_occurred else messages.SUCCESS
            self.message_user(
                request,
                f"Import completed. Total results imported across all events: {total_imported}",
                level=level,
            )
        elif not errors_occurred:
            self.message_user(
                request,
                "No results were imported. Check that tournaments have prize money > $0.00 and format = 'stroke'.",
                level=messages.INFO,
            )

    import_tournament_results.short_description = (
        "Import tournament results from Golf Genius"
    )

    def import_points_from_golf_genius(self, request, queryset):
        """Import points tournament results from Golf Genius for selected events"""
        from golfgenius.results_import_service import ResultsImportService

        if queryset.count() > 5:
            self.message_user(
                request,
                "Please select 5 or fewer events at a time to avoid timeout issues.",
                level=messages.ERROR,
            )
            return

        results_service = ResultsImportService()
        total_imported = 0
        errors_occurred = False

        for event in queryset:
            try:
                # Import points results for this event
                results = results_service.import_points(event.id)

                if not results:
                    self.message_user(
                        request,
                        f"No points tournaments found for event '{event.name}'.",
                        level=messages.WARNING,
                    )
                    continue

                event_imported = 0
                for tournament_result in results:
                    event_imported += tournament_result.results_imported

                    if tournament_result.errors:
                        errors_occurred = True
                        for error in tournament_result.errors:
                            self.message_user(
                                request,
                                f"{event.name} - {tournament_result.tournament_name}: {error}",
                                level=messages.ERROR,
                            )
                    else:
                        if tournament_result.results_imported > 0:
                            self.message_user(
                                request,
                                f"Successfully imported {tournament_result.results_imported} points for {tournament_result.tournament_name}.",
                                level=messages.SUCCESS,
                            )

                total_imported += event_imported

                if event_imported > 0:
                    self.message_user(
                        request,
                        f"Event '{event.name}': Total {event_imported} points imported across all tournaments.",
                        level=messages.SUCCESS,
                    )

            except Exception as e:
                errors_occurred = True
                self.message_user(
                    request,
                    f"Error importing points for event '{event.name}': {str(e)}",
                    level=messages.ERROR,
                )

        # Summary message
        if total_imported > 0:
            level = messages.WARNING if errors_occurred else messages.SUCCESS
            self.message_user(
                request,
                f"Points import completed. Total points imported across all events: {total_imported}",
                level=level,
            )
        elif not errors_occurred:
            self.message_user(
                request,
                "No points were imported. Check that tournaments have points > 0 and format = 'points'.",
                level=messages.INFO,
            )

    import_points_from_golf_genius.short_description = "Import points from Golf Genius"

    def import_skins_from_golf_genius(self, request, queryset):
        """Import skins tournament results from Golf Genius for selected events"""
        from golfgenius.results_import_service import ResultsImportService

        if queryset.count() > 5:
            self.message_user(
                request,
                "Please select 5 or fewer events at a time to avoid timeout issues.",
                level=messages.ERROR,
            )
            return

        results_service = ResultsImportService()
        total_imported = 0
        errors_occurred = False

        for event in queryset:
            try:
                # Import skins results for this event
                results = results_service.import_skins(event.id)

                if not results:
                    self.message_user(
                        request,
                        f"No skins tournaments found for event '{event.name}'.",
                        level=messages.WARNING,
                    )
                    continue

                event_imported = 0
                for tournament_result in results:
                    event_imported += tournament_result.results_imported

                    if tournament_result.errors:
                        errors_occurred = True
                        for error in tournament_result.errors:
                            self.message_user(
                                request,
                                f"{event.name} - {tournament_result.tournament_name}: {error}",
                                level=messages.ERROR,
                            )
                    else:
                        if tournament_result.results_imported > 0:
                            self.message_user(
                                request,
                                f"Successfully imported {tournament_result.results_imported} skins results for {tournament_result.tournament_name}.",
                                level=messages.SUCCESS,
                            )

                total_imported += event_imported

                if event_imported > 0:
                    self.message_user(
                        request,
                        f"Event '{event.name}': Total {event_imported} skins results imported across all tournaments.",
                        level=messages.SUCCESS,
                    )

            except Exception as e:
                errors_occurred = True
                self.message_user(
                    request,
                    f"Error importing skins for event '{event.name}': {str(e)}",
                    level=messages.ERROR,
                )

        # Summary message
        if total_imported > 0:
            level = messages.WARNING if errors_occurred else messages.SUCCESS
            self.message_user(
                request,
                f"Skins import completed. Total skins results imported across all events: {total_imported}",
                level=level,
            )
        elif not errors_occurred:
            self.message_user(
                request,
                "No skins results were imported. Check that tournaments have purse > $0.00 and format = 'skins'.",
                level=messages.INFO,
            )

    import_skins_from_golf_genius.short_description = "Import skins from Golf Genius"

    def import_user_scored_from_golf_genius(self, request, queryset):
        """Import user-scored tournament results from Golf Genius for selected events"""
        from golfgenius.results_import_service import ResultsImportService

        if queryset.count() > 5:
            self.message_user(
                request,
                "Please select 5 or fewer events at a time to avoid timeout issues.",
                level=messages.ERROR,
            )
            return

        results_service = ResultsImportService()
        total_imported = 0
        errors_occurred = False

        for event in queryset:
            try:
                # Import user-scored results for this event
                results = results_service.import_user_scored_results(event.id)

                if not results:
                    self.message_user(
                        request,
                        f"No user_scored tournaments found for event '{event.name}'.",
                        level=messages.WARNING,
                    )
                    continue

                event_imported = 0
                for tournament_result in results:
                    event_imported += tournament_result.results_imported

                    if tournament_result.errors:
                        errors_occurred = True
                        for error in tournament_result.errors:
                            self.message_user(
                                request,
                                f"{event.name} - {tournament_result.tournament_name}: {error}",
                                level=messages.ERROR,
                            )
                    else:
                        if tournament_result.results_imported > 0:
                            self.message_user(
                                request,
                                f"Successfully imported {tournament_result.results_imported} results for {tournament_result.tournament_name}.",
                                level=messages.SUCCESS,
                            )

                total_imported += event_imported

                if event_imported > 0:
                    self.message_user(
                        request,
                        f"Event '{event.name}': Total {event_imported} results imported across all tournaments.",
                        level=messages.SUCCESS,
                    )

            except Exception as e:
                errors_occurred = True
                self.message_user(
                    request,
                    f"Error importing user_scored results for event '{event.name}': {str(e)}",
                    level=messages.ERROR,
                )

        # Summary message
        if total_imported > 0:
            level = messages.WARNING if errors_occurred else messages.SUCCESS
            self.message_user(
                request,
                f"Import completed. Total results imported across all events: {total_imported}",
                level=level,
            )
        elif not errors_occurred:
            self.message_user(
                request,
                "No results were imported. Check that tournaments have prize money > $0.00 and format = 'user_scored'.",
                level=messages.INFO,
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
        "position",
        "score",
        "points",
        "amount",
        "details",
    ]
    list_display = [
        "tournament",
        "flight",
        "player",
        "position",
        "score",
        "points",
        "amount",
    ]
    list_display_links = ("tournament",)
    list_filter = (TournamentResultEventFilter, "flight")
    ordering = ["tournament", "position"]
    search_fields = ["tournament__name", "player__first_name", "player__last_name"]
    save_on_top = True


admin.site.register(FeeType, FeeTypeAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Round, RoundAdmin)
admin.site.register(Tournament, TournamentAdmin)
admin.site.register(TournamentResult, TournamentResultAdmin)
