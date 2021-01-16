from django.contrib import admin

from damcup import models


@admin.register(models.DamCup)
class DamCupAdmin(admin.ModelAdmin):
    fields = ["season", "good_guys", "bad_guys", "site", ]
    list_display = ["season", "good_guys", "bad_guys", "site", ]
    save_on_top = True
