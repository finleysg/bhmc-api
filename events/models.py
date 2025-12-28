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
    ("Non-Members", "Non-Members"),
    ("None", "None"),
)
EVENT_TYPE_CHOICES = (
    ("N", "Weeknight Event"),
    ("W", "Weekend Major"),
    ("M", "Meeting"),
    ("O", "Other"),
    ("E", "External Event"),
    ("R", "Season Registration"),
    ("D", "Deadline"),
    ("P", "Open Event"),
    ("S", "Season Long Match Play"),
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
    ("R", "Returning Member"),
    ("N", "None"),
)
AGE_RESTRICTION_CHOICES = (
    ("O", "Over"),
    ("U", "Under"),
    ("N", "None"),
)
PAYOUT_TYPE_CHOICES = (
    ("Cash", "Cash"),
    ("Credit", "Credit"),
    ("Passthru", "Passthru"),
    ("None", "None"),
)
PAYOUT_CHOICES = (("Individual", "Individual"), ("Team", "Team"))
PAYOUT_STATUS_CHOICES = (
    ("Pending", "Pending"),
    ("Confirmed", "Confirmed"),
    ("Paid", "Paid"),
)
TOURNAMENT_FORMAT_CHOICES = (
    ("Skins", "Skins"),
    ("Stroke", "Stroke"),
    ("Team", "Team"),
    ("Quota", "Quota"),
    ("UserScored", "UserScored"),
    ("Other", "Other"),
)

