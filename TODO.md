# PRDforge TODO

## High Impact, Moderate Effort – Do Next

- [x] Demo GIF/video in README — Playwright-based recording script (`scripts/record_demo.py`), GIF above the fold
- [ ] Token savings dashboard in Web UI — chart showing cumulative tokens saved over time, savings per section read, comparison bar ("full doc: 15,000 tokens vs loaded: 1,320 tokens"). Proof-of-value screen users will screenshot and share
- [ ] `prd_import_url` tool — fetch a Google Doc, Notion page, or raw URL and import as sections. Support public Google Docs and raw GitHub markdown files to reduce onboarding friction
- [ ] Section templates — offer project templates beyond blank/SnapHabit: "SaaS MVP", "API Design", "Mobile App", "Infrastructure Migration". Each is a seed SQL or importable markdown showcasing different dependency patterns

## Medium Impact, Lower Effort – Quick Wins

- [ ] Health check in docker-compose — add `healthcheck` directives for MCP server and UI containers (UI already has `/health`). Fixes startup ordering, makes `docker compose up` more reliable
- [ ] CONTRIBUTING.md — how to run tests locally, code style expectations, PR process
- [ ] GitHub repo metadata — description, topics/tags (`mcp`, `claude`, `prd`, `product-requirements`, `ai-tools`, `developer-tools`, `mcp-server`), website URL
- [ ] Multi-arch Docker builds — add `linux/amd64,linux/arm64` to GH Actions build for Apple Silicon support
- [ ] `prd_diff_sections` tool — unified diff between two revisions of a section, avoids loading both and diffing manually

## Medium Impact, Higher Effort – Plan For These

- [ ] Webhooks / notifications — POST to a configured URL on section update for Slack/Discord/pipeline integration
- [ ] Export to Google Docs / Notion — push assembled PRD back to where stakeholders read it (Notion API is more reasonable than Google Docs)
- [ ] Section-level permissions / locking — advisory lock with timestamp and owner field so two Claude sessions don't clobber each other
- [ ] Embeddings-based dependency suggestions — store embeddings in pgvector, compute cosine similarity to catch semantic relationships that FTS keyword overlap misses
- [ ] Version tagging / snapshots — `prd_tag_version` tool that snapshots all current section revision numbers under a named tag for milestone tracking

## Lower Priority – Worth Tracking

- [ ] Conflict detection — optimistic concurrency with revision check on write (warn/fail if section was edited since last read)
- [ ] Section ordering visualization — Gantt-style view based on `blocks` dependency type for timeline sections
- [ ] Prometheus `/metrics` endpoint — request counts, latency histograms, DB connection pool stats
- [ ] claude.ai MCP marketplace listing — be ready when Anthropic opens MCP server discovery
- [ ] Replace heuristic markdown import parser with `markdown-it-py` AST parser
- [ ] Add WebSocket push to UI for real-time updates when sections change
- [ ] Support `### ` (h3) splitting in import for nested section hierarchies
- [ ] Add `prd_merge_sections` tool (combine two sections into one)
- [ ] Add `prd_reorder_sections` tool (bulk sort_order update)
- [ ] Export as PDF via headless browser
- [ ] UI: keyboard navigation (j/k to move through sections, Enter to select)

## Done

- [x] Demo GIF/video recording script (Playwright-based, `scripts/record_demo.py`)
- [x] Infrastructure files (.gitignore, .env.example, docker-compose.yml, Dockerfiles, requirements)
- [x] Database schema with composite FK cross-project guard
- [x] Seed data (SnapHabit, 12 sections, 12 dependencies)
- [x] MCP server — 31 tools with atomic revision-before-update
- [x] Web UI — dark theme SPA with vendored marked.js
- [x] Test suite (test_mcp_tools.py, test_ui_api.py)
- [x] README.md with architecture diagrams
- [x] AGENTS.md with agent instructions
- [x] Claude Desktop stdio config (working)
- [x] Claude Code HTTP config
- [x] Pencil UI mockup design
- [x] One-command install script (`install.sh`)
- [x] Tag multi-selector dropdown with colored chips and search
- [x] Interactive force-directed dependency graph in main panel
- [x] `prd_list_comments` tool for context-efficient comment scanning
- [x] Editable comments (PATCH endpoint + inline edit UI)
- [x] Graph node popups with section summary, click-to-open
- [x] Full test suite fixed (70 unit tests + 9 smoke tests passing)
- [x] Concurrent revision writes verified (SELECT FOR UPDATE correctness)
- [x] MCP transport path verified (`/mcp/` streamable-http working)
- [x] `test_smoke.py` — CI contract tests (MCP liveness, DB readiness, UI endpoints, seed data)
- [x] Container images pinned by digest (postgres:16-alpine, python:3.11-slim)
- [x] Google Fonts vendored locally (Inter, JetBrains Mono in ui/static/fonts/)
- [x] Light theme / dark-light toggle in UI nav rail
- [x] Docker build pipeline (GitHub Actions → ghcr.io) + `docker-compose.prod.yml` + install.sh pull support
