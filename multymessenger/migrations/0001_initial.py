# Generated by Django 5.1.1 on 2024-12-02 06:54

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="MultyMessenger",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "unique_id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("contact_num", models.CharField(max_length=15)),
                ("message", models.TextField()),
                ("date_sent", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]