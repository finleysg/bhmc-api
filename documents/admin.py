from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Document, Tag, DocumentTag, PhotoTag, Photo, StaticDocument


class PhotoTagInline(admin.TabularInline):
    model = PhotoTag
    can_delete = True
    extra = 0


class DocumentAdmin(admin.ModelAdmin):
    fields = ["year", "event", "title", "document_type", "file", "created_by", "last_update", ]
    readonly_fields = ("created_by", "last_update",)
    exclude = ("tags",)
    list_display = ["year", "title", "event", "document_type", "last_update", ]
    list_filter = ("year", "document_type", )
    save_on_top = True

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.save()


class PhotoAdmin(admin.ModelAdmin):
    fields = ["year", "caption", "raw_image", "created_by", "last_update", ]
    readonly_fields = ("image_preview", "created_by", "last_update",)
    inlines = [PhotoTagInline, ]
    list_display = ["year", "caption", "image_preview", "created_by", "last_update", ]
    list_filter = ("year",)
    save_on_top = True

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.save()

    def image_preview(self, obj):
        return mark_safe('<img src="{url}" width="200" />'.format(url=obj.raw_image.url))


class StaticDocumentAdmin(admin.ModelAdmin):
    fields = ["code", "document", ]
    list_display = ["code", "document", ]
    save_on_top = True


admin.site.register(Document, DocumentAdmin)
admin.site.register(Photo, PhotoAdmin)
admin.site.register(StaticDocument, StaticDocumentAdmin)
