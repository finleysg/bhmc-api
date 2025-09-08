from django.db import models
from django.db.models import DO_NOTHING

from register.models import Player
from events.models import Event
from courses.models import Course, Hole

TRANSACTION_DIRECTION_CHOICES = (
    ("Inbound", "Inbound"),
    ("Outbound", "Outbound"),
)

SKIN_TYPE_CHOICES = (
    ("Gross", "Gross"),
    ("Net", "Net"),
)

PAYMENT_FREQUENCY_CHOICES = (
    ("Bi-Monthly", "Bi-Monthly"),
    ("Monthly", "Monthly"),
    ("Season End", "Season End"),
)

class SkinTransaction(models.Model):
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=DO_NOTHING)
    season = models.IntegerField(verbose_name="Season")
    transaction_type = models.CharField(verbose_name="Transaction Type", max_length=20)
    transaction_amount = models.DecimalField(verbose_name="Transaction Amount", max_digits=8, decimal_places=2)
    transaction_date = models.DateField(verbose_name="Transaction Date")
    transaction_timestamp = models.DateTimeField(verbose_name="Transaction Timestamp", auto_now_add=True)
    direction = models.CharField(verbose_name="Direction", max_length=8, choices=TRANSACTION_DIRECTION_CHOICES)

    class Meta:
        ordering = ['-transaction_date', '-transaction_timestamp']

    def __str__(self):
        return f"{self.player} - {self.transaction_type} ${self.transaction_amount} ({self.direction})"

class Skin(models.Model):
    event = models.ForeignKey(verbose_name="Event", to=Event, on_delete=DO_NOTHING)
    course = models.ForeignKey(verbose_name="Course", to=Course, on_delete=DO_NOTHING)
    hole = models.ForeignKey(verbose_name="Hole", to=Hole, on_delete=DO_NOTHING)
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=DO_NOTHING)
    skin_type = models.CharField(verbose_name="Skin Type", max_length=5, choices=SKIN_TYPE_CHOICES)
    skin_amount = models.DecimalField(verbose_name="Skin Amount", max_digits=8, decimal_places=2)
    is_team = models.BooleanField(verbose_name="Is Team", default=False)

    class Meta:
        ordering = ['-event__start_date', 'hole__hole_number']

    def __str__(self):
        return f"{self.event.name} - {self.player} - Hole {self.hole.hole_number} (${self.skin_amount})"

class SkinSettings(models.Model):
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=DO_NOTHING)
    payment_frequency = models.CharField(verbose_name="Payment Frequency", max_length=10, 
                                       choices=PAYMENT_FREQUENCY_CHOICES)

    class Meta:
        verbose_name_plural = "Skin Settings"

    def __str__(self):
        return f"{self.player} - {self.payment_frequency}"
