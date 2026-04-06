from django.db import migrations


class Migration(migrations.Migration):
    """Drop the stale counselor_note column that was added outside of Django migrations."""

    dependencies = [
        ("domain", "0006_stream_report_meta_domain_report_meta_next_steps"),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE domain DROP COLUMN IF EXISTS "counselor_note"',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
