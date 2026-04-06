from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("career", "0002_initial"),
        ("domain", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DomainCareerMapping",
            fields=[
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("deleted", models.BooleanField(default=False)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("weight_score", models.PositiveSmallIntegerField()),
                ("is_active", models.BooleanField(default=True)),
                (
                    "career",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="domain_career_mappings",
                        to="career.career",
                    ),
                ),
                (
                    "domain",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="domain_career_mappings",
                        to="domain.domain",
                    ),
                ),
            ],
            options={
                "db_table": "domain_career_mapping",
                "ordering": ["-weight_score", "id"],
            },
        ),
        migrations.CreateModel(
            name="DomainCareerMappingImportBatch",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("imported_count", models.PositiveIntegerField(default=0)),
                ("failed_count", models.PositiveIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="domain_career_mapping_import_batches",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "domain_career_mapping_import_batch",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DomainCareerMappingImportError",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("row_number", models.PositiveIntegerField()),
                ("message", models.CharField(max_length=500)),
                ("row_data", models.JSONField(default=dict)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="error_rows",
                        to="domain_career_mapping.domaincareermappingimportbatch",
                    ),
                ),
            ],
            options={
                "db_table": "domain_career_mapping_import_error",
                "ordering": ["batch", "row_number"],
            },
        ),
        migrations.AddIndex(
            model_name="domaincareermapping",
            index=models.Index(
                fields=["domain"], name="domain_care_domain_i_9f0b6b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="domaincareermapping",
            index=models.Index(
                fields=["career"], name="domain_care_career__56a2f9_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="domaincareermapping",
            index=models.Index(
                fields=["weight_score"], name="domain_care_weight__ff3f12_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="domaincareermapping",
            index=models.Index(
                fields=["is_active"], name="domain_care_is_acti_4f1f42_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="domaincareermapping",
            index=models.Index(
                fields=["deleted"], name="domain_care_deleted_fa3b0b_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="domaincareermapping",
            constraint=models.UniqueConstraint(
                fields=("domain", "career"),
                name="domain_career_mapping_domain_career_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="domaincareermapping",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("weight_score__gte", 0), ("weight_score__lte", 100)
                ),
                name="domain_career_mapping_weight_score_0_100_ck",
            ),
        ),
    ]
