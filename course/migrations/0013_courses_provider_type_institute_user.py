from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("course", "0012_fix_why_this_course_to_textfield"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="courses",
            name="provider_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("school_college", "School / College"),
                    ("institute", "Institute"),
                ],
                help_text="Select whether this course is posted by a School/College or an Institute.",
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="courses",
            name="institute_user",
            field=models.ForeignKey(
                blank=True,
                help_text="Select the specific institute/school-college user posting this course.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="institute_courses",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
