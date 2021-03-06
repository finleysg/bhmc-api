# Generated by Django 3.1.3 on 2021-03-14 22:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0004_refund'),
        ('register', '0003_auto_20210307_0914'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registrationfee',
            name='payment',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='payment_details', to='payments.payment', verbose_name='Payment'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='registrationfee',
            name='registration_slot',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fees', to='register.registrationslot', verbose_name='Registration Slot'),
        ),
    ]
