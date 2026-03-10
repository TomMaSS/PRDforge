# Scaling & Multi-User Considerations

PRD Forge is designed as a **single-user local tool**. This document describes what you'd need to change if you want to scale it beyond that.

## Current Configuration

The MCP server uses an asyncpg connection pool with these defaults:

```python
asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
```

This is appropriate for a single user running Claude against one PostgreSQL instance.

## Connection Pooling for Multi-User

If multiple users connect concurrently, you'll want external connection pooling:

- **PgBouncer** — lightweight PostgreSQL connection pooler. Place between the MCP server and PostgreSQL. Configure in transaction pooling mode to maximize connection reuse.
- **Increase `max_size`** — bump the asyncpg pool to 20-50 depending on expected concurrency.
- **Monitor connections** — watch `pg_stat_activity` for connection saturation.

Example PgBouncer setup:

```ini
[databases]
prdforge = host=postgres port=5432 dbname=prdforge

[pgbouncer]
pool_mode = transaction
max_client_conn = 200
default_pool_size = 20
```

## Authentication & Reverse Proxy

PRD Forge has **no built-in authentication**. For multi-user or non-localhost deployments:

1. **Reverse proxy** — put nginx, Caddy, or Traefik in front of the MCP server (port 8080) and Web UI (port 8088)
2. **TLS termination** — configure HTTPS at the proxy level
3. **Authentication** — add HTTP Basic Auth, OAuth2 proxy (e.g., oauth2-proxy), or mTLS at the proxy layer
4. **Network isolation** — restrict the MCP server to only accept connections from the proxy, not directly from clients

Example nginx config snippet:

```nginx
server {
    listen 443 ssl;
    server_name prdforge.internal;

    ssl_certificate     /etc/ssl/prdforge.crt;
    ssl_certificate_key /etc/ssl/prdforge.key;

    # Basic auth
    auth_basic "PRD Forge";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location /mcp/ {
        proxy_pass http://127.0.0.1:8080;
    }

    location / {
        proxy_pass http://127.0.0.1:8088;
    }
}
```

## Database Scaling

- **Read replicas** — for read-heavy workloads, configure PostgreSQL streaming replication and point read-only MCP tools to a replica
- **Backup strategy** — already documented in the README (`pg_dump` to file or MinIO)
- **Vacuuming** — with heavy `token_estimates` inserts, ensure autovacuum is tuned. Consider periodic `DELETE FROM token_estimates WHERE created_at < now() - interval '90 days'` to prune old data.

## What PRD Forge Does NOT Support (Yet)

- Multi-tenant isolation (all data is in one schema)
- Per-user permissions or RBAC
- Session management or API keys
- Rate limiting

These would need to be built if you're deploying PRD Forge as a shared service.
