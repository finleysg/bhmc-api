from django.conf import settings
from storages.backends.s3 import S3StaticStorage


class StaticStorage(S3StaticStorage):
    location = settings.STATICFILES_LOCATION


class MediaStorage(S3StaticStorage):
    location = settings.MEDIAFILES_LOCATION
