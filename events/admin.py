from django.contrib import admin
from django.contrib import messages

from .models import Event, EventFee, FeeType, Round, Tournament


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
    actions = ['export_roster_to_golf_genius']

    def export_roster_to_golf_genius(self, request, queryset):
        """Admin action to export roster to Golf Genius"""
        from golfgenius.services import RosterService
        
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

    def event_type_display(self, obj):
        return obj.get_event_type_display()

    event_type_display.short_description = "Event Type"
    date_hierarchy = "start_date"
    list_display = ["season", "name", "start_date", "event_type_display", ]
    list_display_links = ("name",)
    list_filter = ("season", "event_type",)
    ordering = ["start_date", ]
    search_fields = ["name", "notes", ]
    save_on_top = True


class RoundAdmin(admin.ModelAdmin):
    fields = ["event", "round_number", "round_date", "gg_id"]
    list_display = ["event", "round_number", "round_date", "gg_id"]
    list_display_links = ("round_number",)
    list_filter = ("event", "round_date")
    ordering = ["event", "round_number"]
    search_fields = ["event__name", "gg_id"]
    save_on_top = True


class TournamentAdmin(admin.ModelAdmin):
    fields = ["event", "round", "course", "name", "format", "is_net", "gg_id"]
    list_display = ["event", "round", "name", "course", "format", "is_net", "gg_id"]
    list_display_links = ("name",)
    list_filter = ("event", "round", "course", "is_net", "format")
    ordering = ["event", "round", "name"]
    search_fields = ["event__name", "name", "gg_id"]
    save_on_top = True


admin.site.register(FeeType, FeeTypeAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Round, RoundAdmin)
admin.site.register(Tournament, TournamentAdmin)
