# Generated by Django 4.2.7 on 2024-01-20 18:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0012_eventfeeoverride_eventfee_override_amount_and_more'),
        ('core', '0010_majorchampion_is_net_alter_majorchampion_score'),
    ]

    operations = [
        migrations.AddField(
            model_name='majorchampion',
            name='event',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='events.event', verbose_name='Event'),
        ),
    ]
