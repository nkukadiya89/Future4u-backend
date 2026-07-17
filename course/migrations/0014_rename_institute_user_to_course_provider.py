from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("course", "0013_courses_provider_type_institute_user"),
    ]

    operations = [
        migrations.RenameField(
            model_name="courses",
            old_name="institute_user",
            new_name="course_provider",
        ),
    ]
