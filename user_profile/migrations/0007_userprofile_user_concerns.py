from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0006_science_track_parent_support"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="user_concerns",
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="Concerns selected during onboarding e.g. ['job_security', 'education_cost']",
            ),
        ),
    ]
