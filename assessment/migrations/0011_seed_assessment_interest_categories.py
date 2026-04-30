from django.db import migrations


INTEREST_CATEGORIES = [
    ("technology", "Technology / Coding", 1),
    ("healthcare", "Healthcare / Life Sciences", 2),
    ("business", "Business / Finance", 3),
    ("creative", "Creative / Design", 4),
    ("science", "Science / Research", 5),
    ("agriculture", "Agriculture / Environment", 6),
    ("sports", "Sports / Fitness", 7),
    ("government", "Government / Public Service", 8),
]


def seed_categories(apps, schema_editor):
    AssessmentInterestCategory = apps.get_model("assessment", "AssessmentInterestCategory")
    for code, name, order in INTEREST_CATEGORIES:
        AssessmentInterestCategory.objects.update_or_create(
            category_code=code,
            defaults={
                "category_name": name,
                "sequence_order": order,
                "is_active": True,
                "deleted": False,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0010_assessmentinterestcategory"),
    ]

    operations = [
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
