from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0005_onboarding_career_goal_interests_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="science_track",
            field=models.CharField(
                max_length=10,
                choices=[
                    ("pcm", "PCM (Physics, Chemistry, Maths)"),
                    ("pcb", "PCB (Physics, Chemistry, Biology)"),
                    ("pcmb", "PCMB (All four)"),
                ],
                null=True,
                blank=True,
                help_text="Science sub-track — only relevant when stream is science",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="parent_support_level",
            field=models.CharField(
                max_length=25,
                choices=[
                    ("very_supportive", "Very Supportive"),
                    ("somewhat_supportive", "Somewhat Supportive"),
                    ("neutral", "Neutral"),
                    ("somewhat_restrictive", "Somewhat Restrictive"),
                    ("very_restrictive", "Very Restrictive"),
                ],
                null=True,
                blank=True,
                help_text="How supportive parents are of career choices — used to weight parent_acceptance_level in recommendations",
            ),
        ),
    ]
