from django.contrib import admin

from core.models import SeasonSettings


class SettingsAdmin(admin.ModelAdmin):
    fields = ['year', 'reg_event', 'match_play_event', 'accept_new_members', ]
    list_display = ['year', ]
    can_delete = False


admin.site.register(SeasonSettings, SettingsAdmin)
