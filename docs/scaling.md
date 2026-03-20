# Scaling & Production Deployment

**Last updated:** 2026-03-20
**Status:** Current
**Audience:** Self-hosters, DevOps engineers, contributors planning production deployment

---

## Overview

PRDforge ships as a Docker Compose stack designed for single-host deployment. This document covers what to consider when scaling beyond a single user or deploying to production infrastructure.

## Table of Contents

- [Current Architecture](#current-architecture)
- [Connection Pooling](#connection-pooling)
- [Authentication & Access Control](#authentication--access-control)
- [Reverse Proxy & TLS](#reverse-proxy--tls)
- [Database Scaling](#database-scaling)
- [WebSocket Scaling](#websocket-scaling)
- [Monitoring & Observability](#monitoring--observability)
- [Backup & Recovery](#backup--recovery)
- [Production Checklist](#production-checklist)

---

## Current Architecture

PRDforge runs **5 Docker containers** on a single host:

| Service | Port | Purpose |
|:--------|:-----|:--------|
| `postgres` | 5432 | PostgreSQL 16 — app data + Prefect-style metadata |
| `mcp-server` | 8080 | MCP tool server (Python, FastMCP, Streamable HTTP) |
| `python-api` | 8088 | FastAPI — REST API for dashboard, chat SSE, WebSocket |
| `redis` | — | Token replay protection (WS jti SET NX EX), pub/sub |
| `frontend` | 3000 | Next.js — dashboard UI |

The asyncpg connection pool defaults:

```python
asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
```

Suitable for 1–5 concurrent users on a single host.

---

## Connection Pooling

For higher concurrency (10+ simultaneous users), add external connection pooling:

### PgBouncer (recommended)

Place between application containers and PostgreSQL. Use transaction pooling mode:

```ini
[databases]
prdforge = host=postgres port=5432 dbname=prdforge

[pgbouncer]
pool_mode = transaction
max_client_conn = 200
default_pool_size = 20
min_pool_size = 5
```

### Application-Level Tuning

Increase the asyncpg pool size in both the MCP server and Python API:

```python
# For 10-20 concurrent users
asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=30)
```

### Monitoring

Watch for connection saturation:

```sql
SELECT count(*), state FROM pg_stat_activity
WHERE datname = 'prdforge'
GROUP BY state;
```

---

## Authentication & Access Control

PRDforge includes **built-in authentication** via Better Auth:

| Feature | Status |
|:--------|:-------|
| Email/password authentication | Implemented |
| Closed sign-up (admin creates users) | Implemented |
| First-user bootstrap flow | Implemented |
| Password reset (admin-generated tokens) | Implemented |
| RBAC (5 roles: owner → viewer) | Implemented |
| Session-based auth on all endpoints | Implemented |
| Google OAuth | Config ready, needs Cloud Console credentials |

### Pre-Setup Mode

When no users exist (bootstrap table empty), all endpoints are open — no auth enforced. This allows initial setup via MCP tools or the UI. After the first user is created via `/api/auth/setup`, authentication is enforced on all protected endpoints.

### WebSocket Authentication

WebSocket connections use short-lived HMAC tokens:
1. Client calls `POST /api/ws-token` (authenticated, user_id derived from session)
2. Server mints a token with 120-second TTL
3. Client connects to `ws://host/ws/projects/{slug}?token=...`
4. Server verifies HMAC, checks jti uniqueness via Redis (replay protection)
5. Server re-checks project membership before accepting

---

## Reverse Proxy & TLS

For non-localhost deployment, place a reverse proxy in front of all services:

### Nginx Example

```nginx
server {
    listen 443 ssl http2;
    server_name prdforge.example.com;

    ssl_certificate     /etc/ssl/prdforge.crt;
    ssl_certificate_key /etc/ssl/prdforge.key;

    # Frontend (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8088;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
    }

    # MCP Server (restrict to internal/VPN)
    location /mcp/ {
        proxy_pass http://127.0.0.1:8080;
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        deny all;
    }
}
```

**Key considerations:**
- WebSocket endpoints need `Upgrade` and `Connection` headers
- MCP server should be restricted to trusted networks (Claude Code/Desktop connects directly)
- Set `proxy_read_timeout` high for WebSocket connections and SSE chat streams

---

## Database Scaling

### Read Replicas

For read-heavy workloads, configure PostgreSQL streaming replication and route read-only MCP tools to a replica:

```python
# Read pool (replica)
read_pool = asyncpg.create_pool(REPLICA_URL, min_size=2, max_size=20)

# Write pool (primary)
write_pool = asyncpg.create_pool(PRIMARY_URL, min_size=2, max_size=10)
```

### Vacuuming

The `token_estimates` and `section_access_log` tables grow continuously. Ensure autovacuum is tuned:

```sql
-- Check autovacuum stats
SELECT relname, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_dead_tup DESC;
```

Consider periodic pruning for analytics tables:

```sql
-- Keep 90 days of token estimates
DELETE FROM token_estimates WHERE created_at < now() - interval '90 days';

-- Keep 90 days of access logs
DELETE FROM section_access_log WHERE created_at < now() - interval '90 days';
```

### Indexes

All critical indexes are created in the migration files. Verify they exist:

```sql
SELECT indexname, tablename FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename;
```

---

## WebSocket Scaling

### Single Host (Current)

WebSocket connections are held in-memory by the Python API process. Presence broadcasts use a local dict. Redis pub/sub is used for cross-process event broadcasting.

### Multi-Process / Multi-Host

If running multiple API instances behind a load balancer:

1. **Sticky sessions** — required for WebSocket connections. Configure your load balancer to route WebSocket upgrades to the same backend.
2. **Redis pub/sub** — already implemented. All project events are published to Redis channels. Multiple API instances subscribe and broadcast to their local connections.
3. **Token replay protection** — already uses Redis `SET NX EX`. Works across multiple instances.

---

## Monitoring & Observability

### Built-in

| What | Where |
|:-----|:------|
| Pipeline health | Stats tab in the dashboard |
| Token savings | Stats tab — gauge, charts, by-operation breakdown |
| MCP tool activity | `mcp_activity` table (last 50 entries in Stats tab) |
| Audit trail | `audit_events` table, `/api/projects/{slug}/audit` endpoint |

### External Integration (Optional)

| Tool | Integration point |
|:-----|:-----------------|
| **Prometheus** | Add `/metrics` endpoint (TODO — see `TODO.md`) |
| **Grafana** | Connect to PostgreSQL directly for custom dashboards |
| **Structured logging** | Python API and MCP server use Python `logging` — configure JSON formatter for log aggregation |

### Health Checks

All services expose health checks used by Docker Compose:

```bash
# PostgreSQL
pg_isready -U prdforge

# MCP Server
curl -sf http://localhost:8080/mcp/

# Python API
curl -sf http://localhost:8088/health

# Redis
redis-cli ping

# Frontend
curl -sf http://localhost:3000/
```

---

## Backup & Recovery

### Database Backup

```bash
# Dump to file
docker compose exec postgres pg_dump -U prdforge prdforge > backup_$(date +%Y%m%d).sql

# Restore from file
docker compose exec -i postgres psql -U prdforge prdforge < backup_20260320.sql
```

### Volume Backup

PostgreSQL data lives in the `pgdata` Docker volume:

```bash
# Find volume location
docker volume inspect prdforge_pgdata --format '{{ .Mountpoint }}'

# Backup volume (stop services first)
docker compose stop
tar czf pgdata_backup.tar.gz -C /var/lib/docker/volumes/prdforge_pgdata/_data .
docker compose up -d
```

### Recovery Testing

Periodically verify backups can be restored:

```bash
# Create a test database
docker compose exec postgres createdb -U prdforge prdforge_test

# Restore backup into test database
docker compose exec -i postgres psql -U prdforge prdforge_test < backup.sql

# Verify
docker compose exec postgres psql -U prdforge prdforge_test -c "SELECT count(*) FROM projects;"

# Cleanup
docker compose exec postgres dropdb -U prdforge prdforge_test
```

---

## Production Checklist

Before deploying to production, verify:

### Security

- [ ] `WS_TOKEN_SECRET` env var set (not using default dev value)
- [ ] `BETTER_AUTH_SECRET` env var set
- [ ] PostgreSQL password changed from default (`prdforge`)
- [ ] MCP server port (8080) not exposed to public internet
- [ ] TLS configured via reverse proxy
- [ ] First user created via bootstrap flow

### Reliability

- [ ] Docker restart policies set to `unless-stopped` (default in compose)
- [ ] PostgreSQL health check passing
- [ ] Redis health check passing
- [ ] Log rotation configured for Docker containers
- [ ] Database backup schedule in place

### Performance

- [ ] asyncpg pool size tuned for expected concurrency
- [ ] PgBouncer deployed if >10 concurrent users expected
- [ ] Autovacuum verified on analytics tables
- [ ] Redis maxmemory configured if running on constrained host

### Observability

- [ ] Health check endpoints monitored
- [ ] Database connection count monitored
- [ ] Disk space monitored (PostgreSQL data volume)
- [ ] Log aggregation configured (optional)
