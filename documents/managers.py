from django.db import models
from django.db.models.aggregates import Count
from random import randint, sample


class DocumentManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related('tags')


class PhotoManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related('tags')

    def random(self, tag, take):
        if tag is None:
            # profile pics have a year = 0 -- exclude those
            count = self.exclude(year=0).aggregate(count=Count("id"))["count"]
            total = take if take <= count else count
            indices = sample(range(count), total)
            images = self.exclude(year=0)
        else:
            count = self.filter(tags__tag__name__icontains=tag).aggregate(count=Count("id"))["count"]
            total = take if take <= count else count
            indices = sample(range(count), total)
            images = self.filter(tags__tag__name__icontains=tag)

        return [images[i] for i in indices]
