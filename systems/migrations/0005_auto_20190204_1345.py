# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2019-02-04 13:45
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('systems', '0004_auto_20190201_0633'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='system',
            name='allocation',
        ),
        migrations.DeleteModel(
            name='Allocation',
        ),
    ]