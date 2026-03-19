-- MCP activity tracking (write operations only)
CREATE TABLE IF NOT EXISTS mcp_activity (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID REFERENCES projects(id) ON DELETE CASCADE,
    tool_name   TEXT NOT NULL,
    detail      JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mcp_activity_project
    ON mcp_activity(project_id, created_at DESC);
