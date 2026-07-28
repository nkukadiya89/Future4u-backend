from django.db import migrations

SQL_FORWARD = """
-- 1. Drop FK from career_chat_message that references career_chat_session
DO $$
DECLARE
    fk_name text;
BEGIN
    SELECT conname INTO fk_name FROM pg_constraint
    WHERE conrelid = 'career_chat_message'::regclass
      AND confrelid = 'career_chat_session'::regclass
      AND contype = 'f';
    IF fk_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE career_chat_message DROP CONSTRAINT ' || quote_ident(fk_name);
    END IF;
END $$;

-- 2. Drop FKs on career_chat_session itself (self-referencing)
DO $$
DECLARE
    rec record;
BEGIN
    FOR rec IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'career_chat_session'::regclass
          AND contype = 'f'
    LOOP
        EXECUTE 'ALTER TABLE career_chat_session DROP CONSTRAINT ' || quote_ident(rec.conname);
    END LOOP;
END $$;

-- 3. Drop indexes on career_chat_session (except primary key)
DROP INDEX IF EXISTS career_chat_session_created_at_bc9650a0;
DROP INDEX IF EXISTS career_chat_session_updated_at_50d13a87;
DROP INDEX IF EXISTS career_chat_session_created_by_id_69231d85;
DROP INDEX IF EXISTS career_chat_session_deleted_by_id_b1ec61fe;
DROP INDEX IF EXISTS career_chat_session_updated_by_id_747b995e;
DROP INDEX IF EXISTS career_chat_session_child_id_7d724bc5;

-- 4. Create new table with correct column order
CREATE TABLE career_chat_session_new (
    id              bigint NOT NULL,
    created_at      timestamptz NOT NULL,
    updated_at      timestamptz,
    deleted_at      timestamptz,
    deleted         boolean NOT NULL,
    summary         text NOT NULL DEFAULT '',
    created_by_id   bigint,
    deleted_by_id   bigint,
    suggestion_id   bigint NOT NULL,
    child_id        bigint,
    updated_by_id   bigint
);

-- 5. Copy data
INSERT INTO career_chat_session_new
    SELECT id, created_at, updated_at, deleted_at, deleted, summary,
           created_by_id, deleted_by_id, suggestion_id, child_id, updated_by_id
    FROM career_chat_session;

-- 6. Drop old table (no CASCADE - all FKs and indexes already dropped)
DROP TABLE career_chat_session;

-- 7. Rename new table
ALTER TABLE career_chat_session_new RENAME TO career_chat_session;

-- 8. Recreate primary key
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_pkey PRIMARY KEY (id);

-- 9. Recreate foreign keys on career_chat_session
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_created_by_id_fk
    FOREIGN KEY (created_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_deleted_by_id_fk
    FOREIGN KEY (deleted_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_suggestion_id_fk
    FOREIGN KEY (suggestion_id) REFERENCES career_suggestion(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_updated_by_id_fk
    FOREIGN KEY (updated_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_child_id_fk
    FOREIGN KEY (child_id) REFERENCES parent_child_profile(id) DEFERRABLE INITIALLY DEFERRED;

-- 10. Recreate unique constraint
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_suggestion_id_key UNIQUE (suggestion_id);

-- 11. Recreate indexes
CREATE INDEX career_chat_session_created_at_idx ON career_chat_session USING btree (created_at);
CREATE INDEX career_chat_session_updated_at_idx ON career_chat_session USING btree (updated_at);
CREATE INDEX career_chat_session_created_by_id_idx ON career_chat_session USING btree (created_by_id);
CREATE INDEX career_chat_session_deleted_by_id_idx ON career_chat_session USING btree (deleted_by_id);
CREATE INDEX career_chat_session_updated_by_id_idx ON career_chat_session USING btree (updated_by_id);
CREATE INDEX career_chat_session_child_id_idx ON career_chat_session USING btree (child_id);

-- 12. Recreate FK from career_chat_message to career_chat_session
ALTER TABLE ONLY career_chat_message
    ADD CONSTRAINT career_chat_message_session_id_fk
    FOREIGN KEY (session_id) REFERENCES career_chat_session(id) DEFERRABLE INITIALLY DEFERRED;

-- 13. Recreate sequence
CREATE SEQUENCE IF NOT EXISTS career_chat_session_id_seq
    OWNED BY career_chat_session.id;
ALTER TABLE career_chat_session ALTER COLUMN id
    SET DEFAULT nextval('career_chat_session_id_seq');
SELECT setval('career_chat_session_id_seq',
    COALESCE((SELECT MAX(id) FROM career_chat_session), 1), true);
"""

