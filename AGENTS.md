# PRD Forge — Agent Instructions

## Project Overview

PRD Forge is a self-hosted sectional PRD management system. It stores documents in PostgreSQL split into independently addressable sections, and exposes 31 MCP tools for Claude to read/write individual sections with dependency-aware context loading. The web UI supports inline comments (Google Docs-style) with threaded replies, a vertical nav rail, per-project settings, project creation/switching, and an always-visible project-level Claude chat with optional selection context from sections plus text file attachments.

## Architecture

Four Docker Compose services:
- **PostgreSQL 16** (`postgres:16-alpine`) — 11 tables, 2 views, schema in `db/01_init.sql`, seed in `db/02_seed.sql` (SnapHabit sample, 12 sections), comments in `db/03_comments.sql`, replies+settings in `db/04_replies_and_settings.sql`, token stats in `db/05_token_stats.sql`, chat memory in `db/06_chat.sql`, MCP activity in `db/08_mcp_activity.sql`
- **MCP Server** (`mcp_server/server.py`, ~1560 lines) — FastMCP with 31 tools, asyncpg, stdio + HTTP transports
- **Python API** (`api/app.py`, ~1620 lines) — FastAPI backend, REST endpoints for projects/sections/chat/comments/token-stats
- **Frontend** (`frontend/`, Next.js 15) — React 19, Tailwind v4, shadcn/ui. Proxies `/api/*` to Python API
- **Shared** (`shared/settings.py`) — Settings schema + validation, imported by both MCP server and Python API

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
| `docker-compose.yml` | 4-service stack definition | 75 |
| `db/01_init.sql` | Schema DDL (tables, indexes, triggers, views) | 154 |
| `db/02_seed.sql` | SnapHabit sample seed (12 sections, 12 deps) | 570 |
| `db/05_token_stats.sql` | Token usage estimates table | 12 |
| `db/06_chat.sql` | Chat tables migration (project chats + messages) | 41 |
| `db/08_mcp_activity.sql` | MCP write activity tracking | 12 |
| `docs/tool-reference.md` | MCP tool table and usage examples | 100 |
| `docs/data-model.md` | ER diagram, dependency types, statuses, tags | 141 |
| `docs/scaling.md` | Multi-user and scaling guidance | 90 |
| `db/03_comments.sql` | Inline comments table (section_comments) | 20 |
| `db/04_replies_and_settings.sql` | Comment replies + project settings tables | 40 |
| `shared/settings.py` | Settings schema, defaults, validation (shared) | 30 |
| `mcp_server/server.py` | MCP server with 31 tools + activity tracking | 1560 |
| `api/app.py` | FastAPI Python API (REST endpoints, chat, auth) | 1620 |
| `api/auth.py` | Python auth middleware (session validation, role resolution) | 100 |
| `api/auth_contract.py` | Better Auth table/column contract verification | 50 |
| `api/errors.py` | Structured error responses (9 error codes) | 70 |
| `api/ws.py` | WebSocket token minting + verification (HMAC-SHA256) | 80 |
| `frontend/` | Next.js 15 frontend (React 19, Tailwind v4, shadcn/ui) | — |
| `frontend/server.ts` | Custom Node server with WS proxy | 45 |
| `frontend/prisma/schema.prisma` | Better Auth tables (7 models) | 110 |
| `tests/conftest.py` | Test fixtures (db pool, cleanup, monkeypatch) | 64 |
| `tests/test_mcp_tools.py` | MCP tool tests (53 tests) | 700+ |
| `tests/test_ui_api.py` | UI endpoint tests (71 tests) | 940+ |
| `tests/test_smoke.py` | CI smoke tests (MCP, DB, UI, seed data) | 85 |
| `.github/workflows/test.yml` | CI: runs 124 tests on every PR to main | 50 |
| `.github/workflows/build-and-push.yml` | CD: builds 3 Docker images on tag push | 65 |

## MCP Tool Groups

