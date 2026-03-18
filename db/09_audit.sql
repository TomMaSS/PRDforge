-- Audit events table
CREATE TABLE IF NOT EXISTS audit_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id     UUID,
    action      TEXT NOT NULL,
    resource    TEXT NOT NULL,
    detail      JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_project
    ON audit_events(project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_user
    ON audit_events(user_id, created_at DESC);
