# Generated by Django 4.1.8 on 2023-10-28 16:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0010_alter_historicalplayer_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalplayer',
            name='is_member',
            field=models.BooleanField(default=False, verbose_name='Is Member'),
        ),
        migrations.AddField(
            model_name='historicalplayer',
            name='last_season',
            field=models.IntegerField(blank=True, null=True, verbose_name='Most Recent Membership Season'),
        ),
        migrations.AddField(
            model_name='player',
            name='is_member',
            field=models.BooleanField(default=False, verbose_name='Is Member'),
        ),
        migrations.AddField(
            model_name='player',
            name='last_season',
            field=models.IntegerField(blank=True, null=True, verbose_name='Most Recent Membership Season'),
        ),
    ]
