"""PRD Forge Web UI — FastAPI application."""

import os
import sys
import uuid as _uuid
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.settings import DEFAULT_PROJECT_SETTINGS, validate_settings

pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])
    yield
    if pool:
        await pool.close()


app = FastAPI(title="PRD Forge UI", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


def dt(v):
    if v is None:
        return None
    return v.isoformat() if hasattr(v, "isoformat") else str(v)


def row_dict(r):
    d = dict(r)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


_static_dir = os.path.join(os.path.dirname(__file__), "static")
with open(os.path.join(_static_dir, "index.html")) as _f:
    HTML = _f.read()




@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.get("/api/projects")
async def list_projects():
    rows = await pool.fetch("""
        SELECT p.slug, p.name, p.description, p.version,
               COUNT(s.id) AS section_count,
               COALESCE(SUM(s.word_count), 0) AS total_words
        FROM projects p
        LEFT JOIN sections s ON s.project_id = p.id
        GROUP BY p.id ORDER BY p.created_at
    """)
    return [row_dict(r) for r in rows]


@app.get("/api/projects/{slug}")
async def get_project(slug: str):
    proj = await pool.fetchrow("SELECT * FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)

    sections = await pool.fetch("""
        SELECT slug, title, section_type, sort_order, status, summary, tags,
               word_count, parent_slug, revision_count, updated_at
        FROM section_tree WHERE project_id = $1 ORDER BY sort_order
    """, proj["id"])

    deps = await pool.fetch("""
        SELECT s1.slug AS from_slug, s1.title AS from_title,
               s2.slug AS to_slug, s2.title AS to_title,
               d.dependency_type
        FROM section_dependencies d
        JOIN sections s1 ON s1.id = d.section_id
        JOIN sections s2 ON s2.id = d.depends_on_id
        WHERE d.project_id = $1
    """, proj["id"])

    changelog = await pool.fetch("""
        SELECT section_slug, section_title, revision_number,
               change_description, created_at
        FROM project_changelog WHERE project_slug = $1
        ORDER BY created_at DESC LIMIT 20
    """, slug)

    status_counts = {}
    total_words = 0
    for s in sections:
        st = s["status"]
        status_counts[st] = status_counts.get(st, 0) + 1
        total_words += s["word_count"]

    return {
        "project": {"slug": proj["slug"], "name": proj["name"], "description": proj["description"],
                     "version": proj["version"], "created_at": dt(proj["created_at"])},
        "stats": {"sections": len(sections), "words": total_words, "by_status": status_counts},
        "sections": [row_dict(r) for r in sections],
        "dependencies": [row_dict(r) for r in deps],
        "changelog": [row_dict(r) for r in changelog],
    }


@app.get("/api/projects/{slug}/sections/{section}")
async def get_section(slug: str, section: str):
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)

    sec = await pool.fetchrow("""
        SELECT s.slug, s.title, s.content, s.summary, s.status, s.section_type,
               s.tags, s.notes, s.word_count, s.updated_at
        FROM sections s WHERE s.project_id = $1 AND s.slug = $2
    """, proj["id"], section)
    if not sec:
        return JSONResponse({"error": f"section '{section}' not found"}, 404)

    sec_id = await pool.fetchval(
        "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", proj["id"], section
    )

    depends_on = await pool.fetch("""
        SELECT s.slug, s.title, s.summary, s.status,
               d.dependency_type AS dep_type, d.description AS dep_reason
        FROM section_dependencies d
        JOIN sections s ON s.id = d.depends_on_id
        WHERE d.section_id = $1
    """, sec_id)

    depended_by = await pool.fetch("""
        SELECT s.slug, s.title, s.summary, s.status,
               d.dependency_type AS dep_type, d.description AS dep_reason
        FROM section_dependencies d
        JOIN sections s ON s.id = d.section_id
        WHERE d.depends_on_id = $1
    """, sec_id)

    revisions = await pool.fetch("""
        SELECT revision_number, change_description, created_at
        FROM section_revisions WHERE section_id = $1
        ORDER BY revision_number DESC
    """, sec_id)

    comments = await pool.fetch("""
        SELECT id, anchor_text, anchor_prefix, anchor_suffix, body, resolved, created_at
        FROM section_comments WHERE section_id = $1
        ORDER BY created_at
    """, sec_id)

    # Batch-fetch replies
    comment_ids = [c["id"] for c in comments]
    replies = await pool.fetch(
        "SELECT id, comment_id, author, body, created_at "
        "FROM comment_replies WHERE comment_id = ANY($1) ORDER BY created_at",
        comment_ids,
    ) if comment_ids else []

    replies_by_comment = {}
    for r in replies:
        cid = str(r["comment_id"])
        replies_by_comment.setdefault(cid, []).append(row_dict(r))

    comment_dicts = []
    for c in comments:
        cd = row_dict(c)
        cd["replies"] = replies_by_comment.get(str(c["id"]), [])
        comment_dicts.append(cd)

    return {
        "section": row_dict(sec),
        "depends_on": [row_dict(r) for r in depends_on],
        "depended_by": [row_dict(r) for r in depended_by],
        "revisions": [row_dict(r) for r in revisions],
        "comments": comment_dicts,
    }


@app.post("/api/projects/{slug}/sections/{section}/notes")
async def update_notes(slug: str, section: str, request: Request):
    body = await request.json()
    notes = body.get("notes", "")
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    result = await pool.execute(
        "UPDATE sections SET notes = $1 WHERE project_id = $2 AND slug = $3",
        notes, proj["id"], section,
    )
    if result.split()[-1] == "0":
        return JSONResponse({"error": f"section '{section}' not found"}, 404)
    return {"ok": True, "notes": notes}


@app.post("/api/projects/{slug}/sections/{section}/comments")
async def create_comment(slug: str, section: str, request: Request):
    body = await request.json()
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    sec_id = await pool.fetchval(
        "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", proj["id"], section
    )
    if not sec_id:
        return JSONResponse({"error": f"section '{section}' not found"}, 404)
    row = await pool.fetchrow("""
        INSERT INTO section_comments (section_id, anchor_text, anchor_prefix, anchor_suffix, body)
        VALUES ($1, $2, $3, $4, $5) RETURNING *
    """, sec_id, body["anchor_text"], body.get("anchor_prefix", ""),
        body.get("anchor_suffix", ""), body["body"])
    return row_dict(row)


@app.post("/api/projects/{slug}/sections/{section}/comments/{comment_id}/resolve")
async def resolve_comment(slug: str, section: str, comment_id: str):
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id, c.resolved FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    await pool.execute("UPDATE section_comments SET resolved = $1 WHERE id = $2", not row["resolved"], row["id"])
    return {"ok": True, "resolved": not row["resolved"]}


@app.patch("/api/projects/{slug}/sections/{section}/comments/{comment_id}")
async def update_comment(slug: str, section: str, comment_id: str, request: Request):
    body = await request.json()
    new_body = body.get("body", "").strip()
    if not new_body:
        return JSONResponse({"error": "body required"}, 400)
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    await pool.execute("UPDATE section_comments SET body = $1 WHERE id = $2", new_body, row["id"])
    return {"ok": True}


@app.delete("/api/projects/{slug}/sections/{section}/comments/{comment_id}")
async def delete_comment(slug: str, section: str, comment_id: str):
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    await pool.execute("DELETE FROM section_comments WHERE id = $1", row["id"])
    return {"ok": True}


@app.post("/api/projects/{slug}/sections/{section}/comments/{comment_id}/replies")
async def add_comment_reply(slug: str, section: str, comment_id: str, request: Request):
    body = await request.json()
    reply_body = body.get("body", "").strip()
    if not reply_body:
        return JSONResponse({"error": "body required"}, 400)
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    reply = await pool.fetchrow(
        "INSERT INTO comment_replies (comment_id, author, body) VALUES ($1, 'user', $2) RETURNING *",
        row["id"], reply_body,
    )
    return row_dict(reply)


@app.get("/api/projects/{slug}/settings")
async def get_settings(slug: str):
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    row = await pool.fetchrow(
        "SELECT settings FROM project_settings WHERE project_id = $1", proj["id"]
    )
    if row:
        import json as _json2
        raw = row["settings"]
        db_settings = _json2.loads(raw) if isinstance(raw, str) else dict(raw)
    else:
        db_settings = {}
    merged = {**DEFAULT_PROJECT_SETTINGS, **db_settings}
    return merged


@app.put("/api/projects/{slug}/settings")
async def update_settings(slug: str, request: Request):
    body = await request.json()
    clean, errors = validate_settings(body)
    if errors:
        return JSONResponse({"error": f"invalid settings: {'; '.join(errors)}"}, 400)
    if not clean:
        return JSONResponse({"error": "no valid settings provided"}, 400)
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    import json as _json
    await pool.execute("""
        INSERT INTO project_settings (project_id, settings)
        VALUES ($1, $2::jsonb)
        ON CONFLICT (project_id)
        DO UPDATE SET settings = project_settings.settings || $2::jsonb
    """, proj["id"], _json.dumps(clean))
    row = await pool.fetchrow(
        "SELECT settings FROM project_settings WHERE project_id = $1", proj["id"]
    )
    raw = row["settings"]
    db_settings = _json.loads(raw) if isinstance(raw, str) else dict(raw)
    merged = {**DEFAULT_PROJECT_SETTINGS, **db_settings}
    return merged


@app.get("/api/projects/{slug}/comments")
async def list_project_comments(slug: str):
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    rows = await pool.fetch("""
        SELECT c.id, c.anchor_text, c.anchor_prefix, c.anchor_suffix,
               c.body, c.resolved, c.created_at, c.updated_at,
               s.slug AS section_slug, s.title AS section_title,
               COALESCE(rc.cnt, 0) AS reply_count
        FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        LEFT JOIN (SELECT comment_id, COUNT(*) AS cnt FROM comment_replies GROUP BY comment_id) rc
            ON rc.comment_id = c.id
        WHERE s.project_id = $1
        ORDER BY c.created_at DESC
    """, proj["id"])
    return [row_dict(r) for r in rows]


@app.get("/api/projects/{slug}/token-stats")
async def get_token_stats(slug: str):
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    pid = proj["id"]

    totals = await pool.fetchrow("""
        SELECT COUNT(*) AS operations,
               COALESCE(SUM(full_doc_tokens), 0) AS total_full,
               COALESCE(SUM(loaded_tokens), 0) AS total_loaded
        FROM token_estimates WHERE project_id = $1
    """, pid)

    by_op = await pool.fetch("""
        SELECT operation,
               COUNT(*) AS count,
               SUM(full_doc_tokens) AS full_tokens,
               SUM(loaded_tokens) AS loaded_tokens
        FROM token_estimates WHERE project_id = $1
        GROUP BY operation ORDER BY count DESC
    """, pid)

    daily = await pool.fetch("""
        SELECT d.day::date AS day,
               COALESCE(COUNT(t.id), 0) AS operations,
               COALESCE(SUM(t.full_doc_tokens - t.loaded_tokens), 0) AS tokens_saved
        FROM generate_series(current_date - 6, current_date, '1 day') AS d(day)
        LEFT JOIN (
            SELECT * FROM token_estimates WHERE project_id = $1
        ) t ON t.created_at::date = d.day
        GROUP BY d.day ORDER BY d.day ASC
    """, pid)

    total_full = totals["total_full"]
    total_loaded = totals["total_loaded"]
    saved = total_full - total_loaded
    pct = round(saved / total_full * 100, 1) if total_full > 0 else 0

    return {
        "operations": totals["operations"],
        "total_full_doc_tokens": total_full,
        "total_loaded_tokens": total_loaded,
        "total_saved_tokens": saved,
        "savings_percent": pct,
        "by_operation": [row_dict(r) for r in by_op],
        "daily_trend": [{"day": str(r["day"]), "operations": r["operations"],
                         "tokens_saved": r["tokens_saved"]} for r in daily],
    }


@app.get("/api/projects/{slug}/export")
async def export_project(slug: str):
    proj = await pool.fetchrow("SELECT * FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)

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

    return PlainTextResponse("\n".join(lines), media_type="text/plain")


@app.get("/health")
async def health():
    try:
        await pool.fetchval("SELECT 1")
        return {"status": "ok", "db": "connected"}
    except Exception:
        return JSONResponse({"status": "error", "db": "error"}, 503)