class Event(models.Model):
    event_type = models.CharField(
        verbose_name="Event type", choices=EVENT_TYPE_CHOICES, max_length=1, default="N"
    )
    name = models.CharField(verbose_name="Event title", max_length=100)
    rounds = models.IntegerField(verbose_name="Number of rounds", blank=True, null=True)
    registration_type = models.CharField(
        verbose_name="Registration type",
        max_length=1,
        default="M",
        choices=REGISTRATION_CHOICES,
    )
    skins_type = models.CharField(
        verbose_name="Skins type",
        max_length=1,
        choices=SKIN_TYPE_CHOICES,
        blank=True,
        null=True,
    )
    minimum_signup_group_size = models.IntegerField(
        verbose_name="Minimum sign-up group size", blank=True, null=True
    )
    maximum_signup_group_size = models.IntegerField(
        verbose_name="Maximum sign-up group size", blank=True, null=True
    )
    group_size = models.IntegerField(verbose_name="Group size", blank=True, null=True)
    total_groups = models.IntegerField(
        verbose_name="Groups per course (tee times)", blank=True, null=True
    )
    start_type = models.CharField(
        verbose_name="Start type",
        choices=START_TYPE_CHOICES,
        max_length=2,
        blank=True,
        null=True,
    )
    can_choose = models.BooleanField(
        verbose_name="Player can choose starting hole or tee time", default=False
    )
    ghin_required = models.BooleanField(verbose_name="GHIN required", default=False)
    season_points = models.IntegerField(
        verbose_name="Season long points available", blank=True, null=True
    )
    notes = models.TextField(blank=True, null=True)
    start_date = models.DateField(verbose_name="Start date")
    start_time = models.CharField(
        verbose_name="Starting time", max_length=40, blank=True, null=True
    )
    priority_signup_start = models.DateTimeField(
        verbose_name="Priority signup start", blank=True, null=True
    )
    signup_start = models.DateTimeField(
        verbose_name="Signup start", blank=True, null=True
    )
    signup_end = models.DateTimeField(verbose_name="Signup end", blank=True, null=True)
    payments_end = models.DateTimeField(
        verbose_name="Online payments deadline", blank=True, null=True
    )
    registration_maximum = models.IntegerField(
        verbose_name="Signup maximum", blank=True, null=True
    )
    portal_url = models.CharField(
        verbose_name="Golf Genius Portal", max_length=240, blank=True, null=True
    )
    courses = models.ManyToManyField(verbose_name="Course(s)", to=Course, blank=True)
    external_url = models.CharField(
        verbose_name="External url", max_length=255, blank=True, null=True
    )
    status = models.CharField(
        verbose_name="Status", max_length=1, choices=EVENT_STATUS_CHOICES, default="S"
    )
    season = models.IntegerField(verbose_name="Season", default=0)
    tee_time_splits = models.CharField(
        verbose_name="Tee time splits", max_length=10, blank=True, null=True
    )
    default_tag = models.ForeignKey(
        verbose_name="Default tag", to=Tag, on_delete=DO_NOTHING, blank=True, null=True
    )
    starter_time_interval = models.IntegerField(
        verbose_name="Starter time interval", default=0
    )
    team_size = models.IntegerField(verbose_name="Team size", default=1)
    age_restriction = models.IntegerField(
        verbose_name="Age restriction", blank=True, null=True
    )
    age_restriction_type = models.CharField(
        verbose_name="Age restriction type",
        max_length=1,
        choices=AGE_RESTRICTION_CHOICES,
        default="N",
    )
    gg_id = models.CharField(
        verbose_name="Golf Genius id: event_id", max_length=22, blank=True, null=True
    )
    signup_waves = models.IntegerField(
        verbose_name="Signup waves", blank=True, null=True
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["name", "start_date"], name="unique_name_startdate"
            )
        ]

    history = HistoricalRecords()
    objects = EventManager()

    def __str__(self):
        return "{} {}".format(self.start_date, self.name)

    @property
    def registration_window(self):
        """
        Determine the current registration window state for the event.
        
        The result is a string representing one of the possible registration states:
        - "n/a": registration is not applicable (registration_type == "N").
        - "past": registration window has passed.
        - "priority": the current time is between priority_signup_start and signup_start.
        - "registration": the current time is between signup_start and signup_end.
        - "future": signup_start is in the future and no priority window applies.
        - "pending": signup_start is in the future while the code previously considered the window "past" (used as a transitional state).
        
        Returns:
            str: One of "n/a", "past", "priority", "registration", "future", or "pending".
        """
        state = "n/a"
        if self.registration_type != "N":
            state = "past"
            right_now = timezone.now()
            if (
                self.priority_signup_start is not None
                and self.priority_signup_start < right_now < self.signup_start
            ):
                state = "priority"
            elif self.signup_start < right_now < self.signup_end:
                state = "registration"
            elif self.signup_start > right_now:
                state = "future"
            elif state == "past" and self.signup_start > right_now:
                state = "pending"

        return state

    def validate_registration_window(self):
        """
        Validate that signup start and end dates are present and ordered for events that require registration.
        
        Raises:
            ValidationError: if registration_type is not "N" and either `signup_start` or `signup_end` is missing, or if `signup_start` is later than `signup_end`.
        """
        if self.registration_type != "N":
            if self.signup_start is None or self.signup_end is None:
                raise ValidationError(
                    "When an event requires registration, both signup start and signup end are "
                    "required"
                )
            if self.signup_start > self.signup_end:
                raise ValidationError(
                    "The signup start must be earlier than signup end"
                )

    def validate_groups_size(self):
        """
        Ensure a group size is set when players may choose their starting hole or tee time.
        
        Raises:
            ValidationError: If `can_choose` is true and `group_size` is None or zero.
        """
        if self.can_choose and (self.group_size is None or self.group_size == 0):
            raise ValidationError(
                "A group size is required if players are choosing their starting hole or tee time"
            )

    def validate_signup_size(self):
        """
        Validate that both minimum and maximum signup group sizes are set when the event allows registration.
        
        Raises:
            ValidationError: if either `minimum_signup_group_size` or `maximum_signup_group_size` is None or zero while `registration_type` is not "N".
        """
        if self.registration_type != "N":
            if (
                self.minimum_signup_group_size is None
                or self.minimum_signup_group_size == 0
            ):
                raise ValidationError(
                    "You must have a minimum and maximum signup group size when an event "
                    "includes registration"
                )
            if (
                self.maximum_signup_group_size is None
                or self.maximum_signup_group_size == 0
            ):
                raise ValidationError(
                    "You must have a minimum and maximum signup group size when an event "
                    "includes registration"
                )

    def validate_total_groups(self):
        """
        Ensure `total_groups` is set when players can choose tee times and start type is "TT".
        
        Raises:
            ValidationError: If `can_choose` is true, `start_type` equals "TT", and `total_groups` is None or zero.
        """
        if self.can_choose and self.start_type == "TT":
            if self.total_groups is None or self.total_groups == 0:
                raise ValidationError(
                    "You must include the number of groups per course when players are choosing "
                    "their own tee times"
                )

    def clean(self):
        """
        Ensure the event's configuration satisfies all business validation rules.
        
        Calls the model's validation helpers to check group size requirements, signup size constraints, total-groups requirements when group selection is enabled, and the registration window timing.
        
        Raises:
        	django.core.exceptions.ValidationError: If any validation rule is violated.
        """
        self.validate_groups_size()
        self.validate_signup_size()
        self.validate_total_groups()
        self.validate_registration_window()

    @staticmethod
    def autocomplete_search_fields():
        """
        Provide field lookups used for autocomplete searches.
        
        Returns:
            tuple: Lookup strings for Django ORM filters; e.g., ("name__icontains",) to perform case-insensitive containment matches on the `name` field.
        """
        return ("name__icontains",)


