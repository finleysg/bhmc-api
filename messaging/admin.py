from django.contrib import admin
from django.db import models
from pagedown.widgets import AdminPagedownWidget

from .models import Announcement, ContactMessage


class AnnouncementAdmin(admin.ModelAdmin):
    fields = ["title", "text", "starts", "expires", "visibility", "event", "documents", ]
    list_display = ["starts", "expires", "title", ]
    list_filter = ("starts", )
    save_on_top = True
    formfield_overrides = {
        models.TextField: {'widget': AdminPagedownWidget},
    }


admin.site.register(Announcement, AnnouncementAdmin)


class ContactMessageAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            "fields": ("full_name", "email", )
        }),
        ("Message", {
            "fields": ("message_text", )
        }),
    )
    list_display = ["full_name", "message_date", ]
    list_filter = ("message_date", )
    save_on_top = True


admin.site.register(ContactMessage, ContactMessageAdmin)
