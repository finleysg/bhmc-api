from django.contrib import admin

from payments import models
from register.admin import CurrentSeasonFilter
from register.models import RegistrationFee


class PaymentDetailInline(admin.TabularInline):
    model = RegistrationFee
    can_delete = False
    extra = 0
    show_change_link = True
    verbose_name_plural = "Payment details"
    fields = ["registration_slot", "event_fee", ]
    readonly_fields = ["registration_slot", "event_fee", ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):

    fieldsets = (
        (None, {
            "fields": ("event", "user", "payment_amount", "transaction_fee", )
        }),
        (None, {
            "fields": ("payment_code", "confirmed", )
        }),
    )
    list_display = ["payment_code", "event", "user", "payment_amount", "transaction_fee", "payment_date", "confirmed", ]
    list_display_links = ("payment_code", )
    list_filter = (CurrentSeasonFilter, "confirmed", "payment_date", )
    date_hierarchy = "event__start_date"
    search_fields = ("payment_code", "player__last_name", "player__email")
    inlines = [PaymentDetailInline, ]
    can_delete = False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.id == 1:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.id == 1:
            return True
        return False


@admin.register(models.Refund)
class RefundAdmin(admin.ModelAdmin):

    fields = ["issuer", "refund_amount", "refund_code", "confirmed", "notes", ]
    readonly_fields = ["refund_date", ]
    list_display = ["refund_code", "payment", "issuer", "refund_amount", "refund_date", "confirmed", ]
    list_display_links = ("refund_code", )
    list_filter = (CurrentSeasonFilter, )
    search_fields = ("refund_code", )
    can_delete = False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.id == 1:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        return False
