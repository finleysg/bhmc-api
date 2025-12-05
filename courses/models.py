from django.db import models
from django.db.models import CASCADE, UniqueConstraint

from courses.managers import CourseManager


class Course(models.Model):
    name = models.CharField(max_length=100, unique=True)
    number_of_holes = models.IntegerField(default=18)
    gg_id = models.CharField(verbose_name="Golf Genius id: course_id", max_length=22, blank=True, null=True)

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
        """
        Provide a human-readable label combining the course name and hole number.
        
        Returns:
            A string in the format "<course name> Hole <hole_number>".
        """
        return "{} Hole {}".format(self.course.name, self.hole_number)


class Tee(models.Model):
    course = models.ForeignKey(Course, related_name='tees', on_delete=CASCADE)
    name = models.CharField(max_length=20)
    gg_id = models.CharField(verbose_name="Golf Genius id: tee_id", max_length=22, blank=True, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["course", "name"], name="unique_course_tee")
        ]

    def __str__(self):
        """
        Human-readable representation combining the course and tee names.
        
        Returns:
            str: The string "<course name> - <tee name>".
        """
        return "{} - {}".format(self.course.name, self.name)