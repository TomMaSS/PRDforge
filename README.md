# PRD Forge

![PRDforge Demo](demo.gif)

**Stop feeding your entire spec to Claude every time you change one paragraph.**

PRD Forge splits your product requirements into independently addressable sections stored in PostgreSQL, then gives Claude surgical read/write access through 31 MCP tools. The result: edits that used to burn ~15,000 tokens now cost 500-2,000 — an **85-95% reduction** in context per operation.

## The Problem

Every AI-assisted PRD workflow today has the same bottleneck: Claude needs the full document loaded into context to make a single edit. A 20-page spec means ~15K tokens of context consumed on every interaction — even if you're only changing one section. That context cost adds up fast, limits how much Claude can reason about, and makes large specs unwieldy.

## How PRD Forge Solves It

Each section stores both its full **content** and a short **summary** (1-3 sentences). When Claude reads a section, it gets:

- Full content for the target section
- Only summaries of related (dependent) sections
- Inline comments and revision history

**Real example:** Reading `data-model` (820 words, ~1,200 tokens) loads summaries of `tech-stack` (~60 tokens) and `pipeline` (~60 tokens). Total: **~1,320 tokens** instead of ~15,000.

Claude always has enough context to make informed edits without paying for the entire document.

## What You Get

- **31 MCP tools** — read, write, search, import/export, manage dependencies, track revisions, resolve comments. Claude operates on your spec like a database, not a blob of text.
- **Dependency-aware context** — sections know what they depend on. When Claude reads one, it automatically gets summaries of upstream sections for context.
- **Full revision history** — every content change creates a revision. Roll back any section to any point. No content is ever lost.
- **Google Docs-style comments** — leave inline comments anchored to specific text, Claude reads them, implements changes, resolves them. Threaded replies included.
- **Web UI** — browse your specs, leave comments, view the dependency graph, toggle dark/light theme. No editing through the UI — that's Claude's job.
- **One command to install** — `./install.sh` handles Docker, MCP config, and validation in ~15 seconds.

## Architecture

```mermaid
graph LR
    A[Claude.ai / Claude Code / Claude Desktop] <-->|MCP Protocol| B[MCP Server<br/>FastMCP/Python<br/>:8080]
    B <-->|asyncpg| C[(PostgreSQL 16<br/>sections, revisions<br/>dependencies, comments)]
    D[Web UI<br/>FastAPI<br/>:8088] <-->|read + comments| C
    A -.->|reads comments| D
```

Three Docker services, all localhost-only:
- **PostgreSQL 16** — source of truth (8 tables, 2 views)
- **MCP Server** — 28 tools for Claude integration (stdio + HTTP transports)
- **Web UI** — browser interface with inline comments, dependency graph, dark/light theme

## Quick Start

```bash
cd PRDforge
./install.sh
```

This single command:
1. Pulls pre-built images from ghcr.io (or builds locally if unavailable)
2. Starts Docker services (PostgreSQL, MCP server, Web UI)
3. Configures your Claude client (Code or Desktop)
4. Validates everything works

```bash
# Options
./install.sh --claude-code      # Non-interactive (HTTP transport)
./install.sh --claude-desktop   # Non-interactive (stdio transport)
./install.sh --build            # Force local build instead of pulling images
./install.sh --uninstall        # Remove config + optionally stop services
POSTGRES_PORT=5433 ./install.sh # Override host PostgreSQL port
```

If `5432` is already in use, `install.sh` automatically picks the first free port in `5433-5500` and configures it for Docker + Claude Desktop.

For Claude Desktop setup, `install.sh` now auto-selects a compatible Python interpreter (`3.10-3.13`) for `mcp_server/.venv` and recreates that venv if it was previously created with an unsupported Python (for example, `3.14`).

The stack starts in ~15 seconds. PostgreSQL seeds a sample "SnapHabit" project (12 sections, 12 dependencies) on first boot — a mobile habit-tracking app with AWS serverless backend. Edit or delete the seed data to start your own PRD.

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
  python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
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
> If PostgreSQL is published on a non-default host port, replace `5432` in `DATABASE_URL` with your chosen port.
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

