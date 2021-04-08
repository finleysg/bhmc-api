from django.db import models
from django.db.models import DO_NOTHING

from register.models import Player


class BoardMember(models.Model):
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=DO_NOTHING)
    role = models.CharField(verbose_name="Role", max_length=40)
    term_expires = models.IntegerField(verbose_name="Member thru")

    def __str__(self):
        return "{} {} ({})".format(self.player.first_name, self.player.last_name, self.role)


class MajorChampion(models.Model):
    season = models.IntegerField(verbose_name="Season")
    event_name = models.CharField(verbose_name="Event name", max_length=60)
    flight = models.CharField(verbose_name="Flight", max_length=30)
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=DO_NOTHING)
    score = models.CharField(verbose_name="Score", max_length=20)

    def __str__(self):
        return "{} {} - {}".format(self.season, self.event_name, self.player.last_name)


class LowScore(models.Model):
    season = models.IntegerField(verbose_name="Season")
    course_name = models.CharField(verbose_name="Course", max_length=40)
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=DO_NOTHING)
    score = models.CharField(verbose_name="Score", max_length=20)

    def __str__(self):
        return "{} {} - {}".format(self.season, self.course_name, self.player.last_name)


class Ace(models.Model):
    season = models.IntegerField(verbose_name="Season")
    hole_name = models.CharField(verbose_name="Hole", max_length=30)
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=DO_NOTHING)
    shot_date = models.DateField(verbose_name="Date", null=True)

    def __str__(self):
        return "{} {} - {}".format(self.season, self.hole_name, self.player.last_name)
