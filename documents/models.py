from django.db import models
from django.db.models import DO_NOTHING, CASCADE
from imagekit import ImageSpec, register
from imagekit.models import ImageSpecField
from pilkit.processors import ResizeToFit
from simple_history.models import HistoricalRecords

from documents.managers import PhotoManager, DocumentManager
from events.models import Event


def document_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/documents/year/<filename>
    return "documents/{0}/{1}".format(instance.year, filename)


def photo_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/documents/year/<filename>
    return "photos/{0}/{1}".format(instance.year, filename)


class ThumbnailSpec(ImageSpec):
    format = 'JPEG'
    options = {'quality': 80}
    processors = [ResizeToFit(288, 288)]


class WebSpec(ImageSpec):
    format = 'JPEG'
    options = {'quality': 80}
    processors = [ResizeToFit(1200, 1200)]


register.generator("documents:photo:thumbnail_image", ThumbnailSpec)
register.generator("documents:photo:web_image", WebSpec)


class Tag(models.Model):

    class Meta:
        ordering = ["name", ]

    name = models.CharField(verbose_name="Tag", max_length=40)

    def __str__(self):
        return self.name


class Document(models.Model):
    year = models.IntegerField(verbose_name="Golf Season", blank=True, null=True)
    title = models.CharField(verbose_name="Title", max_length=120)
    event = models.ForeignKey(verbose_name="Event", to=Event, null=True, blank=True, on_delete=DO_NOTHING,
                              related_name="documents")
    file = models.FileField(verbose_name="File", upload_to=document_directory_path)
    created_by = models.CharField(verbose_name="Created By", max_length=100)
    last_update = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()
    objects = DocumentManager()

    def __str__(self):
        return "{}: {}".format(self.year, self.title)


class DocumentTag(models.Model):
    document = models.ForeignKey(verbose_name="Document", to=Document, on_delete=CASCADE, related_name="tags")
    tag = models.ForeignKey(verbose_name="Tag", to=Tag, on_delete=CASCADE)


class Photo(models.Model):
    year = models.IntegerField(verbose_name="Golf Season", default=0)
    player_id = models.IntegerField(verbose_name="Player Id", null=True, blank=True)
    caption = models.CharField(verbose_name="Caption", max_length=240, null=True, blank=True)
    raw_image = models.ImageField(verbose_name="Image", upload_to=photo_directory_path)
    thumbnail_image = ImageSpecField(source="raw_image", id="documents:photo:thumbnail_image")
    web_image = ImageSpecField(source="raw_image", id="documents:photo:web_image")
    created_by = models.CharField(verbose_name="Created By", max_length=100)
    last_update = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()
    objects = PhotoManager()

    def __str__(self):
        return "{}: {}".format(self.year, self.caption)


class PhotoTag(models.Model):
    document = models.ForeignKey(verbose_name="Photo", to=Photo, on_delete=CASCADE, related_name="tags")
    tag = models.ForeignKey(verbose_name="Tag", to=Tag, on_delete=CASCADE)
