from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0004_delete_jobskill"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="jobpreference",
            name="soft_skills",
        ),
    ]
