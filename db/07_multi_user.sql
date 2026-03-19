-- Multi-user schema: bridge columns, project_members, bootstrap flag
-- All statements idempotent (IF NOT EXISTS / DO $$ BEGIN ... END $$)

-- Bridge columns on existing tables (nullable for backward compat)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'projects' AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE projects ADD COLUMN organization_id UUID;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'projects' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE projects ADD COLUMN created_by UUID;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sections' AND column_name = 'updated_by'
    ) THEN
        ALTER TABLE sections ADD COLUMN updated_by UUID;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'section_revisions' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE section_revisions ADD COLUMN created_by UUID;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'section_comments' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE section_comments ADD COLUMN created_by UUID;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'chat_messages' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE chat_messages ADD COLUMN created_by UUID;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'mcp_activity' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE mcp_activity ADD COLUMN user_id UUID;
    END IF;
END $$;

-- Project members (5 roles)
CREATE TABLE IF NOT EXISTS project_members (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'commenter', 'viewer')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(project_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_project_members_user
    ON project_members(user_id);

-- Trigger for updated_at on project_members
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_project_members_updated'
    ) THEN
        CREATE TRIGGER trg_project_members_updated
            BEFORE UPDATE ON project_members
            FOR EACH ROW EXECUTE FUNCTION update_timestamp();
    END IF;
END $$;

-- Bootstrap flag table (ensures first-user setup runs once)
CREATE TABLE IF NOT EXISTS prdforge_bootstrap (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setup_type  TEXT NOT NULL UNIQUE,
    completed   BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
