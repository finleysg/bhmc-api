from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.db.models import DO_NOTHING, SET_NULL, CASCADE, UniqueConstraint
from simple_history.models import HistoricalRecords

from documents.models import Photo
from events.models import Event, EventFee
from courses.models import Course, Hole
from payments.models import Payment
from .managers import RegistrationSlotManager, RegistrationManager

STATUS_CHOICES = (
    ("A", "Available"),
    ("P", "Pending"),
    ("X", "Payment Processing"),
    ("R", "Reserved"),
    ("U", "Unavailable")
)

User.__str__ = lambda user: user.get_full_name()


class Player(models.Model):
    first_name = models.CharField(verbose_name="First name", max_length=30)
    last_name = models.CharField(verbose_name="Last name", max_length=30)
    email = models.CharField(verbose_name="Email", unique=True, max_length=200)
    phone_number = models.CharField(verbose_name="Phone number", max_length=20, blank=True, null=True)
    ghin = models.CharField(verbose_name="GHIN", max_length=8, unique=True, blank=True, null=True)
    tee = models.CharField(verbose_name="Tee", max_length=8, default="Club")
    birth_date = models.DateField(verbose_name="Birth date", blank=True, null=True)
    save_last_card = models.BooleanField(verbose_name="Save Last Card Used", default=True)
    stripe_customer_id = models.CharField(verbose_name="Stripe ID", max_length=40, blank=True, null=True)
    profile_picture = models.ForeignKey(verbose_name="Profile picture", to=Photo, null=True, blank=True,
                                        on_delete=CASCADE)
    favorites = models.ManyToManyField("self", blank=True)
    is_member = models.BooleanField(verbose_name="Is Member", default=False)
    last_season = models.IntegerField(verbose_name="Most Recent Membership Season", null=True, blank=True)
    gg_id = models.CharField(verbose_name="Golf Genius id: member_card_id", max_length=22, blank=True, null=True)
    user = models.ForeignKey(verbose_name="User record", to=User, null=True, blank=True, on_delete=DO_NOTHING)

    history = HistoricalRecords()

    class Meta:
        ordering = ('last_name', 'first_name')
        base_manager_name = 'objects'

    def player_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    def age(self):
        my_age = 0
        if self.birth_date:
            my_age = (datetime.utcnow() - self.birth_date).total_years()
        return my_age

    def __str__(self):
        return self.player_name()

    @staticmethod
    def autocomplete_search_fields():
        return ["user__last_name__icontains", "user__first_name__icontains", ]


class Registration(models.Model):
    event = models.ForeignKey(verbose_name="Event", to=Event, on_delete=CASCADE)
    course = models.ForeignKey(verbose_name="Course", to=Course, null=True, blank=True, on_delete=DO_NOTHING)
    user = models.ForeignKey(verbose_name="User", to=User, null=True, blank=True, on_delete=DO_NOTHING)
    signed_up_by = models.CharField(verbose_name="Signed up by", max_length=40, null=True, blank=True)
    expires = models.DateTimeField(verbose_name="Expiration", null=True, blank=True)
    notes = models.TextField(verbose_name="Registration notes", blank=True, null=True)
    created_date = models.DateTimeField(verbose_name="Created date", auto_now_add=True)
    gg_id = models.CharField(verbose_name="Golf Genius id: group_id from the teesheet", max_length=22, blank=True,
                             null=True)

    objects = RegistrationManager()

    @property
    def players(self):
        return self.slots.values_list('player', flat=True)

    def __str__(self):
        return "{} registration: {}".format(self.event.name, self.signed_up_by)


class RegistrationSlot(models.Model):
    event = models.ForeignKey(verbose_name="Event", to=Event, related_name="registrations", on_delete=CASCADE)
    hole = models.ForeignKey(verbose_name="Hole", to=Hole, null=True, blank=True, on_delete=DO_NOTHING)
    registration = models.ForeignKey(verbose_name="Registration", to=Registration, blank=True, null=True,
                                     on_delete=SET_NULL, related_name="slots")
    player = models.ForeignKey(verbose_name="Player", to=Player, blank=True, null=True, on_delete=DO_NOTHING)
    starting_order = models.IntegerField(verbose_name="Starting order", default=0)
    slot = models.IntegerField(verbose_name="Slot number", default=0)
    status = models.CharField(verbose_name="Status", choices=STATUS_CHOICES, max_length=1, default="A")
    gg_id = models.CharField(verbose_name="Golf Genius id: member_id specific to this event", max_length=22, blank=True,
                             null=True)

    class Meta:
        ordering = ("hole", "slot")
        constraints = [
            UniqueConstraint(fields=["event", "player"], name="unique_player_registration")
        ]

    objects = RegistrationSlotManager()

    def __str__(self):
        return "{} - {} ({})".format(self.player, self.status, self.registration)


class PlayerHandicap(models.Model):
    player = models.ForeignKey(verbose_name="Player", to=Player, blank=True, null=True, on_delete=CASCADE)
    season = models.IntegerField(verbose_name="Season")
    handicap = models.DecimalField(verbose_name="Year End Index", max_digits=4, decimal_places=1)

    class Meta:
        ordering = ("season", "handicap")
        constraints = [
            UniqueConstraint(fields=["player", "season"], name="unique_player_season_index")
        ]

    def __str__(self):
        return "{} - {} ({})".format(self.season, self.player, self.handicap)


class RegistrationFee(models.Model):
    event_fee = models.ForeignKey(verbose_name="Event Fee", to=EventFee, on_delete=CASCADE)
    registration_slot = models.ForeignKey(verbose_name="Registration Slot", to=RegistrationSlot, on_delete=CASCADE,
                                          blank=True, null=True, related_name="fees")
    is_paid = models.BooleanField(verbose_name="Is Paid", default=False)
    amount = models.DecimalField(verbose_name="Amount Paid", max_digits=5, decimal_places=2, default=0)
    payment = models.ForeignKey(verbose_name="Payment", to=Payment, blank=True,
                                on_delete=CASCADE, related_name="payment_details")

    def __str__(self):
        return "{} - {}".format(self.registration_slot, self.event_fee)
