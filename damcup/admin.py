from django.contrib import admin

from damcup import models
from register.admin import CurrentSeasonFilter


@admin.register(models.DamCup)
class DamCupAdmin(admin.ModelAdmin):
    fields = ["season", "good_guys", "bad_guys", "site", ]
    list_display = ["season", "good_guys", "bad_guys", "site", ]
    save_on_top = True


@admin.register(models.DamCup)
class SeasonLongPointsAdmin(admin.ModelAdmin):
    fields = ["event", "player", "gross_points", "net_points", ]
    list_display = ["event", "player", "gross_points", "net_points", ]
    date_hierarchy = "event__start_date"
    ordering = ["event", "gross_points", "net_points", ]
    search_fields = ("player__first_name", "player__last_name", )
    list_filter = (CurrentSeasonFilter, )

    save_on_top = True

