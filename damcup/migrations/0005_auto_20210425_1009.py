# Generated by Django 3.1.3 on 2021-04-25 15:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('damcup', '0004_seasonlongpoints_source'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='seasonlongpoints',
            name='source',
        ),
        migrations.AddField(
            model_name='seasonlongpoints',
            name='additional_info',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='Additional Info'),
        ),
    ]
