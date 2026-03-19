# PRD Forge

**Stop feeding your entire spec to Claude every time you change one paragraph.**

![PRDforge Demo](demo.gif)

PRD Forge splits your product requirements into independently addressable sections stored in PostgreSQL, then gives Claude surgical read/write access through 31 MCP tools. The result: edits that used to burn ~15,000 tokens now cost 500-2,000 — an **85-95% reduction** in context per operation.

## The Problem

Every AI-assisted PRD workflow today has the same bottleneck: Claude needs the full document loaded into context to make a single edit. A 20-page spec means ~15K tokens of context consumed on every interaction — even if you're only changing one section.

## How PRD Forge Solves It

Each section stores both its full **content** and a short **summary** (1-3 sentences). When Claude reads a section, it gets:

- Full content for the target section
- Only summaries of related (dependent) sections
- Inline comments and revision history

**Real example:** Reading `data-model` (820 words, ~1,200 tokens) loads summaries of `tech-stack` (~60 tokens) and `pipeline` (~60 tokens). Total: **~1,320 tokens** instead of ~15,000.

## Features

- **31 MCP tools** — read, write, search, import/export, manage dependencies, track revisions, resolve comments
- **Multi-user auth** — Better Auth (email/password + Google OAuth), 5 roles (owner/admin/editor/commenter/viewer), org-scoped access control
- **Real-time collaboration** — WebSocket presence, live section updates across clients
- **Project templates** — start with Blank, SaaS MVP, Mobile App, or API Design — pre-built section structures with starter content
- **Dependency-aware context** — sections know what they depend on; Claude automatically gets upstream summaries
- **Full revision history** — every content change creates a revision, roll back to any point
- **Google Docs-style comments** — inline comments anchored to specific text, threaded replies
- **AI chat** — streaming chat panel with Claude (Anthropic API or CLI), tool-calling into your PRD
- **Dependency graph** — interactive SVG visualization of section relationships
- **Token stats** — dashboard showing per-section token usage
- **Next.js frontend** — React 19, Tailwind v4, shadcn/ui, dark/light theme
- **One command install** — `./install.sh` handles Docker, MCP config, validation

## Architecture

```mermaid
graph LR
    A[Claude.ai / Claude Code / Claude Desktop] <-->|MCP Protocol| B[MCP Server<br/>FastMCP/Python<br/>:8080]
    B <-->|asyncpg| C[(PostgreSQL 16<br/>sections, revisions<br/>dependencies, comments)]
    D[Python API<br/>FastAPI<br/>:8088] <-->|read + write + chat| C
    E[Frontend<br/>Next.js 15<br/>:3000] <-->|REST proxy| D
    F[Redis 7] <-->|pub/sub, jti| D
    A -.->|reads comments| D
```

Five Docker services:

| Service | Stack | Port | Purpose |
|---------|-------|------|---------|
| **PostgreSQL 16** | 15+ tables, 2 views | 5432 | Source of truth |
| **MCP Server** | FastMCP / Python | 8080 | 31 tools for Claude |
| **Python API** | FastAPI | 8088 | REST backend (projects, sections, chat, auth, audit) |
| **Frontend** | Next.js 15, React 19, Tailwind v4, shadcn/ui, Better Auth | 3000 | Web UI |
| **Redis 7** | — | 6379 | WebSocket token uniqueness, real-time pub/sub |

## Quick Start

```bash
cd PRDforge
./install.sh
```

This single command:
1. Pulls pre-built images from ghcr.io (or builds locally if unavailable)
2. Starts Docker services (PostgreSQL, MCP server, API, Frontend, Redis)
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

If `5432` is already in use, `install.sh` automatically picks the first free port in `5433-5500`.

The stack starts in ~15 seconds. PostgreSQL seeds a sample "SnapHabit" project (12 sections, 12 dependencies) on first boot.

After install, restart your Claude client. Web UI: http://localhost:3000

## Configuration

### MCP Configuration (Manual)

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

### Chat Configuration

Chat is an experimental feature, disabled by default. Enable per-project in **Settings → Experimental Features**.

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Anthropic API key for chat |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | Model for chat responses |
| `CHAT_MAX_ATTACHMENTS` | `5` | Max files per chat turn |
| `CHAT_ATTACHMENT_MAX_BYTES` | `200000` | Max size per file payload |

## MCP Tools Reference

31 MCP tools across 10 groups: project management, section CRUD, dependencies, comments, context/search, revisions, import/export, batch operations, token stats, and settings.

See **[docs/tool-reference.md](docs/tool-reference.md)** for the full tool table and usage examples.

## Inline Comments

Google Docs-style comments anchored to specific text in any section:

1. **In the UI** — select text → click "+ Comment" → write your note → Save
2. **Via MCP** — `prd_add_comment(project, section, anchor_text, body)`
3. **Claude scans comments** — `prd_list_comments` returns all open comments
4. **Resolve after implementing** — `prd_resolve_comment` or click "Resolve" in the UI

## Development

```bash
# Run backend tests (requires postgres running)
docker compose up -d postgres
pip install -r tests/requirements.txt
pytest tests/ -x -v

# Frontend type checking and lint
cd frontend && yarn typecheck && yarn lint && yarn test --run

# Smoke tests (requires full stack)
docker compose up -d
pytest tests/test_smoke.py -v

# Record demo video
pip install -r scripts/requirements.txt
playwright install chromium
python scripts/record_demo.py
```

**Project structure:**
```
PRDforge/
├── docker-compose.yml
├── frontend/            # Next.js 15 app (React 19, Tailwind v4, shadcn/ui)
├── api/                 # FastAPI backend (REST, chat, auth, WebSocket)
├── mcp_server/          # FastMCP server (31 tools, stdio + HTTP)
├── shared/              # Shared Python modules (settings, constants, templates)
├── db/                  # PostgreSQL schema migrations (13 files)
├── tests/               # pytest test suite
├── scripts/             # Demo recording, utilities
└── docs/                # Tool reference, data model, scaling guide
```

## Security & Deployment

PRD Forge ships with **Better Auth** (email/password + Google OAuth) and role-based access control. Sign-up is closed after the first user is created — new users are invited via organization member management.

**Localhost-only by default:**
- All ports bound to `127.0.0.1` — not accessible from LAN
- No TLS — acceptable only for localhost
- Database credentials are defaults (`prdforge`/`prdforge`)

**For production deployment:**
- Put behind a reverse proxy with TLS (nginx, Caddy, Traefik)
- Change database credentials in `.env`
- Set `BETTER_AUTH_SECRET` to a strong random value
- See [docs/scaling.md](docs/scaling.md) for detailed guidance
- **Do NOT** bind ports to `0.0.0.0` or expose via tunnels without auth

## Data Model

15+ tables, 2 views. See **[docs/data-model.md](docs/data-model.md)** for the full ER diagram, dependency types, tags, statuses, and the SnapHabit example.

## Backup & Restore

```bash
# Export as markdown
curl http://localhost:8088/api/projects/snaphabit/export > backup.md

# PostgreSQL dump
docker exec prdforge-postgres-1 pg_dump -U prdforge prdforge > backup.sql

# Full reset (destroys all data)
docker compose down -v && docker compose up -d
```

## License

MIT
