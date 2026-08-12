"""Seed additional JSON Resume-compatible themes into the template registry.

These are presentation themes only - the AI generates ONE canonical JSON
Resume regardless of the selected theme. The frontend renders the theme;
the backend only stores the code as metadata. New themes never change AI
content or token cost.
"""

from django.db import migrations

# Classic jsonresume.org theme names plus the base themes already seeded.
# Presentation themes only - the frontend renders them from the canonical
# JSON Resume returned by the API.
THEMES = [
    {
        "code": "modern",
        "name": "Modern",
        "description": "Colorful gradient header with card-based sections (jsonresume-theme-modern inspired)",
        "category": "modern",
        "sort_order": 3,
    },
    {
        "code": "minimal",
        "name": "Minimal",
        "description": "Light, airy single column with hairline rules and small-caps headings",
        "category": "minimal",
        "sort_order": 4,
    },
    {
        "code": "academic",
        "name": "Academic",
        "description": "Formal serif layout suited for research and teaching roles",
        "category": "academic",
        "sort_order": 5,
    },
    {
        "code": "elegant",
        "name": "Elegant",
        "description": "Refined two-tone layout inspired by jsonresume-theme-elegant",
        "category": "professional",
        "sort_order": 6,
    },
    {
        "code": "compact",
        "name": "Compact",
        "description": "Dense single-page layout inspired by jsonresume-theme-compact",
        "category": "ats",
        "sort_order": 7,
    },
    {
        "code": "stackoverflow",
        "name": "Stack Overflow",
        "description": "Two-column layout inspired by jsonresume-theme-stackoverflow",
        "category": "professional",
        "sort_order": 8,
    },
]


def seed_themes(apps, schema_editor):
    ResumeTemplate = apps.get_model("resume_builder", "ResumeTemplate")
    for item in THEMES:
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


def unseed_themes(apps, schema_editor):
    ResumeTemplate = apps.get_model("resume_builder", "ResumeTemplate")
    ResumeTemplate.objects.filter(code__in=[t["code"] for t in THEMES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("resume_builder", "0003_seed_templates"),
    ]

    operations = [
        migrations.RunPython(seed_themes, unseed_themes),
    ]
