from django.db import migrations

RETIRED_APP_LABELS = [
    "career",
    "domain_career_mapping",
    "domain_skill_mapping",
    "stream_domain_mapping",
]

RETIRED_DOMAIN_MODELS = [
    "domaincounsellorknowledge",
    "domainreportmeta",
    "domainscoringconfig",
    "streamcounsellorknowledge",
    "streamreportmeta",
]


def remove_retired_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label__in=RETIRED_APP_LABELS).delete()
    ContentType.objects.filter(
        app_label="domain",
        model__in=RETIRED_DOMAIN_MODELS,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        # These retired apps' migrations already applied in production:
        ("domain", "0019_remove_unused_domain_enrichment_tables"),
    ]

    operations = [
        migrations.RunPython(
            remove_retired_content_types,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