**Group 1 — Project Management (3):** `prd_list_projects`, `prd_create_project`, `prd_delete_project`

**Group 2 — Section CRUD (7):** `prd_list_sections`, `prd_read_section` (primary tool — 3 queries), `prd_create_section`, `prd_update_section` (atomic revision), `prd_delete_section`, `prd_move_section`, `prd_duplicate_section`

**Group 3a — Dependencies (3):** `prd_add_dependency` (idempotent upsert, same-project validation), `prd_remove_dependency`, `prd_suggest_dependencies` (FTS-based content similarity suggestions)

**Group 3b — Inline Comments (4):** `prd_list_comments` (all comments across project with section pointers — use FIRST to find feedback), `prd_add_comment` (anchored to selected text with prefix/suffix context), `prd_resolve_comment` (mark as done after implementing, ownership-validated), `prd_delete_comment` (ownership-validated)

**Group 3c — Comment Replies (1):** `prd_add_comment_reply` (threaded replies with author 'user'/'claude', ownership-validated)

**Group 4 — Context & Search (4):** `prd_get_overview` (starting point), `prd_search` (FTS + tag:prefix), `prd_get_changelog`, `prd_token_stats` (cumulative token savings per project)

**Group 5 — Revisions (3):** `prd_get_revisions`, `prd_read_revision`, `prd_rollback_section` (atomic with backup)

**Group 6 — Export/Import (2):** `prd_export_markdown` (full doc, use sparingly), `prd_import_markdown` (configurable heading level or manual delimiter, fence-aware)

**Group 7 — Batch (1):** `prd_bulk_status`

**Group 8 — Project Settings (2):** `prd_get_settings` (merged defaults + DB overrides), `prd_update_settings` (validates against SETTINGS_SCHEMA)

## Database Schema Quick Reference

- **projects** — id, name, slug (unique), description, version, organization_id, created_by, created_at, updated_at
- **sections** — id, project_id, parent_section_id, slug, title, section_type, sort_order, status, content, summary, tags[], notes, word_count (generated), updated_by, created_at, updated_at. UNIQUE(project_id, slug), UNIQUE(project_id, id)
- **section_revisions** — id, section_id, revision_number, content, summary, change_description, created_by, created_at. UNIQUE(section_id, revision_number)
- **section_dependencies** — id, project_id, section_id, depends_on_id, dependency_type, description. Composite FKs enforce same-project. UNIQUE(section_id, depends_on_id)
- **section_comments** — id, section_id, anchor_text, anchor_prefix, anchor_suffix, body, resolved, created_by, created_at, updated_at
- **comment_replies** — id, comment_id (FK section_comments), author ('user'|'claude' CHECK), body, created_at
- **project_settings** — project_id (PK, FK projects), settings (JSONB, merged with defaults at read time), updated_at
- **token_estimates** — id, project_id (FK projects), operation, full_doc_tokens, loaded_tokens, created_at
- **project_chats** — id, project_id, chat_type ('main'|section), section_id, created_by, created_at, updated_at. Multi-thread support.
- **chat_messages** — id, chat_id (FK project_chats), role, content, metadata (JSONB), created_by, created_at
- **mcp_activity** — id, project_id, tool_name, detail (JSONB), user_id, created_at. 12 mutating tools.
- **project_members** — id, project_id, user_id, role (owner/admin/editor/commenter/viewer), created_at, updated_at
- **audit_events** — id, project_id, user_id, action, resource, detail (JSONB), created_at
- **password_reset_tokens** — id, user_id, token, expires_at, used, created_by, created_at
- **prdforge_bootstrap** — id, setup_type (unique), completed, created_at
- Better Auth tables: user, session, account, verification, organization, member, invitation (managed by Prisma)
- **section_tree** (view) — sections + project_slug, parent_slug, parent_title, revision_count, dep_out_count, dep_in_count
- **project_changelog** (view) — revisions joined with section and project slugs

## UI Change Workflow

