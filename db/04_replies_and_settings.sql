-- Comment replies + project settings

-- === comment_replies table ===
CREATE TABLE IF NOT EXISTS comment_replies (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id  UUID        NOT NULL REFERENCES section_comments(id) ON DELETE CASCADE,
    author      TEXT        NOT NULL DEFAULT 'user',
    body        TEXT        NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_replies_comment ON comment_replies(comment_id);

-- Repair: fix any dirty rows first, then add CHECK constraint if missing
UPDATE comment_replies SET author = 'user' WHERE author NOT IN ('user', 'claude');
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'comment_replies_author_check'
            AND conrelid = 'comment_replies'::regclass
    ) THEN
        ALTER TABLE comment_replies ADD CONSTRAINT comment_replies_author_check
            CHECK (author IN ('user', 'claude'));
    END IF;
END $$;

-- === project_settings table ===
CREATE TABLE IF NOT EXISTS project_settings (
    project_id  UUID        PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    settings    JSONB       NOT NULL DEFAULT '{}'::jsonb,
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Repair: add trigger if missing
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'project_settings_updated_at'
            AND tgrelid = 'project_settings'::regclass
    ) THEN
        CREATE TRIGGER project_settings_updated_at
            BEFORE UPDATE ON project_settings
            FOR EACH ROW EXECUTE FUNCTION update_timestamp();
    END IF;
END $$;
