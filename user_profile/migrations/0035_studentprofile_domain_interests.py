from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0010_assessmentinterestcategory"),
        ("user_profile", "0034_alter_parentprofile_academic_performance"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="domain_interests",
            field=models.ManyToManyField(blank=True, related_name="student_profiles", to="assessment.assessmentinterestcategory"),
        ),
    ]
