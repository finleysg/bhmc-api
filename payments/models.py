from django.contrib.auth.models import User
from django.db import models
from django.db.models import DO_NOTHING, CASCADE

from events.models import Event
from payments.managers import RefundManager, PaymentManager

NOTIFICATION_CHOICES = (
    ("A", "Admin"),
    ("N", "New Member"),
    ("R", "Returning Member"),
    ("C", "Signup Confirmation"),
    ("M", "Match Play"),
    ("U", "Update Registration"),
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
    payment_date = models.DateTimeField(verbose_name="Payment date", auto_now_add=True, null=True)
    confirm_date = models.DateTimeField(verbose_name="Confirm date", blank=True, null=True)

    objects = PaymentManager()

    def __str__(self):
        return "Payment {} ({})".format(self.payment_code, self.user.last_name)


class Refund(models.Model):
    payment = models.ForeignKey(verbose_name="Payment", to=Payment, related_name="refunds", on_delete=CASCADE)
    refund_code = models.CharField(verbose_name="Refund code", max_length=40, unique=True)
    refund_amount = models.DecimalField(verbose_name="Refund amount", max_digits=5, decimal_places=2, default=0.0)
    issuer = models.ForeignKey(verbose_name="Issuer", to=User, on_delete=DO_NOTHING)
    notes = models.TextField(verbose_name="Notes", blank=True, null=True)
    confirmed = models.BooleanField(verbose_name="Confirmed", default=False)
    refund_date = models.DateTimeField(verbose_name="Refund date", auto_now_add=True, null=True)

    objects = RefundManager()

    def __str__(self):
        return "Refund id {} ({})".format(self.refund_code, "Confirmed" if self.confirmed else "Not Confirmed")
