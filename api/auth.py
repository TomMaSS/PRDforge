"""Python-side auth: read-only consumer of Better Auth tables.

All auth write operations happen in Next.js. Python API validates
sessions and resolves roles by querying the auth tables directly.
"""

import logging
from datetime import datetime, timezone
from functools import wraps

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("prd_forge_auth")

# Actual Better Auth table/column names (verified by contract test)
AUTH_TABLES = {
    "user": "user",
    "session": "session",
    "account": "account",
    "organization": "organization",
    "member": "member",
    "invitation": "invitation",
    "verification": "verification",
}


async def get_session_user(request: Request, pool):
    """Extract user from session token in cookie or Authorization header.

    Returns dict with user info or None if not authenticated.
    """
    # Try cookie first (browser), then Authorization header (API)
    token = None
    cookie = request.cookies.get("better-auth.session_token")
    if cookie:
        # Cookie value may have .signature suffix
        token = cookie.split(".")[0] if "." in cookie else cookie
    else:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return None

    row = await pool.fetchrow(
        f"""
        SELECT s.id AS session_id, s."userId" AS user_id, s."expiresAt",
               u.name, u.email, u.image
        FROM "{AUTH_TABLES['session']}" s
        JOIN "{AUTH_TABLES['user']}" u ON u.id = s."userId"
        WHERE s.token = $1
        """,
        token,
    )

    if not row:
        return None

    # Check expiry
    expires = row["expiresAt"]
    if expires and expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return None

    return {
        "session_id": row["session_id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "email": row["email"],
        "image": row["image"],
    }


async def get_user_project_role(pool, user_id: str, project_slug: str) -> str | None:
    """Get user's role for a project.

    Checks project_members first, then falls back to org membership.
    Returns role string or None if no access.
    """
    # Direct project membership
    role = await pool.fetchval(
        """
        SELECT pm.role FROM project_members pm
        JOIN projects p ON p.id = pm.project_id
        WHERE pm.user_id = $1 AND p.slug = $2
        """,
        user_id,
        project_slug,
    )
    if role:
        return role

    # Org membership fallback: org owner/admin → project admin
    org_role = await pool.fetchval(
        f"""
        SELECT m.role FROM "{AUTH_TABLES['member']}" m
        JOIN "{AUTH_TABLES['organization']}" o ON o.id = m."organizationId"
        JOIN projects p ON p.organization_id = o.id::uuid
        WHERE m."userId" = $1 AND p.slug = $2
        """,
        user_id,
        project_slug,
    )
    if org_role in ("owner", "admin"):
        return "admin"
    if org_role == "member":
        return "editor"

    return None


# Role hierarchy for permission checks
ROLE_HIERARCHY = {
    "owner": 5,
    "admin": 4,
    "editor": 3,
    "commenter": 2,
    "viewer": 1,
}


def has_min_role(user_role: str, min_role: str) -> bool:
    """Check if user_role meets the minimum required role."""
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(min_role, 0)


async def require_authenticated_user(request: Request, pool):
    """Check user is authenticated. Returns user dict or JSONResponse error.

    Does NOT check project role — use for endpoints where the project doesn't exist yet.
    During migration / pre-setup: if auth not bootstrapped, returns a local-mode user.
    """
    from errors import unauthorized

    if not await _is_auth_enforced(pool):
        return {"user_id": None, "name": "local", "email": ""}

    user = await get_session_user(request, pool)
    if not user:
        return unauthorized()

    return user


async def _is_auth_enforced(pool) -> bool:
    """Return True if auth should be enforced (tables exist AND setup completed)."""
    auth_exists = await pool.fetchval("SELECT to_regclass('session')")
    if not auth_exists:
        return False
    bootstrap_table = await pool.fetchval("SELECT to_regclass('prdforge_bootstrap')")
    if bootstrap_table:
        has_bootstrap = await pool.fetchval("SELECT 1 FROM prdforge_bootstrap LIMIT 1")
        if not has_bootstrap:
            return False
    return True


async def require_project_access(request: Request, pool, slug: str, min_role: str = "viewer"):
    """Check user has required role for project. Returns (user, role) or JSONResponse error.

    During migration / pre-setup: allow all access (single-user mode).
    """
    from errors import unauthorized, permission_denied, not_found

    if not await _is_auth_enforced(pool):
        return {"user_id": None, "name": "local", "email": ""}, "owner"

    user = await get_session_user(request, pool)
    if not user:
        return unauthorized(), None

    role = await get_user_project_role(pool, user["user_id"], slug)
    if not role:
        return not_found("project", slug), None

    if not has_min_role(role, min_role):
        return permission_denied(f"Requires {min_role} role, you have {role}"), None

    return user, role
