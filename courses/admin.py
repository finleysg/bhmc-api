from django.contrib import admin
from courses.models import Course, Hole


class HoleInline(admin.TabularInline):
    model = Hole
    can_delete = True
    extra = 0
    fields = ["hole_number", "par", ]


class CourseAdmin(admin.ModelAdmin):
    fields = ["name", "number_of_holes", ]
    list_display = ["name", "number_of_holes", ]
    save_on_top = True
    inlines = [HoleInline, ]


admin.site.register(Course, CourseAdmin)
