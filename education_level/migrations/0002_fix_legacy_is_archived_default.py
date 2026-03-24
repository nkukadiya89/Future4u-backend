from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("education_level", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'education_level'
                      AND column_name = 'is_archived'
                ) THEN
                    UPDATE education_level
                    SET is_archived = FALSE
                    WHERE is_archived IS NULL;

                    ALTER TABLE education_level
                    ALTER COLUMN is_archived SET DEFAULT FALSE;
                END IF;
            END$$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'education_level'
                      AND column_name = 'is_archived'
                ) THEN
                    ALTER TABLE education_level
                    ALTER COLUMN is_archived DROP DEFAULT;
                END IF;
            END$$;
            """,
        ),
    ]

