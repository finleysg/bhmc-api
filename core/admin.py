from django.contrib import admin

from core.models import BoardMember


class BoardMemberAdmin(admin.ModelAdmin):
    fields = ["player", "role", "term_expires", ]
    list_display = ["player", "role", "term_expires", ]


admin.site.register(BoardMember, BoardMemberAdmin)
