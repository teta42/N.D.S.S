# Generated by Django 5.0.1 on 2025-07-02 08:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_alter_note_dead_line'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='note',
            name='read_only',
        ),
    ]
