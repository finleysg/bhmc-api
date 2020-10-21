from django.db import models
from django.db.models import DO_NOTHING
from django.conf import settings

from core.manager import SettingsManager
from events.models import Event


class SeasonSettings(models.Model):
    year = models.IntegerField(verbose_name="Current golf season")
    reg_event = models.ForeignKey(verbose_name="Registration event", to=Event, related_name="season_registration",
                                  on_delete=DO_NOTHING)
    match_play_event = models.ForeignKey(verbose_name="Match play event", to=Event, related_name="match_play",
                                         blank=True, null=True, on_delete=DO_NOTHING)
    accept_new_members = models.BooleanField(verbose_name="Accepting new member registration?", default=False)

    @property
    def admin_url(self):
        return settings.ADMIN_URL

    @property
    def raven_dsn(self):
        return settings.RAVEN_DSN

    @property
    def stripe_pk(self):
        return settings.STRIPE_PUBLIC_KEY

    objects = SettingsManager()
