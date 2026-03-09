# PRD Forge

Sectional PRD management system that reduces AI context cost from ~15K to ~500-2000 tokens per edit. Store documents in PostgreSQL, expose section-level read/write via MCP, and browse via a read-only web UI.

## How It Works

Traditional approach: every edit loads the full 15K-token document into context.

PRD Forge approach: each section has a `content` field (full body, loaded when editing) and a `summary` field (1-3 sentences, loaded as context for dependent sections). When Claude reads a section, it receives full content for that section plus only summaries of related sections.

**Example:** Reading `data-model` (820 words, ~1200 tokens) also loads summaries of `tech-stack` (~60 tokens) and `pipeline` (~60 tokens) — total ~1320 tokens instead of ~15,000.

## Architecture

```mermaid
graph LR
    A[Claude.ai / Claude Code / Claude Desktop] <-->|MCP Protocol| B[MCP Server<br/>FastMCP/Python<br/>:8080]
    B <-->|asyncpg| C[(PostgreSQL 16<br/>sections, revisions<br/>dependencies, comments)]
    D[Web UI<br/>FastAPI<br/>:8088] <-->|read + comments| C
    A -.->|reads comments| D
```

Three services:
- **PostgreSQL 16** — source of truth (7 tables, 2 views)
- **MCP Server** — 28 tools for Claude integration (stdio + HTTP transports)
- **Web UI** — dark-theme browser interface with inline comments, vertical nav rail, and project settings

## Quick Start

```bash
cd PRDforge
./install.sh
```

This single command:
1. Starts Docker services (PostgreSQL, MCP server, Web UI)
2. Configures your Claude client (Code or Desktop)
3. Validates everything works

```bash
# Options
./install.sh --claude-code      # Non-interactive (HTTP transport)
./install.sh --claude-desktop   # Non-interactive (stdio transport)
./install.sh --uninstall        # Remove config + optionally stop services
```

The stack starts in ~15 seconds. PostgreSQL seeds a sample "ContentForge" project on first boot.

After install, restart your Claude client. Web UI: http://localhost:8088

## MCP Configuration (Manual)

If you prefer to configure manually instead of using `install.sh`:

<details>
<summary>Claude Code (HTTP — recommended with Docker)</summary>

Add to `~/.claude/mcp.json` (or `.claude/mcp.json` in project):
```json
{
  "mcpServers": {
    "prd-forge": {
      "type": "http",
      "url": "http://localhost:8080/mcp/"
    }
  }
}
```

Start services: `docker compose up -d`
</details>

<details>
<summary>Claude Desktop (stdio)</summary>

1. Install Python dependencies:
   ```bash
   cd PRDforge/mcp_server
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```

2. Open Claude Desktop → **Settings → Developer → Edit Config**:
   ```json
   {
     "mcpServers": {
       "prd-forge": {
         "command": "/absolute/path/to/PRDforge/mcp_server/.venv/bin/python",
         "args": ["/absolute/path/to/PRDforge/mcp_server/server.py"],
         "env": {
           "DATABASE_URL": "postgresql://prdforge:prdforge@localhost:5432/prdforge"
         }
       }
     }
   }
   ```

3. Start postgres: `docker compose up -d postgres`
4. Restart Claude Desktop (Cmd+Q, reopen)

> **Note:** Claude Desktop does not support HTTP transport. Use stdio (spawns server as subprocess).
</details>

<details>
<summary>HTTP transport (claude.ai or other MCP clients)</summary>

```json
{
  "mcpServers": {
    "prd-forge": {
      "type": "streamable-http",
      "url": "http://localhost:8080/mcp/"
    }
  }
}
```
</details>

## Tool Reference

