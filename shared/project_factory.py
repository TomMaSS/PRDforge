"""Shared project creation logic used by both API and MCP server."""

import re
import logging

import asyncpg

from shared.constants import VALID_SECTION_TYPES
from shared.templates import get_template

logger = logging.getLogger("prd_forge_factory")

SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
MAX_SLUG = 100
MAX_CONTENT_LEN = 50_000


def _validate_slug(slug: str) -> str | None:
    if not slug or len(slug) > MAX_SLUG or not SLUG_RE.match(slug):
        return f"invalid slug '{slug}': must be 1-{MAX_SLUG} chars, lowercase alphanumeric with hyphens"
    return None


async def create_project_with_template(
    pool: asyncpg.Pool,
    name: str,
    slug: str,
    description: str = "",
    template_id: str | None = None,
    user_id: str | None = None,
    organization_id: str | None = None,
) -> dict:
    """Create a project with optional template sections in a single transaction.

    Returns the created project dict (with section_count).
    Raises ValueError for validation errors, asyncpg.UniqueViolationError for slug conflicts.
    """
    # Validate slug
    slug_err = _validate_slug(slug)
    if slug_err:
        raise ValueError(slug_err)

    # Resolve template
    template = None
    if template_id and template_id != "blank":
        template = get_template(template_id)
        if template is None:
            raise ValueError(f"unknown template '{template_id}'")
        # Validate template sections
        seen_slugs: set[str] = set()
        for sec in template.sections:
            sec_slug_err = _validate_slug(sec.slug)
            if sec_slug_err:
                raise ValueError(f"template section: {sec_slug_err}")
            if sec.section_type not in VALID_SECTION_TYPES:
                raise ValueError(f"template section '{sec.slug}': invalid type '{sec.section_type}'")
            if len(sec.content) > MAX_CONTENT_LEN:
                raise ValueError(f"template section '{sec.slug}': content exceeds {MAX_CONTENT_LEN} chars")
            if sec.slug in seen_slugs:
                raise ValueError(f"template has duplicate section slug '{sec.slug}'")
            seen_slugs.add(sec.slug)

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Insert project
            row = await conn.fetchrow(
                """
                INSERT INTO projects (name, slug, description, created_by, organization_id)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, slug, name, description, version, created_at, updated_at
                """,
                name,
                slug,
                description,
                user_id,
                organization_id,
            )
            project_id = row["id"]

            section_count = 0
            # Insert template sections
            if template and template.sections:
                for sec in template.sections:
                    sec_row = await conn.fetchrow(
                        """
                        INSERT INTO sections (project_id, slug, title, section_type,
                                              sort_order, content, summary, tags, notes)
                        VALUES ($1, $2, $3, $4, $5, $6, '', '{}', '')
                        RETURNING id
                        """,
                        project_id,
                        sec.slug,
                        sec.title,
                        sec.section_type,
                        sec.sort_order,
                        sec.content,
                    )
                    await conn.execute(
                        """
                        INSERT INTO section_revisions (section_id, revision_number, content, summary, change_description)
                        VALUES ($1, 1, $2, '', 'Initial section creation')
                        ON CONFLICT (section_id, revision_number) DO NOTHING
                        """,
                        sec_row["id"],
                        sec.content,
                    )
                    section_count += 1

            # Add project_members owner row if user_id provided
            if user_id:
                # Check if project_members table exists
                has_pm = await conn.fetchval("SELECT to_regclass('project_members')")
                if has_pm:
                    await conn.execute(
                        """
                        INSERT INTO project_members (project_id, user_id, role)
                        VALUES ($1, $2, 'owner')
                        ON CONFLICT (project_id, user_id) DO NOTHING
                        """,
                        project_id,
                        user_id,
                    )

    # Build result
    result = {}
    for key in ("id", "slug", "name", "description", "version", "created_at", "updated_at"):
        val = row[key]
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        elif hasattr(val, "hex"):  # UUID
            val = str(val)
        result[key] = val
    result["section_count"] = section_count
    result["total_words"] = 0
    return result
