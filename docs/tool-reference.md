# MCP Tool Reference

**Last updated:** 2026-03-20
**Status:** Current
**Audience:** Claude agents, MCP integrators, contributors

---

## Overview

PRDforge exposes **32 MCP tools** for reading, writing, searching, and managing PRD sections. Tools are designed to minimize context window usage — prefer lightweight tools (`prd_list_sections`, `prd_get_overview`) for navigation and reserve full reads (`prd_read_section`) for editing.

## Table of Contents

- [Tool Index](#tool-index)
- [Workflows](#workflows)
- [Token Budget Guide](#token-budget-guide)
- [Tool Details by Group](#tool-details-by-group)

---

## Tool Index

| Tool | Group | Description | ~Tokens |
|:-----|:------|:-----------|:--------|
| `prd_list_projects` | Project | List all projects with section counts | 50 |
| `prd_create_project` | Project | Create project (optional template: `saas-mvp`, `mobile-app`) | — |
| `prd_delete_project` | Project | Delete project and all sections (cascades) | — |
| `prd_list_sections` | Section | List sections — metadata only, no content | 200 |
| `prd_read_section` | Section | Read full section content + dependency context summaries | 500–3000 |
| `prd_create_section` | Section | Create new section with content, tags, type | — |
| `prd_update_section` | Section | Update fields, auto-revision on content change, atomic comment resolve | — |
| `prd_delete_section` | Section | Delete section (warns about dependencies) | — |
| `prd_move_section` | Section | Change sort_order or parent section | — |
| `prd_duplicate_section` | Section | Copy section with new slug | — |
| `prd_add_dependency` | Deps | Add/update dependency link (idempotent) | — |
| `prd_remove_dependency` | Deps | Remove a dependency link | — |
| `prd_suggest_dependencies` | Deps | Auto-suggest deps via content similarity (TF-IDF) | 200 |
| `prd_list_comments` | Comments | List all comments across project with section pointers | 100–500 |
| `prd_add_comment` | Comments | Add inline comment anchored to selected text | — |
| `prd_resolve_comment` | Comments | Resolve or reopen a comment | — |
| `prd_delete_comment` | Comments | Delete a comment | — |
| `prd_add_comment_reply` | Replies | Add a reply to an inline comment | — |
| `prd_get_settings` | Settings | Get project settings (merged defaults + overrides) | 50 |
| `prd_update_settings` | Settings | Update project settings | — |
| `prd_get_overview` | Context | Project overview with section summaries (~10% of full doc) | 400 |
| `prd_search` | Context | Full-text or tag search across sections | 200 |
| `prd_get_changelog` | Context | Recent revision history across all sections | 300 |
| `prd_token_stats` | Context | Token savings statistics for the project | 200 |
| `prd_get_revisions` | Revision | List revision metadata for a section | 100 |
| `prd_read_revision` | Revision | Read a specific historical revision's content | 500–3000 |
| `prd_rollback_section` | Revision | Rollback to a previous revision (current saved as backup) | — |
| `prd_export_markdown` | Export | Export full document as assembled markdown | 15000+ |
| `prd_import_markdown` | Import | Import from markdown (configurable heading level or delimiter) | — |
| `prd_bulk_status` | Batch | Update status for multiple sections at once | — |

**Read tools** (return data, consume tokens): 14 tools
**Write tools** (mutate data, logged to `mcp_activity`): 12 tools
**Hybrid tools** (read + compute): 6 tools (search, suggest, stats, changelog, export, import)

---

## Workflows

### Standard Editing

Navigate → Read → Edit → Verify:

```
prd_get_overview(project="my-project")
  → Section list with summaries (~400 tokens)

prd_read_section(project="my-project", section="architecture")
  → Full content + dependency context summaries (~1500 tokens)

prd_update_section(
    project="my-project",
    section="architecture",
    content="...updated...",
    change_description="Added caching layer"
)
  → Content saved, revision created automatically
```

### Impact Analysis

Read a section to see what depends on it, then update dependents:

```
prd_read_section(section="requirements")
  → Response includes depended_by list with summaries

# Update each dependent section that needs changes
prd_update_section(section="api-spec", content="...", change_description="Aligned with updated requirements")
```

### Comment-Driven Editing

Read comments, make changes, resolve comments atomically:

```
prd_read_section(project="my-project", section="requirements")
  → Content + open comments with IDs and replies

prd_update_section(
    project="my-project",
    section="requirements",
    content="...updated addressing feedback...",
    change_description="Addressed review feedback",
    resolve_comments=["comment-id-1", "comment-id-2"]
)
  → Atomically: updates content + resolves comments + auto-replies
```

### Rollback

View history, restore a previous version:

```
prd_get_revisions(section="architecture")
  → Revision list with numbers, dates, descriptions

prd_read_revision(section="architecture", revision=3)
  → Content of revision 3

prd_rollback_section(section="architecture", revision=3)
  → Restores revision 3, current content saved as new revision (backup)
```

### Import

Import markdown from external sources:

```
# Split on ## headings (default)
prd_import_markdown(project="my-project", markdown="## Section One\n...")

# Split on ### headings
prd_import_markdown(project="my-project", markdown="...", heading_level=3)

# Split on custom delimiter
prd_import_markdown(project="my-project", markdown="...", manual_delimiter="<!-- split -->")
```

### Dependency Suggestions

Find related sections automatically:

```
prd_suggest_dependencies(project="my-project", section="architecture")
  → Top 5 sections with overlapping content, ranked by TF-IDF similarity
```

---

## Token Budget Guide

Context window is finite. Use the lightest tool that gets the job done:

| Task | Best tool | Tokens | Avoid |
|:-----|:----------|:-------|:------|
| "What sections exist?" | `prd_list_sections` | ~200 | `prd_get_overview` (4× more) |
| "What's the project about?" | `prd_get_overview` | ~400 | `prd_read_section` on each (10×) |
| "What does this section say?" | `prd_read_section` | ~1500 | `prd_export_markdown` (all sections) |
| "What changed recently?" | `prd_get_changelog` | ~300 | Reading each section's revisions |
| "Find sections about auth" | `prd_search` | ~200 | Reading every section |
| "What's the full document?" | `prd_export_markdown` | ~15000 | Only when needed for export |

### Cost hierarchy (cheapest → most expensive)

```
prd_list_sections     ~200 tokens   ← metadata only
prd_get_revisions     ~100 tokens   ← revision metadata
prd_search            ~200 tokens   ← matching snippets
prd_get_changelog     ~300 tokens   ← recent changes
prd_get_overview      ~400 tokens   ← all summaries
prd_read_section    ~1500 tokens   ← one section + dep context
prd_export_markdown ~15000 tokens   ← everything
```

---

## Tool Details by Group

### Project Tools

**`prd_create_project`** accepts an optional `template` parameter:

| Template | Sections created | Description |
|:---------|:----------------|:-----------|
| *(blank)* | 0 | Empty project |
| `saas-mvp` | 7 | SaaS MVP PRD (overview, tech stack, data model, API, UI, security, timeline) |
| `mobile-app` | 5 | Mobile app PRD (overview, features, UI, data model, deployment) |

### Section Tools

**`prd_update_section`** is the most versatile tool. Only provided fields are updated:

```
# Update just status
prd_update_section(section="auth", status="approved")

# Update content with revision
prd_update_section(section="auth", content="...", change_description="Added OAuth flow")

# Update content AND resolve comments atomically
prd_update_section(section="auth", content="...", resolve_comments=["id1", "id2"])
```

If `content` is provided, the current content is saved as a revision **before** the update (atomic transaction).

### Dependency Tools

**`prd_add_dependency`** is idempotent — calling it twice with the same arguments is safe (upserts on conflict).

Dependency types: `blocks`, `extends`, `implements`, `references` (default).

See [Data Model — Dependency Types](./data-model.md#dependency-types) for full descriptions.

### Comment Tools

**`prd_list_comments`** is context-efficient: returns all project comments with section pointers in ~100-500 tokens, avoiding the need to read each section individually.

Comments support:
- **Text anchoring** — `anchor_text`, `anchor_prefix`, `anchor_suffix` for precise positioning
- **Resolve/reopen** — toggle via `prd_resolve_comment(reopen=True)`
- **Threaded replies** — via `prd_add_comment_reply`
- **Atomic resolve** — resolve comments in the same transaction as content update

### Settings Tools

Project settings are stored as JSONB with sensible defaults. `prd_get_settings` returns the merged result (defaults + overrides).

Key settings:

| Setting | Default | Description |
|:--------|:--------|:-----------|
| `chat_enabled` | `false` | Enable/disable chat panel |
| `chat_provider` | `claude_cli` | Chat provider: `claude_cli` or `anthropic_api` |
| `chat_model` | `sonnet` | Model for chat |
| `auto_reply_on_resolve` | `true` | Auto-generate reply when resolving comments |
