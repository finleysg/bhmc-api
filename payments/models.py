from django.contrib.auth.models import User
from django.db import models
from django.db.models import DO_NOTHING

from events.models import Event

NOTIFICATION_CHOICES = (
    ("N", "New Member"),
    ("R", "Returning Member"),
    ("C", "Signup Confirmation"),
    ("M", "Match Play"),
    ("O", "General Online Payment"),
)


class Payment(models.Model):
    payment_code = models.CharField(verbose_name="Payment code", max_length=40)
    payment_key = models.CharField(verbose_name="Secret key", max_length=100, blank=True, null=True)
    payment_amount = models.DecimalField(verbose_name="Payment amount", max_digits=5, decimal_places=2, default=0.0)
    transaction_fee = models.DecimalField(verbose_name="Payment fees", max_digits=4, decimal_places=2, default=0.0)
    event = models.ForeignKey(verbose_name="Event", to=Event, related_name="payments", on_delete=DO_NOTHING)
    user = models.ForeignKey(verbose_name="User", to=User, on_delete=DO_NOTHING)
    notification_type = models.CharField(verbose_name="Notification type", max_length=1, choices=NOTIFICATION_CHOICES,
                                         blank=True, null=True)
    confirmed = models.BooleanField(verbose_name="Confirmed", default=False)
