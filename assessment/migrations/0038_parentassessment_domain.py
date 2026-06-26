from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0020_remove_retired_content_types"),
        ("assessment", "0037_parentassessment_child"),
    ]

    operations = [
        migrations.AlterField(
            model_name="parentassessment",
            name="current_screen",
            field=models.CharField(
                choices=[
                    ("domain_category", "Domain Category"),
                    ("domain", "Domain"),
                    ("career_direction", "Career Direction"),
                    ("parent_support", "Parent Support"),
                    ("concerns", "Concerns"),
                    ("parent_career_expectations", "Parent Career Expectations"),
                    ("limitations", "Limitations"),
                    ("career_familiarity", "Career Familiarity"),
                    ("decision_style", "Decision Style"),
                    ("career_values", "Career Values"),
                    ("user_goals", "User Goals"),
                    ("complete", "Complete"),
                ],
                default="domain_category",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="parentassessment",
            name="domain",
            field=models.ForeignKey(
                blank=True,
                help_text="Child domain selected by the parent.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="parent_domain_assessments",
                to="domain.domain",
            ),
        ),
    ]
