-- ContentForge Seed Data

-- Project
INSERT INTO projects (id, name, slug, description, version)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'ContentForge',
    'contentforge',
    'AI-powered content generation and management platform for creative teams',
    1
);

-- Helper: project ID variable
-- Using explicit UUIDs for referential integrity

-- Sections
-- 0: Overview
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    'overview',
    'Overview & Goals',
    'overview',
    0,
    'approved',
    ARRAY['mvp', 'core'],
    'ContentForge is an AI-powered content generation and management platform designed for creative teams working with text, images, and video. The platform orchestrates multiple AI models (GPT-4, Stable Diffusion, ComfyUI) through a unified pipeline that handles job scheduling, asset management, and workflow automation.

The primary goal is to reduce content production time by 60% while maintaining brand consistency through templated workflows. Teams can define reusable content pipelines that combine text generation, image creation, and post-processing steps into single-click operations.

Key objectives:
- Unified dashboard for all content generation tasks
- Template-based workflow system with approval gates
- Asset versioning and collaborative review
- Integration with existing DAM (Digital Asset Management) systems
- Cost tracking per generation job with budget alerts

The platform targets mid-size marketing teams (5-20 people) who currently use 3-5 separate AI tools and spend significant time on manual handoffs between tools.',
    'AI content generation platform orchestrating GPT-4, Stable Diffusion, and ComfyUI through unified pipelines. Targets 60% reduction in content production time for marketing teams of 5-20 people.',
    'Q: Should we support video generation in v1 or defer to v2?
Decision: Defer video to v2, focus on text + image pipelines for MVP.'
);

-- 1: Hardware
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000002',
    'a0000000-0000-0000-0000-000000000001',
    'hardware',
    'Hardware Constraints',
    'tech_spec',
    1,
    'approved',
    ARRAY['infra', 'core'],
    'ContentForge runs on a hybrid infrastructure combining cloud GPU instances and local development servers.

Production environment:
- 2x NVIDIA A100 80GB nodes for Stable Diffusion and ComfyUI workloads
- 1x 32-core CPU node for API server, queue workers, and database
- Shared NFS storage: 2TB for asset files, 500GB for model weights
- PostgreSQL 16 on dedicated SSD storage (1TB)

Development environment:
- Mac Mini M2 Pro (local development and testing)
- Single NVIDIA RTX 4090 for local model inference
- Docker Desktop with 16GB RAM allocation

Network constraints:
- Inter-node communication via 10Gbps internal network
- External API rate limits: OpenAI (10K RPM), Stability AI (150 RPM)
- Asset CDN bandwidth: 1Gbps with 50TB monthly transfer

Cost targets:
- GPU compute: < $3,000/month at 70% utilization
- Storage: < $200/month
- API costs: variable, tracked per-job',
    'Hybrid cloud-local infrastructure: 2x A100 GPU nodes for AI workloads, 32-core CPU node for services, NFS shared storage. Dev on Mac Mini M2 Pro with RTX 4090. GPU budget under $3K/month.',
    ''
);

-- 2: Tech Stack
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000003',
    'a0000000-0000-0000-0000-000000000001',
    'tech-stack',
    'Technology Stack',
    'tech_spec',
    2,
    'approved',
    ARRAY['mvp', 'core'],
    'Core technology decisions for ContentForge:

**Backend:**
- Python 3.11 with FastAPI for REST API
- Temporal.io for workflow orchestration (job scheduling, retry logic, saga patterns)
- Celery + Redis for lightweight async tasks (notifications, thumbnails)
- asyncpg for PostgreSQL access

**Frontend:**
- Next.js 14 with App Router
- Tailwind CSS + shadcn/ui component library
- TanStack Query for server state management

**AI/ML:**
- OpenAI GPT-4 API for text generation
- Stable Diffusion (self-hosted via diffusers library) for image generation
- ComfyUI for advanced image workflows (inpainting, upscaling, style transfer)
- CLIP for image-text similarity scoring

**Infrastructure:**
- Docker Compose for local development
- Kubernetes (k3s) for production deployment
- MinIO for S3-compatible object storage
- Prometheus + Grafana for monitoring
- Loki for log aggregation

**Database:**
- PostgreSQL 16 (primary datastore)
- Redis 7 (caching, rate limiting, Celery broker)
- pgvector extension for embedding similarity search',
    'Python/FastAPI backend, Next.js frontend, Temporal.io for workflow orchestration. AI stack: GPT-4, self-hosted Stable Diffusion, ComfyUI. PostgreSQL 16 + Redis, deployed via Docker/k3s.',
    'TODO: Evaluate n8n as Temporal alternative — simpler ops, visual workflow editor.
