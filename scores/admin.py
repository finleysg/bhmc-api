from django.contrib import admin

from scores import models
from register.admin import CurrentSeasonFilter


@admin.register(models.EventScore)
class EventScoreAdmin(admin.ModelAdmin):
    fields = ["event", "player", "hole", "score", "is_net", ]
    list_display = ["event", "player", "hole", "score", "is_net", ]
    date_hierarchy = "event__start_date"
    ordering = ["event", "player", ]
    search_fields = ("player__first_name", "player__last_name", )
    list_filter = (CurrentSeasonFilter, "is_net", )

    save_on_top = True

