from django.db import models
from django.db.models import DO_NOTHING
from simple_history.models import HistoricalRecords
from events.models import Event
from documents.models import Document

VISIBILITY_CHOICES = (
    ("M", "Members Only"),
    ("N", "Non-members Only"),
    ("A", "All"),
)


class Announcement(models.Model):
    title = models.CharField(verbose_name="Title", max_length=200)
    event = models.ForeignKey(verbose_name="Event", to=Event, blank=True, null=True, on_delete=DO_NOTHING)
    documents = models.ManyToManyField(verbose_name="Document(s)", to=Document, blank=True)
    text = models.TextField(verbose_name="Announcement text")
    starts = models.DateTimeField(verbose_name="Display start")
    expires = models.DateTimeField(verbose_name="Display expiration")
    visibility = models.CharField(verbose_name="Who should see the message?", max_length=1, choices=VISIBILITY_CHOICES,
                                  default="A")

    history = HistoricalRecords()

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    full_name = models.CharField(verbose_name="Full name", max_length=100)
    email = models.CharField(verbose_name="Email", max_length=254)
    message_text = models.TextField(verbose_name="Message text")
    message_date = models.DateTimeField(verbose_name="Message date", auto_now_add=True)
