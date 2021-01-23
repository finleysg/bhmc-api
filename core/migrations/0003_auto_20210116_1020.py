# Generated by Django 3.1.3 on 2021-01-16 16:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_ace_lowscore_majorchampion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ace',
            name='hole_name',
            field=models.CharField(max_length=30, verbose_name='Hole'),
        ),
        migrations.AlterField(
            model_name='lowscore',
            name='course_name',
            field=models.CharField(max_length=40, verbose_name='Course'),
        ),
    ]