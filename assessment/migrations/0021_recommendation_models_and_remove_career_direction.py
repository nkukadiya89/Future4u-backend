# Generated manually for recommendation storage and removal of career_direction JSON.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0020_alter_studentassessment_updated_at"),
        # career dependency removed — career app is deleted; migration already applied in production
        ("domain", "0018_alter_domain_updated_at"),
        ("skill", "0003_alter_skill_updated_at"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="studentassessment",
            name="career_direction",
        ),
        migrations.CreateModel(
            name="OptionCareerMapping",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("weight", models.FloatField(default=1)),
                (
                    "career",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="option_mappings",
                        to="career.career",
                    ),
                ),
                (
                    "option",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="career_mappings",
                        to="assessment.option",
                    ),
                ),
            ],
            options={
                "db_table": "assessment_option_career_mapping",
                "ordering": ("option_id", "career_id"),
                "unique_together": {("option", "career")},
            },
        ),
        migrations.CreateModel(
            name="OptionSkillMapping",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("weight", models.FloatField(default=1)),
                (
                    "option",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skill_mappings",
                        to="assessment.option",
                    ),
                ),
                (
                    "skill",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="option_mappings",
                        to="skill.skill",
                    ),
                ),
            ],
            options={
                "db_table": "assessment_option_skill_mapping",
                "ordering": ("option_id", "skill_id"),
                "unique_together": {("option", "skill")},
            },
        ),
        migrations.CreateModel(
            name="AssessmentCareerRecommendation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("score", models.FloatField(default=0)),
                ("rank", models.PositiveSmallIntegerField(default=1)),
                ("match_percentage", models.FloatField(default=0)),
                ("reasoning", models.JSONField(blank=True, default=list)),
                ("is_recommended", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "assessment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="career_recommendations",
                        to="assessment.studentassessment",
                    ),
                ),
                (
                    "career",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="career_recommendations",
                        to="career.career",
                    ),
                ),
            ],
            options={
                "db_table": "assessment_career_recommendation",
                "ordering": ("rank", "-score"),
                "unique_together": {("assessment", "career")},
                "indexes": [
                    models.Index(
                        fields=["assessment"],
                        name="acr_assessment_idx",
                    ),
                    models.Index(
                        fields=["career"],
                        name="acr_career_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="AssessmentSkillScore",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("score", models.FloatField(default=0)),
                (
                    "assessment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skill_scores",
                        to="assessment.studentassessment",
                    ),
                ),
                (
                    "skill",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assessment_skill_scores",
                        to="skill.skill",
                    ),
                ),
            ],
            options={
                "db_table": "assessment_skill_score",
                "ordering": ("assessment_id", "-score"),
                "unique_together": {("assessment", "skill")},
                "indexes": [
                    models.Index(
                        fields=["assessment", "skill"],
                        name="ask_assessment_skill_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="AssessmentDomainScore",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("score", models.FloatField(default=0)),
                (
                    "assessment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="domain_scores",
                        to="assessment.studentassessment",
                    ),
                ),
                (
                    "domain",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assessment_domain_scores",
                        to="domain.domain",
                    ),
                ),
            ],
            options={
                "db_table": "assessment_domain_score",
                "ordering": ("assessment_id", "-score"),
                "unique_together": {("assessment", "domain")},
                "indexes": [
                    models.Index(
                        fields=["assessment", "domain"],
                        name="ads_assessment_domain_idx",
                    ),
                ],
            },
        ),
    ]
