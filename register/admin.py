from datetime import datetime
import logging

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.forms import Form

from core.models import SeasonSettings
from events.models import Event
from register.decorators import action_form
# from register.payments import refund_payment
from .models import Registration, RegistrationSlot, Player

# config = SeasonSettings.objects.current_settings()
logger = logging.getLogger("register")


# class NoLeagueFilter(SimpleListFilter):
#     title = "events" if config is None else "{} events".format(config.year)
#     parameter_name = "event"
#
#     def lookups(self, request, model_admin):
#         year = datetime.today().year if config is None else config.year
#         events = set([c for c in Event.objects.filter(start_date__year=year).filter(requires_registration=True).exclude(event_type="L")])
#         return [(e.id, e.name) for e in events]
#
#     def queryset(self, request, queryset):
#         if self.value():
#             return queryset.filter(event__id__exact=self.value())
#         else:
#             return queryset


# class LeagueFilter(SimpleListFilter):
#     title = "events" if config is None else "{} events".format(config.year)
#     parameter_name = "event"
#
#     def lookups(self, request, model_admin):
#         year = datetime.today().year if config is None else config.year
#         events = set([c for c in Event.objects.filter(start_date__year=year).filter(event_type="L")])
#         return [(e.id, "{} ({})".format(e.name, e.start_date)) for e in events]
#
#     def queryset(self, request, queryset):
#         if self.value():
#             return queryset.filter(event__id__exact=self.value())
#         else:
#             return queryset


# class RequiresRegistrationFilter(SimpleListFilter):
#     title = "events" if config is None else "{} events".format(config.year)
#     parameter_name = "event_id"
#
#     def lookups(self, request, model_admin):
#         year = datetime.today().year if config is None else config.year
#         events = set([c for c in Event.objects.filter(start_date__year=year).filter(requires_registration=True)])
#         return [(e.id, "{} ({})".format(e.name, e.start_date)) for e in sorted(events, key=lambda event: event.start_date)]
#
#     def queryset(self, request, queryset):
#         if self.value():
#             return queryset.filter(event_id=self.value())
#         else:
#             return queryset


class RegistrationSlotInline(admin.TabularInline):
    model = RegistrationSlot
    can_delete = True
    extra = 0
    verbose_name_plural = "Signed up"
    fields = ["member", "is_event_fee_paid", "is_gross_skins_paid", "is_net_skins_paid", "is_greens_fee_paid",
              "is_cart_fee_paid", ]
    # raw_id_fields = ("member", )
    # autocomplete_lookup_fields = {
    #     "fk": ["member", ]
    # }


class PlayerAdmin(admin.ModelAdmin):
    model = Player
    can_delete = True
    save_on_top = True
    fields = ["email", "first_name", "last_name", "ghin", "tee", "birth_date", "profile_picture", "stripe_customer_id", ]
    list_display = ["email", "first_name", "last_name", "ghin", "tee", "birth_date", ]
    list_display_links = ("email", )
    ordering = ["last_name", "first_name", ]
    search_fields = ("first_name", "last_name", "email", )


class RegistrationAdmin(admin.ModelAdmin):
    model = Registration
    can_delete = True
    save_on_top = True

    fieldsets = (
        (None, {
            "fields": (("event", "signed_up_by", "user", ), )
        }),
        ("Notes", {
            "fields": ("notes", )
        })
    )
    # inlines = [RegistrationSlotInline, ]
    readonly_fields = ["created_date", ]

    list_display = ["id", "signed_up_by", "created_date", "event", "notes", ]
    list_display_links = ("id", )
    list_select_related = ("event", )
    date_hierarchy = "event__start_date"
    ordering = ["signed_up_by"]
    # search_fields = ["user__email"]
    # list_filter = (NoLeagueFilter, )
    # raw_id_fields = ("event", )
    # autocomplete_lookup_fields = {
    #     "fk": ["event", ]
    # }

    # def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
    #     if db_field.name == "event":
    #         kwargs["queryset"] = Event.objects.filter(start_date__year=config.year).filter(requires_registration=True).exclude(event_type="L")
    #     return super(RegistrationAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    # def get_changeform_initial_data(self, request):
    #     initial = super().get_changeform_initial_data(request)
    #     initial["signed_up_by"] = request.user.member.id
    #     if "_changelist_filters" in request.GET:
    #         filters = request.GET["_changelist_filters"]
    #         initial["event"] = filters.split("=")[1]
    #     return initial

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.event_id = instance.registration_group.event_id
            instance.status = "R"
            instance.save()
        formset.save_m2m()


