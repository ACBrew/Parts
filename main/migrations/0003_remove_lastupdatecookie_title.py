# Generated by Django 3.2.4 on 2021-10-21 12:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_lastupdatecookie'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lastupdatecookie',
            name='title',
        ),
    ]
