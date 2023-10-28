import pytz
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CASCADE, DO_NOTHING, UniqueConstraint
from simple_history.models import HistoricalRecords
from django.utils import timezone

from content.models import Tag
from courses.models import Course
from events.managers import EventManager, EventFeeManager

FEE_RESTRICTION_CHOICES = (
    ("Members", "Members"),
    ("Returning Members", "Returning Members"),
    ("New Members", "New Members"),
    ("Seniors", "Seniors"),
    ("Non-Seniors", "Non-Seniors"),
    ("None", "None"),
)
EVENT_TYPE_CHOICES = (
    ("N", "Weeknight Event"),
    ("W", "Weekend Major"),
    ("H", "Holiday Pro-shop Event"),
    ("M", "Meeting"),
    ("O", "Other"),
    ("E", "External Event"),
    ("R", "Season Registration"),
    ("D", "Deadline"),
    ("P", "Open Event"),
)
START_TYPE_CHOICES = (
    ("TT", "Tee Times"),
    ("SG", "Shotgun"),
    ("NA", "Not Applicable"),
)
SKIN_TYPE_CHOICES = (
    ("I", "Individual"),
    ("T", "Team"),
    ("N", "No Skins"),
)
EVENT_STATUS_CHOICES = (
    ("C", "Canceled"),
    ("S", "Scheduled"),
    ("T", "Tentative"),
)
REGISTRATION_CHOICES = (
    ("M", "Member"),
    ("G", "Member Guest"),
    ("O", "Open"),
    ("N", "None"),
)


