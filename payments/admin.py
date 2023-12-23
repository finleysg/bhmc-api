from django.contrib import admin

from payments import models
from payments.models import Refund
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


class RefundInline(admin.TabularInline):
    model = Refund
    can_delete = False
    extra = 0
    show_change_link = True
    verbose_name_plural = "Refund details"
    fields = ["refund_code", "issuer", "refund_amount", "refund_date", "confirmed", ]
    readonly_fields = ["refund_code", "issuer", "refund_amount", "refund_date", "confirmed", ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):

    fieldsets = (
        (None, {
            "fields": ("event", "user", "payment_amount", "transaction_fee", "payment_date", )
        }),
        (None, {
            "fields": ("payment_code", "confirmed", "confirm_date", )
        }),
    )
    readonly_fields = ("payment_date", "confirm_date", )
    list_display = ["payment_code", "event", "user", "payment_amount", "transaction_fee", "payment_date", "confirmed", "confirm_date" ]
    list_display_links = ("payment_code", )
    list_filter = (CurrentSeasonFilter, "confirmed", "payment_date", )
    date_hierarchy = "event__start_date"
    search_fields = ("payment_code", "player__last_name", "player__email")
    inlines = [PaymentDetailInline, RefundInline, ]
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
