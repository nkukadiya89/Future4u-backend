from django.db import migrations


def recreate_job_application_table(apps, schema_editor):

    table_names = {
        name.lower() for name in schema_editor.connection.introspection.table_names()
    }
    if "job_application" in table_names:
        return

    JobApplication = apps.get_model("internship_job", "JobApplication")
    schema_editor.create_model(JobApplication)


class Migration(migrations.Migration):

    dependencies = [
        ("internship_job", "0026_remove_job_corporate"),
        ("skill", "0006_remove_jobs_app"),
    ]

    operations = [
        migrations.RunPython(recreate_job_application_table, migrations.RunPython.noop),
    ]
