from django.db import models
from django.db.models.aggregates import Count
from random import randint


class DocumentManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related('tags')


class PhotoManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related('tags')

    def random(self):
        count = self.aggregate(count=Count("id"))["count"]
        random_index = randint(0, count - 1)
        return self[random_index]
