from django.contrib import admin

from scores import models
from register.admin import CurrentSeasonFilter


class EventScoreAdmin(admin.TabularInline):
    model = models.EventScore
    can_delete = False
    extra = 0
    show_change_link = True
    verbose_name_plural = "Scores"
    fields = ["hole", "score", "is_net", ]


@admin.register(models.EventScoreCard)
class EventScoreCardAdmin(admin.ModelAdmin):
    fields = ["event", "player", "course", "tee", "handicap_index", "course_handicap", ]
    inlines = [EventScoreAdmin]
    list_display = ["event", "player", "course", "tee", ]
    date_hierarchy = "event__start_date"
    ordering = ["event", "course", "player", ]
    search_fields = ("player__first_name", "player__last_name", )
    list_filter = (CurrentSeasonFilter, "course", "tee", )

    save_on_top = True

