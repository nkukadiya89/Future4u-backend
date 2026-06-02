from django.db import migrations


def remove_retired_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label__in=["skill", "user_skill"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("skill", "0004_remove_legacy_skill_master"),
    ]

    operations = [
        migrations.RunPython(
            remove_retired_content_types,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
