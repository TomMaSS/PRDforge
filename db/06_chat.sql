-- Project chat memory (one chat thread per project)

CREATE TABLE IF NOT EXISTS project_chats (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID        NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id     UUID        NOT NULL REFERENCES project_chats(id) ON DELETE CASCADE,
    role        TEXT        NOT NULL,
    content     TEXT        NOT NULL DEFAULT '',
    metadata    JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_project_chats_project ON project_chats(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_created ON chat_messages(chat_id, created_at);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chat_messages_role_check'
            AND conrelid = 'chat_messages'::regclass
    ) THEN
        ALTER TABLE chat_messages ADD CONSTRAINT chat_messages_role_check
            CHECK (role IN ('user', 'assistant', 'system', 'tool'));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'project_chats_updated_at'
            AND tgrelid = 'project_chats'::regclass
    ) THEN
        CREATE TRIGGER project_chats_updated_at
            BEFORE UPDATE ON project_chats
            FOR EACH ROW EXECUTE FUNCTION update_timestamp();
    END IF;
END $$;
