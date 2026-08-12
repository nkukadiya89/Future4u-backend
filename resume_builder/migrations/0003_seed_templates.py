"""Seed the initial ResumeTemplate registry (standard + professional)."""

from django.db import migrations

TEMPLATES = [
    {
        "code": "standard",
        "name": "Standard",
        "description": "Simple ATS-friendly single-column resume",
        "category": "ats",
        "sort_order": 1,
    },
    {
        "code": "professional",
        "name": "Professional",
        "description": "Professional two-column layout with photo and skill bars",
        "category": "professional",
        "sort_order": 2,
    },
]


def seed_templates(apps, schema_editor):
    ResumeTemplate = apps.get_model("resume_builder", "ResumeTemplate")
    for item in TEMPLATES:
        ResumeTemplate.objects.get_or_create(
            code=item["code"],
            defaults={
                "name": item["name"],
                "description": item["description"],
                "category": item["category"],
                "is_active": True,
                "sort_order": item["sort_order"],
            },
        )


def unseed_templates(apps, schema_editor):
    ResumeTemplate = apps.get_model("resume_builder", "ResumeTemplate")
    ResumeTemplate.objects.filter(code__in=[t["code"] for t in TEMPLATES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("resume_builder", "0002_resumetemplate_generatedresume"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
