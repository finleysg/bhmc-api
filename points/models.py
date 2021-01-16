from django.db import models
from django.db.models import DO_NOTHING, CASCADE, UniqueConstraint

from events.models import Event
from register.models import Player


class PlayerPoints(models.Model):
    event = models.ForeignKey(verbose_name="Event", to=Event, on_delete=CASCADE, related_name="points")
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=DO_NOTHING)
    group = models.CharField(verbose_name="Course or Flight", max_length=30)
    points1 = models.DecimalField(verbose_name="Gross Points", max_digits=5, decimal_places=2)
    points2 = models.DecimalField(verbose_name="Net Points", max_digits=5, decimal_places=2)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["event", "player"], name="unique_event_player")
        ]

    def __str__(self):
        return "{} (${}) {}".format(self.player, self.event.name, self.group)
