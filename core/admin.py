from django.contrib import admin

from core.models import BoardMember, MajorChampion, LowScore, Ace, SeasonSettings


class BoardMemberAdmin(admin.ModelAdmin):
    fields = ["player", "role", "term_expires", ]
    list_display = ["player", "role", "term_expires", ]


class MajorChampionAdmin(admin.ModelAdmin):
    fields = ["season", "event", "event_name", "flight", "player", "team_id", "score", "is_net", ]
    list_display = ["season", "event_name", "flight", "player", "team_id", "score", "is_net", ]
    list_filter = ("season", "event_name")


class LowScoreAdmin(admin.ModelAdmin):
    fields = ["season", "course_name", "player", "score", "is_net", ]
    list_display = ["season", "course_name", "player", "score", "is_net", ]
    list_filter = ("season", )


class AceAdmin(admin.ModelAdmin):
    fields = ["season", "hole_name", "player", "shot_date", ]
    list_display = ["season", "hole_name", "player", "shot_date", ]
    list_filter = ("season", )


# class SeasonSettingsAdmin(admin.ModelAdmin):
#     fields = ["season", "member_event", "match_play_event", "is_active", ]
#     list_display = ["season", "member_event", "match_play_event", "is_active", ]
#     list_filter = ("season", )


admin.site.register(BoardMember, BoardMemberAdmin)
admin.site.register(MajorChampion, MajorChampionAdmin)
admin.site.register(LowScore, LowScoreAdmin)
admin.site.register(Ace, AceAdmin)
# admin.site.register(SeasonSettings, SeasonSettingsAdmin)
