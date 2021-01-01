from django.contrib import admin

from .models import Event, EventFee, FeeType


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
    fields = ["display_order", "fee_type", "is_required", "amount", ]


class FeeTypeAdmin(admin.ModelAdmin):
    fields = ["name", "code", ]
    list_display = ["name", "code", ]
    list_display_links = ("name",)
    ordering = ["name", ]


class EventAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Event Details", {
            "fields": ("season", "name", ("event_type", "start_type", "status"),
                       ("rounds", "season_points", "skins_type", ))
        }),
        ("Event Date", {
            "fields": ("start_date", "start_time",)
        }),
        ("Registration Settings", {
            "fields": ("registration_type", ("signup_start", "signup_end", "payments_end",),
                       ("group_size", "total_groups", "registration_maximum",
                        "minimum_signup_group_size", "maximum_signup_group_size",),
                       ("ghin_required", "can_choose", ),
                       ("courses",),)
        }),
        ("Format, Rules, and Notes", {
            "classes": ("wide",),
            "fields": ("notes",),
        }),
        ("Other", {
            "fields": ("external_url", "portal_url",)
        }),
    )
    inlines = [EventFeesInline, ]

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


admin.site.register(FeeType, FeeTypeAdmin)
admin.site.register(Event, EventAdmin)
