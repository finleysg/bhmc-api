# Generated by Django 4.2.7 on 2023-12-23 18:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0010_alter_event_event_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='priority_signup_start',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Priority signup start'),
        ),
        migrations.AddField(
            model_name='historicalevent',
            name='priority_signup_start',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Priority signup start'),
        ),
        migrations.AlterField(
            model_name='event',
            name='registration_type',
            field=models.CharField(choices=[('M', 'Member'), ('G', 'Member Guest'), ('O', 'Open'), ('R', 'Returning Member'), ('N', 'None')], default='M', max_length=1, verbose_name='Registration type'),
        ),
        migrations.AlterField(
            model_name='historicalevent',
            name='registration_type',
            field=models.CharField(choices=[('M', 'Member'), ('G', 'Member Guest'), ('O', 'Open'), ('R', 'Returning Member'), ('N', 'None')], default='M', max_length=1, verbose_name='Registration type'),
        ),
    ]
