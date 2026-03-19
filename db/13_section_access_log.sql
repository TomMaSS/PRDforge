-- Honest token savings: track section-level access for deduplication
-- Replaces the old token_estimates approach which inflated savings

CREATE TABLE IF NOT EXISTS section_access_log (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    operation     TEXT        NOT NULL,
    section_id    UUID        REFERENCES sections(id) ON DELETE SET NULL,
    access_level  TEXT        NOT NULL CHECK (access_level IN ('full', 'summary', 'snippet')),
    loaded_words  INT         NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sal_project_time
    ON section_access_log(project_id, created_at);
