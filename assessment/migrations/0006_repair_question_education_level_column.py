from django.db import migrations


class Migration(migrations.Migration):
    """
    Repair migration.

    assessment.0003 used SeparateDatabaseAndState and assumed the DB already had
    assessment_question.education_level_id. In some environments (like yours)
    that column doesn't exist, causing runtime errors during seeding/queries.
    """

    dependencies = [
        ("assessment", "0005_question_background_dimension"),
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
                AND c.column_name = 'education_level_id';

              -- If column doesn't exist, create with correct UUID type.
              IF col_type IS NULL THEN
                ALTER TABLE assessment_question
                ADD COLUMN education_level_id uuid NULL;
              ELSIF col_type <> 'uuid' THEN
                -- Wrong type (e.g., bigint) from a previous failed attempt.
                -- Drop and recreate as uuid. (Safe because column is expected to be empty in broken environments.)
                ALTER TABLE assessment_question
                DROP COLUMN education_level_id;
                ALTER TABLE assessment_question
                ADD COLUMN education_level_id uuid NULL;
              END IF;

              IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'assessment_question_education_level_id_fk'
              ) THEN
                ALTER TABLE assessment_question
                ADD CONSTRAINT assessment_question_education_level_id_fk
                FOREIGN KEY (education_level_id)
                REFERENCES education_level (id)
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
                WHERE conname = 'assessment_question_education_level_id_fk'
              ) THEN
                ALTER TABLE assessment_question
                DROP CONSTRAINT assessment_question_education_level_id_fk;
              END IF;
            END
            $$;

            ALTER TABLE assessment_question
            DROP COLUMN IF EXISTS education_level_id;
            """,
        )
    ]

