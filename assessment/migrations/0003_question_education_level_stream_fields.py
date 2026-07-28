import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    The DB already has education_level_id and stream_id (target_stream) columns
    from a previous unapplied session. We use SeparateDatabaseAndState to tell
    Django the DB columns exist without re-creating them, and only create the
    new mapped_streams M2M table which is genuinely missing.
    """

    dependencies = [
        ("assessment", "0002_question_mapped_domains_and_signal_strength"),
        ("education_level", "0002_initial"),
        ("stream", "0002_initial"),
    ]

    operations = [
        # education_level FK — column already in DB, just update state
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="question",
                    name="education_level",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assessment_questions",
                        to="education_level.educationlevel",
                        help_text="If set, this question is only shown to users at this education level.",
                    ),
                ),
            ],
            database_operations=[],  # column already exists
        ),
        # target_stream FK — DB has it as stream_id, update state with correct name
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="question",
                    name="target_stream",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assessment_questions",
                        to="stream.stream",
                        help_text="If set, this question is only shown to 12th-grade users who selected this stream.",
                        db_column="stream_id",
                    ),
                ),
            ],
            database_operations=[],  # column already exists as stream_id
        ),
        # mapped_streams M2M — genuinely new, create the through table
        migrations.AddField(
            model_name="question",
            name="mapped_streams",
            field=models.ManyToManyField(
                blank=True,
                related_name="signal_questions",
                to="stream.stream",
                help_text="Streams this question signals affinity for (used for 10th-grade stream recommendations).",
            ),
        ),
    ]
