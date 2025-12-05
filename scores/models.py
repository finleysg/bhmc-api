from django.db import models
from django.db.models import UniqueConstraint, CASCADE, DO_NOTHING

from courses.models import Hole, Course, Tee
from events.models import Event
from register.models import Player


class EventScoreCard(models.Model):
    event = models.ForeignKey(verbose_name="Event", to=Event, on_delete=CASCADE)
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=DO_NOTHING)
    course = models.ForeignKey(verbose_name="Course", to=Course, null=True, blank=True, on_delete=DO_NOTHING)
    tee = models.ForeignKey(verbose_name="Tee", to=Tee, null=True, blank=True, on_delete=DO_NOTHING)
    handicap_index = models.DecimalField(verbose_name="Handicap Index", max_digits=4, decimal_places=2, blank=True, null=True)
    course_handicap = models.IntegerField(verbose_name="Course Handicap", default=0)

    class Meta:
        verbose_name = "Event Scorecard"
        verbose_name_plural = "Event Scorecards"
        constraints = [
            UniqueConstraint(fields=["event", "player"], name="unique_event_scorecard")
        ]

    def __str__(self):
        """
        Provide a human-readable representation of the scorecard combining its event and player.
        
        Returns:
            str: A string in the format "<event>: <player>" where `event` and `player` are the related objects' string representations.
        """
        return "{}: {}".format(self.event, self.player)


class EventScore(models.Model):
    scorecard = models.ForeignKey(verbose_name="Scorecard", to=EventScoreCard, on_delete=CASCADE, null=True, blank=True)
    event = models.ForeignKey(verbose_name="Event", to=Event, on_delete=CASCADE, null=True, blank=True)
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=CASCADE, null=True, blank=True)
    course = models.ForeignKey(verbose_name="Course", to=Course, null=True, blank=True, on_delete=CASCADE)
    tee = models.ForeignKey(verbose_name="Tee", to=Tee, null=True, blank=True, on_delete=CASCADE)
    hole = models.ForeignKey(verbose_name="Hole", to=Hole, on_delete=CASCADE)
    score = models.IntegerField(verbose_name="Score")
    is_net = models.BooleanField(verbose_name="Is Net?", default=False)

    class Meta:
        verbose_name = "Event Score"
        verbose_name_plural = "Event Scores"
        constraints = [
            UniqueConstraint(fields=["event", "player", "hole", "is_net"], name="unique_event_score")
        ]

    def __str__(self):
        return "{}: {} {} {} {}".format(self.event, self.player, self.hole, self.score, "net" if self.is_net else "gross")