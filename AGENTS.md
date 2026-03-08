# PRD Forge — Agent Instructions

## Project Overview

PRD Forge is a self-hosted sectional PRD management system. It stores documents in PostgreSQL split into independently addressable sections, and exposes 20 MCP tools for Claude to read/write individual sections with dependency-aware context loading.

## Architecture

Three Docker Compose services:
- **PostgreSQL 16** (`postgres:16-alpine`) — 4 tables, 2 views, schema in `db/01_init.sql`, seed in `db/02_seed.sql`
- **MCP Server** (`mcp_server/server.py`, ~650 lines) — FastMCP with 20 tools, asyncpg, stdio + HTTP transports
- **Web UI** (`ui/app.py`, ~400 lines) — FastAPI, read-only, dark theme, vendored marked.js

## Key Design Principles

1. **Dependency-aware context loading** — `prd_read_section` returns full content for the target section plus only summaries of its dependencies. This is the core value proposition.

2. **Revision-before-update atomicity** — When content is updated, the current content is saved as a revision BEFORE the update, inside the same transaction with `SELECT ... FOR UPDATE`. No content is ever lost.

3. **JSON error responses** — All tools return JSON. Errors are `{"error": "message"}`. Tools never raise exceptions to the MCP transport layer.

4. **Partial UPDATE** — `prd_update_section` only modifies fields that are explicitly provided. Dynamic SQL construction avoids overwriting fields the caller didn't intend to change.

5. **Slug validation** — All slugs must match `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$`, max 100 chars. Validated at the application layer before DB queries.

6. **Same-project dependency enforcement** — `section_dependencies` has a `project_id` column with composite foreign keys `FOREIGN KEY (project_id, section_id) REFERENCES sections(project_id, id)` on both sides. This gives schema-level enforcement that both sides of a dependency belong to the same project. The `prd_add_dependency` tool also uses `INSERT ... SELECT` with a same-project JOIN for friendly error messages.

## File Map

| File | Purpose | ~Lines |
|------|---------|--------|
| `docker-compose.yml` | 3-service stack definition | 45 |
| `db/01_init.sql` | Schema DDL (tables, indexes, triggers, views) | 140 |
| `db/02_seed.sql` | ContentForge sample data (13 sections, 15 deps) | 200+ |
| `mcp_server/server.py` | MCP server with 20 tools | 650 |
| `ui/app.py` | FastAPI read-only web UI | 400 |
| `tests/conftest.py` | Test fixtures (db pool, cleanup, monkeypatch) | 80 |
| `tests/test_mcp_tools.py` | MCP tool tests (30+ tests) | 350 |
| `tests/test_ui_api.py` | UI endpoint tests (8 tests) | 120 |

## MCP Tool Groups

**Group 1 — Project Management (3):** `prd_list_projects`, `prd_create_project`, `prd_delete_project`

**Group 2 — Section CRUD (7):** `prd_list_sections`, `prd_read_section` (primary tool — 3 queries), `prd_create_section`, `prd_update_section` (atomic revision), `prd_delete_section`, `prd_move_section`, `prd_duplicate_section`

**Group 3 — Dependencies (2):** `prd_add_dependency` (idempotent upsert, same-project validation), `prd_remove_dependency`

**Group 4 — Context & Search (3):** `prd_get_overview` (starting point), `prd_search` (FTS + tag:prefix), `prd_get_changelog`

**Group 5 — Revisions (3):** `prd_get_revisions`, `prd_read_revision`, `prd_rollback_section` (atomic with backup)

**Group 6 — Export/Import (2):** `prd_export_markdown` (full doc, use sparingly), `prd_import_markdown` (splits on ## headings, fence-aware)

**Group 7 — Batch (1):** `prd_bulk_status`

## Database Schema Quick Reference

- **projects** — id, name, slug (unique), description, version, created_at, updated_at
- **sections** — id, project_id, parent_section_id, slug, title, section_type, sort_order, status, content, summary, tags[], notes, word_count (generated), created_at, updated_at. UNIQUE(project_id, slug), UNIQUE(project_id, id)
- **section_revisions** — id, section_id, revision_number, content, summary, change_description, created_at. UNIQUE(section_id, revision_number)
- **section_dependencies** — id, project_id, section_id, depends_on_id, dependency_type, description. Composite FKs enforce same-project. UNIQUE(section_id, depends_on_id)
- **section_tree** (view) — sections + project_slug, parent_slug, parent_title, revision_count, dep_out_count, dep_in_count
- **project_changelog** (view) — revisions joined with section and project slugs

## Common Tasks

**Adding a new MCP tool:**
1. Add the tool function to the appropriate group in `server.py`
2. Use `@mcp.tool(annotations={...})` decorator with correct hints
3. Return `json.dumps(result)` or `json.dumps({"error": "..."})` — never raise
4. Add tests in `test_mcp_tools.py`

**Modifying the schema:**
1. Update `db/01_init.sql` (this runs only on first boot)
2. For existing databases: write a migration SQL and run it manually
3. Update `db/02_seed.sql` if the seed data format changed
4. Update AGENTS.md schema reference

**Adding a UI endpoint:**
1. Add the route to `ui/app.py`
2. Query the pool directly (read-only only)
3. Add a test in `test_ui_api.py`

**Running tests:**
```bash
docker compose up -d postgres
pip install -r tests/requirements.txt
pytest tests/ -v
```

## Gotchas

- `word_count` is a GENERATED ALWAYS column — never include in INSERT or UPDATE
- asyncpg returns `Record` objects, not dicts — use `dict(row)` or `row['field']`
- PostgreSQL `TEXT[]` arrays: pass Python lists directly to asyncpg
- `parent_section=""` (empty string) means "move to root" (set `parent_section_id = NULL`)
- Slug collisions: `prd_import_markdown` generates slugs from headings — duplicates are skipped unless `replace_existing=true`
- FastMCP lifespan: uses `@asynccontextmanager` pattern
- Cross-project dependency guard: composite FK at schema level + INSERT...SELECT with JOIN at app level
- Import parser only splits on `## ` (h2 headings) — `###` and deeper are part of the section body
- `/health` endpoint is a v1.1 addition beyond the original PRD §5.1 spec (5 routes → 6)

## Residual Risks

1. **Markdown import parser is heuristic** — fence-state tracking handles common code blocks but won't handle malformed or exotic markdown constructs
2. **No latency/error-rate metrics** — structured logging and `/health` provide basic operability
3. **No reverse proxy hardening** — localhost-only binding prevents accidental LAN exposure
4. **Container image tags** — pinned by tag (`postgres:16-alpine`, `python:3.11-slim`), not by digest
5. **Google Fonts CDN** — offline environments fall back to system fonts

## Testing

Tests run against a real PostgreSQL database (no mocks). The `conftest.py` provides:
- Session-scoped connection pool
- Auto-cleanup that preserves seed data between tests
- Monkeypatched pool for MCP server tests
- httpx `AsyncClient` with `ASGITransport` for UI tests

Concurrency tests verify that concurrent `prd_update_section` calls don't produce revision_number collisions or content loss (using `SELECT ... FOR UPDATE` inside transactions).
