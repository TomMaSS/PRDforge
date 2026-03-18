-- Multi-user chat: thread types, user attribution, org API key
-- All statements idempotent

-- Add chat_type to project_chats (main thread vs per-section)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'project_chats' AND column_name = 'chat_type'
    ) THEN
        ALTER TABLE project_chats ADD COLUMN chat_type TEXT NOT NULL DEFAULT 'main';
        -- Drop unique constraint on project_id to allow multiple threads
        ALTER TABLE project_chats DROP CONSTRAINT IF EXISTS project_chats_project_id_key;
    END IF;
END $$;

-- Add section_id for per-section threads
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'project_chats' AND column_name = 'section_id'
    ) THEN
        ALTER TABLE project_chats ADD COLUMN section_id UUID REFERENCES sections(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Add created_by for user attribution on chats
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'project_chats' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE project_chats ADD COLUMN created_by UUID;
    END IF;
END $$;

-- Unique constraint: one thread per type per project (per section if section thread)
CREATE UNIQUE INDEX IF NOT EXISTS idx_project_chats_type_section
    ON project_chats(project_id, chat_type, COALESCE(section_id, '00000000-0000-0000-0000-000000000000'));

-- Add encrypted API key to organization table (if it exists from Better Auth)
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organization') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'organization' AND column_name = 'anthropic_api_key_encrypted'
        ) THEN
            ALTER TABLE organization ADD COLUMN anthropic_api_key_encrypted TEXT;
        END IF;
    END IF;
END $$;
