from django.contrib import admin
from policies.models import Policy


class PolicyAdmin(admin.ModelAdmin):
    fields = ['policy_type', 'title', 'description', ]
    list_display = ['title', 'policy_type', ]
    list_filter = ('policy_type', )
    save_on_top = True


admin.site.register(Policy, PolicyAdmin)