| Tool | Group | Description | ~Tokens |
|------|-------|-------------|---------|
| `prd_list_projects` | Project | List all projects with stats | 50 |
| `prd_create_project` | Project | Create new project | — |
| `prd_delete_project` | Project | Delete project (cascades) | — |
| `prd_list_sections` | Section | List sections (metadata only) | 200 |
| `prd_read_section` | Section | Read section + dependency context | 500-3000 |
| `prd_create_section` | Section | Create new section | — |
| `prd_update_section` | Section | Update fields, auto-revision on content change | — |
| `prd_delete_section` | Section | Delete section (warns about deps) | — |
| `prd_move_section` | Section | Change sort_order or parent | — |
| `prd_duplicate_section` | Section | Copy section with new slug | — |
| `prd_add_dependency` | Deps | Add/update dependency (idempotent) | — |
| `prd_remove_dependency` | Deps | Remove dependency | — |
| `prd_get_overview` | Context | Project overview with summaries | 400 |
| `prd_search` | Context | Full-text or tag search | 200 |
| `prd_get_changelog` | Context | Recent revision history | 300 |
| `prd_get_revisions` | Revision | List revision metadata | 100 |
| `prd_read_revision` | Revision | Read revision content | 500-3000 |
| `prd_rollback_section` | Revision | Rollback with backup | — |
| `prd_export_markdown` | Export | Full document as markdown | 15000+ |
| `prd_import_markdown` | Import | Import from markdown (splits on ##) | — |
| `prd_bulk_status` | Batch | Update status for multiple sections | — |
| `prd_list_comments` | Comments | List all comments across project with section pointers | 100-500 |
| `prd_add_comment` | Comments | Add inline comment anchored to selected text | — |
| `prd_resolve_comment` | Comments | Resolve/reopen a comment after implementing changes | — |
| `prd_delete_comment` | Comments | Delete a comment | — |
| `prd_add_comment_reply` | Replies | Add a reply to an inline comment | — |
| `prd_get_settings` | Settings | Get project settings (merged defaults + overrides) | 50 |
| `prd_update_settings` | Settings | Update project settings | — |

## Inline Comments

Google Docs-style comments anchored to specific text in any section:

1. **In the UI** — select text in a section → click "+ Comment" → write your note → Save
2. **Via MCP** — `prd_add_comment(project, section, anchor_text, body)` with optional `anchor_prefix`/`anchor_suffix` for disambiguation
3. **Claude scans comments** — `prd_list_comments` returns all open comments with section pointers (~100 tokens), then read only the sections that have feedback
4. **Claude reads comments** — `prd_read_section` includes all comments with their anchor text and body
5. **Resolve after implementing** — use `prd_resolve_comment` or click "Resolve" in the UI

Workflow: leave comments → ask Claude to check feedback → Claude calls `prd_list_comments` to see which sections have comments → reads only those sections → implements changes → resolves comments.

## Data Model

```mermaid
erDiagram
    projects ||--o{ sections : has
    sections ||--o{ section_revisions : tracks
    sections ||--o{ section_dependencies : from
    sections ||--o{ section_dependencies : to
    sections ||--o{ section_comments : has
    section_comments ||--o{ comment_replies : has
    projects ||--o| project_settings : has
    sections ||--o| sections : parent

    projects {
        uuid id PK
        text slug UK
        text name
        int version
    }
    sections {
        uuid id PK
        uuid project_id FK
        text slug
        text content
        text summary
        text status
        text[] tags
        int word_count
    }
    section_revisions {
        uuid id PK
        uuid section_id FK
        int revision_number
        text content
        text summary
    }
    section_dependencies {
        uuid id PK
        uuid project_id FK
        uuid section_id FK
        uuid depends_on_id FK
        text dependency_type
    }
    section_comments {
        uuid id PK
        uuid section_id FK
        text anchor_text
        text body
        boolean resolved
    }
    comment_replies {
        uuid id PK
        uuid comment_id FK
        text author
        text body
    }
    project_settings {
        uuid project_id PK_FK
        jsonb settings
    }
```

## Dependency Graph (Seed Data)

```mermaid
graph TD
    HW[hardware] --> TS[tech-stack]
    TS --> DM[data-model]
    TS --> PL[pipeline]
    HW --> PL
    DM --> PL
    DM --> API[api-spec]
    PL --> API
    PL --> CUI[comfyui-workflows]
    API --> UI[ui-design]
    TS --> DEP[deployment]
    HW --> DEP
    DM --> TL[timeline]
    PL --> TL
    UI --> TL
    DEP --> TL
```

## Dependency Types

When linking sections with `prd_add_dependency`, use one of these types:

| Type | Meaning | Example |
|------|---------|---------|
| `blocks` | Section cannot proceed until dependency is complete | `pipeline` blocks `api-spec` |
| `extends` | Section builds upon or extends the dependency | `api-spec` extends `data-model` |
| `implements` | Section implements what the dependency specifies | `ui-design` implements `api-spec` |
| `references` | Section references the dependency for context (default) | `security` references `tech-stack` |

## Tags

Tags categorize sections for filtering and search (via `prd_search(query="tag:mvp")`):

| Tag | Purpose |
|-----|---------|
| `mvp` | Part of minimum viable product scope |
| `core` | Core system functionality |
| `infra` | Infrastructure and deployment concerns |
| `ai` | AI/ML related components |
| `frontend` | User-facing interface components |

Tags are freeform — you can create any tag. The above are conventions used in the seed data.

## Section Statuses

| Status | Meaning |
|--------|---------|
| `draft` | Initial writing, not yet reviewed |
| `in_progress` | Actively being worked on |
| `review` | Ready for review |
| `approved` | Finalized and approved |
| `outdated` | Needs update due to changes in dependencies |

## Usage Examples

**Standard editing workflow:**
```
prd_get_overview(project="contentforge")           → TOC + summaries (~400 tokens)
prd_read_section(project="contentforge", section="data-model")  → full content + dep summaries
prd_update_section(project="contentforge", section="data-model",
    content="...updated...", change_description="Added Schedule entity")
```

**Impact analysis:**
```
prd_read_section(section="tech-stack")  → see depended_by list
# Then update each dependent section in order
```

**Comment-driven editing (auto-resolve):**
```
prd_read_section(project="contentforge", section="tech-stack")
  → content + 2 open comments with IDs + replies
prd_update_section(project="contentforge", section="tech-stack",
    content="...updated...", change_description="Switched Redis to Valkey",
    resolve_comments=["comment-id-1", "comment-id-2"])
  → atomically updates content + resolves comments + auto-replies if setting enabled
```

**Rollback:**
```
prd_get_revisions(section="data-model")     → see revision history
prd_rollback_section(section="data-model", revision=3)  → restore, current saved as backup
```

## Seed Data

The "ContentForge" sample project ships with 13 sections:

| # | Slug | Title | Status | Tags |
|---|------|-------|--------|------|
| 0 | overview | Overview & Goals | approved | mvp, core |
| 1 | hardware | Hardware Constraints | approved | infra, core |
| 2 | tech-stack | Technology Stack | approved | mvp, core |
| 3 | data-model | Data Model | in_progress | mvp, core |
| 4 | pipeline | Processing Pipeline | in_progress | mvp, core, ai |
| 5 | comfyui-workflows | ComfyUI Workflows | draft | ai |
| 6 | api-spec | API Specification | in_progress | mvp, frontend |
| 7 | ui-design | UI Design | draft | frontend |
| 8 | deployment | Deployment Strategy | approved | infra |
| 9 | security | Security Model | draft | infra |
| 10 | legal | Legal & Compliance | draft | — |
| 11 | risks | Risks & Mitigations | draft | — |
| 12 | timeline | Implementation Timeline | in_progress | mvp |

## Backup & Restore

```bash
# Export as markdown
curl http://localhost:8088/api/projects/contentforge/export > backup.md

# PostgreSQL dump
docker exec prdforge-postgres-1 pg_dump -U prdforge prdforge > backup.sql

# Full reset (destroys all data)
docker compose down -v
docker compose up -d
```

## Security Notes

- All ports bound to `127.0.0.1` — not accessible from LAN by default
- No authentication — single-user local tool
- For non-local access, put behind a reverse proxy with TLS
- Database credentials are defaults — acceptable for local personal tool

## Known Limitations

- Markdown import parser splits on `## ` headings only (heuristic, handles code fences)
- No latency/error-rate metrics (structured logging + `/health` endpoint only)
- No reverse proxy hardening — localhost-only binding prevents accidental exposure
- Container images pinned by tag, not digest
- Google Fonts CDN for Inter/JetBrains Mono — offline falls back to system fonts

## Development

```bash
# Run tests (requires postgres running)
docker compose up -d postgres
pip install -r tests/requirements.txt
pytest tests/test_mcp_tools.py tests/test_ui_api.py -v

# Smoke tests (full stack)
docker compose down -v && docker compose up -d
pytest tests/test_smoke.py -v
```

**Project structure:**
```
PRDforge/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── claude_mcp_config.json
├── README.md
├── AGENTS.md
├── prd.md
├── db/
│   ├── 01_init.sql
│   ├── 02_seed.sql
│   ├── 03_comments.sql
│   └── 04_replies_and_settings.sql
├── shared/
│   ├── __init__.py
│   └── settings.py
├── mcp_server/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── server.py
├── ui/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   └── static/
│       ├── marked.min.js
│       ├── highlight.min.js
│       ├── github-dark.min.css
│       └── MARKED_VERSION
└── tests/
    ├── requirements.txt
    ├── conftest.py
    ├── test_mcp_tools.py
    └── test_ui_api.py
```

## License

MIT
