# Generated by Django 4.0.2 on 2022-02-06 20:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_seasonsettings'),
    ]

    operations = [
        migrations.RenameField(
            model_name='seasonsettings',
            old_name='match_play_event_id',
            new_name='match_play_event',
        ),
        migrations.RenameField(
            model_name='seasonsettings',
            old_name='member_event_id',
            new_name='member_event',
        ),
    ]
