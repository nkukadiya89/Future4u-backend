from django.db import migrations, models


def backup_education_tags(apps, schema_editor):
    """Copy existing JSON education_tags data to a temporary field."""
    Courses = apps.get_model("course", "Courses")
    for course in Courses.objects.all():
        if course.education_tags:
            course.education_tags_backup = list(course.education_tags)
            course.save(update_fields=["education_tags_backup"])


def populate_m2m_education_tags(apps, schema_editor):
    """Populate new M2M education_tags from the backup field."""
    Courses = apps.get_model("course", "Courses")
    EducationLevel = apps.get_model("education_level", "EducationLevel")
    for course in Courses.objects.all():
        tags = course.education_tags_backup or []
        if tags:
            edu_levels = EducationLevel.objects.filter(level_code__in=tags)
            course.education_tags.set(edu_levels)


class Migration(migrations.Migration):

    dependencies = [
        ("course", "0017_courseinquiry_career_suggestion"),
        ("education_level", "0005_alter_educationlevel_updated_at"),
    ]

    operations = [
        # Step 1: Add temporary JSONField to backup existing data
        migrations.AddField(
            model_name="courses",
            name="education_tags_backup",
            field=models.JSONField(default=list, blank=True),
        ),
        # Step 2: Copy data from old JSONField to backup field
        migrations.RunPython(backup_education_tags, migrations.RunPython.noop),
        # Step 3: Remove old JSONField (data is now safely in backup)
        migrations.RemoveField(
            model_name="courses",
            name="education_tags",
        ),
        # Step 4: Add new ManyToManyField with correct name
        # This creates the 'course_courses_education_tags' through table
        migrations.AddField(
            model_name="courses",
            name="education_tags",
            field=models.ManyToManyField(
                blank=True, to="education_level.educationlevel"
            ),
        ),
        # Step 5: Populate M2M relationships from backup
        migrations.RunPython(populate_m2m_education_tags, migrations.RunPython.noop),
        # Step 6: Remove temporary backup field
        migrations.RemoveField(
            model_name="courses",
            name="education_tags_backup",
        ),
    ]