TODO: Benchmark pgvector vs dedicated vector DB (Qdrant) for embedding search.'
);

-- 3: Data Model
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000004',
    'a0000000-0000-0000-0000-000000000001',
    'data-model',
    'Data Model',
    'data_model',
    3,
    'in_progress',
    ARRAY['mvp', 'core'],
    'PostgreSQL schema for ContentForge, managed via Alembic migrations.

**Core entities:**

`jobs` — Central work unit. Each content generation request creates a Job.
- id (UUID), project_id (FK), workflow_id (FK), status (enum: queued/running/completed/failed/cancelled)
- input_params (JSONB), output_assets (UUID[]), cost_cents (INT)
- created_by (FK users), created_at, completed_at
- Priority queue ordering via (priority, created_at) index

`assets` — Generated or uploaded files.
- id (UUID), job_id (FK nullable), file_path (TEXT), mime_type (TEXT), size_bytes (BIGINT)
- metadata (JSONB — dimensions, duration, model used, seed)
- version (INT), parent_asset_id (FK self — for iterations)
- Soft delete via deleted_at timestamp

`workflows` — Reusable generation templates.
- id (UUID), name, slug, description, steps (JSONB array)
- Each step: {type: "text"|"image"|"transform", model: str, params: {}}
- is_template (BOOL), created_by (FK users)

`users` — Team members with role-based access.
- id (UUID), email, name, role (enum: admin/editor/viewer)
- budget_limit_cents (INT nullable), api_keys (JSONB encrypted)

Indexes: composite on (project_id, status, created_at) for dashboard queries, GIN on input_params and metadata JSONB fields, trigram on asset file_path for search.',
    'PostgreSQL schema with 4 core entities: Jobs (generation tasks with cost tracking), Assets (versioned files with metadata), Workflows (reusable step-based templates), Users (role-based access). Managed via Alembic migrations.',
    'TODO: Add Schedule entity for recurring job execution.
Q: Should asset versions be separate rows or use a versions JSONB array?
Decision pending: leaning toward separate rows for queryability.'
);

-- 4: Pipeline
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000005',
    'a0000000-0000-0000-0000-000000000001',
    'pipeline',
    'Processing Pipeline',
    'tech_spec',
    4,
    'in_progress',
    ARRAY['mvp', 'core', 'ai'],
    'The processing pipeline is the core execution engine of ContentForge. It receives job requests, resolves workflow steps, dispatches to appropriate AI models, and manages the output lifecycle.

**Pipeline stages:**

1. **Job Intake** — API receives generation request, validates input, creates Job record with status=queued.
2. **Workflow Resolution** — Temporal workflow starts, loads workflow template, resolves step parameters from input_params + defaults.
3. **Step Execution** — Each step runs as a Temporal activity:
   - Text steps → OpenAI GPT-4 API call with prompt template
   - Image steps → Stable Diffusion inference (local GPU) or ComfyUI workflow
   - Transform steps → FFmpeg, ImageMagick, or custom Python transforms
4. **Asset Registration** — Each step output is saved to MinIO, registered as Asset with metadata.
5. **Quality Gate** — Optional CLIP similarity check: does output match intent? Auto-retry if score < threshold.
6. **Completion** — Job marked completed, cost calculated from model usage, notification sent.

**Error handling:**
- Temporal handles retries with exponential backoff (max 3 attempts per step)
- Failed steps produce partial results (completed steps preserved)
- Dead letter queue for jobs that exceed retry limits
- Circuit breaker on external APIs (OpenAI) — fallback to cached similar results

**Throughput targets:**
- Text generation: < 5s per 1000 words
- Image generation: < 30s per 1024x1024 image (A100)
- End-to-end pipeline: < 2 minutes for typical 3-step workflow',
    'Temporal-orchestrated pipeline: Job Intake → Workflow Resolution → Step Execution (text/image/transform) → Asset Registration → Quality Gate (CLIP scoring) → Completion. Handles retries, partial failures, and cost tracking per step.',
    'TODO: Implement priority queue — high-priority jobs should preempt batch jobs.
TODO: Add webhook callback support for pipeline completion events.'
);

