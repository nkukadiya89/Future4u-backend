from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0047_remove_legacy_corporate_add_org_profiles"),
    ]

    operations = [
        migrations.RenameField(
            model_name="corporateprofile",
            old_name="student_trained",
            new_name="open_job",
        ),
        migrations.RenameField(
            model_name="corporateprofile",
            old_name="placements",
            new_name="employees",
        ),
        migrations.RenameField(
            model_name="corporateprofile",
            old_name="courses_offered",
            new_name="perks_benefits",
        ),
        migrations.RemoveField(
            model_name="corporateprofile",
            name="success_rate",
        ),
        migrations.RemoveField(
            model_name="corporateprofile",
            name="key_highlights",
        ),
        migrations.AddField(
            model_name="corporateprofile",
            name="years_in_business",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