**IMPORTANT: Design-first rule.** When making ANY UI changes (new features, layout changes, component additions), ALWAYS update the Pencil design file (`/Users/artem/git/design/main.pen`) FIRST using the Pencil MCP tools, then implement the code changes in `ui/app.py`. This ensures the design stays in sync with the implementation.

1. Open the `.pen` file with `get_editor_state()`
2. Find the relevant screen frame and update/add the design
3. Verify with `get_screenshot()`
4. Then implement the code changes

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

**Adding an API endpoint:**
1. Add the route to `api/app.py`
2. Query the pool directly
3. Add a test in `test_ui_api.py`

**After ANY changes:**
1. Update `README.md` — architecture diagram, tool reference table, data model diagram, project structure tree, and any affected sections
2. Update `AGENTS.md` — file map (line counts), tool groups, schema reference, gotchas
3. Keep tool counts, table counts, and line estimates accurate across both docs

**Running tests:**
```bash
docker compose up -d postgres
cd /Users/artem/git/personal/PRDforge
uvx --from pytest pytest tests/ -v --override asyncpg --override fastapi --override httpx --override uvicorn
# Or with a venv:
python -m venv .venv && .venv/bin/pip install -r tests/requirements.txt
.venv/bin/pytest tests/ -v
```
**Important:** Always use `uvx` or a virtual environment for running tests — never install packages into the global Python environment.

## Git Branching Strategy

Always work on **feature branches**, never commit directly to `main` or `multiuser`.

### Branch naming

| Type | Pattern | Example |
|------|---------|---------|
| New feature | `feature/<short-name>` | `feature/pdf-export` |
| Bug fix | `fix/<short-name>` | `fix/sidebar-status-dot` |
| Documentation | `docs/<short-name>` | `docs/token-stats-metrics` |
| Refactor | `refactor/<short-name>` | `refactor/auth-middleware` |

### Workflow

```bash
# 1. Create branch from the current base (usually multiuser or main)
git checkout -b feature/my-feature multiuser

# 2. Make changes, commit
git add <files>
git commit -m "Description of changes"

# 3. Push and create PR
git push -u origin feature/my-feature
gh pr create --base multiuser --title "Short title" --body "..."
```

### Rules

- **One branch per logical change.** Don't mix unrelated features in one branch.
- **Base branch:** Use `multiuser` for active development. Use `main` only for release PRs.
- **PR required:** All changes go through pull requests — no direct pushes to `main` or `multiuser`.
- **Delete after merge:** Feature branches are deleted after PR is merged.

## Critical Rules

- **NEVER DROP THE DATABASE.** Do not run `DROP SCHEMA`, `DROP DATABASE`, `DROP TABLE` or any destructive SQL on the PRDforge PostgreSQL database. It contains user project data (sections, revisions, dependencies, comments) that cannot be recreated. For database restores, use `psql < backup.sql` directly — never drop-and-restore. Always ask the user before any destructive database operation.
- **Never add AI/agent signatures to git commits.** No "Co-Authored-By: Claude", "Generated by AI", etc.
- **Never install packages globally.** Always use `uvx` or a virtual environment (`.venv`).

## Gotchas

