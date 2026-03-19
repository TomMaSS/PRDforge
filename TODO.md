# PRDforge TODO

## High Impact, Moderate Effort – Do Next

- [ ] Agent personas for chat — per-project `system_prompt` in settings + per-section `agent_prompt` override. Ship 5-6 presets (PRD Architect, Technical Reviewer, UX/Design, QA Strategist, Executive Summary). Users pick preset or write custom. Passed as system message to Claude CLI. Section-level prompt overrides project-level when chatting in that section context.
- [ ] Section templates — offer project templates beyond blank/SnapHabit: "SaaS MVP", "API Design", "Mobile App", "Infrastructure Migration". Each is a seed SQL or importable markdown showcasing different dependency patterns.
- [ ] add notes (accordion) to section. Here, I would like the option to add a note to the entire section.
- [ ] We need to update the readme relative to all our recent changes, create a preview as we did through the playwrite, and make it as commercially product-successful as possible to attract potential users' attention.

## Medium Impact, Lower Effort – Quick Wins

- [ ] CONTRIBUTING.md — how to run tests locally, code style expectations, PR process
- [ ] GitHub repo metadata — description, topics/tags (`mcp`, `claude`, `prd`, `product-requirements`, `ai-tools`, `developer-tools`, `mcp-server`), website URL
- [ ] `prd_diff_sections` tool — unified diff between two revisions of a section, avoids loading both and diffing manually
- [ ] ui playwrite tests
- [ ] add playwrite preview autoupdate (ci for pr + agents.md for agents instaction which sections observe)

## Medium Impact, Higher Effort – Plan For These

- [ ] Webhooks / notifications — POST to a configured URL on section update for Slack/Discord/pipeline integration
- [ ] Export to Google Docs / Notion — push assembled PRD back to where stakeholders read it (Notion API is more reasonable than Google Docs)
- [ ] Embeddings-based dependency suggestions — store embeddings in pgvector, compute cosine similarity to catch semantic relationships that FTS keyword overlap misses
- [ ] Version tagging / snapshots — `prd_tag_version` tool that snapshots all current section revision numbers under a named tag for milestone tracking
- [ ] Google OAuth provider — Better Auth config ready, needs Google Cloud Console credentials

## Lower Priority – Worth Tracking

- [ ] `prd_import_url` tool — fetch public Google Docs, GitHub markdown, or raw URLs and import as sections. Private docs deferred (each provider needs its own OAuth — not worth the complexity for an import tool). Public-only version is ~2h of work.
- [ ] Section ordering visualization — Gantt-style view based on `blocks` dependency type for timeline sections
- [ ] Prometheus `/metrics` endpoint — request counts, latency histograms, DB connection pool stats
- [ ] claude.ai MCP marketplace listing — be ready when Anthropic opens MCP server discovery
- [ ] Replace heuristic markdown import parser with `markdown-it-py` AST parser
- [ ] Support `### ` (h3) splitting in import for nested section hierarchies
- [ ] Add `prd_merge_sections` tool (combine two sections into one)
- [ ] Add `prd_reorder_sections` tool (bulk sort_order update)
- [ ] Export as PDF via headless browser
- [ ] UI: keyboard navigation (j/k to move through sections, Enter to select)
- [ ] MCP auth for remote Claude clients (SSH tunnel or authenticated ingress)
- [ ] Redis jti uniqueness for WS tokens (SET NX EX — currently TODO in code)
- [ ] move to tasks github projects

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
- [x] Token savings dashboard — Grafana-style with recharts, area/bar/pie/gauge, session-based honest savings math, section heatmap
- [x] Health checks in docker-compose — all services (postgres, mcp-server, redis) have healthchecks with depends_on conditions
- [x] Multi-arch Docker builds — `linux/amd64,linux/arm64` in GH Actions
- [x] Multi-user auth — Better Auth (email/password), closed sign-up, first-user bootstrap
- [x] RBAC — project_members with 5 roles (owner/admin/editor/commenter/viewer), permission middleware
- [x] Next.js frontend — React 19, Tailwind v4, shadcn/ui, replaces server-rendered HTML
- [x] Real-time WebSocket — presence tracking, event broadcasting via Redis pub/sub
- [x] Optimistic locking — expected_revision on section PATCH, 409 Conflict with details
- [x] MCP activity tracking — 12 mutating tools logged to mcp_activity table
- [x] Chat with streaming — SSE, tool calls display, selection context, file attachments, stop button
- [x] Audit events table — project + user indexed
- [x] Password reset flow — admin-generated tokens, no email
- [x] Member management — add/remove/change role via API + UI
- [x] Dependency graph — dual view (force-directed SVG graph + list with type badges), click popup, drag nodes, curved colored arrows
- [x] Structured error handling — 9 error codes, frontend error boundaries
- [x] Comments — text selection anchoring, resolve/reopen toggle, edit/delete, existing comment detection
- [x] Section status management — clickable dropdown to change status
- [x] Multi-user chat threads — per-project + per-section, chat_type column
- [x] Org-level encrypted API key — Fernet/AES-256
- [x] Wider chat section — 40% viewport width, min 480px, max 700px
- [x] Honest token savings math — section_access_log with session-based dedup, coverage fractions (full/summary/snippet), 30-min session windowing
