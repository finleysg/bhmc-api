# Generated by Django 4.0.2 on 2022-05-08 17:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('register', '0009_alter_player_favorites'),
        ('courses', '0001_initial'),
        ('events', '0006_event_starter_time_interval_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventScore',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.IntegerField(verbose_name='Score')),
                ('is_net', models.BooleanField(default=False, verbose_name='Is Net?')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.event', verbose_name='Event')),
                ('hole', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.hole', verbose_name='Hole')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='register.player', verbose_name='Player')),
            ],
        ),
        migrations.AddConstraint(
            model_name='eventscore',
            constraint=models.UniqueConstraint(fields=('event', 'player', 'hole', 'is_net'), name='unique_event_score'),
        ),
    ]
