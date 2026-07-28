import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0005_domain_report_meta"),
    ]

    operations = [
        # Add next_step fields to DomainReportMeta
        migrations.AddField(
            model_name="domainreportmeta",
            name="next_step_1",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="domainreportmeta",
            name="next_step_2",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="domainreportmeta",
            name="next_step_3",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        # Create StreamReportMeta
        migrations.CreateModel(
            name="StreamReportMeta",
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
                ("why", models.CharField(blank=True, max_length=512)),
                (
                    "subjects",
                    models.TextField(
                        blank=True, help_text="Pipe-separated subject names"
                    ),
                ),
                (
                    "careers",
                    models.TextField(
                        blank=True, help_text="Pipe-separated career titles"
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=512)),
                ("next_step_1", models.TextField(blank=True)),
                ("next_step_2", models.TextField(blank=True)),
                ("next_step_3", models.TextField(blank=True)),
            ],
            options={"db_table": "stream_report_meta"},
        ),
    ]