-- 5: ComfyUI Workflows
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000006',
    'a0000000-0000-0000-0000-000000000001',
    'comfyui-workflows',
    'ComfyUI Workflows',
    'tech_spec',
    5,
    'draft',
    ARRAY['ai'],
    'ComfyUI integration provides advanced image generation capabilities beyond basic text-to-image. ContentForge packages common operations as reusable ComfyUI workflow templates.

**Supported workflow types:**

1. **Style Transfer** — Apply artistic style from reference image to generated content.
   - Input: source image + style reference + strength (0.0-1.0)
   - Models: IP-Adapter + SDXL
   - Output: styled image at source resolution

2. **Inpainting** — Modify specific regions of existing images.
   - Input: source image + mask + text prompt
   - Models: SDXL Inpainting checkpoint
   - Output: composited image

3. **Upscaling** — Enhance resolution of generated images.
   - Input: low-res image + scale factor (2x/4x)
   - Models: Real-ESRGAN or SwinIR
   - Output: high-res image

4. **Batch Variations** — Generate multiple variations from single prompt.
   - Input: prompt + count + seed range
   - Output: N images with sequential seeds

**Integration pattern:**
- ComfyUI runs as a sidecar container with GPU access
- ContentForge sends workflow JSON via ComfyUI REST API
- Results polled via WebSocket connection
- Workflow templates stored in `workflows` table as JSONB',
    'ComfyUI sidecar provides advanced image ops: style transfer (IP-Adapter), inpainting (SDXL), upscaling (Real-ESRGAN), and batch variations. Integrated via REST API with WebSocket result polling.',
    ''
);

-- 6: API Spec
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000007',
    'a0000000-0000-0000-0000-000000000001',
    'api-spec',
    'API Specification',
    'api_spec',
    6,
    'in_progress',
    ARRAY['mvp', 'frontend'],
    'RESTful API built with FastAPI. All endpoints return JSON. Authentication via Bearer token (JWT).

**Base URL:** `https://api.contentforge.local/v1`

**Jobs:**
- `POST /jobs` — Create generation job {workflow_id, input_params, priority}
- `GET /jobs` — List jobs with filters {status, project_id, created_after, limit, offset}
- `GET /jobs/{id}` — Job details including step progress
- `DELETE /jobs/{id}` — Cancel running job (sends cancel signal to Temporal)
- `GET /jobs/{id}/assets` — List output assets for job

**Assets:**
- `GET /assets/{id}` — Asset metadata + signed download URL
- `GET /assets/{id}/download` — Direct file download (redirects to MinIO pre-signed URL)
- `POST /assets/upload` — Upload source asset (multipart/form-data)
- `DELETE /assets/{id}` — Soft delete asset

**Workflows:**
- `GET /workflows` — List available workflow templates
- `POST /workflows` — Create custom workflow {name, steps}
- `GET /workflows/{id}` — Workflow details with step definitions
- `PUT /workflows/{id}` — Update workflow (creates new version)

**Projects:**
- `GET /projects` — List projects for current user
- `POST /projects` — Create project {name, description}
- `GET /projects/{id}/stats` — Usage statistics and cost breakdown

**Rate limiting:** 100 req/min per user, 1000 req/min global. 429 response with Retry-After header.

**Pagination:** Cursor-based using `?after={last_id}&limit=50`. Response includes `has_more` boolean.',
    'FastAPI REST API with JWT auth. CRUD for Jobs (create, list, cancel), Assets (metadata, download, upload), Workflows (template management), and Projects (with cost stats). Rate limited at 100 RPM per user.',
    'TODO: Add WebSocket endpoint for real-time job progress updates.
TODO: Define error response schema (error code, message, details).'
);

-- 7: UI Design
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000008',
    'a0000000-0000-0000-0000-000000000001',
    'ui-design',
    'UI Design',
    'ui_design',
    7,
    'draft',
    ARRAY['frontend'],
    'Next.js application with three primary views:

**1. Dashboard** — Overview of recent jobs, active workflows, and cost summary.
- Job status cards with real-time progress indicators
- Cost-per-day chart (last 30 days)
- Quick-launch buttons for favorite workflows

**2. Job Detail** — Full job view with step-by-step progress.
- Timeline visualization of pipeline stages
- Side-by-side input/output comparison for each step
- Asset preview gallery with zoom and download
- Cost breakdown per step (tokens, GPU seconds, API calls)

