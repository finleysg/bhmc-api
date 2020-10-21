from django.db import models
from simple_history.models import HistoricalRecords

POLICY_TYPE_CHOICES = (
    ("P", "Policy or Procedure"),
    ("R", "Local Rule"),
    ("S", "Scoring and Handicap"),
    ("N", "New Member Information"),
    ("A", "About Us"),
    ("F", "Payment FAQs")
)


class Policy(models.Model):
    policy_type = models.CharField(verbose_name="Type", choices=POLICY_TYPE_CHOICES, max_length=1, default="P")
    title = models.CharField(verbose_name="Title", max_length=120)
    description = models.TextField(verbose_name="Description")

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Policies"

    def __str__(self):
        return self.title
