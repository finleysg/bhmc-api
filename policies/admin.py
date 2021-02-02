from django.contrib import admin
from django.db import models
from pagedown.widgets import AdminPagedownWidget

from policies.models import Policy


class PolicyAdmin(admin.ModelAdmin):
    fields = ['policy_type', 'title', 'description', ]
    list_display = ['title', 'policy_type', ]
    list_filter = ('policy_type',)
    save_on_top = True
    formfield_overrides = {
        models.TextField: {'widget': AdminPagedownWidget},
    }


admin.site.register(Policy, PolicyAdmin)
