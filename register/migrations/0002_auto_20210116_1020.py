# Generated by Django 3.1.3 on 2021-01-16 16:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
        ('register', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registration',
            name='course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='courses.course', verbose_name='Course'),
        ),
    ]
