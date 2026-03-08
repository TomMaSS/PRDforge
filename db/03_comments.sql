-- Inline comments (Google Docs-style, anchored to selected text)

CREATE TABLE section_comments (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id      UUID        NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    anchor_text     TEXT        NOT NULL,          -- exact selected text
    anchor_prefix   TEXT        NOT NULL DEFAULT '', -- ~30 chars before for disambiguation
    anchor_suffix   TEXT        NOT NULL DEFAULT '', -- ~30 chars after for disambiguation
    body            TEXT        NOT NULL,           -- comment content (markdown)
    resolved        BOOLEAN     NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_comments_section ON section_comments(section_id);
CREATE INDEX idx_comments_resolved ON section_comments(section_id, resolved);

CREATE TRIGGER comments_updated_at
    BEFORE UPDATE ON section_comments
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();
