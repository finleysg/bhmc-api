from django.db import models
from django.db.models import CASCADE, UniqueConstraint

from courses.managers import CourseManager


class Course(models.Model):
    name = models.CharField(max_length=100, unique=True)
    number_of_holes = models.IntegerField(default=18)

    objects = CourseManager()

    def __str__(self):
        return self.name


class Hole(models.Model):
    course = models.ForeignKey(Course, related_name='holes', on_delete=CASCADE)
    hole_number = models.IntegerField(default=0)
    par = models.IntegerField(default=0)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["course", "hole_number"], name="unique_course_holenumber")
        ]

    def __str__(self):
        return "{} Hole {}".format(self.course.name, self.hole_number)
