# Data Model

**Last updated:** 2026-03-20
**Status:** Current
**Audience:** Contributors, integrators, MCP tool developers

---

## Overview

PRDforge stores all project data in PostgreSQL. The schema supports multi-user collaboration with role-based access, real-time presence via WebSocket tokens, and session-based token savings tracking.

## Table of Contents

- [Entity Relationship Diagram](#entity-relationship-diagram)
- [Core Tables](#core-tables)
- [Multi-User Tables](#multi-user-tables)
- [Analytics Tables](#analytics-tables)
- [Dependency Types](#dependency-types)
- [Section Statuses](#section-statuses)
- [Tags](#tags)
- [Dependency Graph Example](#dependency-graph-example)

---

## Entity Relationship Diagram

```mermaid
erDiagram
    projects ||--o{ sections : has
    projects ||--o{ project_members : has
    projects ||--o{ section_dependencies : scopes
    projects ||--o| project_settings : has
    projects ||--o{ token_estimates : tracks
    projects ||--o{ section_access_log : tracks
    projects ||--o{ mcp_activity : logs
    projects ||--o{ audit_events : logs
    projects ||--o| project_chats : has
    sections ||--o{ section_revisions : tracks
    sections ||--o{ section_dependencies : "from"
    sections ||--o{ section_dependencies : "to"
    sections ||--o{ section_comments : has
    section_comments ||--o{ comment_replies : has
    project_chats ||--o{ chat_messages : has
    sections ||--o| sections : parent

    projects {
        uuid id PK
        text slug UK
        text name
        text description
        int version
        text organization_id
        text created_by
        timestamptz created_at
        timestamptz updated_at
    }
    sections {
        uuid id PK
        uuid project_id FK
        text slug
        text title
        text content
        text summary
        text notes
        text status
        text section_type
        jsonb tags
        int word_count
        int sort_order
        uuid parent_id FK
        text updated_by
    }
    section_revisions {
        uuid id PK
        uuid section_id FK
        int revision_number
        text content
        text summary
        text change_description
        text created_by
        timestamptz created_at
    }
    section_dependencies {
        uuid id PK
        uuid project_id FK
        uuid section_id FK
        uuid depends_on_id FK
        text dependency_type
        text description
    }
    section_comments {
        uuid id PK
        uuid section_id FK
        text anchor_text
        text anchor_prefix
        text anchor_suffix
        text body
        boolean resolved
        text created_by
        timestamptz created_at
    }
    comment_replies {
        uuid id PK
        uuid comment_id FK
        text author
        text body
        timestamptz created_at
    }
    project_members {
        uuid id PK
        uuid project_id FK
        text user_id
        text role
        timestamptz created_at
        timestamptz updated_at
    }
    project_settings {
        uuid project_id PK
        jsonb settings
    }
    token_estimates {
        uuid id PK
        uuid project_id FK
        text operation
        int full_doc_tokens
        int loaded_tokens
        timestamptz created_at
    }
    section_access_log {
        uuid id PK
        uuid project_id FK
        uuid section_id FK
        text access_level
        timestamptz created_at
    }
    mcp_activity {
        uuid id PK
        uuid project_id FK
        text tool_name
        jsonb detail
        text user_id
        timestamptz created_at
    }
    audit_events {
        uuid id PK
        uuid project_id FK
        text user_id
        text action
        text resource
        jsonb detail
        timestamptz created_at
    }
    project_chats {
        uuid id PK
        uuid project_id FK
        text chat_type
        timestamptz created_at
    }
    chat_messages {
        uuid id PK
        uuid chat_id FK
        text role
        text content
        jsonb metadata
        text created_by
        timestamptz created_at
    }
    prdforge_bootstrap {
        uuid id PK
        text setup_type UK
        boolean completed
        timestamptz created_at
    }
```

---

## Core Tables

### `projects`

Top-level container for a PRD. Each project has a unique slug used in URLs and MCP tool calls.

| Column | Type | Description |
|:-------|:-----|:-----------|
| `id` | UUID | Primary key |
| `slug` | TEXT | Unique URL-safe identifier (e.g., `snaphabit`) |
| `name` | TEXT | Display name |
| `description` | TEXT | Optional project description |
| `version` | INT | Incremented on structural changes |
| `organization_id` | TEXT | Optional org scope (Better Auth) |
| `created_by` | TEXT | Better Auth user ID of creator |

### `sections`

Individual PRD sections within a project. Each section has content, metadata, and optional parent for nesting.

| Column | Type | Description |
|:-------|:-----|:-----------|
| `id` | UUID | Primary key |
| `project_id` | UUID | FK → projects |
| `slug` | TEXT | Unique within project (e.g., `data-model`) |
| `title` | TEXT | Display title |
| `content` | TEXT | Markdown content |
| `summary` | TEXT | Short summary for `prd_get_overview` |
| `notes` | TEXT | Private notes (accordion in UI) |
| `status` | TEXT | Workflow status (see [Section Statuses](#section-statuses)) |
| `section_type` | TEXT | Category (overview, tech_spec, data_model, etc.) |
| `tags` | JSONB | Array of string tags |
| `word_count` | INT | Auto-calculated on content change |
| `sort_order` | INT | Display ordering |
| `parent_id` | UUID | FK → sections (self-referential, for nesting) |

### `section_revisions`

Immutable revision history. A new revision is created automatically on every `prd_update_section` that changes content.

### `section_dependencies`

Directed edges between sections. See [Dependency Types](#dependency-types) for the type enum.

### `section_comments`

Inline comments anchored to selected text within a section. Supports resolve/reopen toggle.

### `comment_replies`

Threaded replies on comments. Created by users or auto-generated when a comment is resolved via `prd_update_section(resolve_comments=[...])`.

---

## Multi-User Tables

### `project_members`

Maps users to projects with role-based access. User IDs are Better Auth format (32-char random strings, not UUIDs).

| Column | Type | Description |
|:-------|:-----|:-----------|
| `user_id` | TEXT | Better Auth user ID |
| `role` | TEXT | One of: `owner`, `admin`, `editor`, `commenter`, `viewer` |

**Role hierarchy:** owner > admin > editor > commenter > viewer. Each role inherits all permissions of lower roles.

### `prdforge_bootstrap`

Controls first-user setup flow. When empty (no rows), the system operates in pre-setup mode — all endpoints are open, no auth enforced.

### `audit_events`

Logs user actions for project audit trail. Indexed by project and user.

---

## Analytics Tables

### `token_estimates`

Per-operation token tracking. Written on every MCP read tool call. Source for the "Savings by Operation" chart and daily trend.

| Column | Type | Description |
|:-------|:-----|:-----------|
| `operation` | TEXT | MCP tool name (e.g., `read_section`, `get_overview`) |
| `full_doc_tokens` | INT | What full document load would have cost |
| `loaded_tokens` | INT | What was actually loaded |

### `section_access_log`

Session-based access tracking with coverage levels. Primary source for the savings gauge. See [Token Stats Metrics](./token-stats-metrics.md) for detailed explanation.

| Column | Type | Description |
|:-------|:-----|:-----------|
| `access_level` | TEXT | `full`, `summary`, or `snippet` |

### `mcp_activity`

Logs all mutating MCP tool calls (12 tools) with detail JSON. Source for the "Write Operations" donut chart.

---

## Dependency Types

When linking sections with `prd_add_dependency`, use one of these types:

| Type | Meaning | Example |
|:-----|:--------|:--------|
| `blocks` | Section cannot proceed until dependency is complete | `data-model` blocks `api-spec` |
| `extends` | Section builds upon the dependency | `api-spec` extends `data-model` |
| `implements` | Section implements what the dependency specifies | `ui-design` implements `api-spec` |
| `references` | Section references the dependency for context (default) | `security` references `tech-stack` |

The dependency graph in the UI uses these types for edge coloring:
- `blocks` — red edges
- `extends` — blue edges
- `implements` — green edges
- `references` — gray edges

---

## Section Statuses

| Status | Meaning | Dot color |
|:-------|:--------|:----------|
| `draft` | Initial writing, not yet reviewed | Gray |
| `in_progress` | Actively being worked on | Yellow |
| `review` | Ready for review | Blue |
| `approved` | Finalized and approved | Green |
| `outdated` | Needs update due to changes in dependencies | Red |

Status is set via the dropdown in the section viewer header or via `prd_update_section(status="approved")`.

---

## Tags

Tags categorize sections for filtering and search. Query with `prd_search(query="tag:mvp")`.

| Tag | Purpose |
|:----|:--------|
| `mvp` | Part of minimum viable product scope |
| `core` | Core system functionality |
| `infra` | Infrastructure and deployment |
| `ai` | AI/ML related components |
| `frontend` | User-facing interface |

Tags are freeform — create any tag that fits your project. The above are conventions from the SnapHabit seed data.

---

## Dependency Graph Example

The default SnapHabit seed data (`db/02_seed.sql`) creates this dependency structure:

```mermaid
graph TD
    TS[tech-stack] --> DM[data-model]
    TS --> API[api-spec]
    DM --> API
    API --> MA[mobile-app]
    UR[user-research] --> MA
    TS --> AUTH[auth]
    API --> PN[push-notifications]
    TS --> DEP[deployment]
    DEP --> AN[analytics]
    API --> TEST[testing-strategy]
    DM --> TL[timeline]
    MA --> TL
```

---

## Migration Files

Schema is applied via ordered SQL files in `db/`:

| File | Purpose |
|:-----|:--------|
| `01_init.sql` | Core tables (projects, sections, revisions, dependencies) |
| `02_seed.sql` | SnapHabit seed data (12 sections, 12 dependencies) |
| `03_comments.sql` | Section comments and replies |
| `04_replies_and_settings.sql` | Comment replies, project settings |
| `05_token_stats.sql` | Token estimates tracking |
| `06_chat.sql` | Project chats and messages |
| `07_multi_user.sql` | Project members, bootstrap, bridge columns (TEXT not UUID) |
| `08_mcp_activity.sql` | MCP tool activity logging |
| `09_audit.sql` | Audit events |
| `10_password_reset.sql` | Admin password reset tokens |
| `11_chat_multiuser.sql` | Chat type column, user attribution |
| `12_better_auth.sql` | Better Auth session/user tables |
| `13_section_access_log.sql` | Session-based access tracking |

All migrations are idempotent (`CREATE TABLE IF NOT EXISTS`, `DO $$ BEGIN ... END $$` guards).
