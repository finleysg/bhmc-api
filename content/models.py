from django.db import models
from simple_history.models import HistoricalRecords


class PageContent(models.Model):
    key = models.CharField(verbose_name="Key", max_length=20)
    title = models.CharField(verbose_name="Title", max_length=120, blank=True, null=True)
    content = models.TextField(verbose_name="Content")

    history = HistoricalRecords()

    def __str__(self):
        return self.title


class Tag(models.Model):

    class Meta:
        ordering = ["name", ]

    name = models.CharField(verbose_name="Tag", max_length=40)

    def __str__(self):
        return self.name
