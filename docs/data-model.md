# Data Model

## Entity Relationship Diagram

```mermaid
erDiagram
    projects ||--o{ sections : has
    sections ||--o{ section_revisions : tracks
    sections ||--o{ section_dependencies : "from"
    sections ||--o{ section_dependencies : "to"
    sections ||--o{ section_comments : has
    section_comments ||--o{ comment_replies : has
    projects ||--o| project_settings : has
    projects ||--o{ token_estimates : tracks
    projects ||--o| project_chats : has
    project_chats ||--o{ chat_messages : has
    sections ||--o| sections : parent

    projects {
        uuid id PK
        text slug UK
        text name
        int version
    }
    sections {
        uuid id PK
        uuid project_id FK
        text slug
        text content
        text summary
        text status
        text tags
        int word_count
    }
    section_revisions {
        uuid id PK
        uuid section_id FK
        int revision_number
        text content
        text summary
    }
    section_dependencies {
        uuid id PK
        uuid project_id FK
        uuid section_id FK
        uuid depends_on_id FK
        text dependency_type
    }
    section_comments {
        uuid id PK
        uuid section_id FK
        text anchor_text
        text body
        boolean resolved
    }
    comment_replies {
        uuid id PK
        uuid comment_id FK
        text author
        text body
    }
    project_settings {
        uuid project_id PK
        json settings
    }
    token_estimates {
        uuid id PK
        uuid project_id FK
        text operation
        int full_doc_tokens
        int loaded_tokens
    }
    project_chats {
        uuid id PK
        uuid project_id UK, FK
        timestamptz created_at
        timestamptz updated_at
    }
    chat_messages {
        uuid id PK
        uuid chat_id FK
        text role
        text content
        json metadata
    }
```

## Dependency Types

When linking sections with `prd_add_dependency`, use one of these types:

| Type | Meaning | Example |
|------|---------|---------|
| `blocks` | Section cannot proceed until dependency is complete | `pipeline` blocks `api-spec` |
| `extends` | Section builds upon or extends the dependency | `api-spec` extends `data-model` |
| `implements` | Section implements what the dependency specifies | `ui-design` implements `api-spec` |
| `references` | Section references the dependency for context (default) | `security` references `tech-stack` |

## Tags

Tags categorize sections for filtering and search (via `prd_search(query="tag:mvp")`):

| Tag | Purpose |
|-----|---------|
| `mvp` | Part of minimum viable product scope |
| `core` | Core system functionality |
| `infra` | Infrastructure and deployment concerns |
| `ai` | AI/ML related components |
| `frontend` | User-facing interface components |

Tags are freeform — you can create any tag. The above are conventions used in the seed data.

## Section Statuses

| Status | Meaning |
|--------|---------|
| `draft` | Initial writing, not yet reviewed |
| `in_progress` | Actively being worked on |
| `review` | Ready for review |
| `approved` | Finalized and approved |
| `outdated` | Needs update due to changes in dependencies |

## Dependency Graph (SnapHabit Example)

This graph shows the dependencies in the default seed (`02_seed.sql`):

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
