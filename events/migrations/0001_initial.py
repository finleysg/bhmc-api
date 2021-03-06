# Generated by Django 3.1.3 on 2021-01-02 13:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('N', 'Weeknight Event'), ('W', 'Weekend Major'), ('H', 'Holiday Pro-shop Event'), ('M', 'Meeting'), ('O', 'Other'), ('E', 'External Event'), ('R', 'Open Registration Period'), ('D', 'Deadline'), ('P', 'Open Event')], default='N', max_length=1, verbose_name='Event type')),
                ('name', models.CharField(max_length=100, verbose_name='Event title')),
                ('rounds', models.IntegerField(blank=True, null=True, verbose_name='Number of rounds')),
                ('registration_type', models.CharField(choices=[('M', 'Member Only'), ('G', 'Member Guest'), ('O', 'Open'), ('N', 'None')], default='M', max_length=1, verbose_name='Registration type')),
                ('skins_type', models.CharField(blank=True, choices=[('I', 'Individual'), ('T', 'Team'), ('N', 'No Skins')], max_length=1, null=True, verbose_name='Skins type')),
                ('minimum_signup_group_size', models.IntegerField(blank=True, null=True, verbose_name='Minimum sign-up group size')),
                ('maximum_signup_group_size', models.IntegerField(blank=True, null=True, verbose_name='Maximum sign-up group size')),
                ('group_size', models.IntegerField(blank=True, null=True, verbose_name='Group size')),
                ('total_groups', models.IntegerField(blank=True, null=True, verbose_name='Groups per course (tee times)')),
                ('start_type', models.CharField(blank=True, choices=[('TT', 'Tee Times'), ('SG', 'Shotgun'), ('NA', 'Not Applicable')], max_length=2, null=True, verbose_name='Start type')),
                ('can_choose', models.BooleanField(default=False, verbose_name='Player can choose starting hole or tee time')),
                ('ghin_required', models.BooleanField(default=False, verbose_name='GHIN required')),
                ('season_points', models.IntegerField(blank=True, null=True, verbose_name='Season long points available')),
                ('notes', models.TextField(blank=True, null=True)),
                ('start_date', models.DateField(verbose_name='Start date')),
                ('start_time', models.CharField(blank=True, max_length=40, null=True, verbose_name='Starting time')),
                ('signup_start', models.DateTimeField(blank=True, null=True, verbose_name='Signup start')),
                ('signup_end', models.DateTimeField(blank=True, null=True, verbose_name='Signup end')),
                ('payments_end', models.DateTimeField(blank=True, null=True, verbose_name='Online payments deadline')),
                ('registration_maximum', models.IntegerField(blank=True, null=True, verbose_name='Signup maximum')),
                ('portal_url', models.CharField(blank=True, max_length=240, null=True, verbose_name='Golf Genius Portal')),
                ('external_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='External url')),
                ('status', models.CharField(choices=[('C', 'Canceled'), ('S', 'Scheduled'), ('T', 'Tentative')], default='S', max_length=1, verbose_name='Status')),
                ('season', models.IntegerField(default=0, verbose_name='Season')),
                ('courses', models.ManyToManyField(blank=True, to='courses.Course', verbose_name='Course(s)')),
            ],
        ),
        migrations.CreateModel(
            name='FeeType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True, verbose_name='Fee Name')),
                ('code', models.CharField(default='X', max_length=3, verbose_name='Fee Code')),
            ],
        ),
        migrations.CreateModel(
            name='HistoricalEvent',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('N', 'Weeknight Event'), ('W', 'Weekend Major'), ('H', 'Holiday Pro-shop Event'), ('M', 'Meeting'), ('O', 'Other'), ('E', 'External Event'), ('R', 'Open Registration Period'), ('D', 'Deadline'), ('P', 'Open Event')], default='N', max_length=1, verbose_name='Event type')),
                ('name', models.CharField(max_length=100, verbose_name='Event title')),
                ('rounds', models.IntegerField(blank=True, null=True, verbose_name='Number of rounds')),
                ('registration_type', models.CharField(choices=[('M', 'Member Only'), ('G', 'Member Guest'), ('O', 'Open'), ('N', 'None')], default='M', max_length=1, verbose_name='Registration type')),
                ('skins_type', models.CharField(blank=True, choices=[('I', 'Individual'), ('T', 'Team'), ('N', 'No Skins')], max_length=1, null=True, verbose_name='Skins type')),
                ('minimum_signup_group_size', models.IntegerField(blank=True, null=True, verbose_name='Minimum sign-up group size')),
                ('maximum_signup_group_size', models.IntegerField(blank=True, null=True, verbose_name='Maximum sign-up group size')),
                ('group_size', models.IntegerField(blank=True, null=True, verbose_name='Group size')),
                ('total_groups', models.IntegerField(blank=True, null=True, verbose_name='Groups per course (tee times)')),
                ('start_type', models.CharField(blank=True, choices=[('TT', 'Tee Times'), ('SG', 'Shotgun'), ('NA', 'Not Applicable')], max_length=2, null=True, verbose_name='Start type')),
                ('can_choose', models.BooleanField(default=False, verbose_name='Player can choose starting hole or tee time')),
                ('ghin_required', models.BooleanField(default=False, verbose_name='GHIN required')),
                ('season_points', models.IntegerField(blank=True, null=True, verbose_name='Season long points available')),
                ('notes', models.TextField(blank=True, null=True)),
                ('start_date', models.DateField(verbose_name='Start date')),
                ('start_time', models.CharField(blank=True, max_length=40, null=True, verbose_name='Starting time')),
                ('signup_start', models.DateTimeField(blank=True, null=True, verbose_name='Signup start')),
                ('signup_end', models.DateTimeField(blank=True, null=True, verbose_name='Signup end')),
                ('payments_end', models.DateTimeField(blank=True, null=True, verbose_name='Online payments deadline')),
                ('registration_maximum', models.IntegerField(blank=True, null=True, verbose_name='Signup maximum')),
                ('portal_url', models.CharField(blank=True, max_length=240, null=True, verbose_name='Golf Genius Portal')),
                ('external_url', models.CharField(blank=True, max_length=255, null=True, verbose_name='External url')),
                ('status', models.CharField(choices=[('C', 'Canceled'), ('S', 'Scheduled'), ('T', 'Tentative')], default='S', max_length=1, verbose_name='Status')),
                ('season', models.IntegerField(default=0, verbose_name='Season')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical event',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='EventFee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Amount')),
                ('is_required', models.BooleanField(default=False, verbose_name='Required')),
                ('display_order', models.IntegerField(verbose_name='Display Order')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fees', to='events.event', verbose_name='Event')),
                ('fee_type', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='events.feetype', verbose_name='Fee Type')),
            ],
        ),
        migrations.AddConstraint(
            model_name='eventfee',
            constraint=models.UniqueConstraint(fields=('event', 'fee_type'), name='unique_event_feetype'),
        ),
        migrations.AddConstraint(
            model_name='event',
            constraint=models.UniqueConstraint(fields=('name', 'start_date'), name='unique_name_startdate'),
        ),
    ]
