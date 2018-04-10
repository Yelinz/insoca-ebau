# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-04-10 11:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20180405_1530'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='validation',
            field=models.CharField(blank=True, db_column='VALIDATION', max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='instanceresource',
            name='form_group',
            field=models.ForeignKey(db_column='FORM_GROUP_ID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.FormGroup'),
        ),
    ]
