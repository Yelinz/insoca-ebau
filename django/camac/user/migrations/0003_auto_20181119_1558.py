# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-19 14:58
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_auto_20180531_1314'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupT',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(db_column='LANGUAGE', max_length=2)),
                ('name', models.CharField(blank=True, db_column='NAME', max_length=200, null=True)),
                ('city', models.CharField(blank=True, db_column='CITY', max_length=100, null=True)),
            ],
            options={
                'db_table': 'GROUP_T',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='LocationT',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(db_column='LANGUAGE', max_length=2)),
                ('name', models.CharField(blank=True, db_column='NAME', max_length=100, null=True)),
                ('commune_name', models.CharField(blank=True, db_column='COMMUNE_NAME', max_length=100, null=True)),
                ('district_name', models.CharField(blank=True, db_column='DISTRICT_NAME', max_length=100, null=True)),
                ('section_name', models.CharField(blank=True, db_column='SECTION_NAME', max_length=100, null=True)),
                ('location', models.ForeignKey(db_column='LOCATION_ID', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='user.Location')),
            ],
            options={
                'db_table': 'LOCATION_T',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='RoleT',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(db_column='LANGUAGE', max_length=2)),
                ('name', models.CharField(blank=True, db_column='NAME', max_length=100, null=True)),
            ],
            options={
                'db_table': 'ROLE_T',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ServiceGroupT',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(db_column='LANGUAGE', max_length=2)),
                ('name', models.CharField(blank=True, db_column='NAME', max_length=100, null=True)),
            ],
            options={
                'db_table': 'SERVICE_GROUP_T',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ServiceT',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(db_column='LANGUAGE', max_length=2)),
                ('name', models.CharField(blank=True, db_column='NAME', max_length=200, null=True)),
                ('description', models.CharField(blank=True, db_column='DESCRIPTION', max_length=255, null=True)),
                ('city', models.CharField(blank=True, db_column='CITY', max_length=100, null=True)),
            ],
            options={
                'db_table': 'SERVICE_T',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='UserT',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(db_column='LANGUAGE', max_length=2)),
                ('city', models.CharField(blank=True, db_column='CITY', max_length=100, null=True)),
                ('user', models.ForeignKey(db_column='USER_ID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'USER_T',
                'managed': True,
            },
        ),
        migrations.AddField(
            model_name='service',
            name='disabled',
            field=models.PositiveSmallIntegerField(db_column='DISABLED', default=0),
        ),
        migrations.AlterField(
            model_name='group',
            name='name',
            field=models.CharField(blank=True, db_column='NAME', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='role',
            name='name',
            field=models.CharField(blank=True, db_column='NAME', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='service',
            name='name',
            field=models.CharField(blank=True, db_column='NAME', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='servicegroup',
            name='name',
            field=models.CharField(blank=True, db_column='NAME', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='servicet',
            name='service',
            field=models.ForeignKey(db_column='SERVICE_ID', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='user.Service'),
        ),
        migrations.AddField(
            model_name='servicegroupt',
            name='service_group',
            field=models.ForeignKey(db_column='SERVICE_GROUP_ID', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='user.ServiceGroup'),
        ),
        migrations.AddField(
            model_name='rolet',
            name='role',
            field=models.ForeignKey(db_column='ROLE_ID', on_delete=django.db.models.deletion.CASCADE, related_name='trans', to='user.Role'),
        ),
        migrations.AddField(
            model_name='groupt',
            name='group',
            field=models.ForeignKey(db_column='GROUP_ID', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='user.Group'),
        ),
    ]
