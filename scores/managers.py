from django.db import models
from django.db.models import Prefetch


class EventScoreCardManager(models.Manager):
    def get_queryset(self):
        from scores.models import EventScore
        return (
            super().get_queryset().prefetch_related(
                Prefetch("scores", queryset=EventScore.objects.order_by("hole__hole_number"))
            )
        )