**3. Workflow Editor** — Visual builder for generation pipelines.
- Drag-and-drop step arrangement
- Per-step parameter configuration panel
- Live preview with test inputs
- Version history with diff view

**Design system:**
- Colors: Dark mode default (bg #0a0a0a, surface #1a1a1a, accent #7c3aed violet)
- Typography: Inter for UI, Fira Code for technical content
- Components: shadcn/ui with custom theme tokens
- Responsive: Desktop-first, minimum 1280px viewport
- Accessibility: WCAG 2.1 AA compliance target

**State management:**
- TanStack Query for server state (jobs, assets, workflows)
- Zustand for client state (filters, preferences, UI state)
- Optimistic updates for job creation and workflow saves',
    'Next.js dashboard with three views: Dashboard (job overview + costs), Job Detail (step progress + asset preview), Workflow Editor (visual pipeline builder). Dark mode, shadcn/ui components, TanStack Query state management.',
    'TODO: Design mobile-responsive layout for job monitoring (tablet minimum).
TODO: Add keyboard shortcuts for power users (j/k navigation, Cmd+Enter to launch).'
);

-- 8: Deployment
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000009',
    'a0000000-0000-0000-0000-000000000001',
    'deployment',
    'Deployment Strategy',
    'deployment',
    8,
    'approved',
    ARRAY['infra'],
    'ContentForge deploys as a set of Docker containers orchestrated by k3s in production and Docker Compose for development.

**Container topology:**
- `api` — FastAPI application server (2 replicas, 2GB RAM each)
- `worker` — Celery workers for async tasks (2 replicas, 1GB RAM each)
- `temporal` — Temporal server + PostgreSQL persistence (single node)
- `temporal-worker` — Temporal workflow workers with GPU access (1 per GPU node)
- `comfyui` — ComfyUI server with GPU passthrough (1 per GPU node)
- `postgres` — PostgreSQL 16 with persistent volume (8GB RAM)
- `redis` — Redis 7 for caching and Celery broker (1GB RAM)
- `minio` — S3-compatible object storage (persistent volume)
- `nginx` — Reverse proxy with SSL termination

**Deployment workflow:**
1. Push to main → GitHub Actions builds Docker images
2. Images pushed to private registry (Harbor)
3. ArgoCD detects new images, updates k3s manifests
4. Rolling update with health check gates
5. Slack notification on success/failure

**Environment management:**
- dev: Docker Compose on local machine
- staging: k3s single-node with reduced resources
- production: k3s multi-node with GPU scheduling

**Backup strategy:**
- PostgreSQL: pg_dump daily to MinIO bucket (7-day retention)
- Assets: MinIO bucket replication to offsite NAS
- Workflows: exported as JSON, committed to git repo',
    'Docker/k3s deployment with 9 containers. CI/CD via GitHub Actions → Harbor → ArgoCD rolling updates. Three environments (dev/staging/prod). Daily PostgreSQL backups to MinIO with 7-day retention.',
    ''
);

-- 9: Security
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000010',
    'a0000000-0000-0000-0000-000000000001',
    'security',
    'Security Model',
    'security',
    9,
    'draft',
    ARRAY['infra'],
    'Security model for ContentForge covers authentication, authorization, API security, and data protection.

**Authentication:**
- JWT tokens issued by API server (RS256 signing)
- Token expiry: 1 hour access, 7 day refresh
- SSO integration via OIDC (Google Workspace planned)

**Authorization:**
- Role-based: admin (full access), editor (create/edit jobs and workflows), viewer (read-only)
- Project-scoped: users belong to projects, can only access their project resources
- API key scoping: per-project keys with configurable permissions

**API Security:**
- Rate limiting per user and global (Redis-backed)
- Request size limits: 10MB for uploads, 1MB for JSON bodies
- CORS: restricted to frontend domain
- Input validation: Pydantic models on all endpoints

**Data Protection:**
- API keys encrypted at rest (Fernet symmetric encryption)
- Database connections via SSL in production
- Asset URLs: pre-signed with 1-hour expiry
- No PII stored beyond email and name
- Audit log for all write operations (append-only table)

**Infrastructure:**
- Network policies: API only accessible via nginx ingress
- Secrets management: Kubernetes secrets (production), .env files (dev)
- Container scanning: Trivy in CI pipeline
- Dependency scanning: Dependabot alerts enabled',
    'JWT auth (RS256) with role-based access (admin/editor/viewer). Project-scoped authorization, rate limiting, encrypted API keys. Production uses K8s secrets, SSL, and Trivy container scanning.',
    'TODO: Implement OIDC SSO integration with Google Workspace.
