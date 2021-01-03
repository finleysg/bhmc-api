from django.db import models
from django.db.models import DO_NOTHING

from register.models import Player


class BoardMember(models.Model):
    player = models.ForeignKey(verbose_name="Player", to=Player, on_delete=DO_NOTHING)
    role = models.CharField(verbose_name="Role", max_length=40)
    term_expires = models.IntegerField(verbose_name="Member thru")

    def __str__(self):
        return "{} {} ({})".format(self.player.first_name, self.player.last_name, self.role)
