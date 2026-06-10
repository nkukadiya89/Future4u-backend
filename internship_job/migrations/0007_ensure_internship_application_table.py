# Recreates internship_application if it was dropped by user_profile.0041 CASCADE.

from django.db import migrations


def create_table_if_missing(apps, schema_editor):
    connection = schema_editor.connection
    table_names = connection.introspection.table_names()
    if "internship_application" in table_names:
        return
    model = apps.get_model("internship_job", "InternshipApplication")
    schema_editor.create_model(model)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("internship_job", "0006_alter_internshipapplication_table"),
        ("user_profile", "0041_remove_internshipprofile_deleted_by_and_more"),
    ]

    operations = [
        migrations.RunPython(create_table_if_missing, noop_reverse),
    ]
