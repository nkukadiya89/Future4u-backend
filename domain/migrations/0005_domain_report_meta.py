import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0004_seed_domain_affinity_weights"),
    ]

    operations = [
        migrations.CreateModel(
            name="DomainReportMeta",
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
                (
                    "domain_code",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                (
                    "degrees",
                    models.TextField(
                        blank=True, help_text="Pipe-separated degree options"
                    ),
                ),
                (
                    "careers",
                    models.TextField(
                        blank=True, help_text="Pipe-separated career titles"
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=512)),
                ("how_to_choose_hint", models.CharField(blank=True, max_length=512)),
            ],
            options={"db_table": "domain_report_meta"},
        ),
        migrations.CreateModel(
            name="DomainCounsellorKnowledge",
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
                (
                    "domain_code",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("insight", models.TextField(blank=True)),
                ("tradeoff", models.TextField(blank=True)),
                ("action", models.TextField(blank=True)),
                ("tension", models.TextField(blank=True)),
            ],
            options={"db_table": "domain_counsellor_knowledge"},
        ),
        migrations.CreateModel(
            name="StreamCounsellorKnowledge",
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
                (
                    "stream_code",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("insight", models.TextField(blank=True)),
                ("tradeoff", models.TextField(blank=True)),
                ("action", models.TextField(blank=True)),
                ("tension", models.TextField(blank=True)),
            ],
            options={"db_table": "stream_counsellor_knowledge"},
        ),
    ]
