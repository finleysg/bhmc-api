# Generated by Django 3.1.3 on 2021-03-19 23:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0005_auto_20210319_1849'),
        ('register', '0004_auto_20210314_1702'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registrationfee',
            name='payment',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='payment_details', to='payments.payment', verbose_name='Payment'),
        ),
    ]