SQL_REVERSE = """
-- Reverse: put child_id back to end
DO $$
DECLARE
    fk_name text;
BEGIN
    SELECT conname INTO fk_name FROM pg_constraint
    WHERE conrelid = 'career_chat_message'::regclass
      AND confrelid = 'career_chat_session'::regclass
      AND contype = 'f';
    IF fk_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE career_chat_message DROP CONSTRAINT ' || quote_ident(fk_name);
    END IF;
END $$;

DO $$
DECLARE
    rec record;
BEGIN
    FOR rec IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'career_chat_session'::regclass
          AND contype = 'f'
    LOOP
        EXECUTE 'ALTER TABLE career_chat_session DROP CONSTRAINT ' || quote_ident(rec.conname);
    END LOOP;
END $$;

DROP INDEX IF EXISTS career_chat_session_created_at_idx;
DROP INDEX IF EXISTS career_chat_session_updated_at_idx;
DROP INDEX IF EXISTS career_chat_session_created_by_id_idx;
DROP INDEX IF EXISTS career_chat_session_deleted_by_id_idx;
DROP INDEX IF EXISTS career_chat_session_updated_by_id_idx;
DROP INDEX IF EXISTS career_chat_session_child_id_idx;

CREATE TABLE career_chat_session_old (
    id              bigint NOT NULL,
    created_at      timestamptz NOT NULL,
    updated_at      timestamptz,
    deleted_at      timestamptz,
    deleted         boolean NOT NULL,
    summary         text NOT NULL DEFAULT '',
    created_by_id   bigint,
    deleted_by_id   bigint,
    suggestion_id   bigint NOT NULL,
    updated_by_id   bigint,
    child_id        bigint
);

INSERT INTO career_chat_session_old
    SELECT id, created_at, updated_at, deleted_at, deleted, summary,
           created_by_id, deleted_by_id, suggestion_id, updated_by_id, child_id
    FROM career_chat_session;

DROP TABLE career_chat_session;
ALTER TABLE career_chat_session_old RENAME TO career_chat_session;

ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_pkey PRIMARY KEY (id);
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_created_by_id_fk
    FOREIGN KEY (created_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_deleted_by_id_fk
    FOREIGN KEY (deleted_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_suggestion_id_fk
    FOREIGN KEY (suggestion_id) REFERENCES career_suggestion(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_updated_by_id_fk
    FOREIGN KEY (updated_by_id) REFERENCES "user"(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_child_id_fk
    FOREIGN KEY (child_id) REFERENCES parent_child_profile(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY career_chat_session
    ADD CONSTRAINT career_chat_session_suggestion_id_key UNIQUE (suggestion_id);
CREATE INDEX career_chat_session_created_at_idx ON career_chat_session USING btree (created_at);
CREATE INDEX career_chat_session_updated_at_idx ON career_chat_session USING btree (updated_at);
CREATE INDEX career_chat_session_created_by_id_idx ON career_chat_session USING btree (created_by_id);
CREATE INDEX career_chat_session_deleted_by_id_idx ON career_chat_session USING btree (deleted_by_id);
CREATE INDEX career_chat_session_updated_by_id_idx ON career_chat_session USING btree (updated_by_id);
CREATE INDEX career_chat_session_child_id_idx ON career_chat_session USING btree (child_id);
ALTER TABLE ONLY career_chat_message
    ADD CONSTRAINT career_chat_message_session_id_fk
    FOREIGN KEY (session_id) REFERENCES career_chat_session(id) DEFERRABLE INITIALLY DEFERRED;
CREATE SEQUENCE IF NOT EXISTS career_chat_session_id_seq
    OWNED BY career_chat_session.id;
ALTER TABLE career_chat_session ALTER COLUMN id
    SET DEFAULT nextval('career_chat_session_id_seq');
SELECT setval('career_chat_session_id_seq',
    COALESCE((SELECT MAX(id) FROM career_chat_session), 1), true);
"""


class Migration(migrations.Migration):

    dependencies = [
        ("assessment_career", "0014_backfill_chat_session_child"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL_FORWARD, reverse_sql=SQL_REVERSE),
    ]
