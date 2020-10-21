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
CONTENT_CHOICES = (
    ("H", "Home"),
    ("DC", "Dam Cup"),
    ("MP", "Match Play"),
    ("CC", "Code of Conduct"),
)


class Announcement(models.Model):
    name = models.CharField(verbose_name="Name", max_length=100, blank=True)
    event = models.ForeignKey(verbose_name="Event", to=Event, blank=True, null=True, on_delete=DO_NOTHING)
    documents = models.ManyToManyField(verbose_name="Document(s)", to=Document, blank=True)
    text = models.TextField(verbose_name="Announcement text")
    starts = models.DateTimeField(verbose_name="Display start")
    expires = models.DateTimeField(verbose_name="Display expiration")
    visibility = models.CharField(verbose_name="Who should see the message?", max_length=1, choices=VISIBILITY_CHOICES,
                                  default="A")

    history = HistoricalRecords()

    @property
    def short_text(self):
        return "".join(self.text.split()[:20])

    def __str__(self):
        return self.short_text


class ContactMessage(models.Model):
    full_name = models.CharField(verbose_name="Full name", max_length=100)
    email = models.CharField(verbose_name="Email", max_length=254)
    message_text = models.TextField(verbose_name="Message text")
    message_date = models.DateTimeField(verbose_name="Message date", auto_now_add=True)


# class Contact(models.Model):
#     directors = models.TextField(verbose_name="Directors")
#     committees = models.TextField(verbose_name="Committees")
#     staff = models.TextField(verbose_name="Golf Course Staff")
#     president_name = models.CharField(verbose_name="Current President", max_length=100)
#     vice_president_name = models.CharField(verbose_name="Current Vice-President", max_length=100)
#     secretary_name = models.CharField(verbose_name="Current Secretary", max_length=100)
#     treasurer_name = models.CharField(verbose_name="Current Treasurer", max_length=100)
#     president_phone = models.CharField(verbose_name="President Phone", max_length=20, blank=True)
#     vice_president_phone = models.CharField(verbose_name="Vice-President Phone", max_length=20, blank=True)
#     secretary_phone = models.CharField(verbose_name="Secretary Phone", max_length=20, blank=True)
#     treasurer_phone = models.CharField(verbose_name="Treasurer Phone", max_length=20, blank=True)
#
#     history = HistoricalRecords()


class WebContent(models.Model):
    content_type = models.CharField(verbose_name="Type", choices=CONTENT_CHOICES, max_length=2)
    name = models.CharField(verbose_name="Name", max_length=120)
    content = models.TextField(verbose_name="Content")

    history = HistoricalRecords()

    def __str__(self):
        return self.name
