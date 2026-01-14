from django.db import models


class EventScoreCardManager(models.Manager):
    def get_queryset(self):
        return (
            super().get_queryset().prefetch_related("scores").prefetch_related("course").prefetch_related("tee")
        )
