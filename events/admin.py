from django.contrib import admin
from django.contrib import messages

from register.admin import CurrentSeasonFilter

from .models import Event, EventFee, FeeType, Round, Tournament, TournamentResult


class CoursesInline(admin.TabularInline):
    model = Event.courses.through
    can_delete = True
    extra = 0
    fields = ["name", ]
    
    
class EventFeesInline(admin.TabularInline):
    model = EventFee
    can_delete = True
    extra = 0
    verbose_name_plural = "Event Fees"
    fields = ["display_order", "fee_type", "is_required", "amount", "override_amount", "override_restriction", ]


class FeeTypeAdmin(admin.ModelAdmin):
    fields = ["name", "code", "restriction", ]
    list_display = ["name", "code", "restriction", ]
    list_display_links = ("name",)
    ordering = ["name", ]


class EventAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Event Details", {
            "fields": ("season", "name", ("event_type", "start_type", "status"),
                       ("rounds", "season_points", "skins_type", ))
        }),
        ("Event Date", {
            "fields": ("start_date", "start_time", "tee_time_splits", "starter_time_interval", )
        }),
        ("Registration Settings", {
            "fields": ("registration_type", ("signup_start", "signup_end", "payments_end", "priority_signup_start", ),
                       ("group_size", "team_size", "total_groups", "registration_maximum",
                        "minimum_signup_group_size", "maximum_signup_group_size", ),
                       ("ghin_required", "can_choose", "age_restriction", "age_restriction_type", ),
                       ("courses",),)
        }),
        ("Format, Rules, and Notes", {
            "classes": ("wide",),
            "fields": ("notes",),
        }),
        ("Other", {
            "fields": ("external_url", "portal_url", "default_tag", )
        }),
    )
    inlines = [EventFeesInline, ]
    actions = ['export_roster_to_golf_genius', 'sync_event_with_golf_genius']

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
                        f'{len(result.errors)} errors'
                    )
                else:
                    messages.success(
                        request,
                        f'Event "{event.name}": Successfully exported {result.exported_players} players'
                    )
                    
            except Exception as e:
                messages.error(request, f'Event "{event.name}": Export failed - {str(e)}')
                total_errors += 1
        
        if total_exported > 0:
            messages.success(
                request,
                f'Total: Exported {total_exported} players across {queryset.count()} events'
            )
        
        if total_errors > 0:
            messages.warning(
                request,
                f'Completed with {total_errors} errors'
            )
    
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
                        messages.warning(
                            request,
                            f'Event "{event.name}": {error}'
                        )
                else:
                    total_synced += 1
                    messages.success(
                        request,
                        f'Event "{event.name}": Successfully synced with Golf Genius'
                    )
                    
            except Exception as e:
                messages.error(request, f'Event "{event.name}": Sync failed - {str(e)}')
                total_errors += 1
        
        if total_synced > 0:
            messages.success(
                request,
                f'Total: Synced {total_synced} events with Golf Genius'
            )
        
        if total_errors > 0:
            messages.warning(
                request,
                f'Completed with {total_errors} errors'
            )
    
    sync_event_with_golf_genius.short_description = "Sync event with Golf Genius"

    def event_type_display(self, obj):
        return obj.get_event_type_display()

    event_type_display.short_description = "Event Type"
    date_hierarchy = "start_date"
    list_display = ["season", "name", "start_date", "event_type_display", "gg_id", ]
    list_display_links = ("name",)
    list_filter = ("season", "event_type",)
    ordering = ["start_date", ]
    search_fields = ["name", "notes", ]
    save_on_top = True


class RoundAdmin(admin.ModelAdmin):
    fields = ["event", "round_number", "round_date", "gg_id"]
    list_display = ["event", "round_number", "round_date", "gg_id"]
    list_display_links = ("round_number",)
    list_filter = (CurrentSeasonFilter, "round_date")
    ordering = ["event", "round_number"]
    search_fields = ["event__name", "gg_id"]
    save_on_top = True
    actions = ['import_scores_from_golf_genius']

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
                            request,
                            f'Round "{round_obj}": {player_name} - {error}'
                        )
                else:
                    total_success += result.success_count
                    messages.success(
                        request,
                        f'Round "{round_obj}": Successfully imported {result.success_count} scores'
                    )

            except Exception as e:
                messages.error(request, f'Round "{round_obj}": Import failed - {str(e)}')
                total_errors += 1

        if total_success > 0:
            messages.success(
                request,
                f'Total: Imported {total_success} scores across {queryset.count()} rounds'
            )

        if total_errors > 0:
            messages.warning(
                request,
                f'Completed with {total_errors} errors'
            )

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
    fields = ["tournament", "player", "position", "score", "points", "amount", "details"]
    list_display = ["tournament", "player", "position", "score", "points", "amount"]
    list_display_links = ("tournament",)
    list_filter = ("tournament", "position")
    ordering = ["tournament", "position"]
    search_fields = ["tournament__name", "player__first_name", "player__last_name"]
    save_on_top = True


admin.site.register(FeeType, FeeTypeAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Round, RoundAdmin)
admin.site.register(Tournament, TournamentAdmin)
admin.site.register(TournamentResult, TournamentResultAdmin)
