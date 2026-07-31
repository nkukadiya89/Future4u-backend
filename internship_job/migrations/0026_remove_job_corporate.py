from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("internship_job", "0025_job_provider_rename_and_remove_corporate"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="job",
            name="corporate",
        ),
    ]
