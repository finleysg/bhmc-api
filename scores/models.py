from django.db import models
from django.db.models import UniqueConstraint, CASCADE

from courses.models import Hole, Course, Tee
from events.models import Event
from register.models import Player


class EventScore(models.Model):
    event = models.ForeignKey(verbose_name="Event", to=Event, on_delete=CASCADE)
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=CASCADE)
    course = models.ForeignKey(verbose_name="Course", to=Course, null=True, blank=True, on_delete=CASCADE)
    tee = models.ForeignKey(verbose_name="Tee", to=Tee, null=True, blank=True, on_delete=CASCADE)
    hole = models.ForeignKey(verbose_name="Hole", to=Hole, on_delete=CASCADE)
    score = models.IntegerField(verbose_name="Score")
    is_net = models.BooleanField(verbose_name="Is Net?", default=False)

    class Meta:
        verbose_name = "Event Scores"
        verbose_name_plural = "Event Scores"
        constraints = [
            UniqueConstraint(fields=["event", "player", "hole", "is_net"], name="unique_event_score")
        ]

    def __str__(self):
        return "{}: {} {} {} {}".format(self.event, self.player, self.hole, self.score, "net" if self.is_net else "gross")
