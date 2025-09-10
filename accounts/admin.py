from django.contrib import admin
from .models import SkinTransaction, Skin, SkinSettings

class SkinTransactionAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Transaction Details", {
            "fields": ("player", "season", "transaction_type", "transaction_amount", "direction")
        }),
        ("Date Information", {
            "fields": ("transaction_date",)
        }),
    )
    
    list_display = ["player", "season", "transaction_type", "transaction_amount", 
                   "transaction_date", "direction"]
    list_display_links = ("transaction_type",)
    list_filter = ("season", "direction", "transaction_type", "player")
    date_hierarchy = "transaction_date"
    ordering = ["-transaction_date", "-transaction_timestamp"]
    search_fields = ["player__first_name", "player__last_name", "transaction_type"]
    readonly_fields = ["transaction_timestamp"]

class SkinAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Skin Details", {
            "fields": ("event", "course", "hole", "player", "skin_type", "skin_amount", "is_team", "details")
        }),
    )
    
    list_display = ["event", "player", "hole", "skin_type", "skin_amount", "is_team"]
    list_display_links = ("event",)
    list_filter = ("event__season", "skin_type", "is_team", "player", "event")
    date_hierarchy = "event__start_date"
    ordering = ["-event__start_date", "hole__hole_number"]
    search_fields = ["player__first_name", "player__last_name", "event__name"]

class SkinSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Settings", {
            "fields": ("player", "payment_frequency")
        }),
    )
    
    list_display = ["player", "payment_frequency"]
    list_display_links = ("player",)
    list_filter = ("payment_frequency", "player")
    ordering = ["player__last_name", "player__first_name"]
    search_fields = ["player__first_name", "player__last_name"]

admin.site.register(SkinTransaction, SkinTransactionAdmin)
admin.site.register(Skin, SkinAdmin)
admin.site.register(SkinSettings, SkinSettingsAdmin)
