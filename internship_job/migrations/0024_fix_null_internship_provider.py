from django.db import migrations, models


def fix_null_internship_provider(apps, schema_editor):
    Internship = apps.get_model("internship_job", "Internship")
    updated = Internship.objects.filter(
        internship_provider__isnull=True,
        created_by__isnull=False,
        created_by__user_type__in=["institute", "corporate"],
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
