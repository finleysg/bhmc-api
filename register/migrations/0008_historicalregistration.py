# Generated by Django 3.1.3 on 2020-11-29 02:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0002_auto_20201021_2141'),
        ('events', '0005_feetype_code'),
        ('register', '0007_delete_historicalregistration'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalRegistration',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('expires', models.DateTimeField(blank=True, null=True, verbose_name='Expiration')),
                ('starting_hole', models.IntegerField(blank=True, default=1, verbose_name='Starting hole')),
                ('starting_order', models.IntegerField(default=0, verbose_name='Starting order')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='Registration notes')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('course', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='courses.course', verbose_name='Course')),
                ('event', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='events.event', verbose_name='Event')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Signed up by')),
            ],
            options={
                'verbose_name': 'historical registration',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