class FeeType(models.Model):
    name = models.CharField(verbose_name="Fee Name", max_length=30, unique=True)
    code = models.CharField(verbose_name="Fee Code", max_length=3, default="X")
    payout = models.CharField(
        verbose_name="Payout Type", 
        max_length=12, 
        default="Credit", 
        choices=PAYOUT_TYPE_CHOICES)
    restriction = models.CharField(
        verbose_name="Restrict to",
        max_length=20,
        choices=FEE_RESTRICTION_CHOICES,
        default="None",
    )

    def __str__(self):
        """
        Return the model's human-readable name.
        
        Returns:
            str: The instance's `name` value.
        """
        return self.name


class EventFeeOverride(models.Model):
    amount = models.DecimalField(verbose_name="Amount", max_digits=5, decimal_places=2)
    restriction = models.CharField(
        verbose_name="Restrict to",
        max_length=20,
        choices=FEE_RESTRICTION_CHOICES,
        default="Members",
    )

    def __str__(self):
        """
        Provide a human-readable label for the fee override combining its restriction and amount.
        
        Returns:
            str: The representation in the format "<restriction> ($<amount>)".
        """
        return "{} (${})".format(self.restriction, self.amount)


class EventFee(models.Model):
    event = models.ForeignKey(
        verbose_name="Event", to=Event, on_delete=CASCADE, related_name="fees"
    )
    fee_type = models.ForeignKey(
        verbose_name="Fee Type", to=FeeType, on_delete=DO_NOTHING
    )
    amount = models.DecimalField(verbose_name="Amount", max_digits=5, decimal_places=2)
    override_amount = models.DecimalField(
        verbose_name="Override Amount",
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
    )
    override_restriction = models.CharField(
        verbose_name="Override Restriction",
        max_length=20,
        choices=FEE_RESTRICTION_CHOICES,
        blank=True,
        null=True,
    )
    is_required = models.BooleanField(verbose_name="Required", default=False)
    display_order = models.IntegerField(verbose_name="Display Order")

    class Meta:
        constraints = [
            UniqueConstraint(fields=["event", "fee_type"], name="unique_event_feetype")
        ]
        ordering = [
            "display_order",
        ]

    objects = EventFeeManager()

    def __str__(self):
        """
        Human-readable representation of the event fee combining fee type and amount.
        
        Returns:
            str: A string in the format "<fee_type> ($<amount>)".
        """
        return "{} (${})".format(self.fee_type, self.amount)


class Round(models.Model):
    event = models.ForeignKey(
        verbose_name="Event", to=Event, on_delete=CASCADE, related_name="gg_rounds"
    )
    round_number = models.IntegerField(verbose_name="Round number")
    round_date = models.DateField(verbose_name="Round date")
    gg_id = models.CharField(verbose_name="Golf Genius id: round_id", max_length=22)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["event", "round_number"], name="unique_event_roundnumber"
            )
        ]

    def __str__(self):
        """
        Return a human-readable label for the round combining the parent event's name and the round number.
        
        Returns:
            str: String in the format "<event name> - Round <round_number>".
        """
        return "{} - Round {}".format(self.event.name, self.round_number)


