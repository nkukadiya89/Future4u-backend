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

    dependencies = [
        ("course", "0019_remove_provider_field_from_courses"),
    ]

    operations = [
        migrations.RunPython(fix_null_course_provider, migrations.RunPython.noop),
    ]
