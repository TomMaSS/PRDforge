"""PRD Forge MCP Server — 27 tools for sectional PRD management."""

import argparse
import json
import logging
import os
import re
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import asyncpg
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.settings import DEFAULT_PROJECT_SETTINGS, SETTINGS_SCHEMA, validate_settings

logger = logging.getLogger("prd_forge_mcp")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

# --- Constants ---
SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
MAX_SLUG = 100
VALID_STATUSES = {"draft", "in_progress", "review", "approved", "outdated"}
VALID_DEP_TYPES = {"references", "implements", "blocks", "extends"}
VALID_SECTION_TYPES = {
    "overview", "tech_spec", "data_model", "api_spec", "ui_design",
    "architecture", "deployment", "security", "testing", "timeline", "general",
}

# --- Pool ---
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            os.environ["DATABASE_URL"], min_size=2, max_size=10
        )
        logger.info("Connection pool created (min=2, max=10)")
    return _pool


@asynccontextmanager
async def lifespan(server):
    yield
    global _pool
    if _pool:
        await _pool.close()
        logger.info("Connection pool closed")
        _pool = None


mcp = FastMCP("prd_forge_mcp", lifespan=lifespan)


# --- Helpers ---
def validate_slug(slug: str) -> str | None:
    if not slug or len(slug) > MAX_SLUG or not SLUG_RE.match(slug):
        return f"invalid slug '{slug}': must be 1-{MAX_SLUG} chars, lowercase alphanumeric with hyphens"
    return None


