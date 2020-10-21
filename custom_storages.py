from django.conf import settings

from CustomS3Boto3Storage import CustomS3Boto3Storage


class StaticStorage(CustomS3Boto3Storage):
    location = settings.STATICFILES_LOCATION


class MediaStorage(CustomS3Boto3Storage):
    location = settings.MEDIAFILES_LOCATION
