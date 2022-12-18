# Generated by Django 4.1.4 on 2022-12-18 17:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0002_tag'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='historicalpagecontent',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical page content', 'verbose_name_plural': 'historical page contents'},
        ),
        migrations.AlterField(
            model_name='historicalpagecontent',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
    ]
