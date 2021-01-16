from django.db import models
from django.db.models import UniqueConstraint


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
