# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-07-08 19:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0002_blank_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exclusioncondition',
            name='on_date',
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
    ]
