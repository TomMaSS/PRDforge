# Token Stats Dashboard

**Last updated:** 2026-03-20
**Status:** Current
**Audience:** PRDforge users, contributors, and integrators

---

## Overview

The Stats tab measures how efficiently MCP tools consume LLM context window tokens when interacting with a PRD project. Rather than loading the entire document into context on every tool call, PRDforge serves targeted slices — individual sections, summaries, or metadata — and tracks the resulting savings.

This document explains every metric, chart, and data source visible on the Stats dashboard.

## Table of Contents

- [Core Concepts](#core-concepts)
- [Dashboard Layout](#dashboard-layout)
  - [Top-Level Stat Cards](#top-level-stat-cards)
  - [7-Day Token Savings](#7-day-token-savings)
  - [Full Doc vs Loaded](#full-doc-vs-loaded)
  - [Savings by Operation](#savings-by-operation)
  - [Write Operations](#write-operations)
  - [Section Heatmap](#section-heatmap)
- [Calculation Methodology](#calculation-methodology)
- [Data Sources](#data-sources)
- [API Response Schema](#api-response-schema)
- [Interpreting Your Dashboard](#interpreting-your-dashboard)
- [Troubleshooting](#troubleshooting)

---

## Core Concepts

### Token Estimation

PRDforge converts word counts to token estimates using a **1.3× multiplier** (1 word ≈ 1.3 tokens). This approximation is consistent with typical English-language tokenization across Claude models.

```
tokens = word_count × 1.3
```

### Access Levels

Every section read is tagged with an access level that determines its **coverage fraction** — the proportion of the section's content actually delivered to the agent:

| Access Level | Coverage | Triggered by | Example |
|:------------|:---------|:------------|:--------|
| `full` | 100% | `prd_read_section` | Agent reads complete section content for editing |
| `summary` | 10% | `prd_get_overview` | Agent needs a quick overview of all sections |
| `snippet` | 15% | `prd_list_sections` | Agent checks section titles, statuses, and tags |

### Session Windowing

Tool calls are grouped into **sessions** using a 30-minute inactivity window:

```
Call at 10:00 ──┐
Call at 10:05   │ Session 1
Call at 10:22 ──┘
                    ← 35 min gap (> 30 min) →
Call at 10:57 ──┐
Call at 11:03   │ Session 2
Call at 11:10 ──┘
```

**Deduplication rule:** Within a session, if the same section is accessed multiple times, only the **highest** access level counts. Reading a section summary and then reading it in full counts as one full read, not a summary + a full read.

### Savings Formula

Per-session savings percentage:

```
savings_pct = (1 - unique_loaded_words / full_doc_words) × 100
```

Where:
- `full_doc_words` = total word count across all sections in the project
- `unique_loaded_words` = sum of `section_word_count × coverage_fraction` for each section touched in the session, deduplicated by highest access level

---

## Dashboard Layout

### Top-Level Stat Cards

Five cards displayed across the top of the dashboard:

#### 1. Savings Gauge (ring chart)

Average token savings percentage across all sessions.

| Ring Color | Range | Meaning |
|:----------|:------|:--------|
| Green | > 80% | Excellent — agents rely on summaries and targeted reads |
| Yellow | 50–80% | Moderate — some full-document loads occurring |
| Red | < 50% | Low — agents are loading most of the document per session |

A new project typically starts at 0% and improves as usage patterns shift toward `prd_get_overview` and `prd_list_sections` instead of reading every section in full.

#### 2. Sessions

Total number of distinct interaction sessions. The subtitle shows average sections touched per session (e.g., `12.0 sections/session`).

When session-based tracking has no data (legacy mode), this card falls back to showing total operation count.

#### 3. Best Session

Highest savings percentage achieved in any single session. Represents the best-case efficiency your workflow has produced so far.

#### 4. Full Document

Total token count of the entire PRD if loaded all at once.

```
full_doc_tokens = SUM(sections.word_count) × 1.3
```

Subtitle shows the number of sections in the project.

#### 5. Project

Structural stats for the project:
- **Dependencies** — total dependency links between sections
- **Revisions** — total revision count across all sections

---

### 7-Day Token Savings

**Chart type:** Area chart with gradient fill
**Color:** Green (`#22c55e`)

Displays daily total tokens saved over the last 7 calendar days.

**Data point formula:**
```sql
tokens_saved = SUM(full_doc_tokens - loaded_tokens)
-- per day, from token_estimates table
```

**What to look for:**
- **Rising trend** — agents are becoming more efficient (using summaries, targeted reads)
- **Spikes** — bulk operations (e.g., creating 12 sections via template) generate large savings in a single day
- **Flat at zero** — no MCP tool usage in the time period, or every call loaded full content

---

### Full Doc vs Loaded

**Chart type:** Custom vertical bar chart with three columns

| Column | Color | Meaning |
|:-------|:------|:--------|
| **Full Doc** | Red (`#ef4444`) | What would have been consumed if the entire PRD was loaded into context every session |
| **Loaded** | Green (`#22c55e`) | Tokens actually delivered to agents across all sessions |
| **Saved** | Dashed purple outline (`#6366f1`) | Difference: `Full Doc − Loaded` |

**Calculation:**
```
Full Doc = full_doc_tokens × session_count
Loaded   = total_loaded_tokens (sum of unique loaded words × 1.3 across all sessions)
Saved    = Full Doc − Loaded
```

**When Saved = 0:** Every section was read in full during every session. Normal for:
- Newly created projects (agent just built all sections)
- Comprehensive review workflows (agent intentionally reads everything)
- Projects with very few sections where the overhead is negligible

---

### Savings by Operation

**Chart type:** Horizontal stacked bar chart
**Location:** Bottom-left, spans 2 columns

Breaks down token savings per MCP tool type. Each operation gets a bar with two segments:

| Segment | Color | Meaning |
|:--------|:------|:--------|
| Colored | Per-operation color | Tokens loaded by this operation across all calls |
| Gray | `var(--surface)`, 40% opacity | Tokens saved (full doc size minus loaded, per call) |

**Common operations and their savings profile:**

| Operation | Description | Typical loaded | Savings characteristic |
|:----------|:-----------|:--------------|:----------------------|
| `read section` | Loads one section's full content | ~1K tokens | High — loads 1 section instead of 12+ |
| `get overview` | Returns all section summaries (no content) | ~200 tokens | Very high — lightweight summaries only |
| `list sections` | Returns metadata (titles, status, tags, word count) | ~150 tokens | Very high — no content at all |
| `read revision` | Loads a specific historical revision | ~1K tokens | Similar to read section |
| `search` | Full-text search, returns matching snippets | Variable | High — only matching fragments returned |

**Tooltip displays:** Operation name, Tokens Loaded (cumulative), Tokens Saved (cumulative).

**How savings compound:** Each call to `read section` saves `full_doc_tokens − section_tokens`. With a 13K-token document and 26 read calls averaging 500 tokens each, total savings = `26 × (13,000 − 500) = 325K tokens saved`.

---

### Write Operations

**Chart type:** Donut chart
**Location:** Bottom-right

Distribution of mutating MCP tool calls logged in `mcp_activity`. Shows how the project was modified, not read.

**Operations tracked:**

| Operation | Description |
|:----------|:-----------|
| `update_section` | Edit section content (creates a revision) |
| `create_section` | Add a new section to the project |
| `add_dependency` | Create a dependency link between two sections |
| `remove_dependency` | Remove a dependency link |
| `move_section` | Change section sort order |
| `duplicate_section` | Clone a section |
| `delete_section` | Remove a section |
| `update_settings` | Modify project settings |

**Legend:** Displays below the donut with operation name and count. The header shows total write operation count.

**Interpreting the ratio:** Initial PRD creation is write-heavy (many `create_section` + `add_dependency`). Ongoing refinement shifts toward `update_section`. A healthy mature project shows mostly updates with occasional creates.

---

### Section Heatmap

**Condition:** Only displayed when `section_access_log` has data for the project.

Shows which sections are accessed most frequently, helping identify:
- **Hot sections** — frequently read, may benefit from better summaries
- **Cold sections** — rarely accessed, may be candidates for archiving or merging
- **Full-read sections** — sections that are always read in full (no summary suffices)

---

## Calculation Methodology

### Session-Based (Primary)

Used when `section_access_log` has data for the project. This is the "honest" calculation.

```sql
-- 1. Identify session boundaries (30-min gap)
-- 2. Per session, per section: take MAX access level
-- 3. Per session: sum(section_word_count × coverage_fraction)
-- 4. Per session: savings_pct = (1 - loaded / full_doc) × 100
-- 5. Aggregate: avg(savings_pct) across sessions
```

Coverage fractions: `full = 1.0`, `summary = 0.10`, `snippet = 0.15`

### Legacy Fallback

Used when `section_access_log` is empty (older data before the access log was added).

```sql
-- Simple per-operation calculation from token_estimates table
savings = SUM(full_doc_tokens) - SUM(loaded_tokens)
savings_pct = savings / SUM(full_doc_tokens) × 100
```

Both systems are populated in parallel — the access log provides the accurate session-based view, while `token_estimates` provides the per-operation breakdown used by the "Savings by Operation" chart.

---

## Data Sources

| Table | Schema | Purpose |
|:------|:-------|:--------|
| `section_access_log` | `project_id`, `section_id`, `access_level`, `created_at` | Session-based tracking with access levels. Primary source for savings gauge, sessions, and heatmap. |
| `token_estimates` | `project_id`, `operation`, `full_doc_tokens`, `loaded_tokens`, `created_at` | Per-operation token tracking. Source for daily trend, by-operation breakdown, and legacy fallback. |
| `mcp_activity` | `project_id`, `tool_name`, `detail` (JSONB), `created_at` | Logs all mutating MCP tools. Source for write operations donut chart. Up to 50 most recent entries returned. |
| `sections` | `project_id`, `word_count`, ... | Current word counts for full document size calculation. |
| `section_dependencies` | `project_id`, ... | Dependency count for the Project stat card. |
| `section_revisions` | `section_id`, ... | Revision count for the Project stat card. |

---

## API Response Schema

**Endpoint:** `GET /api/projects/{slug}/token-stats`

```typescript
interface TokenStats {
  operations: number;              // Total MCP read operations
  total_full_doc_tokens: number;   // Full PRD token count (current)
  total_loaded_tokens: number;     // Tokens actually loaded across all sessions
  total_saved_tokens: number;      // Tokens saved (full × sessions − loaded)
  savings_percent: number;         // Average savings % across sessions
  sessions: number;                // Distinct session count
  best_session_savings: number;    // Highest savings % in any session
  avg_sections_per_session: number;// Average sections touched per session

  by_operation: {
    operation: string;             // MCP tool name (e.g., "read_section")
    count: number;                 // Times called
    full_tokens: number;           // Cumulative full-doc tokens
    loaded_tokens: number;         // Cumulative loaded tokens
  }[];

  daily_trend: {
    day: string;                   // ISO date (YYYY-MM-DD)
    operations: number;            // Operations that day
    tokens_saved: number;          // Tokens saved that day
  }[];

  project_stats: {
    sections: number;              // Section count
    dependencies: number;          // Dependency count
    revisions: number;             // Total revisions
  };

  activity: {
    tool_name: string;             // e.g., "prd_update_section"
    detail: Record<string, unknown>;
    created_at: string;            // ISO timestamp
  }[];

  section_heatmap: {
    slug: string;                  // Section slug
    title: string;                 // Section title
    access_count: number;          // Times accessed
    has_full_read: number;         // 1 if ever fully read, 0 otherwise
  }[];
}
```

---

## Interpreting Your Dashboard

### Scenario: New project, just created

| Metric | Expected value | Why |
|:-------|:--------------|:----|
| Savings gauge | 0% | Every section was just created and read in full |
| Full Doc vs Loaded | Equal bars, Saved = 0 | All content was loaded during creation |
| Savings by Operation | `create_section` dominates | Project is being built |
| Write Operations | `create_section`, `add_dependency` | Initial structure |

### Scenario: Mature project, daily agent usage

| Metric | Expected value | Why |
|:-------|:--------------|:----|
| Savings gauge | 70–90% | Agents use `get_overview` and `list_sections` for navigation |
| Full Doc vs Loaded | Loaded much smaller than Full Doc | Targeted reads dominate |
| Savings by Operation | `get overview` and `list sections` show highest savings | Lightweight operations most frequent |
| Write Operations | `update_section` dominates | Iterative refinement |

### Scenario: Agent doing comprehensive review

| Metric | Expected value | Why |
|:-------|:--------------|:----|
| Savings gauge | 10–30% | Agent reads most sections in full |
| Best Session | May still show high % from prior sessions | Historical best preserved |
| 7-Day Trend | Spike on review day, otherwise normal | One-off comprehensive read |

---

## Troubleshooting

### Savings always showing 0%

**Cause:** All MCP calls are `prd_read_section` (full reads). No `get_overview` or `list_sections` usage.

**Fix:** Encourage agents to use `prd_get_overview` for navigation and `prd_list_sections` for status checks. The AGENTS.md file instructs Claude to prefer lightweight tools.

### No data on the dashboard

**Cause:** No MCP tools have been called for this project yet. The `token_estimates` and `section_access_log` tables are empty.

**Fix:** Use any MCP tool (e.g., `prd_list_sections`) to generate initial data. Stats appear after the first tool call.

### Daily trend shows data but gauge shows 0%

**Cause:** Session-based tracking (`section_access_log`) has no data, but legacy `token_estimates` does. The gauge uses session-based math; the trend uses per-operation math.

**Fix:** This resolves naturally as new MCP calls populate the access log. Both tables are written to in parallel.

### Write operations count seems too high

**Cause:** The donut chart counts individual tool calls, not unique changes. An agent that creates 12 sections and 15 dependencies in one conversation generates 27 write operations.

**Expected behavior:** This is correct. The chart shows agent activity volume, not content change count.