class Tournament(models.Model):
    event = models.ForeignKey(
        verbose_name="Event", to=Event, on_delete=CASCADE, related_name="gg_tournaments"
    )
    round = models.ForeignKey(
        verbose_name="Round", to=Round, on_delete=CASCADE, related_name="gg_rounds"
    )
    name = models.CharField(verbose_name="Tournament name", max_length=120)
    format = models.CharField(
        verbose_name="Format", max_length=20, choices=TOURNAMENT_FORMAT_CHOICES
    )
    is_net = models.BooleanField(verbose_name="Is Net", default=False)
    gg_id = models.CharField(
        verbose_name="Golf Genius id: tournament_id", max_length=22
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["event", "name"], name="unique_event_tournamentname"
            )
        ]

    def __str__(self):
        """
        Return a human-readable representation combining the parent event name and this tournament's name.
        
        @returns A string in the format "<event name> - <tournament name>".
        """
        return "{} - {}".format(self.event.name, self.name)


class TournamentResult(models.Model):
    tournament = models.ForeignKey(
        verbose_name="Tournament",
        to=Tournament,
        on_delete=CASCADE,
        related_name="tournament_results",
    )
    flight = models.CharField(
        verbose_name="Flight", max_length=20, blank=True, null=True
    )
    player = models.ForeignKey(
        verbose_name="Player",
        to="register.Player",
        on_delete=CASCADE,
        related_name="tournament_results",
    )
    team_id = models.CharField(
        verbose_name="Team id", max_length=22, blank=True, null=True
    )
    position = models.IntegerField(verbose_name="Position")
    score = models.IntegerField(verbose_name="Score", blank=True, null=True)
    amount = models.DecimalField(
        verbose_name="Amount won", max_digits=6, decimal_places=2
    )
    payout_type = models.CharField(
        verbose_name="Payout Type",
        max_length=10,
        blank=True,
        null=True,
        choices=PAYOUT_TYPE_CHOICES,
    )
    payout_to = models.CharField(
        verbose_name="Payout To",
        max_length=10,
        blank=True,
        null=True,
        choices=PAYOUT_CHOICES,
    )
    payout_status = models.CharField(
        verbose_name="Payout Status",
        max_length=10,
        blank=True,
        null=True,
        choices=PAYOUT_STATUS_CHOICES,
    )
    payout_date = models.DateTimeField(
        verbose_name="Date and Time Paid", blank=True, null=True
    )
    create_date = models.DateTimeField(
        verbose_name="Date Created", blank=True, null=True, auto_now_add=True
    )
    summary = models.CharField(
        verbose_name="Summary", max_length=120, blank=True, null=True
    )
    details = models.CharField(
        verbose_name="Details", max_length=120, blank=True, null=True
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["tournament", "player"], name="unique_tournament_player"
            )
        ]
        ordering = ["tournament", "flight", "position"]

    def __str__(self):
        """
        Provide a human-readable representation of this tournament result.
        
        Returns:
            str: A string formatted as "<tournament name> - <player name> (<position>)".
        """
        return "{} - {} ({})".format(
            self.tournament.name, self.player.player_name, self.position
        )


class TournamentPoints(models.Model):
    tournament = models.ForeignKey(
        verbose_name="Tournament",
        to=Tournament,
        on_delete=CASCADE,
        related_name="season_long_points",
    )
    player = models.ForeignKey(
        verbose_name="Player",
        to="register.Player",
        on_delete=CASCADE,
        related_name="season_long_points",
    )
    position = models.IntegerField(verbose_name="Position", default=999)
    score = models.IntegerField(verbose_name="Score", blank=True, null=True)
    points = models.IntegerField(verbose_name="Points", default=0)
    details = models.CharField(verbose_name="Details", max_length=120, blank=True, null=True)
    create_date = models.DateTimeField(verbose_name="Date Created", auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["tournament", "player"], name="unique_points"
            )
        ]

    def __str__(self):
        """
        Represent the TournamentPoints record as "TournamentName - PlayerName (points)".
        
        Returns:
            str: Formatted string containing the tournament name, player name, and points.
        """
        return "{} - {} ({})".format(
            self.tournament.name, self.player.player_name, self.points
        )
