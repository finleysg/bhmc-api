# Generated by Django 3.1.3 on 2021-01-02 13:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('number_of_holes', models.IntegerField(default=18)),
            ],
        ),
        migrations.CreateModel(
            name='Hole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hole_number', models.IntegerField(default=0)),
                ('par', models.IntegerField(default=0)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='holes', to='courses.course')),
            ],
        ),
        migrations.AddConstraint(
            model_name='hole',
            constraint=models.UniqueConstraint(fields=('course', 'hole_number'), name='unique_course_holenumber'),
        ),
    ]
