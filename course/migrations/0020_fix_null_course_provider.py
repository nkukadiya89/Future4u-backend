from django.conf import settings
from django.db import migrations, models


def fix_null_course_provider(apps, schema_editor):
    Courses = apps.get_model("course", "Courses")
    User = apps.get_model("user", "User")
    # Historical User model uses `role` before the rename to `user_type`.
    type_field = "user_type" if hasattr(User, "user_type") else "role"
    provider_ids = list(
        User.objects.filter(
            **{f"{type_field}__in": ["school_college", "institute"]}
        ).values_list("id", flat=True)
    )
    updated = Courses.objects.filter(
        course_provider__isnull=True,
        created_by__isnull=False,
        created_by_id__in=provider_ids,
    ).update(course_provider=models.F("created_by"))

    if updated:
        print(f"  Fixed {updated} course(s) with null course_provider")


class Migration(migrations.Migration):

    dependencies = [
        ("course", "0019_remove_provider_field_from_courses"),
        # The historical User model must include `user_type` (renamed from
        # `role` in user.0012), otherwise fresh DB builds fail to resolve it.
        ("user", "0030_alter_user_user_type"),
    ]

    operations = [
        migrations.RunPython(fix_null_course_provider, migrations.RunPython.noop),
    ]