- `word_count` is a GENERATED ALWAYS column — never include in INSERT or UPDATE
- asyncpg returns `Record` objects, not dicts — use `dict(row)` or `row['field']`
- PostgreSQL `TEXT[]` arrays: pass Python lists directly to asyncpg
- `parent_section=""` (empty string) means "move to root" (set `parent_section_id = NULL`)
- Slug collisions: `prd_import_markdown` generates slugs from headings — duplicates are skipped unless `replace_existing=true`
- FastMCP lifespan: uses `@asynccontextmanager` pattern
- Cross-project dependency guard: composite FK at schema level + INSERT...SELECT with JOIN at app level
- Import parser splits on configurable heading level (default `## `) — `###` and deeper are part of the section body. Manual delimiter mode (`<!-- split -->`) also available.
- `/health` endpoint is a v1.1 addition beyond the original PRD §5.1 spec (5 routes → 6)
- Inline comments use text anchoring (prefix + anchor_text + suffix) not character offsets — survives minor content edits. If anchor text can't be found after major edits, comment becomes "orphaned" (shown in panel but not highlighted)
- Comment highlights use `range.surroundContents()` which fails if selection spans multiple DOM elements — in that case the comment is still saved and shown in the panel, just without inline highlight
- **Comment ownership validation:** ALL comment mutation routes/tools (resolve, delete, reply) MUST validate that the comment belongs to the specified project/section using a JOIN through `sections → projects`. Use `resolve_comment_id()` helper in MCP server, or inline ownership JOIN in UI endpoints. Never mutate by comment_id alone.
- **Shared settings module:** `shared/settings.py` is the single source of truth for `SETTINGS_SCHEMA` and `validate_settings()`. Both `server.py` and `app.py` import from it via `sys.path.insert(0, "..")`
- `prd_update_section` supports `resolve_comments` param — atomically resolves comments + auto-replies if `claude_comment_replies` setting is enabled
- **Chat is experimental** — disabled by default, gated behind `chat_enabled` project setting. All 4 chat endpoints return 403 when disabled. Enable in Settings → Experimental Features.
- **Chat model selector** — `chat_model` setting (`sonnet`/`opus`/`haiku`) per-project, stored in `project_settings` JSONB. Passed to CLI as `--model` flag. For API provider, mapped via `API_MODEL_MAP` dict.
- **Section status editor** — `PATCH /api/projects/{slug}/sections/{section}` supports updating status, tags, title, summary. Valid statuses: `draft`, `in_progress`, `review`, `approved`, `outdated`.
- Web UI Claude chat uses Anthropic API key for authentication
- Chat tool execution uses an allowlist of MCP tool functions with project slug enforced server-side
- Web UI chat can attach selected section text as context; backend stores this in `chat_messages.metadata.selection_context` and rehydrates it into future model history turns
- Web UI chat can attach local files (text payloads); backend stores them in `chat_messages.metadata.attachments` and injects their content into future model history turns
- Web UI chat provider can be overridden per project via settings (`chat_provider`)
- Web UI chat renders selected context inline inside user message bubbles and triggers best-effort live refresh of project/section views after each completed assistant turn
- Chat attachment limits are controlled via env vars: `CHAT_MAX_ATTACHMENTS`, `CHAT_ATTACHMENT_MAX_BYTES`, `CHAT_ATTACHMENT_MAX_CHARS`, `CHAT_ATTACHMENTS_MAX_TOTAL_CHARS`
- `GET /api/projects/{slug}` now backfills missing initial revisions for sections; if a project has chat activity and zero dependencies, it backfills a linear references chain so Dependencies/Changelog tabs are populated for chat-generated projects
- `GET /api/projects/{slug}/token-stats` now includes `project_stats` (`sections`, `dependencies`, `revisions`) in addition to token-savings metrics
- `install.sh` now auto-selects a free host PostgreSQL port (`5432`, else first free in `5433-5500`) and exports `POSTGRES_PORT` so Docker + Claude Desktop config stay in sync

## Residual Risks

1. **Markdown import parser is heuristic** — fence-state tracking handles common code blocks but won't handle malformed or exotic markdown constructs. Now supports configurable heading level and manual delimiters.
2. **No latency/error-rate metrics** — structured logging, `/health`, and `prd_token_stats` provide operability and token savings tracking
3. **No reverse proxy hardening** — localhost-only binding prevents accidental LAN exposure

## Testing

Tests run against a real PostgreSQL database (no mocks). The `conftest.py` provides:
- Session-scoped connection pool
- Auto-cleanup that preserves seed data between tests
- Monkeypatched pool for MCP server tests
- httpx `AsyncClient` with `ASGITransport` for UI tests

Concurrency tests verify that concurrent `prd_update_section` calls don't produce revision_number collisions or content loss (using `SELECT ... FOR UPDATE` inside transactions).
