from django.db import migrations

JOBS_TABLES = (
    "saved_job",
    "job_application",
    "job_preference",
    "job",
)


def drop_jobs_tables(apps, schema_editor):
    for table in JOBS_TABLES:
        schema_editor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')


def remove_jobs_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="jobs").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("skill", "0005_remove_retired_skill_content_types"),
    ]

    operations = [
        migrations.RunPython(
            drop_jobs_tables,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            remove_jobs_content_types,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
