from django.contrib import admin

from core.models import SeasonSettings, BoardMember


class SettingsAdmin(admin.ModelAdmin):
    fields = ['year', 'reg_event', 'match_play_event', 'accept_new_members', ]
    list_display = ['year', ]
    can_delete = False


class BoardMemberAdmin(admin.ModelAdmin):
    fields = ["player", "role", "term_expires", ]
    list_display = ["player", "role", "term_expires", ]


admin.site.register(SeasonSettings, SettingsAdmin)
admin.site.register(BoardMember, BoardMemberAdmin)
