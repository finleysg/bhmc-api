import os
import requests

from django.core.files.storage import default_storage
from django.db.models import FileField
from io import BytesIO
from openpyxl.reader.excel import load_workbook
from xlrd import open_workbook

from bhmc import settings
from bhmc.settings import is_development


def open_xls_workbook(document):
    if is_development:
        file_name = os.path.join(settings.MEDIA_ROOT, document.file.name)
        return open_workbook(file_name)
    else:
        file_bytes = requests.get(document.file.url).content
        return open_workbook(file_contents=file_bytes)


def open_xlsx_workbook(document):
    if is_development:
        file_name = os.path.join(settings.MEDIA_ROOT, document.file.name)
        return load_workbook(filename=str(file_name), read_only=True)
    else:
        file_bytes = requests.get(document.file.url).content
        return load_workbook(filename=BytesIO(file_bytes), read_only=True)


def file_cleanup(sender, **kwargs):
    """
    File cleanup callback used to emulate the old delete
    behavior using signals. Initially django deleted linked
    files when an object containing a File/ImageField was deleted.
    """
    for fieldname in sender._meta.get_all_field_names():
        try:
            field = sender._meta.get_field(fieldname)
        except:
            field = None

        if field and isinstance(field, FileField):
            inst = kwargs["instance"]
            f = getattr(inst, fieldname)
            m = inst.__class__._default_manager
            if (
                    hasattr(f, "path")
                    and os.path.exists(f.path)
                    and not m.filter(
                **{"%s__exact" % fieldname: getattr(inst, fieldname)}
            ).exclude(pk=inst._get_pk_val())
            ):
                try:
                    default_storage.delete(f.path)
                except:
                    pass
