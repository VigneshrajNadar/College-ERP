# Generated by Django 5.1.7 on 2025-04-03 09:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0003_alter_chatbot_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='roll_number',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
    ]
