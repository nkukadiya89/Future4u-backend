from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0007_userprofile_user_concerns"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="career_values",
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="What user values in a career e.g. ['high_salary_potential', 'work_life_balance']",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="platform_goals",
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="What user wants from the platform e.g. ['career_clarity', 'course_recommendations']",
            ),
        ),
    ]
