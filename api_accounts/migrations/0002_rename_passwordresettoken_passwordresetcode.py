# Generated by Django 5.1.6 on 2025-03-04 06:51

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api_accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name='PasswordResetToken',
            new_name='PasswordResetCode',
        ),
    ]
