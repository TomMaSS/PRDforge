# MCP Tool Reference

PRD Forge exposes 31 MCP tools for Claude to read, write, search, and manage your PRD sections.

## Tool Table

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
| `prd_suggest_dependencies` | Deps | Auto-suggest deps via content similarity | 200 |
| `prd_get_overview` | Context | Project overview with summaries | 400 |
| `prd_search` | Context | Full-text or tag search | 200 |
| `prd_get_changelog` | Context | Recent revision history | 300 |
| `prd_token_stats` | Context | Token savings statistics per project | 200 |
| `prd_get_revisions` | Revision | List revision metadata | 100 |
| `prd_read_revision` | Revision | Read revision content | 500-3000 |
| `prd_rollback_section` | Revision | Rollback with backup | — |
| `prd_export_markdown` | Export | Full document as markdown | 15000+ |
| `prd_import_markdown` | Import | Import from markdown (configurable heading level or manual delimiter) | — |
| `prd_bulk_status` | Batch | Update status for multiple sections | — |
| `prd_list_comments` | Comments | List all comments across project with section pointers | 100-500 |
| `prd_add_comment` | Comments | Add inline comment anchored to selected text | — |
| `prd_resolve_comment` | Comments | Resolve/reopen a comment after implementing changes | — |
| `prd_delete_comment` | Comments | Delete a comment | — |
| `prd_add_comment_reply` | Replies | Add a reply to an inline comment | — |
| `prd_get_settings` | Settings | Get project settings (merged defaults + overrides) | 50 |
| `prd_update_settings` | Settings | Update project settings | — |

## Usage Examples

**Standard editing workflow:**
```
prd_get_overview(project="my-project")           → TOC + summaries (~400 tokens)
prd_read_section(project="my-project", section="architecture")  → full content + dep summaries
prd_update_section(project="my-project", section="architecture",
    content="...updated...", change_description="Added caching layer")
```

**Impact analysis:**
```
prd_read_section(section="requirements")  → see depended_by list
# Then update each dependent section in order
```

**Comment-driven editing (auto-resolve):**
```
prd_read_section(project="my-project", section="requirements")
  → content + 2 open comments with IDs + replies
prd_update_section(project="my-project", section="requirements",
    content="...updated...", change_description="Addressed review feedback",
    resolve_comments=["comment-id-1", "comment-id-2"])
  → atomically updates content + resolves comments + auto-replies if setting enabled
```

**Rollback:**
```
prd_get_revisions(section="architecture")     → see revision history
prd_rollback_section(section="architecture", revision=3)  → restore, current saved as backup
```

**Import with custom heading level:**
```
prd_import_markdown(project="my-project", markdown="...", heading_level=3)
  → splits on ### headings instead of ##
```

**Import with manual delimiter:**
```
prd_import_markdown(project="my-project", markdown="...", manual_delimiter="<!-- split -->")
  → splits on <!-- split --> markers, extracts title from first heading in each chunk
```

**Token savings:**
```
prd_token_stats(project="my-project")
  → total operations, tokens saved, savings %, daily trend
```

**Dependency suggestions:**
```
prd_suggest_dependencies(project="my-project", section="architecture")
  → top 5 sections with overlapping content, ranked by relevance
```
