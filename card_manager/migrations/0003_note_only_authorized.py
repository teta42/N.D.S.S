# Generated by Django 5.1.4 on 2025-01-10 09:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('card_manager', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='only_authorized',
            field=models.BooleanField(default=False),
        ),
    ]
