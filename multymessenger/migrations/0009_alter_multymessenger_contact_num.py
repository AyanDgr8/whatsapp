# Generated by Django 5.1.1 on 2024-12-03 07:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("multymessenger", "0008_multymessenger_f_name_multymessenger_l_name_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="multymessenger",
            name="contact_num",
            field=models.TextField(),
        ),
    ]
