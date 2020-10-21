from django.db import models


class SettingsManager(models.Manager):

    def current_settings(self):
        try:
            return self.latest("year")
        except self.model.DoesNotExist:
            return None
