from django.db import migrations, models


def fix_null_internship_provider(apps, schema_editor):
    Internship = apps.get_model("internship_job", "Internship")
    User = apps.get_model("user", "User")
    # Historical User model uses `role` before the rename to `user_type`.
    type_field = "user_type" if hasattr(User, "user_type") else "role"
    provider_ids = list(
        User.objects.filter(
            **{f"{type_field}__in": ["institute", "corporate"]}
        ).values_list("id", flat=True)
    )
    updated = Internship.objects.filter(
        internship_provider__isnull=True,
        created_by__isnull=False,
        created_by_id__in=provider_ids,
    ).update(internship_provider=models.F("created_by"))

    if updated:
        print(f"  Fixed {updated} internship(s) with null internship_provider")


class Migration(migrations.Migration):

    dependencies = [
        ("internship_job", "0023_remove_provider_field_from_internship"),
    ]

    operations = [
        migrations.RunPython(fix_null_internship_provider, migrations.RunPython.noop),
    ]