class Event(models.Model):
    event_type = models.CharField(verbose_name="Event type", choices=EVENT_TYPE_CHOICES, max_length=1, default="N")
    name = models.CharField(verbose_name="Event title", max_length=100)
    rounds = models.IntegerField(verbose_name="Number of rounds", blank=True, null=True)
    registration_type = models.CharField(verbose_name="Registration type", max_length=1, default="M",
                                         choices=REGISTRATION_CHOICES)
    skins_type = models.CharField(verbose_name="Skins type", max_length=1, choices=SKIN_TYPE_CHOICES,
                                  blank=True, null=True)
    minimum_signup_group_size = models.IntegerField(verbose_name="Minimum sign-up group size", blank=True, null=True)
    maximum_signup_group_size = models.IntegerField(verbose_name="Maximum sign-up group size", blank=True, null=True)
    group_size = models.IntegerField(verbose_name="Group size", blank=True, null=True)
    total_groups = models.IntegerField(verbose_name="Groups per course (tee times)", blank=True, null=True)
    start_type = models.CharField(verbose_name="Start type", choices=START_TYPE_CHOICES, max_length=2,
                                  blank=True, null=True)
    can_choose = models.BooleanField(verbose_name="Player can choose starting hole or tee time", default=False)
    ghin_required = models.BooleanField(verbose_name="GHIN required", default=False)
    season_points = models.IntegerField(verbose_name="Season long points available", blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    start_date = models.DateField(verbose_name="Start date")
    start_time = models.CharField(verbose_name="Starting time", max_length=40, blank=True, null=True)
    signup_start = models.DateTimeField(verbose_name="Signup start", blank=True, null=True)
    signup_end = models.DateTimeField(verbose_name="Signup end", blank=True, null=True)
    payments_end = models.DateTimeField(verbose_name="Online payments deadline", blank=True, null=True)
    registration_maximum = models.IntegerField(verbose_name="Signup maximum", blank=True, null=True)
    portal_url = models.CharField(verbose_name="Golf Genius Portal", max_length=240, blank=True, null=True)
    courses = models.ManyToManyField(verbose_name="Course(s)", to=Course, blank=True)
    external_url = models.CharField(verbose_name="External url", max_length=255, blank=True, null=True)
    status = models.CharField(verbose_name="Status", max_length=1, choices=EVENT_STATUS_CHOICES, default="S")
    season = models.IntegerField(verbose_name="Season", default=0)
    tee_time_splits = models.CharField(verbose_name="Tee time splits", max_length=10, blank=True, null=True)
    default_tag = models.ForeignKey(verbose_name="Default tag", to=Tag, on_delete=DO_NOTHING, blank=True, null=True)
    starter_time_interval = models.IntegerField(verbose_name="Starter time interval", default=0)
    team_size = models.IntegerField(verbose_name="Team size", default=1)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["name", "start_date"], name="unique_name_startdate")
        ]

    history = HistoricalRecords()
    objects = EventManager()

    def __str__(self):
        return "{} {}".format(self.start_date, self.name)

    @property
    def registration_window(self):
        state = "n/a"
        if self.registration_type != "N":
            state = "past"
            right_now = timezone.now()
            # aware_start = pytz.utc.localize(datetime.combine(self.start_date, time=datetime.min.time()))
            # signup_start = pytz.utc.normalize(self.signup_start)
            # signup_end = pytz.utc.normalize(self.signup_end)

            if self.signup_start < right_now < self.signup_end:
                state = "registration"
            elif self.signup_start > right_now:
                state = "future"
            elif state == "past" and self.signup_start > right_now:
                state = "pending"

        return state

    def validate_registration_window(self):
        if self.registration_type != "N":
            if self.signup_start is None or self.signup_end is None:
                raise ValidationError('When an event requires registration, both signup start and signup end are '
                                      'required')
            if self.signup_start > self.signup_end:
                raise ValidationError('The signup start must be earlier than signup end')

    # def validate_courses(self):
    #     if self.can_choose and not self.courses.exists():
    #         raise ValidationError('At least one course is required if players are choosing their starting hole or '
    #                               'tee time')

    def validate_groups_size(self):
        if self.can_choose and (self.group_size is None or self.group_size == 0):
            raise ValidationError('A group size is required if players are choosing their starting hole or tee time')

    def validate_signup_size(self):
        if self.registration_type != "N":
            if self.minimum_signup_group_size is None or self.minimum_signup_group_size == 0:
                raise ValidationError('You must have a minimum and maximum signup group size when an event '
                                      'includes registration')
            if self.maximum_signup_group_size is None or self.maximum_signup_group_size == 0:
                raise ValidationError('You must have a minimum and maximum signup group size when an event '
                                      'includes registration')

    def validate_total_groups(self):
        if self.can_choose and self.start_type == "TT":
            if self.total_groups is None or self.total_groups == 0:
                raise ValidationError('You must include the number of groups per course when players are choosing '
                                      'their own tee times')

    def clean(self):
        # self.validate_courses()
        self.validate_groups_size()
        self.validate_signup_size()
        self.validate_total_groups()
        self.validate_registration_window()

    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     if self.can_choose and self.registration_window == "future":
    #         self.registrations.remove_slots_for_event(self)
    #         self.registrations.create_slots_for_event(self)

    @staticmethod
    def autocomplete_search_fields():
        return ("name__icontains", )


class FeeType(models.Model):
    name = models.CharField(verbose_name="Fee Name", max_length=30, unique=True)
    code = models.CharField(verbose_name="Fee Code", max_length=3, default="X")
    restriction = models.CharField(verbose_name="Restrict to", max_length=20, choices=FEE_RESTRICTION_CHOICES,
                                   default="None")

    def __str__(self):
        return self.name


class EventFee(models.Model):
    event = models.ForeignKey(verbose_name="Event", to=Event, on_delete=CASCADE, related_name="fees")
    fee_type = models.ForeignKey(verbose_name="Fee Type", to=FeeType, on_delete=DO_NOTHING)
    amount = models.DecimalField(verbose_name="Amount", max_digits=5, decimal_places=2)
    is_required = models.BooleanField(verbose_name="Required", default=False)
    display_order = models.IntegerField(verbose_name="Display Order")

    class Meta:
        constraints = [
            UniqueConstraint(fields=["event", "fee_type"], name="unique_event_feetype")
        ]
        ordering = ["display_order", ]

    objects = EventFeeManager()

    def __str__(self):
        return "{} (${})".format(self.fee_type, self.amount)