class RegistrationSlotAdmin(admin.ModelAdmin):
    model = RegistrationSlot
    can_delete = True
    save_on_top = True

    fieldsets = (
        ("Event", {
            "fields": ("event", "registration", "hole", "starting_order", )
        }),
        ("Player", {
            "fields": ("Player", "status", )
        }),
    )
    list_display = ["id", "registration", "player", "hole", "starting_order", "status", ]
    list_display_links = ("id", )
    # list_filter = (LeagueFilter, )
    list_select_related = ("player", "hole", )
    date_hierarchy = "event__start_date"
    search_fields = ("player_first_name", "player__last_name")

    def get_form(self, request, obj=None, **kwargs):
        form = super(RegistrationSlotAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields["registration"].queryset = Registration.objects.filter(event__id=obj.event_id)
        return form


admin.site.register(Player, PlayerAdmin)
admin.site.register(Registration, RegistrationAdmin)
admin.site.register(RegistrationSlot, RegistrationSlotAdmin)


# class PostRefundForm(Form):
#     title = "Refund selected payments"
#     # payments = ModelChoiceField(queryset=OnlinePayment.objects.all())
#
#
# class OnlinePaymentAdmin(admin.ModelAdmin):
#     exclude = ("pkey", "event_id", "signed_up_by_id", "record_id")
#     readonly_fields = ["name", "event_type", "start_date", "first_name", "last_name",
#                        "payment_confirmation_code", "payment_confirmation_timestamp", "payment_amount",
#                        "record_type", "refund_code", "refund_timestamp", "refund_amount", "comment", "refunded_by", ]
#     list_display = ["name", "start_date", "first_name", "last_name", "payment_confirmation_code", "refund_code", ]
#     list_display_links = ["name", ]
#     list_filter = (RequiresRegistrationFilter, "refund_timestamp", )
#     ordering = ["start_date", "last_name", "first_name", ]
#     actions = ["process_refunds", ]
#
#     def has_add_permission(self, request, obj=None):
#         return False
#
#     def has_delete_permission(self, request, obj=None):
#         return False
#
#     def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
#         extra_context = extra_context or {}
#         extra_context["show_save_and_continue"] = False
#         extra_context["show_save"] = False
#         extra_context["title"] = "View Payment"
#         return super(OnlinePaymentAdmin, self).changeform_view(request, object_id, extra_context=extra_context)
#
#     # def get_actions(self, request):
#     #     actions = super(OnlinePaymentAdmin, self).get_actions(request)
#     #     del actions["delete_selected"]
#     #     return actions
#
#     @action_form(PostRefundForm)
#     def process_refunds(self, request, queryset, form):
#         payments = queryset.values_list("record_id", "record_type", "payment_confirmation_code", "payment_amount", "first_name", "last_name", )
#         success = 0
#         failure = 0
#         for payment in payments:
#             if payment[2].startswith("ch_"):
#                 try:
#                     # 0 or None amount == full refund
#                     refund_payment(payment[0], payment[1], payment[2], 0, request.user.member, "bulk refund")
#                     success += 1
#                 except Exception as e:
#                     logger.exception(e)
#                     failure += 1
#
#         return "{} failures, {} ".format(failure, success)  # "objects updated"
#
#
# admin.site.register(OnlinePayment, OnlinePaymentAdmin)
