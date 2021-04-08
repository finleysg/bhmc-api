from django.contrib import admin

from core.models import BoardMember, MajorChampion, LowScore, Ace


class BoardMemberAdmin(admin.ModelAdmin):
    fields = ["player", "role", "term_expires", ]
    list_display = ["player", "role", "term_expires", ]


class MajorChampionAdmin(admin.ModelAdmin):
    fields = ["season", "event_name", "flight", "player", "score", ]
    list_display = ["season", "event_name", "flight", "player", "score", ]
    list_filter = ("season", )


class LowScoreAdmin(admin.ModelAdmin):
    fields = ["season", "course_name", "player", "score", ]
    list_display = ["season", "course_name", "player", "score", ]
    list_filter = ("season", )


class AceAdmin(admin.ModelAdmin):
    fields = ["season", "hole_name", "player", "shot_date", ]
    list_display = ["season", "hole_name", "player", "shot_date", ]
    list_filter = ("season", )


admin.site.register(BoardMember, BoardMemberAdmin)
admin.site.register(MajorChampion, MajorChampionAdmin)
admin.site.register(LowScore, LowScoreAdmin)
admin.site.register(Ace, AceAdmin)
