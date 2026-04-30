import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0012_alter_assessmentinterestcategory_category_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentattempt",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="assessmentattempt",
            name="domain_interests",
            field=models.ManyToManyField(
                blank=True,
                related_name="assessment_attempts",
                to="assessment.assessmentinterestcategory",
            ),
        ),
        migrations.AlterField(
            model_name="assessmentattempt",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name="assessmentattempt",
            options={"ordering": ["-created_at"]},
        ),
    ]