TODO: Add IP allowlisting for API key access.'
);

-- 10: Legal
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000011',
    'a0000000-0000-0000-0000-000000000001',
    'legal',
    'Legal & Compliance',
    'general',
    10,
    'draft',
    ARRAY[]::TEXT[],
    'Legal considerations for AI-generated content platform.

**Content ownership:**
- Generated content belongs to the user/organization that created the job
- Users must have rights to any uploaded source material (style references, inpainting sources)
- Platform retains no ownership claims on generated content

**AI model licensing:**
- OpenAI: commercial use permitted under API ToS
- Stable Diffusion: CreativeML Open RAIL-M license — permits commercial use with attribution
- ComfyUI: GPL-3.0 — server-side use, no distribution of modified code required
- Real-ESRGAN: BSD-3-Clause — permissive commercial use

**Data retention:**
- Generated assets: retained until user deletes or project archived (max 1 year inactive)
- Job metadata: retained for 2 years for billing and audit purposes
- User data: deleted within 30 days of account closure (GDPR compliance)

**Content moderation:**
- NSFW filter on all generated images (configurable per-project for licensed adult content)
- Prompt injection detection on text generation inputs
- Generated content hash stored for provenance tracking

**Terms of Service:**
- Users responsible for ensuring generated content does not infringe third-party IP
- Platform provides tools, not legal guarantees on output originality
- Indemnification clause for API misuse',
    'Content ownership belongs to users. AI model licenses permit commercial use (OpenAI ToS, RAIL-M, GPL-3.0, BSD-3). GDPR-compliant data retention. NSFW filtering and provenance tracking included.',
    ''
);

-- 11: Risks
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000012',
    'a0000000-0000-0000-0000-000000000001',
    'risks',
    'Risks & Mitigations',
    'general',
    11,
    'draft',
    ARRAY[]::TEXT[],
    'Key risks identified for ContentForge and their mitigation strategies.

**Technical risks:**

1. **GPU availability** — Cloud GPU instances may be unavailable during high demand.
   - Mitigation: Multi-provider setup (RunPod + Lambda Labs), preemptible instance fallback.
   - Impact: Medium. Degraded throughput, not outage.

2. **Model quality regression** — OpenAI model updates may change output quality.
   - Mitigation: Pin model versions (gpt-4-0613), A/B test before upgrading.
   - Impact: Medium. Affects output consistency.

3. **Storage growth** — Generated assets accumulate rapidly (avg 5MB per image).
   - Mitigation: Lifecycle policies (compress after 30 days, archive after 90, delete after 365).
   - Impact: Low with policies in place.

**Operational risks:**

4. **API cost overrun** — Unbounded generation could exceed budget.
   - Mitigation: Per-user budget limits, per-project spending caps, daily cost alerts.
   - Impact: High if unmitigated.

5. **Single point of failure** — Temporal server downtime blocks all pipelines.
   - Mitigation: Temporal cluster mode in production, job queue persists through restart.
   - Impact: High. No workaround for orchestration failure.

**Business risks:**

6. **AI regulatory changes** — EU AI Act may impose new requirements.
   - Mitigation: Content provenance tracking already implemented, adaptable moderation.
   - Impact: Unknown, monitored quarterly.',
    'Six key risks: GPU availability (multi-provider), model quality regression (version pinning), storage growth (lifecycle policies), API cost overrun (budget limits), Temporal SPOF (cluster mode), AI regulation (provenance tracking).',
    ''
);

