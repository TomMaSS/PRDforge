-- PRDforge Schema DDL

-- Tables
CREATE TABLE projects (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL,
    slug        TEXT        NOT NULL UNIQUE,
    description TEXT        NOT NULL DEFAULT '',
    version     INT         NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sections (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_section_id UUID        REFERENCES sections(id) ON DELETE SET NULL,
    slug              TEXT        NOT NULL,
    title             TEXT        NOT NULL,
    section_type      TEXT        NOT NULL DEFAULT 'general',
    sort_order        INT         NOT NULL DEFAULT 0,
    status            TEXT        NOT NULL DEFAULT 'draft',
    content           TEXT        NOT NULL DEFAULT '',
    summary           TEXT        NOT NULL DEFAULT '',
    tags              TEXT[]      NOT NULL DEFAULT '{}',
    notes             TEXT        NOT NULL DEFAULT '',
    word_count        INT GENERATED ALWAYS AS (
                          CASE WHEN trim(content) = '' THEN 0
                               ELSE array_length(regexp_split_to_array(trim(content), '\s+'), 1)
                          END
                      ) STORED,
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now(),
    UNIQUE(project_id, slug),
    UNIQUE(project_id, id)  -- needed for composite FK from section_dependencies
);

CREATE TABLE section_revisions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id         UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    revision_number    INT  NOT NULL,
    content            TEXT NOT NULL,
    summary            TEXT NOT NULL DEFAULT '',
    change_description TEXT NOT NULL DEFAULT '',
    created_at         TIMESTAMPTZ DEFAULT now(),
    UNIQUE(section_id, revision_number)
);

CREATE TABLE section_dependencies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL,
    section_id      UUID NOT NULL,
    depends_on_id   UUID NOT NULL,
    dependency_type TEXT NOT NULL DEFAULT 'references',
    description     TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (project_id, section_id) REFERENCES sections(project_id, id) ON DELETE CASCADE,
    FOREIGN KEY (project_id, depends_on_id) REFERENCES sections(project_id, id) ON DELETE CASCADE,
    UNIQUE(section_id, depends_on_id),
    CHECK (section_id != depends_on_id)
);

CREATE TABLE project_chats (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID        NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chat_messages (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id      UUID        NOT NULL REFERENCES project_chats(id) ON DELETE CASCADE,
    role         TEXT        NOT NULL,
    content      TEXT        NOT NULL DEFAULT '',
    metadata     JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ DEFAULT now(),
    CHECK (role IN ('user', 'assistant', 'system', 'tool'))
);

-- Indexes
CREATE INDEX idx_sections_project   ON sections(project_id);
CREATE INDEX idx_sections_parent    ON sections(parent_section_id);
CREATE INDEX idx_sections_status    ON sections(status);
CREATE INDEX idx_sections_slug      ON sections(slug);
CREATE INDEX idx_revisions_section  ON section_revisions(section_id);
CREATE INDEX idx_revisions_created  ON section_revisions(created_at);
CREATE INDEX idx_deps_section       ON section_dependencies(section_id);
CREATE INDEX idx_deps_depends_on    ON section_dependencies(depends_on_id);
CREATE INDEX idx_sections_tags      ON sections USING gin(tags);
CREATE INDEX idx_deps_project_section ON section_dependencies(project_id, section_id);
CREATE INDEX idx_deps_project_depends ON section_dependencies(project_id, depends_on_id);
CREATE INDEX idx_project_chats_project ON project_chats(project_id);
CREATE INDEX idx_chat_messages_chat_created ON chat_messages(chat_id, created_at);

-- Full-text search
CREATE INDEX idx_sections_fts ON sections
    USING gin(to_tsvector('english',
        coalesce(title,'') || ' ' || coalesce(content,'') || ' ' || coalesce(notes,'')
    ));

-- Triggers
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sections_updated_at
    BEFORE UPDATE ON sections
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER project_chats_updated_at
    BEFORE UPDATE ON project_chats
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Views
CREATE VIEW section_tree AS
SELECT
    s.*,
    p.slug                          AS project_slug,
    parent.slug                     AS parent_slug,
    parent.title                    AS parent_title,
    COALESCE(rev_counts.cnt, 0)     AS revision_count,
    COALESCE(dep_out.cnt, 0)        AS dep_out_count,
    COALESCE(dep_in.cnt, 0)         AS dep_in_count
FROM sections s
JOIN projects p ON p.id = s.project_id
LEFT JOIN sections parent ON parent.id = s.parent_section_id
LEFT JOIN (
    SELECT section_id, COUNT(*) AS cnt FROM section_revisions GROUP BY section_id
) rev_counts ON rev_counts.section_id = s.id
LEFT JOIN (
    SELECT section_id, COUNT(*) AS cnt FROM section_dependencies GROUP BY section_id
) dep_out ON dep_out.section_id = s.id
LEFT JOIN (
    SELECT depends_on_id, COUNT(*) AS cnt FROM section_dependencies GROUP BY depends_on_id
) dep_in ON dep_in.depends_on_id = s.id;

CREATE VIEW project_changelog AS
SELECT
    p.slug                    AS project_slug,
    s.slug                    AS section_slug,
    s.title                   AS section_title,
    r.revision_number,
    r.change_description,
    r.created_at
FROM section_revisions r
JOIN sections s ON s.id = r.section_id
JOIN projects p ON p.id = s.project_id;
