"""PRD Forge Web UI — FastAPI application."""

import asyncio
import glob
import json
import logging
import os
import re
import shlex
import shutil
import sys
import tempfile
import uuid as _uuid
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
from shared.settings import CHAT_PROVIDER_VALUES, DEFAULT_PROJECT_SETTINGS, validate_settings

pool: asyncpg.Pool | None = None
logger = logging.getLogger("prd_forge_ui")


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name, "") or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


CHAT_MAX_ATTACHMENTS = _int_env("CHAT_MAX_ATTACHMENTS", 5)
CHAT_ATTACHMENT_MAX_BYTES = _int_env("CHAT_ATTACHMENT_MAX_BYTES", 200_000)
CHAT_ATTACHMENT_MAX_CHARS = _int_env("CHAT_ATTACHMENT_MAX_CHARS", 12_000)
CHAT_ATTACHMENTS_MAX_TOTAL_CHARS = _int_env("CHAT_ATTACHMENTS_MAX_TOTAL_CHARS", 40_000)
PROJECT_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def _slugify_project_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:100]


def _valid_project_slug(slug: str) -> bool:
    return bool(slug and len(slug) <= 100 and PROJECT_SLUG_RE.match(slug))


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
        elif isinstance(v, _uuid.UUID):
            d[k] = str(v)
        elif k == "metadata" and isinstance(v, str):
            try:
                parsed = json.loads(v)
                d[k] = parsed
            except Exception:
                d[k] = v
    return d


_static_dir = os.path.join(os.path.dirname(__file__), "static")
with open(os.path.join(_static_dir, "index.html")) as _f:
    HTML = _f.read()


CHAT_ALLOWED_MCP_TOOLS: dict[str, dict[str, Any]] = {
    "prd_get_overview": {
        "description": "Get project overview with section summaries.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "arg_names": [],
    },
    "prd_list_sections": {
        "description": "List all sections with metadata.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "arg_names": [],
    },
    "prd_read_section": {
        "description": "Read one section with dependency context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "Section slug"},
            },
            "required": ["section"],
            "additionalProperties": False,
        },
        "arg_names": ["section"],
    },
    "prd_search": {
        "description": "Search sections by text or tag:prefix query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "arg_names": ["query"],
    },
    "prd_list_comments": {
        "description": "List comments across the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_resolved": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "arg_names": ["include_resolved"],
    },
    "prd_update_section": {
        "description": "Update section fields. Use after reading the target section.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string"},
                "content": {"type": "string"},
                "summary": {"type": "string"},
                "title": {"type": "string"},
                "status": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "notes": {"type": "string"},
                "change_description": {"type": "string"},
                "resolve_comments": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["section"],
            "additionalProperties": False,
        },
        "arg_names": [
            "section",
            "content",
            "summary",
            "title",
            "status",
            "tags",
            "notes",
            "change_description",
            "resolve_comments",
        ],
    },
    "prd_resolve_comment": {
        "description": "Resolve or reopen comment in section.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string"},
                "comment_id": {"type": "string"},
                "reopen": {"type": "boolean"},
            },
            "required": ["section", "comment_id"],
            "additionalProperties": False,
        },
        "arg_names": ["section", "comment_id", "reopen"],
    },
    "prd_add_comment_reply": {
        "description": "Reply to a section comment as claude.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string"},
                "comment_id": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["section", "comment_id", "body"],
            "additionalProperties": False,
        },
        "arg_names": ["section", "comment_id", "body"],
    },
}

APPROVAL_ALLOWED_TOOLS = {f"mcp__prd-forge__{k}" for k in CHAT_ALLOWED_MCP_TOOLS}


def _chat_tools_for_anthropic() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": spec["description"],
            "input_schema": spec["input_schema"],
        }
        for name, spec in CHAT_ALLOWED_MCP_TOOLS.items()
    ]


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chat_system_prompt(project_slug: str) -> str:
    return (
        "You are Claude inside PRD Forge Web UI. "
        f"Only operate on project '{project_slug}'. "
        "Use tools for factual project data and for any mutations. "
        "When calling prd_create_section, use section_type from: overview, tech_spec, data_model, api_spec, ui_design, architecture, deployment, security, testing, timeline, general (use general if unsure). "
        "Before updating a section, read it first. "
        "Never claim a write succeeded unless tool output confirms success. "
        "If a tool returns an error, explain it briefly and suggest a fix."
    )


def _chat_provider() -> str:
    provider = (os.environ.get("CHAT_PROVIDER", "anthropic_api") or "").strip().lower()
    if provider in {"anthropic_api", "claude_cli"}:
        return provider
    if provider == "auto":
        cli_cmd = (os.environ.get("CLAUDE_CLI_PATH", "claude") or "claude").strip()
        return "claude_cli" if shutil.which(cli_cmd) else "anthropic_api"
    return "anthropic_api"


