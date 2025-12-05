from django.db import models
from django.db.models import UniqueConstraint, CASCADE

from events.models import Event
from register.models import Player


class DamCup(models.Model):
    season = models.IntegerField(verbose_name="Season", )
    good_guys = models.DecimalField(verbose_name="Good Guys", max_digits=3, decimal_places=1)
    bad_guys = models.DecimalField(verbose_name="Bad Guys", max_digits=3, decimal_places=1)
    site = models.CharField(verbose_name="Site", max_length=30)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["season"], name="unique_season")
        ]

    def __str__(self):
        return "{} dam cup results".format(self.season)


class SeasonLongPoints(models.Model):
    event = models.ForeignKey(verbose_name="Event", to=Event, on_delete=CASCADE)
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=CASCADE)
    gross_points = models.IntegerField(verbose_name="Gross Points", default=0)
    net_points = models.IntegerField(verbose_name="Net Points", default=0)
    additional_info = models.CharField(verbose_name="Additional Info", null=True, blank=True, max_length=30)

    class Meta:
        verbose_name = "Season Long Points"
        verbose_name_plural = "Season Long Points"
        constraints = [
            UniqueConstraint(fields=["event", "player", ], name="unique_slp")
        ]

    def __str__(self):
        """
        Provide a human-readable representation of the SeasonLongPoints instance.
        
        Returns:
            str: Formatted string '<event>: <player> points' where <event> and <player> are the related Event and Player representations.
        """
        return "{}: {} points".format(self.event, self.player)