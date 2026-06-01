# Squashes assessment migrations 0021–0026 into a single migration that does
# not reference the deleted `career` app.
#
# Net effect of the replaced migrations on persistent database state:
#   - Remove old JSON career/concern/value/goal fields from StudentAssessment
#   - Create Concern, CareerValue, UserGoal, CareerDirection models
#   - Add M2M fields on StudentAssessment pointing to those models
#
# Models that were created and later dropped (career-referencing) are omitted
# since their net effect is zero.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ("assessment", "0021_recommendation_models_and_remove_career_direction"),
        ("assessment", "0022_careervalue_concern_usergoal_and_more"),
        ("assessment", "0023_alter_studentassessment_career_values_and_more"),
        ("assessment", "0024_alter_studentassessment_career_direction_and_more"),
        ("assessment", "0025_alter_careerdirection_table_alter_careervalue_table_and_more"),
        ("assessment", "0026_remove_static_recommendation_models"),
    ]

    dependencies = [
        ("assessment", "0020_alter_studentassessment_updated_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # -- Remove old JSON fields from StudentAssessment (0021, 0022) --
        migrations.RemoveField(
            model_name="studentassessment",
            name="career_direction",
        ),
        migrations.RemoveField(
            model_name="studentassessment",
            name="career_values",
        ),
        migrations.RemoveField(
            model_name="studentassessment",
            name="concerns",
        ),
        migrations.RemoveField(
            model_name="studentassessment",
            name="user_goals",
        ),
        # -- Create Concern model (0022) --
        migrations.CreateModel(
            name="Concern",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("deleted", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=150)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "assessment_concern"},
        ),
        # -- Create CareerValue model (0022) --
        migrations.CreateModel(
            name="CareerValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("deleted", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=150)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "assessment_career_value"},
        ),
        # -- Create UserGoal model (0022) --
        migrations.CreateModel(
            name="UserGoal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("deleted", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=150)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "assessment_usergoal"},
        ),
        # -- Create CareerDirection model (0023) --
        migrations.CreateModel(
            name="CareerDirection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("deleted", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=150)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "assessment_career_direction"},
        ),
        # -- Alter parent_support to nullable (0022) --
        migrations.AlterField(
            model_name="studentassessment",
            name="parent_support",
            field=models.CharField(
                blank=True,
                choices=[
                    ("very_supportive", "Very Supportive"),
                    ("somewhat_supportive", "SomeWhat Supportive"),
                    ("neutral", "Neutral"),
                    ("not_supportive", "Not Supportive"),
                    ("notsure", "Not Sure"),
                ],
                max_length=150,
                null=True,
            ),
        ),
        # -- Add new M2M fields to StudentAssessment (0022, 0023, 0024) --
        migrations.AddField(
            model_name="studentassessment",
            name="career_direction",
            field=models.ManyToManyField(blank=True, to="assessment.CareerDirection"),
        ),
        migrations.AddField(
            model_name="studentassessment",
            name="career_values",
            field=models.ManyToManyField(blank=True, to="assessment.CareerValue"),
        ),
        migrations.AddField(
            model_name="studentassessment",
            name="concerns",
            field=models.ManyToManyField(blank=True, to="assessment.Concern"),
        ),
        migrations.AddField(
            model_name="studentassessment",
            name="user_goals",
            field=models.ManyToManyField(blank=True, to="assessment.UserGoal"),
        ),
    ]
