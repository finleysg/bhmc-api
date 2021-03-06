# Generated by Django 3.1.3 on 2021-04-25 19:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_auto_20210402_1904'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaticDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=6, unique=True, verbose_name='Code')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='documents.document', verbose_name='Document')),
            ],
        ),
    ]
