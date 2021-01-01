from django.contrib import admin
from .models import PageContent


class PageContentAdmin(admin.ModelAdmin):
    fields = ['key', 'title', 'content', ]
    list_display = ['key', 'title', ]
    list_filter = ('key', )
    save_on_top = True


admin.site.register(PageContent, PageContentAdmin)
