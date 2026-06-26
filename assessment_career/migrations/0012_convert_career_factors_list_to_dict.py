from __future__ import annotations

from django.db import migrations


def convert_career_factors(apps, schema_editor):
    CareerSuggestion = apps.get_model("assessment_career", "CareerSuggestion")
    for obj in CareerSuggestion.objects.iterator():
        if isinstance(obj.career_factors, list):
            obj.career_factors = {}
            obj.save(update_fields=["career_factors"])


class Migration(migrations.Migration):

    dependencies = [
        ("assessment_career", "0011_alter_careersuggestion_career_factors"),
    ]

    operations = [
        migrations.RunPython(convert_career_factors, migrations.RunPython.noop),
    ]
