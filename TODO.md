# PRDforge TODO

## High Priority

- [ ] Run full test suite against live DB and fix any failures
- [ ] Test concurrent revision writes under load (SELECT FOR UPDATE correctness)
- [ ] Verify MCP transport path (`/mcp/` vs `/`) against FastMCP version — smoke test needed

## Medium Priority

- [ ] Add `test_smoke.py` — CI contract tests (MCP liveness, DB readiness, UI endpoints, seed data validation)
- [ ] Pin container images by digest instead of tag for reproducibility
- [ ] Vendor Google Fonts (Inter, JetBrains Mono) locally for offline use
- [ ] Add light theme / dark-light toggle in UI

## Low Priority

- [ ] Replace heuristic markdown import parser with `markdown-it-py` AST parser
- [ ] Add WebSocket push to UI for real-time updates when sections change
- [ ] Support `### ` (h3) splitting in import for nested section hierarchies
- [ ] Add `prd_merge_sections` tool (combine two sections into one)
- [ ] Add `prd_reorder_sections` tool (bulk sort_order update)
- [ ] Export as PDF via headless browser
- [ ] Add Prometheus `/metrics` endpoint to MCP server (request count, latency histograms)
- [ ] UI: keyboard navigation (j/k to move through sections, Enter to select)

## Done

- [x] Infrastructure files (.gitignore, .env.example, docker-compose.yml, Dockerfiles, requirements)
- [x] Database schema with composite FK cross-project guard
- [x] Seed data (ContentForge, 13 sections, 15 dependencies)
- [x] MCP server — 28 tools with atomic revision-before-update
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
