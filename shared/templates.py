"""Project templates with pre-built section structures."""

from dataclasses import dataclass, field


@dataclass
class SectionSpec:
    slug: str
    title: str
    section_type: str
    content: str
    sort_order: int = 0


@dataclass
class TemplateSpec:
    name: str
    description: str
    sections: list[SectionSpec] = field(default_factory=list)

    @property
    def section_count(self) -> int:
        return len(self.sections)


TEMPLATES: dict[str, TemplateSpec] = {
    "blank": TemplateSpec(
        name="Blank Project",
        description="Empty project — add your own sections.",
        sections=[],
    ),
    "saas-mvp": TemplateSpec(
        name="SaaS MVP",
        description="Product requirements for a SaaS minimum viable product.",
        sections=[
            SectionSpec(
                slug="overview",
                title="Product Overview",
                section_type="overview",
                sort_order=1,
                content="""\
## Vision

Describe the product vision and the problem it solves.

## Target Audience

- Primary persona
- Secondary persona

## Success Metrics

| Metric | Target | Timeframe |
|--------|--------|-----------|
| MAU    |        | 3 months  |
| Churn  |        | Monthly   |
""",
            ),
            SectionSpec(
                slug="tech-stack",
                title="Tech Stack & Architecture",
                section_type="architecture",
                sort_order=2,
                content="""\
## Architecture Overview

Describe the high-level system architecture.

## Tech Stack

| Layer     | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend  |           |           |
| Backend   |           |           |
| Database  |           |           |
| Hosting   |           |           |

## Key Decisions

- ADR-001: ...
""",
            ),
            SectionSpec(
                slug="data-model",
                title="Data Model",
                section_type="data_model",
                sort_order=3,
                content="""\
## Core Entities

### Users
| Field | Type | Constraints |
|-------|------|-------------|
| id    | UUID | PK          |
| email | text | unique      |

### (Add more entities)

## Relationships

- Users → ...
""",
            ),
            SectionSpec(
                slug="api-design",
                title="API Design",
                section_type="api_spec",
                sort_order=4,
                content="""\
## Authentication

Describe the auth mechanism (JWT, session, OAuth).

## Endpoints

### `POST /api/auth/login`
- **Request:** `{ email, password }`
- **Response:** `{ token, user }`

### (Add more endpoints)

## Error Handling

Standard error response:
```json
{ "error": { "code": "NOT_FOUND", "message": "..." } }
```
""",
            ),
            SectionSpec(
                slug="ui-design",
                title="UI/UX Design",
                section_type="ui_design",
                sort_order=5,
                content="""\
## Design Principles

1. Simplicity first
2. Mobile-responsive
3. Accessible (WCAG 2.1 AA)

## Key Screens

### Dashboard
- Purpose: ...
- Key components: ...

### Settings
- Purpose: ...

## Design System

- Typography: ...
- Color palette: ...
""",
            ),
            SectionSpec(
                slug="security",
                title="Security Requirements",
                section_type="security",
                sort_order=6,
                content="""\
## Authentication & Authorization

- Auth method: ...
- Session management: ...
- Role-based access control: ...

## Data Protection

- Encryption at rest: ...
- Encryption in transit: TLS 1.2+
- PII handling: ...

## Compliance

- GDPR considerations: ...
""",
            ),
            SectionSpec(
                slug="timeline",
                title="Roadmap & Timeline",
                section_type="timeline",
                sort_order=7,
                content="""\
## Phase 1: MVP (Weeks 1-4)

- [ ] Core user flows
- [ ] Authentication
- [ ] Basic dashboard

## Phase 2: Beta (Weeks 5-8)

- [ ] Feedback integration
- [ ] Performance optimization
- [ ] Documentation

## Phase 3: Launch

- [ ] Marketing site
- [ ] Monitoring & alerting
- [ ] Support workflows
""",
            ),
        ],
    ),
    "mobile-app": TemplateSpec(
        name="Mobile App",
        description="Requirements for a cross-platform mobile application.",
        sections=[
            SectionSpec(
                slug="overview",
                title="App Overview",
                section_type="overview",
                sort_order=1,
                content="""\
## App Concept

Describe the app concept and core value proposition.

## Platforms

- iOS (minimum version: ...)
- Android (minimum API level: ...)

## Target Users

- Primary: ...
- Secondary: ...
""",
            ),
            SectionSpec(
                slug="features",
                title="Core Features",
                section_type="tech_spec",
                sort_order=2,
                content="""\
## Feature List

### P0 — Must Have
1. User registration & login
2. ...

### P1 — Should Have
1. Push notifications
2. ...

### P2 — Nice to Have
1. ...
""",
            ),
            SectionSpec(
                slug="ui-design",
                title="UI/UX Design",
                section_type="ui_design",
                sort_order=3,
                content="""\
## Navigation Structure

- Tab bar / drawer navigation
- Screen flow diagram

## Key Screens

### Onboarding
- Steps: ...

### Home
- Layout: ...

### Profile
- Fields: ...

## Design Guidelines

- Follow platform conventions (Material Design / HIG)
- Accessibility: minimum tap target 44pt
""",
            ),
            SectionSpec(
                slug="data-model",
                title="Data Model & Storage",
                section_type="data_model",
                sort_order=4,
                content="""\
## Local Storage

- Offline-first strategy: ...
- Cache invalidation: ...

## Backend API

- Base URL: ...
- Authentication: Bearer token

## Sync Strategy

- Conflict resolution: last-write-wins / merge
- Background sync: ...
""",
            ),
            SectionSpec(
                slug="deployment",
                title="Build & Deployment",
                section_type="deployment",
                sort_order=5,
                content="""\
## Build Pipeline

- CI/CD: ...
- Code signing: ...

## Distribution

- App Store / Google Play
- TestFlight / Internal testing track
- OTA updates: ...

## Monitoring

- Crash reporting: ...
- Analytics: ...
- Performance monitoring: ...
""",
            ),
        ],
    ),
    "api-design": TemplateSpec(
        name="API Design",
        description="Backend API specification with data model and deployment.",
        sections=[
            SectionSpec(
                slug="overview",
                title="API Overview",
                section_type="overview",
                sort_order=1,
                content="""\
## Purpose

Describe the API's purpose and the systems it serves.

## Consumers

- Frontend web app
- Mobile apps
- Third-party integrations

## Conventions

- REST / GraphQL / gRPC
- Versioning strategy: URL path (`/v1/`) / header
- Pagination: cursor-based / offset
""",
            ),
            SectionSpec(
                slug="auth",
                title="Authentication & Authorization",
                section_type="security",
                sort_order=2,
                content="""\
## Auth Flow

1. Client sends credentials to `POST /auth/token`
2. Server returns JWT (access + refresh)
3. Client includes `Authorization: Bearer <token>` on requests

## Scopes & Permissions

| Scope    | Description        |
|----------|--------------------|
| read     | Read-only access   |
| write    | Create/update      |
| admin    | Full access        |

## Rate Limiting

- Default: 100 req/min per API key
- Authenticated: 1000 req/min
""",
            ),
            SectionSpec(
                slug="endpoints",
                title="Endpoint Reference",
                section_type="api_spec",
                sort_order=3,
                content="""\
## Resources

### Users (`/api/v1/users`)

| Method | Path           | Description      | Auth    |
|--------|---------------|------------------|---------|
| GET    | /users         | List users       | admin   |
| POST   | /users         | Create user      | admin   |
| GET    | /users/:id     | Get user         | read    |
| PATCH  | /users/:id     | Update user      | write   |

### (Add more resources)

## Error Responses

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "email is required",
    "details": { "field": "email" }
  }
}
```
""",
            ),
            SectionSpec(
                slug="data-model",
                title="Data Model",
                section_type="data_model",
                sort_order=4,
                content="""\
## Database

- Engine: PostgreSQL / MySQL / MongoDB
- Migrations: ...

## Schema

### users
| Column     | Type         | Constraints       |
|------------|-------------|-------------------|
| id         | UUID         | PK                |
| email      | VARCHAR(255) | UNIQUE, NOT NULL  |
| created_at | TIMESTAMPTZ  | DEFAULT now()     |

### (Add more tables)

## Indexes

- `users(email)` — unique
""",
            ),
            SectionSpec(
                slug="deployment",
                title="Deployment & Operations",
                section_type="deployment",
                sort_order=5,
                content="""\
## Infrastructure

- Runtime: Docker / serverless
- Hosting: AWS / GCP / Azure
- Database: managed / self-hosted

## CI/CD

- Pipeline stages: lint → test → build → deploy
- Environments: dev / staging / production

## Observability

- Logging: structured JSON
- Metrics: request latency, error rate, throughput
- Alerting: ...

## Backup & Recovery

- Database backups: daily automated
- RTO / RPO targets: ...
""",
            ),
            SectionSpec(
                slug="testing",
                title="Testing Strategy",
                section_type="testing",
                sort_order=6,
                content="""\
## Test Pyramid

### Unit Tests
- Coverage target: 80%
- Framework: ...

### Integration Tests
- Database: test containers
- External services: mocked / sandboxed

### E2E / Contract Tests
- API contract tests for each consumer
- Tool: Pact / Dredd / custom

## Load Testing

- Tool: k6 / Locust
- Targets: p95 < 200ms at 1000 RPS
""",
            ),
        ],
    ),
}


def get_template(template_id: str) -> TemplateSpec | None:
    return TEMPLATES.get(template_id)


def list_templates() -> list[dict]:
    return [
        {
            "id": tid,
            "name": t.name,
            "description": t.description,
            "section_count": t.section_count,
        }
        for tid, t in TEMPLATES.items()
    ]
