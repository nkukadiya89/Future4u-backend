import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0009_domain_counsellor_knowledge_keywords"),
    ]

    operations = [
        migrations.CreateModel(
            name="DomainScoringConfig",
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
                    "config",
                    models.JSONField(
                        default=dict, help_text="Full scoring config for this domain"
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"db_table": "domain_scoring_config"},
        ),
    ]
