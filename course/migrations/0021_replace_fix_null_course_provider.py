from django.db import migrations, models


def fix_null_course_provider(apps, schema_editor):
    Courses = apps.get_model("course", "Courses")
    updated = Courses.objects.filter(
        course_provider__isnull=True,
        created_by__isnull=False,
        created_by__user_type__in=["school_college", "institute"],
    ).update(course_provider=models.F("created_by"))

    if updated:
        print(f"  Fixed {updated} course(s) with null course_provider")


class Migration(migrations.Migration):

    replaces = [("course", "0020_fix_null_course_provider")]

    dependencies = [
        ("course", "0019_remove_provider_field_from_courses"),
        ("user", "0012_remove_user_role_user_user_type"),
    ]

    operations = [
        migrations.RunPython(fix_null_course_provider, migrations.RunPython.noop),
    ]
