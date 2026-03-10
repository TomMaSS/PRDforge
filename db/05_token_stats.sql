-- Token usage estimates for tracking context savings
CREATE TABLE IF NOT EXISTS token_estimates (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    operation       TEXT        NOT NULL,
    full_doc_tokens INT         NOT NULL,
    loaded_tokens   INT         NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_token_est_project ON token_estimates(project_id);
CREATE INDEX IF NOT EXISTS idx_token_est_created ON token_estimates(project_id, created_at);