def _effective_chat_provider(project_settings: dict[str, Any] | None) -> str:
    if project_settings:
        provider = str(project_settings.get("chat_provider") or "").strip().lower()
        if provider in CHAT_PROVIDER_VALUES:
            return provider
    return _chat_provider()


def _chat_mcp_url() -> str:
    return (os.environ.get("CHAT_MCP_URL", "http://localhost:8080/mcp/") or "").strip()


def _create_claude_cli_mcp_config_file() -> str:
    mcp_url = _chat_mcp_url()
    payload = {
        "mcpServers": {
            "prd-forge": {
                "type": "http",
                "url": mcp_url,
            }
        }
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as fp:
        json.dump(payload, fp)
        fp.flush()
        return fp.name


def _prepare_claude_cli_runtime() -> None:
    claude_config_path = "/root/.claude.json"
    if os.path.exists(claude_config_path):
        return

    backup_candidates = sorted(glob.glob("/root/.claude/backups/.claude.json.backup.*"))
    if backup_candidates:
        latest_backup = backup_candidates[-1]
        try:
            shutil.copy2(latest_backup, claude_config_path)
        except Exception:
            logger.warning("Failed to restore Claude CLI config from backup: %s", latest_backup)


def _build_claude_cli_prompt(project_slug: str, history: list[dict[str, Any]], user_message: str) -> str:
    lines = [
        "You are Claude inside PRD Forge Web UI.",
        f"Only operate on project '{project_slug}'.",
        "Answer concisely and use markdown when useful.",
        "",
        "Conversation history:",
    ]

    for turn in history[-20:]:
        role = (turn.get("role") or "assistant").strip().lower()
        content = str(turn.get("content") or "")
        if not content:
            continue
        role_label = "User" if role == "user" else "Assistant"
        lines.append(f"{role_label}:\n{content}\n")

    lines.extend(
        [
            "Current user message:",
            user_message,
            "",
            "Reply as assistant:",
        ]
    )
    return "\n".join(lines)


def _extract_assistant_text_from_cli_message(obj: dict[str, Any]) -> str:
    message = obj.get("message") or {}
    content = message.get("content") or []
    text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
    return "".join(text_parts)


def _canonical_tool_name(raw_name: str) -> str:
    name = str(raw_name or "").strip()
    if not name:
        return ""
    parts = name.split("__")
    return parts[-1] if parts else name


def _manual_approval_payload(final_text: str, requested_tools: list[str]) -> dict[str, Any] | None:
    text = (final_text or "").strip()
    if not text:
        return None

    lowered = text.lower()
    markers = (
        "need your permission",
        "grant access",
        "manual approval",
        "please approve",
        "permission to execute",
        "разрешен",
        "апрув",
    )
    if not any(marker in lowered for marker in markers):
        return None

    tool = ""
    for tool_name in reversed(requested_tools):
        canonical = _canonical_tool_name(tool_name)
        if canonical.startswith("prd_"):
            tool = canonical
            break
    if not tool and requested_tools:
        tool = _canonical_tool_name(requested_tools[-1])

    return {
        "kind": "manual_approval_required",
        "tool": tool,
        "message": text,
    }


async def _iter_json_objects_from_stream(stream: asyncio.StreamReader):
    decoder = json.JSONDecoder()
    buffer = ""

    while True:
        chunk = await stream.read(4096)
        if not chunk:
            break
        buffer += chunk.decode("utf-8", errors="replace")

        while True:
            buffer = buffer.lstrip()
            if not buffer:
                break
            try:
                obj, idx = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                break
            yield obj
            buffer = buffer[idx:]

    buffer = buffer.strip()
    while buffer:
        try:
            obj, idx = decoder.raw_decode(buffer)
        except json.JSONDecodeError:
            logger.debug("Unparsed Claude CLI stream tail: %s", buffer[:200])
            break
        yield obj
        buffer = buffer[idx:].lstrip()


async def _claude_cli_turn_stream(
    project_slug: str,
    history: list[dict[str, Any]],
    user_message: str,
    permission_mode_override: str | None = None,
    allowed_tools_override: list[str] | None = None,
):
    cli_path = (os.environ.get("CLAUDE_CLI_PATH", "claude") or "claude").strip()
    cli_exe = shutil.which(cli_path) if os.path.sep not in cli_path else cli_path
    if not cli_exe:
        raise RuntimeError(
            "Claude CLI not found. Install `claude` and set CHAT_PROVIDER=claude_cli (or set CLAUDE_CLI_PATH)."
        )

    _prepare_claude_cli_runtime()

    prompt = _build_claude_cli_prompt(project_slug, history, user_message)
    mcp_config_path = _create_claude_cli_mcp_config_file()
    permission_mode = (permission_mode_override or "").strip() or (
        os.environ.get("CLAUDE_CLI_PERMISSION_MODE", "acceptEdits") or ""
    ).strip()
    if hasattr(os, "geteuid") and os.geteuid() == 0 and permission_mode in {
        "bypassPermissions",
        "dangerously-skip-permissions",
    }:
        permission_mode = "acceptEdits"
    system_append = (
        _chat_system_prompt(project_slug)
        + f" Always pass project='{project_slug}' in every PRD Forge tool call."
    )

    args = [
        cli_exe,
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--input-format",
        "text",
        "--include-partial-messages",
        "--verbose",
        "--mcp-config",
        mcp_config_path,
        "--strict-mcp-config",
        "--append-system-prompt",
        system_append,
    ]

    if permission_mode:
        args.extend(["--permission-mode", permission_mode])

    if allowed_tools_override:
        allowed_tools = [str(t).strip() for t in allowed_tools_override if str(t).strip()]
        if allowed_tools:
            args.extend(["--allowedTools", ",".join(allowed_tools)])

    model = (os.environ.get("CLAUDE_CLI_MODEL", "") or "").strip()
    if model:
        args.extend(["--model", model])

    extra_args = (os.environ.get("CLAUDE_CLI_ARGS", "") or "").strip()
    if extra_args:
        args.extend(shlex.split(extra_args))

    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assistant_text_parts: list[str] = []
    assistant_message_text = ""
    saw_delta = False
    requested_tools: list[str] = []

    try:
        assert process.stdout is not None
        async for obj in _iter_json_objects_from_stream(process.stdout):
            if not isinstance(obj, dict):
                continue
            obj_type = obj.get("type")

            if obj_type == "stream_event":
                event = obj.get("event") or {}
                event_type = event.get("type")
                if event_type == "content_block_delta":
                    delta = event.get("delta") or {}
                    if delta.get("type") == "text_delta":
                        text = str(delta.get("text") or "")
                        if text:
                            saw_delta = True
                            assistant_text_parts.append(text)
                            yield {"type": "delta", "text": text}
                elif event_type == "content_block_start":
                    content_block = event.get("content_block") or {}
                    if content_block.get("type") == "tool_use":
                        tool_name = str(content_block.get("name") or "")
                        tool_input = content_block.get("input") or {}
                        if tool_name:
                            requested_tools.append(tool_name)
                        yield {
                            "type": "tool",
                            "tool": {
                                "name": tool_name,
                                "input": tool_input,
                            },
                        }

            elif obj_type == "assistant":
                extracted = _extract_assistant_text_from_cli_message(obj)
                if extracted:
                    assistant_message_text = extracted

            elif obj_type == "result" and obj.get("is_error"):
                result_text = str(obj.get("result") or "Claude CLI returned an error")
                raise RuntimeError(result_text)

        stderr_text = ""
        if process.stderr is not None:
            stderr_text = (await process.stderr.read()).decode("utf-8", errors="replace").strip()
        return_code = await process.wait()
        if return_code != 0:
            details = stderr_text or f"exit code {return_code}"
            raise RuntimeError(f"Claude CLI command failed: {details}")

        final_text = "".join(assistant_text_parts).strip()
        if not final_text:
            final_text = assistant_message_text.strip()

        if not final_text:
            raise RuntimeError("Claude CLI returned an empty response")

        approval_payload = _manual_approval_payload(final_text, requested_tools)
        if approval_payload is not None:
            yield {
                "type": "approval",
                "approval": approval_payload,
            }

        if not saw_delta:
            chunk_size = 80
            for i in range(0, len(final_text), chunk_size):
                yield {"type": "delta", "text": final_text[i : i + chunk_size]}

        yield {"type": "done", "text": final_text}
    finally:
        try:
            os.unlink(mcp_config_path)
        except OSError:
            pass


def _normalize_selection_context(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None

    selected_text = str(raw.get("selected_text") or "").strip()
    if not selected_text:
        return None

    def _clean(key: str, max_len: int) -> str:
        return str(raw.get(key) or "").strip()[:max_len]

    return {
        "section_slug": _clean("section_slug", 120),
        "section_title": _clean("section_title", 200),
        "selected_text": selected_text[:2500],
        "anchor_prefix": _clean("anchor_prefix", 600),
        "anchor_suffix": _clean("anchor_suffix", 600),
    }


def _normalize_chat_attachments(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("attachments must be an array")
    if len(raw) > CHAT_MAX_ATTACHMENTS:
        raise ValueError(f"attachments limit exceeded (max {CHAT_MAX_ATTACHMENTS})")

    normalized: list[dict[str, Any]] = []
    total_chars = 0

    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"attachment #{idx} must be an object")

        name = str(item.get("name") or "").strip()[:200]
        if not name:
            raise ValueError(f"attachment #{idx} is missing name")

        mime_type = str(item.get("mime_type") or item.get("type") or "application/octet-stream").strip()[:120]
        content_text = str(item.get("content_text") or "")
        if not content_text.strip():
            raise ValueError(f"attachment '{name}' is empty")
        if len(content_text) > CHAT_ATTACHMENT_MAX_CHARS:
            raise ValueError(
                f"attachment '{name}' exceeds max text length ({CHAT_ATTACHMENT_MAX_CHARS} chars)"
            )

        provided_size = item.get("size_bytes")
        try:
            size_bytes = int(provided_size) if provided_size is not None else len(content_text.encode("utf-8"))
        except (TypeError, ValueError):
            size_bytes = len(content_text.encode("utf-8"))
        if size_bytes < 0:
            raise ValueError(f"attachment '{name}' has invalid size")
        if size_bytes > CHAT_ATTACHMENT_MAX_BYTES:
            raise ValueError(
                f"attachment '{name}' exceeds max size ({CHAT_ATTACHMENT_MAX_BYTES} bytes)"
            )

        total_chars += len(content_text)
        if total_chars > CHAT_ATTACHMENTS_MAX_TOTAL_CHARS:
            raise ValueError(
                f"attachments exceed max combined text length ({CHAT_ATTACHMENTS_MAX_TOTAL_CHARS} chars)"
            )

        normalized.append(
            {
                "name": name,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "content_text": content_text,
            }
        )

    return normalized


def _compose_user_turn_message(
    message: str,
    selection_context: dict[str, str] | None,
    attachments: list[dict[str, Any]] | None = None,
) -> str:
    if not selection_context and not attachments:
        return message

    parts = [
        message,
    ]

    if selection_context:
        section = selection_context.get("section_title") or selection_context.get("section_slug") or "unknown"
        selected_text = selection_context.get("selected_text", "")
        anchor_prefix = selection_context.get("anchor_prefix", "")
        anchor_suffix = selection_context.get("anchor_suffix", "")
        parts.extend(
            [
                "",
                "[Selected context from PRD Forge Web UI]",
                f"Section: {section}",
                "Selected text:",
                selected_text,
            ]
        )
        if anchor_prefix:
            parts.extend(["", "Prefix:", anchor_prefix])
        if anchor_suffix:
            parts.extend(["", "Suffix:", anchor_suffix])
        parts.extend(["", "Use this selected context to interpret the user request."])

    if attachments:
        parts.extend(["", "[Attached files from PRD Forge Web UI]"])
        for attachment in attachments:
            file_name = str(attachment.get("name") or "file")
            mime_type = str(attachment.get("mime_type") or "application/octet-stream")
            content_text = str(attachment.get("content_text") or "")
            parts.extend(
                [
                    "",
                    f"File: {file_name}",
                    f"Type: {mime_type}",
                    "Content:",
                    content_text,
                ]
            )
        parts.extend(["", "Use attached files as supplemental context for this request."])

    return "\n".join(parts)


def _get_mcp_server_module():
    import server as mcp_server  # type: ignore

    if getattr(mcp_server, "_pool", None) is None and pool is not None:
        mcp_server._pool = pool
    return mcp_server


async def _run_mcp_tool(project_slug: str, tool_name: str, tool_input: dict[str, Any] | None):
    spec = CHAT_ALLOWED_MCP_TOOLS.get(tool_name)
    if not spec:
        return {"error": f"tool '{tool_name}' is not allowed"}

    mcp_server = _get_mcp_server_module()
    fn = getattr(mcp_server, tool_name, None)
    if not fn:
        return {"error": f"tool '{tool_name}' is unavailable"}

    safe_input = tool_input or {}
    kwargs: dict[str, Any] = {"project": project_slug}
    for arg in spec["arg_names"]:
        if arg in safe_input:
            kwargs[arg] = safe_input[arg]

    try:
        raw = await fn(**kwargs)
        if not isinstance(raw, str):
            return {"error": f"tool '{tool_name}' returned invalid payload"}
        parsed = json.loads(raw)
        return parsed
    except TypeError as e:
        return {"error": f"invalid arguments for {tool_name}: {e}"}
    except Exception as e:
        logger.exception("chat tool call failed: %s", tool_name)
        return {"error": str(e)}


async def _anthropic_messages(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    project_slug: str,
) -> dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    model = os.environ.get("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")
    max_tokens = int(os.environ.get("CHAT_MAX_TOKENS", "1800"))

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": _chat_system_prompt(project_slug),
        "messages": messages,
        "tools": tools,
    }

    timeout = httpx.Timeout(120.0, connect=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"Anthropic API error ({resp.status_code}): {detail}")

    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Anthropic API error: {data['error']}")
    return data


async def _run_chat_agent_turn(
    project_slug: str,
    history: list[dict[str, Any]],
    user_message: str,
) -> tuple[str, list[dict[str, Any]]]:
    tools = _chat_tools_for_anthropic()
    tool_events: list[dict[str, Any]] = []
    loop_limit = int(os.environ.get("CHAT_MAX_TOOL_LOOPS", "6"))

    messages: list[dict[str, Any]] = list(history)
    messages.append({"role": "user", "content": user_message})

    for _ in range(loop_limit):
        response = await _anthropic_messages(messages, tools, project_slug)
        blocks = response.get("content") or []
        text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        tool_uses = [b for b in blocks if b.get("type") == "tool_use"]

        if not tool_uses:
            final_text = "\n".join([p for p in text_parts if p]).strip()
            return (final_text or "Done."), tool_events

        assistant_blocks = []
        for block in blocks:
            if block.get("type") == "text":
                assistant_blocks.append({"type": "text", "text": block.get("text", "")})
            elif block.get("type") == "tool_use":
                assistant_blocks.append(
                    {
                        "type": "tool_use",
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": block.get("input", {}),
                    }
                )
        messages.append({"role": "assistant", "content": assistant_blocks})

        tool_results = []
        for tool_call in tool_uses:
            tool_name = tool_call.get("name", "")
            tool_input = tool_call.get("input") or {}
            tool_result = await _run_mcp_tool(project_slug, tool_name, tool_input)
            tool_events.append(
                {
                    "name": tool_name,
                    "input": tool_input,
                    "result": tool_result,
                }
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call.get("id"),
                    "content": json.dumps(tool_result, ensure_ascii=False),
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return (
        "I reached the tool-call limit for this turn. Please narrow the request or ask me to continue.",
        tool_events,
    )


async def _resolve_project_id_or_none(slug: str):
    return await pool.fetchval("SELECT id FROM projects WHERE slug = $1", slug)


async def _get_or_create_project_chat(project_id):
    return await pool.fetchval(
        """
        INSERT INTO project_chats (project_id)
        VALUES ($1)
        ON CONFLICT (project_id)
        DO UPDATE SET updated_at = now()
        RETURNING id
        """,
        project_id,
    )


async def _store_chat_message(chat_id, role: str, content: str, metadata: dict[str, Any] | None = None):
    return await pool.fetchrow(
        """
        INSERT INTO chat_messages (chat_id, role, content, metadata)
        VALUES ($1, $2, $3, $4::jsonb)
        RETURNING id, role, content, metadata, created_at
        """,
        chat_id,
        role,
        content,
        json.dumps(metadata or {}),
    )


async def _get_chat_messages_by_project(slug: str):
    rows = await pool.fetch(
        """
        SELECT m.id, m.role, m.content, m.metadata, m.created_at
        FROM projects p
        JOIN project_chats c ON c.project_id = p.id
        JOIN chat_messages m ON m.chat_id = c.id
        WHERE p.slug = $1
        ORDER BY m.created_at ASC
        """,
        slug,
    )
    return [row_dict(r) for r in rows]


async def _get_project_settings_dict(project_id) -> dict[str, Any]:
    row = await pool.fetchrow(
        "SELECT settings FROM project_settings WHERE project_id = $1", project_id
    )
    if not row:
        return {}

    raw = row["settings"]
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


async def _is_chat_enabled(project_id) -> bool:
    """Check if chat is enabled for a project."""
    raw = await _get_project_settings_dict(project_id)
    merged = {**DEFAULT_PROJECT_SETTINGS, **raw}
    return merged.get("chat_enabled", False)


def _metadata_dict(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


async def _build_chat_history(chat_id, before_created_at=None) -> list[dict[str, str]]:
    if before_created_at is None:
        history_rows = await pool.fetch(
            """
            SELECT role, content, metadata
            FROM chat_messages
            WHERE chat_id = $1 AND role IN ('user', 'assistant')
            ORDER BY created_at DESC
            LIMIT 20
            """,
            chat_id,
        )
    else:
        history_rows = await pool.fetch(
            """
            SELECT role, content, metadata
            FROM chat_messages
            WHERE chat_id = $1 AND role IN ('user', 'assistant') AND created_at < $2
            ORDER BY created_at DESC
            LIMIT 20
            """,
            chat_id,
            before_created_at,
        )

    history: list[dict[str, str]] = []
    for row in reversed(history_rows):
        row_context = None
        row_attachments: list[dict[str, Any]] = []
        metadata = _metadata_dict(row["metadata"])
        if row["role"] == "user" and metadata is not None:
            row_context = _normalize_selection_context(metadata.get("selection_context"))
            try:
                row_attachments = _normalize_chat_attachments(metadata.get("attachments"))
            except ValueError:
                row_attachments = []
        history.append(
            {
                "role": row["role"],
                "content": _compose_user_turn_message(row["content"], row_context, row_attachments)
                if row["role"] == "user"
                else row["content"],
            }
        )
    return history


async def _update_chat_message_metadata(message_id, metadata: dict[str, Any]) -> None:
    await pool.execute(
        "UPDATE chat_messages SET metadata = $2::jsonb WHERE id = $1",
        message_id,
        json.dumps(metadata),
    )


def _canonical_chat_tool_name(raw_name: str) -> str:
    name = str(raw_name or "").strip()
    if not name:
        return ""
    parts = name.split("__")
    return parts[-1] if parts else name


def _tool_events_include(tool_events: list[dict[str, Any]], tool_name: str) -> bool:
    if not tool_events:
        return False
    target = str(tool_name or "").strip()
    if not target:
        return False
    for event in tool_events:
        raw = str((event or {}).get("name") or "")
        if _canonical_chat_tool_name(raw) == target:
            return True
    return False


async def _project_has_chat_activity(project_id) -> bool:
    count = await pool.fetchval(
        """
        SELECT COUNT(m.id)
        FROM project_chats c
        JOIN chat_messages m ON m.chat_id = c.id
        WHERE c.project_id = $1
        """,
        project_id,
    )
    return bool(count and count > 0)


async def _backfill_missing_initial_revisions(project_id) -> int:
    missing = await pool.fetch(
        """
        SELECT s.id, s.content, s.summary
        FROM sections s
        LEFT JOIN (
            SELECT section_id, COUNT(*) AS cnt
            FROM section_revisions
            GROUP BY section_id
        ) r ON r.section_id = s.id
        WHERE s.project_id = $1 AND COALESCE(r.cnt, 0) = 0
        """,
        project_id,
    )
    if not missing:
        return 0

    inserted = 0
    for row in missing:
        result = await pool.execute(
            """
            INSERT INTO section_revisions (section_id, revision_number, content, summary, change_description)
            VALUES ($1, 1, $2, $3, $4)
            ON CONFLICT (section_id, revision_number) DO NOTHING
            """,
            row["id"],
            row["content"] or "",
            row["summary"] or "",
            "Initial section snapshot",
        )
        try:
            inserted += int(result.split()[-1])
        except Exception:
            pass
    return inserted


async def _backfill_linear_dependencies(project_id) -> int:
    dep_count = await pool.fetchval(
        "SELECT COUNT(*) FROM section_dependencies WHERE project_id = $1",
        project_id,
    )
    if dep_count and dep_count > 0:
        return 0

    sections = await pool.fetch(
        """
        SELECT id, slug
        FROM sections
        WHERE project_id = $1
        ORDER BY sort_order ASC, created_at ASC, slug ASC
        """,
        project_id,
    )
    if len(sections) < 2:
        return 0

    inserted = 0
    for idx in range(1, len(sections)):
        current = sections[idx]
        previous = sections[idx - 1]
        result = await pool.execute(
            """
            INSERT INTO section_dependencies (project_id, section_id, depends_on_id, dependency_type, description)
            VALUES ($1, $2, $3, 'references', $4)
            ON CONFLICT (section_id, depends_on_id) DO NOTHING
            """,
            project_id,
            current["id"],
            previous["id"],
            "Auto-linked from chat-generated section order",
        )
        try:
            inserted += int(result.split()[-1])
        except Exception:
            pass
    return inserted


async def _ensure_chat_generated_project_graph_data(project_id) -> None:
    await _backfill_missing_initial_revisions(project_id)
    if await _project_has_chat_activity(project_id):
        await _backfill_linear_dependencies(project_id)




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


@app.post("/api/projects")
async def create_project(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON body"}, 400)

    name = str(body.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name required"}, 400)

    provided_slug = str(body.get("slug") or "").strip().lower()
    slug = provided_slug or _slugify_project_name(name)
    if not _valid_project_slug(slug):
        return JSONResponse(
            {"error": "invalid slug: use lowercase letters, numbers, and hyphens (max 100 chars)"},
            400,
        )

    description = str(body.get("description") or "").strip()

    try:
        row = await pool.fetchrow(
            """
            INSERT INTO projects (name, slug, description)
            VALUES ($1, $2, $3)
            RETURNING id, slug, name, description, version, created_at, updated_at
            """,
            name,
            slug,
            description,
        )
    except asyncpg.UniqueViolationError:
        return JSONResponse({"error": f"project slug '{slug}' already exists"}, 409)

    return row_dict(row)


@app.get("/api/projects/{slug}")
async def get_project(slug: str):
    proj = await pool.fetchrow("SELECT * FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)

    await _ensure_chat_generated_project_graph_data(proj["id"])

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
    db_settings = await _get_project_settings_dict(proj["id"])
    merged = {**DEFAULT_PROJECT_SETTINGS, **db_settings}
    merged["chat_provider"] = _effective_chat_provider(db_settings)
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
    await pool.execute("""
        INSERT INTO project_settings (project_id, settings)
        VALUES ($1, $2::jsonb)
        ON CONFLICT (project_id)
        DO UPDATE SET settings = project_settings.settings || $2::jsonb
    """, proj["id"], json.dumps(clean))
    db_settings = await _get_project_settings_dict(proj["id"])
    merged = {**DEFAULT_PROJECT_SETTINGS, **db_settings}
    merged["chat_provider"] = _effective_chat_provider(db_settings)
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

    await _backfill_missing_initial_revisions(pid)

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

    project_stats = await pool.fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM sections WHERE project_id = $1) AS section_count,
            (SELECT COUNT(*) FROM section_dependencies WHERE project_id = $1) AS dependency_count,
            (SELECT COUNT(*) FROM section_revisions r
             JOIN sections s ON s.id = r.section_id
             WHERE s.project_id = $1) AS revision_count
        """,
        pid,
    )

    return {
        "operations": totals["operations"],
        "total_full_doc_tokens": total_full,
        "total_loaded_tokens": total_loaded,
        "total_saved_tokens": saved,
        "savings_percent": pct,
        "by_operation": [row_dict(r) for r in by_op],
        "daily_trend": [{"day": str(r["day"]), "operations": r["operations"],
                         "tokens_saved": r["tokens_saved"]} for r in daily],
        "project_stats": {
            "sections": project_stats["section_count"],
            "dependencies": project_stats["dependency_count"],
            "revisions": project_stats["revision_count"],
        },
    }


@app.get("/api/projects/{slug}/chat/messages")
async def get_chat_messages(slug: str):
    proj = await _resolve_project_id_or_none(slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    if not await _is_chat_enabled(proj):
        return JSONResponse({"error": "Chat is disabled. Enable in Experimental Features settings."}, 403)
    rows = await _get_chat_messages_by_project(slug)
    return {"messages": rows}


@app.post("/api/projects/{slug}/chat/clear")
async def clear_chat(slug: str):
    proj = await _resolve_project_id_or_none(slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    if not await _is_chat_enabled(proj):
        return JSONResponse({"error": "Chat is disabled. Enable in Experimental Features settings."}, 403)
    chat_id = await _get_or_create_project_chat(proj)
    result = await pool.execute("DELETE FROM chat_messages WHERE chat_id = $1", chat_id)
    deleted = int(result.split()[-1])
    return {"ok": True, "deleted": deleted}


@app.post("/api/projects/{slug}/chat/stream")
async def stream_chat(slug: str, request: Request):
    proj = await _resolve_project_id_or_none(slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    if not await _is_chat_enabled(proj):
        return JSONResponse({"error": "Chat is disabled. Enable in Experimental Features settings."}, 403)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON body"}, 400)

    try:
        attachments = _normalize_chat_attachments(body.get("attachments"))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, 400)

    message = (body.get("message") or "").strip()
    if not message and not attachments:
        return JSONResponse({"error": "message required"}, 400)
    if not message:
        message = "Please review attached files."

    selection_context = _normalize_selection_context(body.get("selection_context"))

    chat_id = await _get_or_create_project_chat(proj)
    history = await _build_chat_history(chat_id)

    model_user_message = _compose_user_turn_message(message, selection_context, attachments)
    user_metadata: dict[str, Any] = {}
    if selection_context:
        user_metadata["selection_context"] = selection_context
    if attachments:
        user_metadata["attachments"] = attachments

    user_row = await _store_chat_message(chat_id, "user", message, user_metadata or None)
    project_settings = await _get_project_settings_dict(proj)
    provider = _effective_chat_provider(project_settings)

    async def event_stream():
        yield _sse("user", row_dict(user_row))
        yield _sse("status", {"phase": "thinking"})
        try:
            if provider == "claude_cli":
                assistant_text = ""
                tool_events: list[dict[str, Any]] = []
                approval_events: list[dict[str, Any]] = []
                async for event in _claude_cli_turn_stream(slug, history, model_user_message):
                    if event.get("type") == "delta":
                        chunk = str(event.get("text") or "")
                        assistant_text += chunk
                        yield _sse("delta", {"text": chunk})
                        await asyncio.sleep(0)
                    elif event.get("type") == "tool":
                        tool_event = event.get("tool") or {}
                        tool_events.append(tool_event)
                        yield _sse("tool", tool_event)
                    elif event.get("type") == "approval":
                        approval_event = event.get("approval") or {}
                        approval_events.append(approval_event)
                        yield _sse("approval", approval_event)
                    elif event.get("type") == "done" and not assistant_text:
                        assistant_text = str(event.get("text") or "")

                assistant_row = await _store_chat_message(
                    chat_id,
                    "assistant",
                    assistant_text,
                    {
                        "provider": "claude_cli",
                        "tool_events": tool_events,
                        "approval_requests": approval_events,
                        "approval_resolved": False if approval_events else True,
                    },
                )
            else:
                assistant_text, tool_events = await _run_chat_agent_turn(slug, history, model_user_message)

                for evt in tool_events:
                    yield _sse("tool", evt)

                chunk_size = 80
                for i in range(0, len(assistant_text), chunk_size):
                    chunk = assistant_text[i : i + chunk_size]
                    yield _sse("delta", {"text": chunk})
                    await asyncio.sleep(0)

                assistant_row = await _store_chat_message(
                    chat_id,
                    "assistant",
                    assistant_text,
                    {"provider": "anthropic_api", "tool_events": tool_events},
                )

            yield _sse("done", {"message": row_dict(assistant_row)})
        except Exception as e:
            logger.exception("chat stream failed")
            yield _sse("error", {"error": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/projects/{slug}/chat/approve")
async def approve_chat(slug: str, request: Request):
    proj = await _resolve_project_id_or_none(slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    if not await _is_chat_enabled(proj):
        return JSONResponse({"error": "Chat is disabled. Enable in Experimental Features settings."}, 403)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON body"}, 400)

    assistant_message_id_raw = str(body.get("assistant_message_id") or "").strip()
    if not assistant_message_id_raw:
        return JSONResponse({"error": "assistant_message_id required"}, 400)

    try:
        assistant_message_id = _uuid.UUID(assistant_message_id_raw)
    except ValueError:
        return JSONResponse({"error": "assistant_message_id must be a valid UUID"}, 400)

    chat_id = await _get_or_create_project_chat(proj)
    approval_row = await pool.fetchrow(
        """
        SELECT id, role, content, metadata, created_at
        FROM chat_messages
        WHERE id = $1 AND chat_id = $2
        """,
        assistant_message_id,
        chat_id,
    )
    if not approval_row or approval_row["role"] != "assistant":
        return JSONResponse({"error": "approval message not found"}, 404)

    approval_metadata = _metadata_dict(approval_row["metadata"]) or {}
    approval_requests = approval_metadata.get("approval_requests")
    if not isinstance(approval_requests, list) or not approval_requests:
        return JSONResponse({"error": "message does not contain approval requests"}, 400)
    if approval_metadata.get("approval_resolved"):
        return JSONResponse({"error": "approval already resolved"}, 409)

    source_user_row = await pool.fetchrow(
        """
        SELECT id, content, metadata, created_at
        FROM chat_messages
        WHERE chat_id = $1 AND role = 'user' AND created_at < $2
        ORDER BY created_at DESC
        LIMIT 1
        """,
        chat_id,
        approval_row["created_at"],
    )
    if not source_user_row:
        return JSONResponse({"error": "source user message not found"}, 400)

    history = await _build_chat_history(chat_id, before_created_at=approval_row["created_at"])
    source_user_metadata = _metadata_dict(source_user_row["metadata"]) or {}
    source_selection_context = _normalize_selection_context(source_user_metadata.get("selection_context"))
    try:
        source_attachments = _normalize_chat_attachments(source_user_metadata.get("attachments"))
    except ValueError:
        source_attachments = []
    source_model_user_message = _compose_user_turn_message(
        source_user_row["content"],
        source_selection_context,
        source_attachments,
    )
    approved_model_user_message = (
        "User approved the pending tool-permission request for this turn. "
        "Continue the same task and execute the required PRD Forge tools now. "
        "Do not ask for permission again unless the platform hard-blocks the call.\n\n"
        "Original user request:\n"
        f"{source_model_user_message}"
    )

    approval_permission_mode = (
        os.environ.get("CLAUDE_CLI_APPROVAL_PERMISSION_MODE", "acceptEdits")
        or "acceptEdits"
    ).strip()
    if approval_permission_mode == "dontAsk":
        approval_permission_mode = "acceptEdits"

    approved_allowed_tools = [
        f"mcp__prd-forge__{tool_name}"
        for tool_name in CHAT_ALLOWED_MCP_TOOLS.keys()
    ]

    async def event_stream():
        yield _sse("status", {"phase": "approving", "assistant_message_id": assistant_message_id_raw})
        try:
            assistant_text = ""
            tool_events: list[dict[str, Any]] = []
            nested_approval_events: list[dict[str, Any]] = []

            async for event in _claude_cli_turn_stream(
                slug,
                history,
                approved_model_user_message,
                permission_mode_override=approval_permission_mode,
                allowed_tools_override=approved_allowed_tools,
            ):
                if event.get("type") == "delta":
                    chunk = str(event.get("text") or "")
                    assistant_text += chunk
                    yield _sse("delta", {"text": chunk})
                    await asyncio.sleep(0)
                elif event.get("type") == "tool":
                    tool_event = event.get("tool") or {}
                    tool_events.append(tool_event)
                    yield _sse("tool", tool_event)
                elif event.get("type") == "approval":
                    approval_event = event.get("approval") or {}
                    nested_approval_events.append(approval_event)
                    yield _sse("approval", approval_event)
                elif event.get("type") == "done" and not assistant_text:
                    assistant_text = str(event.get("text") or "")

            assistant_row = await _store_chat_message(
                chat_id,
                "assistant",
                assistant_text,
                {
                    "provider": "claude_cli",
                    "tool_events": tool_events,
                    "approval_requests": nested_approval_events,
                    "approval_resolved": False if nested_approval_events else True,
                    "approval_for_message_id": assistant_message_id_raw,
                },
            )

            updated_approval_metadata = dict(approval_metadata)
            updated_approval_metadata["approval_resolved"] = True
            await _update_chat_message_metadata(assistant_message_id, updated_approval_metadata)

            yield _sse(
                "done",
                {
                    "message": row_dict(assistant_row),
                    "approved_message_id": assistant_message_id_raw,
                },
            )
        except Exception as e:
            logger.exception("chat approval failed")
            yield _sse("error", {"error": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
