import structlog

from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from core.util import current_season
from events.models import Event
from .models import Registration, RegistrationSlot, Player, RegistrationFee, PlayerHandicap

logger = structlog.getLogger(__name__)


class CurrentSeasonFilter(SimpleListFilter):
    season = current_season()
    title = "{} events".format(season)
    parameter_name = "event"

    def lookups(self, request, model_admin):
        year = current_season()
        events = set([event for event in Event.objects.filter(season=year).exclude(registration_type="N")])
        return [(e.id, e.name) for e in events]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(event__id__exact=self.value())
        else:
            return queryset


class RegistrationFeeInline(admin.TabularInline):
    model = RegistrationFee
    extra = 0
    show_change_link = False
    verbose_name_plural = "Registration fees"
    fields = ["event_fee", "amount", "is_paid", ]
    readonly_fields = ["event_fee", ]

    def has_add_permission(self, request, obj=None):
        return False


class RegistrationSlotInline(admin.TabularInline):
    model = RegistrationSlot
    can_delete = True
    extra = 0
    show_change_link = True
    verbose_name_plural = "Registration details (slots)"
    fields = ["player", "hole", "starting_order", "slot", "status", ]


class PlayerHandicapInline(admin.TabularInline):
    model = PlayerHandicap
    can_delete = True
    extra = 0
    show_change_link = True
    verbose_name_plural = "Year End Handicap Index"
    fields = ["season", "handicap", ]


class PlayerAdmin(admin.ModelAdmin):
    model = Player
    can_delete = True
    save_on_top = True
    fields = ["email", "first_name", "last_name", "ghin", "tee", "birth_date", "profile_picture", "stripe_customer_id",
              "is_member", "last_season", ]
    inlines = [PlayerHandicapInline, ]
    list_display = ["email", "first_name", "last_name", "ghin", "tee", "birth_date", "is_member", ]
    list_display_links = ("email", )
    list_filter = ("is_member", "last_season",)

    ordering = ["last_name", "first_name", ]
    search_fields = ("first_name", "last_name", "email", )


class RegistrationAdmin(admin.ModelAdmin):
    model = Registration
    save_on_top = True

    fieldsets = (
        (None, {
            "fields": (("event", "course", ), )
        }),
        (None, {
            "fields": (("user", "signed_up_by", "created_date", "expires", ), )
        }),
        ("Notes", {
            "fields": ("notes", )
        })
    )

    inlines = [RegistrationSlotInline, ]
    readonly_fields = ["created_date", "expires", ]

    list_display = ["id", "event", "created_date", "user", "signed_up_by", "notes", ]
    list_display_links = ("id", )
    list_select_related = ("event", )
    date_hierarchy = "event__start_date"
    ordering = ["event", "created_date", ]
    search_fields = ("signed_up_by", "user__email", "user__first_name", "user__last_name", )
    list_filter = (CurrentSeasonFilter, )

    def has_delete_permission(self, request, obj=None):
        if request.user.id == 1:
            return True
        return False

    # def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
    #     if db_field.name == "event":
    #         kwargs["queryset"] = Event.objects.filter(start_date__year=settings.CURRENT_SEASON)\
    #             .exclude(registration_type="N")\
    #             .exclude(event_type="N")
    #     return super(RegistrationAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial["signed_up_by"] = request.user.get_full_name()
        if "_changelist_filters" in request.GET:
            filters = request.GET["_changelist_filters"]
            initial["event"] = filters.split("=")[1]
        return initial

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.event_id = instance.registration.event_id
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
            "fields": ("player", "status", )
        }),
    )
    list_display = ["id", "registration", "player", "hole", "starting_order", "status", ]
    list_display_links = ("id", )
    list_filter = (CurrentSeasonFilter, )
    list_select_related = ("player", "hole", )
    date_hierarchy = "event__start_date"
    search_fields = ("player__first_name", "player__last_name", "player__email")
    inlines = [RegistrationFeeInline, ]
    ordering = ["id", ]

    def get_form(self, request, obj=None, **kwargs):
        form = super(RegistrationSlotAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields["registration"].queryset = Registration.objects.filter(event__id=obj.event_id)
        return form


class RegistrationFeeAdmin(admin.ModelAdmin):

    model = RegistrationFee
    show_change_link = False
    verbose_name_plural = "Registration fees"
    fields = ["registration_slot", "event_fee", "payment", "amount", "is_paid", ]
    readonly_fields = ["registration_slot", "event_fee", "payment", ]


admin.site.register(Player, PlayerAdmin)
admin.site.register(Registration, RegistrationAdmin)
admin.site.register(RegistrationSlot, RegistrationSlotAdmin)
