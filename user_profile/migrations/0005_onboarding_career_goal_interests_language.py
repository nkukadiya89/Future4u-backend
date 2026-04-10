from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0004_userprofile_medium"),
    ]

    operations = [
        # language: CharField -> JSONField (multi-select languages)
        migrations.AlterField(
            model_name="userprofile",
            name="language",
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="Preferred languages e.g. ['english', 'hindi', 'gujarati']",
            ),
        ),
        # career_goal: new field for screen 6
        migrations.AddField(
            model_name="userprofile",
            name="career_goal",
            field=models.CharField(
                max_length=30,
                choices=[
                    ("study_further", "Study Further"),
                    ("find_job", "Find a Job"),
                    ("internship", "Internship"),
                    ("skill_development", "Skill Development"),
                    ("not_sure", "Not Sure Yet"),
                ],
                null=True,
                blank=True,
                help_text="Career direction selected during onboarding",
            ),
        ),
        # interest_categories: new field for screen 5
        migrations.AddField(
            model_name="userprofile",
            name="interest_categories",
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="Broad interest categories e.g. ['technology', 'healthcare', 'government']",
            ),
        ),
    ]
