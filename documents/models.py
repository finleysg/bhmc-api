from django.db import models
from django.db.models import DO_NOTHING, CASCADE
from imagekit import ImageSpec, register
from imagekit.models import ImageSpecField
from pilkit.processors import ResizeToFit

from content.models import Tag
from documents.managers import PhotoManager, DocumentManager
from events.models import Event

DOCUMENT_TYPE_CHOICES = (
    ("R", "Event Results"),
    ("T", "Event Tee Times"),
    ("P", "Season Long Points"),
    ("D", "Dam Cup"),
    ("M", "Match Play"),
    ("F", "Financial Statements"),
    ("S", "Sign Up"),
    ("O", "Other"),
    ("Z", "Data"),
)


def document_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/documents/year/<filename>
    return "documents/{0}/{1}".format(instance.year, filename)


def photo_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/documents/year/<filename>
    return "photos/{0}/{1}".format(instance.year, filename)


class MobileSpec(ImageSpec):
    format = 'JPEG'
    options = {'quality': 80}
    processors = [ResizeToFit(600, 600)]


class WebSpec(ImageSpec):
    format = 'JPEG'
    options = {'quality': 90}
    processors = [ResizeToFit(1200, 1200, upscale=False)]


register.generator("documents:photo:mobile_image", MobileSpec)
register.generator("documents:photo:web_image", WebSpec)


class Document(models.Model):
    document_type = models.CharField(verbose_name="Type", choices=DOCUMENT_TYPE_CHOICES, max_length=1, default="R")
    year = models.IntegerField(verbose_name="Golf Season", blank=True, null=True)
    title = models.CharField(verbose_name="Title", max_length=120)
    event = models.ForeignKey(verbose_name="Event", to=Event, null=True, blank=True, on_delete=DO_NOTHING,
                              related_name="documents")
    file = models.FileField(verbose_name="File", upload_to=document_directory_path)
    created_by = models.CharField(verbose_name="Created By", max_length=100)
    last_update = models.DateTimeField(auto_now=True)

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
    mobile_image = ImageSpecField(source="raw_image", id="documents:photo:mobile_image")
    web_image = ImageSpecField(source="raw_image", id="documents:photo:web_image")
    created_by = models.CharField(verbose_name="Created By", max_length=100)
    last_update = models.DateTimeField(auto_now=True)

    objects = PhotoManager()

    def __str__(self):
        return "{}: {}".format(self.year, self.caption)


class PhotoTag(models.Model):
    document = models.ForeignKey(verbose_name="Photo", to=Photo, on_delete=CASCADE, related_name="tags")
    tag = models.ForeignKey(verbose_name="Tag", to=Tag, on_delete=CASCADE)


class StaticDocument(models.Model):
    code = models.CharField(verbose_name="Code", max_length=6, unique=True)
    document = models.ForeignKey(verbose_name="Document", to=Document, on_delete=CASCADE)

    def __str__(self):
        return "{}: {}".format(self.code, self.document)