31 MCP tools across 10 groups: project management, section CRUD, dependencies, comments, context/search, revisions, import/export, batch operations, token stats, and settings.

See **[docs/tool-reference.md](docs/tool-reference.md)** for the full tool table and usage examples.

## Inline Comments

Google Docs-style comments anchored to specific text in any section:

1. **In the UI** — select text in a section → click "+ Comment" → write your note → Save
2. **Via MCP** — `prd_add_comment(project, section, anchor_text, body)` with optional `anchor_prefix`/`anchor_suffix` for disambiguation
3. **Claude scans comments** — `prd_list_comments` returns all open comments with section pointers (~100 tokens), then read only the sections that have feedback
4. **Claude reads comments** — `prd_read_section` includes all comments with their anchor text and body
5. **Resolve after implementing** — use `prd_resolve_comment` or click "Resolve" in the UI

Workflow: leave comments → ask Claude to check feedback → Claude calls `prd_list_comments` to see which sections have comments → reads only those sections → implements changes → resolves comments.

## Data Model & Reference

8 tables, 2 views. See **[docs/data-model.md](docs/data-model.md)** for the full ER diagram, dependency types, tags, statuses, and the SnapHabit example dependency graph.

## Seed Data

The default seed (`db/02_seed.sql`) creates a "SnapHabit" project — a mobile habit-tracking app with AWS serverless backend. It has 12 sections (overview, user research, tech stack, data model, API spec, mobile app, push notifications, auth, deployment, analytics, testing strategy, timeline) and 12 dependencies.

Edit or delete these to start your own PRD. To start fresh, simply clear the seed and add your own sections.

## Backup & Restore

```bash
# Export as markdown
curl http://localhost:8088/api/projects/snaphabit/export > backup.md

# PostgreSQL dump
docker exec prdforge-postgres-1 pg_dump -U prdforge prdforge > backup.sql

# Full reset (destroys all data)
docker compose down -v
docker compose up -d
```

## Security Notes

> **WARNING: PRD Forge is a single-user local-only tool.** It has no authentication, no authorization, and no rate limiting. It is NOT suitable for team use, shared access, or deployment on a network.

- All ports bound to `127.0.0.1` — not accessible from LAN by default
- **Do NOT** bind ports to `0.0.0.0`, expose them via tunnels (ngrok, Cloudflare Tunnel), or open firewall rules. Anyone with network access to port 8080 gets full read/write access to all your data with zero authentication.
- Database credentials are defaults (`prdforge`/`prdforge`) — acceptable only for localhost
- If you must expose PRD Forge beyond localhost, put it behind a reverse proxy with TLS and authentication. See [docs/scaling.md](docs/scaling.md) for guidance.

## Known Limitations

- No latency/error-rate metrics beyond structured logging, `/health`, and `prd_token_stats`
- No reverse proxy hardening — localhost-only binding prevents accidental exposure

## Development

```bash
# Run unit tests (requires postgres running)
docker compose up -d postgres
pip install -r tests/requirements.txt
pytest tests/test_mcp_tools.py tests/test_ui_api.py -v

# Smoke tests (requires full stack)
docker compose up -d
pip install httpx pytest
pytest tests/test_smoke.py -v
```

**Project structure:**
```
PRDforge/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── .github/workflows/build-and-push.yml
├── claude_mcp_config.json
├── README.md
├── AGENTS.md
├── prd.md
├── docs/
│   ├── tool-reference.md
│   ├── data-model.md
│   └── scaling.md
├── db/
│   ├── 01_init.sql
│   ├── 02_seed.sql
│   ├── 03_comments.sql
│   ├── 04_replies_and_settings.sql
│   └── 05_token_stats.sql
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
│       ├── fonts.css
│       ├── fonts/
│       │   ├── inter-*.woff2
│       │   └── jetbrains-mono-*.woff2
│       └── MARKED_VERSION
└── tests/
    ├── requirements.txt
    ├── conftest.py
    ├── test_mcp_tools.py
    ├── test_ui_api.py
    └── test_smoke.py
```

## License

MIT
