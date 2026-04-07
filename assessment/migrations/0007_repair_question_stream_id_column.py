from django.db import migrations


class Migration(migrations.Migration):
    """
    Repair migration.

    assessment.Question.target_stream uses db_column="stream_id".
    assessment.0003 assumed assessment_question.stream_id already existed.
    In some DBs it doesn't, causing crashes during seeding/queries.
    """

    dependencies = [
        ("assessment", "0006_repair_question_education_level_column"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            DECLARE
              col_type text;
            BEGIN
              SELECT c.data_type
              INTO col_type
              FROM information_schema.columns c
              WHERE c.table_name = 'assessment_question'
                AND c.column_name = 'stream_id';

              IF col_type IS NULL THEN
                ALTER TABLE assessment_question
                ADD COLUMN stream_id uuid NULL;
              ELSIF col_type <> 'uuid' THEN
                ALTER TABLE assessment_question
                DROP COLUMN stream_id;
                ALTER TABLE assessment_question
                ADD COLUMN stream_id uuid NULL;
              END IF;

              IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'assessment_question_stream_id_fk'
              ) THEN
                ALTER TABLE assessment_question
                ADD CONSTRAINT assessment_question_stream_id_fk
                FOREIGN KEY (stream_id)
                REFERENCES stream (id)
                ON DELETE SET NULL;
              END IF;
            END
            $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'assessment_question_stream_id_fk'
              ) THEN
                ALTER TABLE assessment_question
                DROP CONSTRAINT assessment_question_stream_id_fk;
              END IF;
            END
            $$;

            ALTER TABLE assessment_question
            DROP COLUMN IF EXISTS stream_id;
            """,
        )
    ]