-- 12: Timeline
INSERT INTO sections (id, project_id, slug, title, section_type, sort_order, status, tags, content, summary, notes)
VALUES (
    'b0000000-0000-0000-0000-000000000013',
    'a0000000-0000-0000-0000-000000000001',
    'timeline',
    'Implementation Timeline',
    'timeline',
    12,
    'in_progress',
    ARRAY['mvp'],
    'Phased implementation plan for ContentForge MVP and beyond.

**Phase 1 — Foundation (Weeks 1-4):**
- Database schema and migrations (data-model)
- FastAPI skeleton with auth middleware
- Basic job creation and listing endpoints
- Docker Compose development environment
- CI/CD pipeline setup (GitHub Actions → Harbor)

**Phase 2 — Pipeline Core (Weeks 5-8):**
- Temporal workflow engine integration
- Text generation pipeline (GPT-4)
- Image generation pipeline (Stable Diffusion)
- Asset storage and retrieval (MinIO)
- Job progress tracking and notifications

**Phase 3 — UI & Polish (Weeks 9-12):**
- Next.js dashboard implementation
- Job detail view with progress timeline
- Workflow editor (basic — sequential steps only)
- Cost tracking and budget alerts
- User management and RBAC

**Phase 4 — Advanced Features (Weeks 13-16):**
- ComfyUI integration (style transfer, inpainting)
- Batch operations and scheduling
- Advanced workflow editor (branching, conditions)
- Performance optimization and caching
- Load testing and capacity planning

**MVP definition:** Phases 1-3 complete. Users can create text+image generation jobs via API and UI, with basic workflow templates, cost tracking, and role-based access.

**Post-MVP backlog:**
- Video generation support
- Plugin/webhook system
- Multi-tenant SaaS mode
- Mobile companion app',
    'Four-phase plan: Foundation (weeks 1-4, schema + API + CI), Pipeline Core (5-8, Temporal + AI models + assets), UI & Polish (9-12, dashboard + workflows + RBAC), Advanced (13-16, ComfyUI + batch + optimization). MVP = phases 1-3.',
    'TODO: Re-evaluate timeline after tech-stack decision on Temporal vs n8n.
Blocked on: hardware procurement for second A100 node.'
);

-- Dependencies (matching PRD §8.2 graph)
-- tech-stack → hardware: references
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000003',  -- tech-stack
    'b0000000-0000-0000-0000-000000000002',  -- hardware
    'references',
    'Platform capabilities constrain tech choices'
);

-- data-model → tech-stack: implements
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000004',  -- data-model
    'b0000000-0000-0000-0000-000000000003',  -- tech-stack
    'implements',
    'ORM and migration patterns from tech-stack'
);

-- pipeline → tech-stack: implements
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000005',  -- pipeline
    'b0000000-0000-0000-0000-000000000003',  -- tech-stack
    'implements',
    'Workflow engine and AI model choices from tech-stack'
);

-- pipeline → hardware: references
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000005',  -- pipeline
    'b0000000-0000-0000-0000-000000000002',  -- hardware
    'references',
    'GPU resources and throughput targets from hardware'
);

-- pipeline → data-model: implements
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000005',  -- pipeline
    'b0000000-0000-0000-0000-000000000004',  -- data-model
    'implements',
    'Job and Asset entities from data model'
);

-- comfyui-workflows → pipeline: references
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000006',  -- comfyui-workflows
    'b0000000-0000-0000-0000-000000000005',  -- pipeline
    'references',
    'Integrates as pipeline step type'
);

-- api-spec → data-model: references
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000007',  -- api-spec
    'b0000000-0000-0000-0000-000000000004',  -- data-model
    'references',
    'CRUD endpoints mirror data model entities'
);

-- api-spec → pipeline: references
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000007',  -- api-spec
    'b0000000-0000-0000-0000-000000000005',  -- pipeline
    'references',
    'Job creation triggers pipeline execution'
);

-- ui-design → api-spec: implements
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000008',  -- ui-design
    'b0000000-0000-0000-0000-000000000007',  -- api-spec
    'implements',
    'Consumes REST endpoints defined in API spec'
);

-- deployment → tech-stack: implements
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000009',  -- deployment
    'b0000000-0000-0000-0000-000000000003',  -- tech-stack
    'implements',
    'Docker per component, split by node type'
);

-- deployment → hardware: references
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000009',  -- deployment
    'b0000000-0000-0000-0000-000000000002',  -- hardware
    'references',
    'Container topology matches hardware nodes'
);

-- timeline → data-model: references
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000013',  -- timeline
    'b0000000-0000-0000-0000-000000000004',  -- data-model
    'references',
    'Scopes Phase 1 foundation work'
);

-- timeline → pipeline: references
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000013',  -- timeline
    'b0000000-0000-0000-0000-000000000005',  -- pipeline
    'references',
    'Scopes Phase 2 pipeline work'
);

-- timeline → ui-design: references
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000013',  -- timeline
    'b0000000-0000-0000-0000-000000000008',  -- ui-design
    'references',
    'Scopes Phase 3 UI work'
);

-- timeline → deployment: references
INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000013',  -- timeline
    'b0000000-0000-0000-0000-000000000009',  -- deployment
    'references',
    'Scopes deployment across all phases'
);
