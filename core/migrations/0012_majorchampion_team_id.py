# Generated by Django 4.2.7 on 2024-01-21 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_majorchampion_event'),
    ]

    operations = [
        migrations.AddField(
            model_name='majorchampion',
            name='team_id',
            field=models.CharField(blank=True, max_length=8, null=True, verbose_name='Team Id'),
        ),
    ]