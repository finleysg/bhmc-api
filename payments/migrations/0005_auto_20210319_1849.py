# Generated by Django 3.1.3 on 2021-03-19 23:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payments', '0004_refund'),
    ]

    operations = [
        migrations.AlterField(
            model_name='refund',
            name='issuer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL, verbose_name='Issuer'),
        ),
        migrations.AlterField(
            model_name='refund',
            name='refund_amount',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=5, verbose_name='Refund amount'),
        ),
        migrations.AlterField(
            model_name='refund',
            name='refund_code',
            field=models.CharField(max_length=40, verbose_name='Refund code'),
        ),
    ]