def dt(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


def row_to_dict(row: asyncpg.Record) -> dict:
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            d[k] = str(v)
    return d


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def ok(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=_json_default)


def err(msg: str) -> str:
    return json.dumps({"error": msg})


async def resolve_project_id(pool, slug: str):
    return await pool.fetchval("SELECT id FROM projects WHERE slug = $1", slug)


async def resolve_section(pool, project_id, slug: str):
    return await pool.fetchrow(
        "SELECT * FROM sections WHERE project_id = $1 AND slug = $2",
        project_id, slug,
    )


async def resolve_comment_id(pool, project_slug, section_slug, comment_id_str):
    """Validate comment belongs to project/section. Returns (comment_uuid, section_uuid) or None."""
    cid = uuid.UUID(comment_id_str)
    row = await pool.fetchrow("""
        SELECT c.id, s.id AS section_id FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, project_slug, section_slug)
    return (row["id"], row["section_id"]) if row else None


async def get_project_settings(pool, project_id):
    row = await pool.fetchrow(
        "SELECT settings FROM project_settings WHERE project_id = $1", project_id
    )
    if row:
        raw = row["settings"]
        db_settings = json.loads(raw) if isinstance(raw, str) else dict(raw)
    else:
        db_settings = {}
    return {**DEFAULT_PROJECT_SETTINGS, **db_settings}


# --- Group 1: Project Management ---

@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_list_projects() -> str:
    """List all PRD projects with section counts. ~50 tokens."""
    try:
        pool = await get_pool()
        rows = await pool.fetch("""
            SELECT p.slug, p.name, p.description, p.version,
                   COUNT(s.id) AS section_count,
                   COALESCE(SUM(s.word_count), 0) AS total_words,
                   p.created_at, p.updated_at
            FROM projects p
            LEFT JOIN sections s ON s.project_id = p.id
            GROUP BY p.id ORDER BY p.created_at
        """)
        return ok([row_to_dict(r) for r in rows])
    except Exception as e:
        logger.error("prd_list_projects: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
)
async def prd_create_project(name: str, slug: str, description: str = "") -> str:
    """Create a new PRD project. Slug must be unique, lowercase alphanumeric with hyphens."""
    slug_err = validate_slug(slug)
    if slug_err:
        return err(slug_err)
    try:
        pool = await get_pool()
        row = await pool.fetchrow(
            "INSERT INTO projects (name, slug, description) VALUES ($1, $2, $3) RETURNING *",
            name, slug, description,
        )
        logger.info("Created project: %s", slug)
        return ok({"created": row_to_dict(row)})
    except asyncpg.UniqueViolationError:
        return err(f"project with slug '{slug}' already exists")
    except Exception as e:
        logger.error("prd_create_project: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}
)
async def prd_delete_project(project: str) -> str:
    """Delete a project and all its sections, revisions, and dependencies. Destructive."""
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")
        count = await pool.fetchval("SELECT COUNT(*) FROM sections WHERE project_id = $1", pid)
        await pool.execute("DELETE FROM projects WHERE id = $1", pid)
        logger.info("Deleted project: %s (%d sections)", project, count)
        return ok({"deleted": project, "sections_removed": count})
    except Exception as e:
        logger.error("prd_delete_project: %s", e)
        return err(str(e))


# --- Group 2: Section CRUD ---

@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_list_sections(project: str) -> str:
    """List all sections in a project (metadata only, no content). ~200 tokens for 12 sections."""
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")
        rows = await pool.fetch("""
            SELECT slug, title, section_type, sort_order, status, summary, tags, notes,
                   word_count, parent_slug, parent_title, revision_count,
                   dep_out_count, dep_in_count, updated_at
            FROM section_tree WHERE project_id = $1 ORDER BY sort_order
        """, pid)
        return ok([row_to_dict(r) for r in rows])
    except Exception as e:
        logger.error("prd_list_sections: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_read_section(project: str, section: str) -> str:
    """
    Read ONE section's full content plus dependency context summaries.
    ~500-3000 tokens depending on section size. Call this before editing.
    """
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        sec = await pool.fetchrow("""
            SELECT s.slug, s.title, s.content, s.summary, s.status, s.section_type,
                   s.tags, s.notes, s.word_count, s.sort_order, s.updated_at,
                   COALESCE(rc.cnt, 0) AS revision_count
            FROM sections s
            LEFT JOIN (SELECT section_id, COUNT(*) AS cnt FROM section_revisions GROUP BY section_id) rc
                ON rc.section_id = s.id
            WHERE s.project_id = $1 AND s.slug = $2
        """, pid, section)
        if not sec:
            return err(f"section '{section}' not found in project '{project}'")

        sec_id = await pool.fetchval(
            "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", pid, section
        )

        depends_on = await pool.fetch("""
            SELECT s.slug, s.title, s.summary, s.status, s.tags,
                   d.dependency_type AS dep_type, d.description AS dep_reason
            FROM section_dependencies d
            JOIN sections s ON s.id = d.depends_on_id
            WHERE d.section_id = $1
        """, sec_id)

        depended_by = await pool.fetch("""
            SELECT s.slug, s.title, s.summary, s.status, s.tags,
                   d.dependency_type AS dep_type, d.description AS dep_reason
            FROM section_dependencies d
            JOIN sections s ON s.id = d.section_id
            WHERE d.depends_on_id = $1
        """, sec_id)

        comments = await pool.fetch("""
            SELECT id, anchor_text, anchor_prefix, anchor_suffix, body, resolved, created_at
            FROM section_comments WHERE section_id = $1
            ORDER BY created_at
        """, sec_id)

        # Batch-fetch replies for all comments
        comment_ids = [c["id"] for c in comments]
        replies = await pool.fetch(
            "SELECT id, comment_id, author, body, created_at "
            "FROM comment_replies WHERE comment_id = ANY($1) ORDER BY created_at",
            comment_ids,
        ) if comment_ids else []

        # Group replies by comment_id
        replies_by_comment = {}
        for r in replies:
            cid = str(r["comment_id"])
            replies_by_comment.setdefault(cid, []).append(row_to_dict(r))

        comment_dicts = []
        for c in comments:
            cd = row_to_dict(c)
            cd["replies"] = replies_by_comment.get(str(c["id"]), [])
            comment_dicts.append(cd)

        return ok({
            "section": row_to_dict(sec),
            "depends_on": [row_to_dict(r) for r in depends_on],
            "depended_by": [row_to_dict(r) for r in depended_by],
            "comments": comment_dicts,
        })
    except Exception as e:
        logger.error("prd_read_section: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
)
async def prd_create_section(
    project: str, slug: str, title: str,
    section_type: str = "general", parent_section: str | None = None,
    sort_order: int = 0, content: str = "", summary: str = "",
    tags: list[str] | None = None, notes: str = "",
) -> str:
    """Create a new section in a project."""
    slug_err = validate_slug(slug)
    if slug_err:
        return err(slug_err)
    if section_type not in VALID_SECTION_TYPES:
        return err(f"invalid section_type '{section_type}', must be one of {sorted(VALID_SECTION_TYPES)}")
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        parent_id = None
        if parent_section:
            parent_id = await pool.fetchval(
                "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", pid, parent_section
            )
            if not parent_id:
                return err(f"parent section '{parent_section}' not found")

        row = await pool.fetchrow("""
            INSERT INTO sections (project_id, parent_section_id, slug, title, section_type,
                                  sort_order, content, summary, tags, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING slug, title, section_type, status, sort_order, tags, word_count, created_at
        """, pid, parent_id, slug, title, section_type, sort_order, content, summary,
            tags or [], notes)
        logger.info("Created section: %s/%s", project, slug)
        return ok({"created": row_to_dict(row)})
    except asyncpg.UniqueViolationError:
        return err(f"section '{slug}' already exists in project '{project}'")
    except Exception as e:
        logger.error("prd_create_section: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
)
async def prd_update_section(
    project: str, section: str,
    content: str | None = None, summary: str | None = None,
    title: str | None = None, status: str | None = None,
    tags: list[str] | None = None, notes: str | None = None,
    change_description: str = "",
    resolve_comments: list[str] | None = None,
) -> str:
    """
    Update a section. Only provided fields are changed. If content is provided,
    current content is saved as a revision BEFORE update (atomic).
    Pass resolve_comments (list of comment IDs) to atomically resolve comments in the same transaction.
    """
    if status and status not in VALID_STATUSES:
        return err(f"invalid status '{status}', must be one of {sorted(VALID_STATUSES)}")

    fields = {}
    if content is not None:
        fields["content"] = content
    if summary is not None:
        fields["summary"] = summary
    if title is not None:
        fields["title"] = title
    if status is not None:
        fields["status"] = status
    if tags is not None:
        fields["tags"] = tags
    if notes is not None:
        fields["notes"] = notes

    if not fields:
        return err("nothing to update — no fields provided")

    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT id, content, summary FROM sections "
                    "WHERE project_id = $1 AND slug = $2 FOR UPDATE",
                    pid, section,
                )
                if not row:
                    return err(f"section '{section}' not found in project '{project}'")

                revision_created = None
                if content is not None:
                    max_rev = await conn.fetchval(
                        "SELECT COALESCE(MAX(revision_number), 0) FROM section_revisions WHERE section_id = $1",
                        row["id"],
                    )
                    rev_num = max_rev + 1
                    await conn.execute(
                        "INSERT INTO section_revisions (section_id, revision_number, content, summary, change_description) "
                        "VALUES ($1, $2, $3, $4, $5)",
                        row["id"], rev_num, row["content"], row["summary"],
                        change_description or f"Before update (rev {rev_num})",
                    )
                    revision_created = rev_num

                # Build dynamic UPDATE
                sets = []
                vals = []
                for i, (col, val) in enumerate(fields.items(), start=1):
                    sets.append(f"{col} = ${i}")
                    vals.append(val)
                vals.append(row["id"])
                sql = f"UPDATE sections SET {', '.join(sets)} WHERE id = ${len(vals)} RETURNING slug, title, status, tags, word_count, updated_at"
                updated = await conn.fetchrow(sql, *vals)

                # Auto-resolve comments if requested
                resolved_ids = []
                if resolve_comments:
                    valid_cids = []
                    for cid_str in resolve_comments:
                        try:
                            valid_cids.append(uuid.UUID(cid_str))
                        except ValueError:
                            continue

                    if valid_cids:
                        settings = await get_project_settings(conn, pid)

                        # Auto-reply if setting enabled
                        if settings.get("claude_comment_replies"):
                            await conn.execute("""
                                INSERT INTO comment_replies (comment_id, author, body)
                                SELECT c.id, 'claude', $1
                                FROM section_comments c
                                WHERE c.id = ANY($2) AND c.section_id = $3 AND c.resolved = false
                            """, change_description or "Addressed in this update", valid_cids, row["id"])

                        # Batch resolve
                        resolved_rows = await conn.fetch("""
                            UPDATE section_comments SET resolved = true
                            WHERE id = ANY($1) AND section_id = $2 AND resolved = false
                            RETURNING id
                        """, valid_cids, row["id"])
                        resolved_ids = [str(r["id"]) for r in resolved_rows]

        result = {"updated": row_to_dict(updated)}
        if revision_created is not None:
            result["revision_created"] = revision_created
        if resolved_ids:
            result["resolved_comments"] = resolved_ids
        logger.info("Updated section: %s/%s", project, section)
        return ok(result)
    except Exception as e:
        logger.error("prd_update_section: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}
)
async def prd_delete_section(project: str, section: str) -> str:
    """Delete a section. Warns if other sections depend on it."""
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        sec = await pool.fetchrow(
            "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", pid, section
        )
        if not sec:
            return err(f"section '{section}' not found in project '{project}'")

        depended_by = await pool.fetch(
            "SELECT s.slug FROM section_dependencies d JOIN sections s ON s.id = d.section_id WHERE d.depends_on_id = $1",
            sec["id"],
        )
        affected = [r["slug"] for r in depended_by]

        await pool.execute("DELETE FROM sections WHERE id = $1", sec["id"])
        result = {"deleted": section}
        if affected:
            result["warning"] = f"{len(affected)} sections lost a dependency"
            result["affected_sections"] = affected
        logger.info("Deleted section: %s/%s", project, section)
        return ok(result)
    except Exception as e:
        logger.error("prd_delete_section: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
)
async def prd_move_section(
    project: str, section: str,
    sort_order: int | None = None, parent_section: str | None = None,
) -> str:
    """Move a section (change sort_order and/or parent). parent_section="" moves to root."""
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        sec = await pool.fetchrow(
            "SELECT id, slug, title, sort_order FROM sections WHERE project_id = $1 AND slug = $2",
            pid, section,
        )
        if not sec:
            return err(f"section '{section}' not found in project '{project}'")

        updates = {}
        if sort_order is not None:
            updates["sort_order"] = sort_order

        if parent_section is not None:
            if parent_section == "":
                updates["parent_section_id"] = None
            else:
                if parent_section == section:
                    return err("section cannot be its own parent")
                parent_id = await pool.fetchval(
                    "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", pid, parent_section
                )
                if not parent_id:
                    return err(f"parent section '{parent_section}' not found")
                updates["parent_section_id"] = parent_id

        if not updates:
            return err("nothing to update — no sort_order or parent_section provided")

        sets = []
        vals = []
        for i, (col, val) in enumerate(updates.items(), start=1):
            sets.append(f"{col} = ${i}")
            vals.append(val)
        vals.append(sec["id"])
        await pool.execute(
            f"UPDATE sections SET {', '.join(sets)} WHERE id = ${len(vals)}", *vals
        )

        new_order = sort_order if sort_order is not None else sec["sort_order"]
        return ok({"moved": {"slug": section, "title": sec["title"], "sort_order": new_order}})
    except Exception as e:
        logger.error("prd_move_section: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
)
async def prd_duplicate_section(
    project: str, section: str, new_slug: str, new_title: str | None = None,
) -> str:
    """Duplicate a section with a new slug. Does NOT copy dependencies."""
    slug_err = validate_slug(new_slug)
    if slug_err:
        return err(slug_err)
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        src = await pool.fetchrow(
            "SELECT * FROM sections WHERE project_id = $1 AND slug = $2", pid, section
        )
        if not src:
            return err(f"section '{section}' not found in project '{project}'")

        title = new_title or f"{src['title']} (copy)"
        row = await pool.fetchrow("""
            INSERT INTO sections (project_id, slug, title, section_type, sort_order,
                                  status, content, summary, tags, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING slug, title, word_count, created_at
        """, pid, new_slug, title, src["section_type"], src["sort_order"] + 1,
            src["status"], src["content"], src["summary"], src["tags"], src["notes"])

        logger.info("Duplicated section: %s/%s → %s", project, section, new_slug)
        return ok({"duplicated": row_to_dict(row), "from": section})
    except asyncpg.UniqueViolationError:
        return err(f"section '{new_slug}' already exists in project '{project}'")
    except Exception as e:
        logger.error("prd_duplicate_section: %s", e)
        return err(str(e))


# --- Group 3: Dependencies ---

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_add_dependency(
    project: str, section: str, depends_on: str,
    dependency_type: str = "references", description: str = "",
) -> str:
    """
    Add a dependency between sections. Idempotent (upserts on conflict).
    Both sections must be in the same project.
    """
    if dependency_type not in VALID_DEP_TYPES:
        return err(f"invalid dependency_type '{dependency_type}', must be one of {sorted(VALID_DEP_TYPES)}")
    if section == depends_on:
        return err("a section cannot depend on itself")
    try:
        pool = await get_pool()
        row = await pool.fetchrow("""
            INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
            SELECT s1.project_id, s1.id, s2.id, $3, $4
            FROM sections s1
            JOIN sections s2 ON s2.project_id = s1.project_id AND s2.slug = $2
            JOIN projects p ON p.id = s1.project_id AND p.slug = $5
            WHERE s1.slug = $1
            ON CONFLICT (section_id, depends_on_id)
            DO UPDATE SET dependency_type = EXCLUDED.dependency_type, description = EXCLUDED.description
            RETURNING section_id, depends_on_id
        """, section, depends_on, dependency_type, description, project)
        if not row:
            return err(f"sections '{section}' and/or '{depends_on}' not found in project '{project}'")
        logger.info("Added dependency: %s/%s → %s", project, section, depends_on)
        return ok({"dependency": {"from": section, "to": depends_on, "type": dependency_type}})
    except Exception as e:
        logger.error("prd_add_dependency: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}
)
async def prd_remove_dependency(project: str, section: str, depends_on: str) -> str:
    """Remove a dependency between two sections."""
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        result = await pool.execute("""
            DELETE FROM section_dependencies
            WHERE section_id = (SELECT id FROM sections WHERE project_id = $1 AND slug = $2)
              AND depends_on_id = (SELECT id FROM sections WHERE project_id = $1 AND slug = $3)
        """, pid, section, depends_on)
        removed = result.split()[-1] != "0"
        return ok({"removed": removed, "from": section, "to": depends_on})
    except Exception as e:
        logger.error("prd_remove_dependency: %s", e)
        return err(str(e))


# --- Group 3b: Inline Comments ---

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
)
async def prd_add_comment(
    project: str, section: str, anchor_text: str, body: str,
    anchor_prefix: str = "", anchor_suffix: str = "",
) -> str:
    """Add an inline comment anchored to selected text in a section. Like Google Docs comments."""
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")
        sec = await pool.fetchrow(
            "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", pid, section
        )
        if not sec:
            return err(f"section '{section}' not found in project '{project}'")
        row = await pool.fetchrow("""
            INSERT INTO section_comments (section_id, anchor_text, anchor_prefix, anchor_suffix, body)
            VALUES ($1, $2, $3, $4, $5) RETURNING *
        """, sec["id"], anchor_text, anchor_prefix, anchor_suffix, body)
        logger.info("Added comment on %s/%s: %.40s", project, section, anchor_text)
        return ok({"created": row_to_dict(row)})
    except Exception as e:
        logger.error("prd_add_comment: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_resolve_comment(project: str, section: str, comment_id: str, reopen: bool = False) -> str:
    """Resolve (or reopen) an inline comment. Use after implementing the requested change."""
    try:
        pool = await get_pool()
        resolved = await resolve_comment_id(pool, project, section, comment_id)
        if not resolved:
            return err(f"comment '{comment_id}' not found in {project}/{section}")
        cid, _ = resolved
        await pool.execute(
            "UPDATE section_comments SET resolved = $1 WHERE id = $2",
            not reopen, cid,
        )
        action = "reopened" if reopen else "resolved"
        logger.info("%s comment %s on %s/%s", action, comment_id, project, section)
        return ok({"comment_id": comment_id, "action": action})
    except Exception as e:
        logger.error("prd_resolve_comment: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}
)
async def prd_delete_comment(project: str, section: str, comment_id: str) -> str:
    """Delete an inline comment."""
    try:
        pool = await get_pool()
        resolved = await resolve_comment_id(pool, project, section, comment_id)
        if not resolved:
            return err(f"comment '{comment_id}' not found in {project}/{section}")
        cid, _ = resolved
        await pool.execute("DELETE FROM section_comments WHERE id = $1", cid)
        logger.info("Deleted comment %s on %s/%s", comment_id, project, section)
        return ok({"deleted": comment_id})
    except Exception as e:
        logger.error("prd_delete_comment: %s", e)
        return err(str(e))


# --- Group 3c: Comment Replies ---

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
)
async def prd_add_comment_reply(
    project: str, section: str, comment_id: str, body: str, author: str = "claude",
) -> str:
    """Add a reply to an inline comment. Author must be 'user' or 'claude'."""
    if author not in ("user", "claude"):
        return err(f"author must be 'user' or 'claude', got '{author}'")
    try:
        pool = await get_pool()
        resolved = await resolve_comment_id(pool, project, section, comment_id)
        if not resolved:
            return err(f"comment '{comment_id}' not found in {project}/{section}")
        cid, _ = resolved
        row = await pool.fetchrow(
            "INSERT INTO comment_replies (comment_id, author, body) "
            "VALUES ($1, $2, $3) RETURNING *",
            cid, author, body,
        )
        logger.info("Added reply to comment %s on %s/%s", comment_id, project, section)
        return ok({"created": row_to_dict(row)})
    except Exception as e:
        logger.error("prd_add_comment_reply: %s", e)
        return err(str(e))


# --- Group 8: Project Settings ---

@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_get_settings(project: str) -> str:
    """Get project settings (merged defaults + overrides)."""
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")
        settings = await get_project_settings(pool, pid)
        return ok({"project": project, "settings": settings})
    except Exception as e:
        logger.error("prd_get_settings: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_update_settings(project: str, settings: dict) -> str:
    """Update project settings. Only known keys with correct types are accepted."""
    clean, errors = validate_settings(settings)
    if errors:
        return err(f"invalid settings: {'; '.join(errors)}")
    if not clean:
        return err("no valid settings provided")
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")
        import json as _json
        await pool.execute("""
            INSERT INTO project_settings (project_id, settings)
            VALUES ($1, $2::jsonb)
            ON CONFLICT (project_id)
            DO UPDATE SET settings = project_settings.settings || $2::jsonb
        """, pid, _json.dumps(clean))
        updated = await get_project_settings(pool, pid)
        logger.info("Updated settings for %s: %s", project, clean)
        return ok({"project": project, "settings": updated})
    except Exception as e:
        logger.error("prd_update_settings: %s", e)
        return err(str(e))


# --- Group 4: Context & Search ---

@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_get_overview(project: str) -> str:
    """
    Get project overview with all section summaries (no full content).
    ~400 tokens for 12 sections. Start here in a new conversation.
    """
    try:
        pool = await get_pool()
        proj = await pool.fetchrow("SELECT * FROM projects WHERE slug = $1", project)
        if not proj:
            return err(f"project '{project}' not found")

        sections = await pool.fetch("""
            SELECT slug, title, section_type, status, summary, tags, word_count,
                   parent_slug, updated_at
            FROM section_tree WHERE project_id = $1 ORDER BY sort_order
        """, proj["id"])

        deps = await pool.fetch("""
            SELECT s1.slug AS from_slug, s2.slug AS to_slug, d.dependency_type
            FROM section_dependencies d
            JOIN sections s1 ON s1.id = d.section_id
            JOIN sections s2 ON s2.id = d.depends_on_id
            WHERE d.project_id = $1
        """, proj["id"])

        status_counts = {}
        for s in sections:
            st = s["status"]
            status_counts[st] = status_counts.get(st, 0) + 1

        return ok({
            "project": {
                "slug": proj["slug"], "name": proj["name"],
                "description": proj["description"], "version": proj["version"],
                "created_at": dt(proj["created_at"]),
            },
            "stats": {
                "sections": len(sections),
                "words": sum(s["word_count"] for s in sections),
                "by_status": status_counts,
            },
            "sections": [row_to_dict(r) for r in sections],
            "dependencies": [row_to_dict(r) for r in deps],
        })
    except Exception as e:
        logger.error("prd_get_overview: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_search(project: str, query: str) -> str:
    """
    Search sections. Prefix 'tag:' for tag filter, otherwise full-text search.
    ~200 tokens.
    """
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        if query.startswith("tag:"):
            tag = query[4:].strip()
            rows = await pool.fetch("""
                SELECT slug, title, status, tags, summary
                FROM sections WHERE project_id = $1 AND $2 = ANY(tags)
                ORDER BY sort_order
            """, pid, tag)
            return ok({"tag": tag, "results": [row_to_dict(r) for r in rows]})
        else:
            rows = await pool.fetch("""
                SELECT slug, title, section_type, status, tags,
                       ts_rank(to_tsvector('english',
                           coalesce(title,'') || ' ' || coalesce(content,'') || ' ' || coalesce(notes,'')),
                           plainto_tsquery('english', $2)) AS rank,
                       LEFT(content, 200) AS snippet
                FROM sections
                WHERE project_id = $1
                  AND to_tsvector('english',
                      coalesce(title,'') || ' ' || coalesce(content,'') || ' ' || coalesce(notes,''))
                      @@ plainto_tsquery('english', $2)
                ORDER BY rank DESC
            """, pid, query)
            return ok({"query": query, "results": [row_to_dict(r) for r in rows]})
    except Exception as e:
        logger.error("prd_search: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_get_changelog(project: str, limit: int = 20) -> str:
    """Get recent revision history across all sections. ~300 tokens."""
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        rows = await pool.fetch("""
            SELECT section_slug, section_title, revision_number,
                   change_description, created_at
            FROM project_changelog WHERE project_slug = $1
            ORDER BY created_at DESC LIMIT $2
        """, project, limit)

        total = await pool.fetchval("""
            SELECT COUNT(*) FROM project_changelog WHERE project_slug = $1
        """, project)

        return ok({"changelog": [row_to_dict(r) for r in rows], "total": total})
    except Exception as e:
        logger.error("prd_get_changelog: %s", e)
        return err(str(e))


# --- Group 5: Revisions ---

@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_get_revisions(project: str, section: str) -> str:
    """List revision metadata for a section (no content). ~100 tokens."""
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        sec_id = await pool.fetchval(
            "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", pid, section
        )
        if not sec_id:
            return err(f"section '{section}' not found in project '{project}'")

        rows = await pool.fetch("""
            SELECT revision_number, change_description,
                   LENGTH(content) AS content_length, created_at
            FROM section_revisions WHERE section_id = $1
            ORDER BY revision_number
        """, sec_id)
        return ok({"section": section, "revisions": [row_to_dict(r) for r in rows]})
    except Exception as e:
        logger.error("prd_get_revisions: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_read_revision(project: str, section: str, revision: int) -> str:
    """Read a specific revision's content. ~500-3000 tokens."""
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        sec_id = await pool.fetchval(
            "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", pid, section
        )
        if not sec_id:
            return err(f"section '{section}' not found in project '{project}'")

        row = await pool.fetchrow("""
            SELECT revision_number, content, summary, change_description, created_at
            FROM section_revisions WHERE section_id = $1 AND revision_number = $2
        """, sec_id, revision)
        if not row:
            return err(f"revision {revision} not found for section '{section}'")
        return ok(row_to_dict(row))
    except Exception as e:
        logger.error("prd_read_revision: %s", e)
        return err(str(e))


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
)
async def prd_rollback_section(project: str, section: str, revision: int) -> str:
    """
    Rollback section to a previous revision. Current content is saved as a
    new revision before rollback (atomic, no content loss).
    """
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        async with pool.acquire() as conn:
            async with conn.transaction():
                sec = await conn.fetchrow(
                    "SELECT id, content, summary FROM sections "
                    "WHERE project_id = $1 AND slug = $2 FOR UPDATE",
                    pid, section,
                )
                if not sec:
                    return err(f"section '{section}' not found in project '{project}'")

                rev = await conn.fetchrow(
                    "SELECT content, summary FROM section_revisions "
                    "WHERE section_id = $1 AND revision_number = $2",
                    sec["id"], revision,
                )
                if not rev:
                    return err(f"revision {revision} not found for section '{section}'")

                max_rev = await conn.fetchval(
                    "SELECT COALESCE(MAX(revision_number), 0) FROM section_revisions WHERE section_id = $1",
                    sec["id"],
                )
                backup_rev = max_rev + 1
                await conn.execute(
                    "INSERT INTO section_revisions (section_id, revision_number, content, summary, change_description) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    sec["id"], backup_rev, sec["content"], sec["summary"],
                    f"Saved before rollback to revision {revision}",
                )

                await conn.execute(
                    "UPDATE sections SET content = $1, summary = $2 WHERE id = $3",
                    rev["content"], rev["summary"], sec["id"],
                )

        logger.info("Rolled back %s/%s to revision %d (backup: %d)", project, section, revision, backup_rev)
        return ok({"rolled_back_to": revision, "backup_revision": backup_rev, "section": section})
    except Exception as e:
        logger.error("prd_rollback_section: %s", e)
        return err(str(e))


# --- Group 6: Export / Import ---

@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_export_markdown(project: str) -> str:
    """
    Export entire project as a single markdown document.
    WARNING: Returns full document — can be 15K+ tokens. Use only when needed.
    """
    try:
        pool = await get_pool()
        proj = await pool.fetchrow("SELECT * FROM projects WHERE slug = $1", project)
        if not proj:
            return err(f"project '{project}' not found")

        sections = await pool.fetch("""
            SELECT title, section_type, status, content
            FROM sections WHERE project_id = $1 ORDER BY sort_order
        """, proj["id"])

        lines = [f"# {proj['name']}\n"]
        for s in sections:
            lines.append(f"## {s['title']}")
            lines.append(f"*{s['section_type']} | {s['status']}*\n")
            lines.append(s["content"])
            lines.append("\n---\n")

        return "\n".join(lines)
    except Exception as e:
        logger.error("prd_export_markdown: %s", e)
        return err(str(e))


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80]
    return slug or "untitled"


def _auto_summary(content: str) -> str:
    text = content.strip()[:150]
    dot = text.rfind(".")
    if dot > 20:
        return text[: dot + 1]
    return text


def _parse_markdown_sections(markdown: str) -> list[dict]:
    sections = []
    current = None
    in_fence = False
    for line in markdown.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## ") and not line.startswith("### "):
            if current:
                current["content"] = "\n".join(current["lines"]).strip()
                sections.append(current)
            title = line[3:].strip()
            current = {"title": title, "slug": _slugify(title), "lines": []}
        elif current is not None:
            current["lines"].append(line)
    if current:
        current["content"] = "\n".join(current["lines"]).strip()
        sections.append(current)
    return sections


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
)
async def prd_import_markdown(
    project: str, markdown: str, replace_existing: bool = False,
) -> str:
    """
    Import markdown document into a project. Splits on ## headings.
    replace_existing=true overwrites matching slugs (saves revision first).
    """
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        parsed = _parse_markdown_sections(markdown)
        if not parsed:
            return err("no sections found — expected ## headings")

        results = []
        for i, sec in enumerate(parsed):
            slug = sec["slug"]
            content = sec["content"]
            summary = _auto_summary(content)

            existing = await pool.fetchrow(
                "SELECT id, content, summary FROM sections WHERE project_id = $1 AND slug = $2",
                pid, slug,
            )

            if existing:
                if replace_existing:
                    async with pool.acquire() as conn:
                        async with conn.transaction():
                            row = await conn.fetchrow(
                                "SELECT id, content, summary FROM sections "
                                "WHERE project_id = $1 AND slug = $2 FOR UPDATE",
                                pid, slug,
                            )
                            max_rev = await conn.fetchval(
                                "SELECT COALESCE(MAX(revision_number), 0) FROM section_revisions WHERE section_id = $1",
                                row["id"],
                            )
                            await conn.execute(
                                "INSERT INTO section_revisions (section_id, revision_number, content, summary, change_description) "
                                "VALUES ($1, $2, $3, $4, $5)",
                                row["id"], max_rev + 1, row["content"], row["summary"], "Before markdown import",
                            )
                            await conn.execute(
                                "UPDATE sections SET content = $1, summary = $2 WHERE id = $3",
                                content, summary, row["id"],
                            )
                    wc = len(content.split())
                    results.append({"slug": slug, "action": "updated", "words": wc})
                else:
                    results.append({"slug": slug, "action": "skipped (exists)", "words": 0})
            else:
                await pool.execute("""
                    INSERT INTO sections (project_id, slug, title, sort_order, content, summary)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, pid, slug, sec["title"], i, content, summary)
                wc = len(content.split())
                results.append({"slug": slug, "action": "created", "words": wc})

        imported = sum(1 for r in results if r["action"] != "skipped (exists)")
        logger.info("Imported %d sections into %s", imported, project)
        return ok({"imported": imported, "sections": results})
    except Exception as e:
        logger.error("prd_import_markdown: %s", e)
        return err(str(e))


# --- Group 7: Batch ---

@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def prd_bulk_status(
    project: str, sections: list[str], status: str, change_description: str = "",
) -> str:
    """Bulk update status for multiple sections."""
    if status not in VALID_STATUSES:
        return err(f"invalid status '{status}', must be one of {sorted(VALID_STATUSES)}")
    try:
        pool = await get_pool()
        pid = await resolve_project_id(pool, project)
        if not pid:
            return err(f"project '{project}' not found")

        updated = []
        not_found = []
        for slug in sections:
            result = await pool.execute(
                "UPDATE sections SET status = $1 WHERE project_id = $2 AND slug = $3",
                status, pid, slug,
            )
            if result.split()[-1] == "0":
                not_found.append(slug)
            else:
                updated.append(slug)

        return ok({"status": status, "updated": updated, "not_found": not_found})
    except Exception as e:
        logger.error("prd_bulk_status: %s", e)
        return err(str(e))


# --- Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PRD Forge MCP Server")
    parser.add_argument("--http", type=int, help="Run HTTP transport on this port")
    args = parser.parse_args()

    if args.http:
        logger.info("Starting HTTP transport on port %d", args.http)
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = args.http
        mcp.run(transport="streamable-http")
    else:
        logger.info("Starting stdio transport")
        mcp.run()
