# Generated by Django 3.1.3 on 2021-01-02 13:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_code', models.CharField(max_length=40, verbose_name='Payment code')),
                ('payment_key', models.CharField(blank=True, max_length=100, null=True, verbose_name='Secret key')),
                ('payment_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=5, verbose_name='Payment amount')),
                ('transaction_fee', models.DecimalField(decimal_places=2, default=0.0, max_digits=4, verbose_name='Payment fees')),
                ('notification_type', models.CharField(blank=True, choices=[('N', 'New Member'), ('R', 'Returning Member'), ('C', 'Signup Confirmation'), ('M', 'Match Play'), ('O', 'General Online Payment')], max_length=1, null=True, verbose_name='Notification type')),
                ('confirmed', models.BooleanField(default=False, verbose_name='Confirmed')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='payments', to='events.event', verbose_name='Event')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
        ),
    ]
