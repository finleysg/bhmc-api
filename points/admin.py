from django.contrib import admin

from points import models


@admin.register(models.PlayerPoints)
class PlayerPointsAdmin(admin.ModelAdmin):
    fields = ["event", "player", "group", "points1", "points2", ]
    list_display = ["event", "player", "group", "points1", "points2", ]
    date_hierarchy = "event__start_date"
    list_filter = ("group", )
    save_on_top = True
