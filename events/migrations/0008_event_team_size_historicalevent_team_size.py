# Generated by Django 4.1.4 on 2023-04-07 16:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0007_alter_historicalevent_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='team_size',
            field=models.IntegerField(default=1, verbose_name='Team size'),
        ),
        migrations.AddField(
            model_name='historicalevent',
            name='team_size',
            field=models.IntegerField(default=1, verbose_name='Team size'),
        ),
    ]
