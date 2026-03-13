"""Tests for FastAPI UI endpoints."""

import json

import pytest_asyncio


class TestUIEndpoints:
    async def test_index_html(self, ui_client):
        resp = await ui_client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "PRD Forge" in resp.text
        assert "marked.min.js" in resp.text

    async def test_list_projects(self, ui_client):
        resp = await ui_client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(p["slug"] == "snaphabit" for p in data)

    async def test_project_detail(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit")
        assert resp.status_code == 200
        data = resp.json()
        assert "project" in data
        assert "stats" in data
        assert "sections" in data
        assert "dependencies" in data
        assert "changelog" in data
        assert data["stats"]["sections"] == 12

    async def test_project_not_found(self, ui_client):
        resp = await ui_client.get("/api/projects/nonexistent")
        assert resp.status_code == 404

    async def test_create_project(self, ui_client):
        resp = await ui_client.post(
            "/api/projects",
            json={
                "name": "New UI Project",
                "slug": "new-ui-project",
                "description": "Created from UI API",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New UI Project"
        assert data["slug"] == "new-ui-project"
        assert data["description"] == "Created from UI API"

    async def test_create_project_invalid_payload(self, ui_client):
        missing_name = await ui_client.post(
            "/api/projects",
            json={"slug": "missing-name"},
        )
        assert missing_name.status_code == 400
        assert missing_name.json()["error"] == "name required"

        invalid_slug = await ui_client.post(
            "/api/projects",
            json={"name": "Bad Slug", "slug": "Bad Slug!"},
        )
        assert invalid_slug.status_code == 400
        assert "invalid slug" in invalid_slug.json()["error"]

    async def test_create_project_duplicate_slug(self, ui_client):
        first = await ui_client.post(
            "/api/projects",
            json={"name": "Project One", "slug": "same-slug"},
        )
        assert first.status_code == 200

        second = await ui_client.post(
            "/api/projects",
            json={"name": "Project Two", "slug": "same-slug"},
        )
        assert second.status_code == 409
        assert "already exists" in second.json()["error"]

        async def test_project_detail_backfills_chat_generated_graph_data(self, ui_client):
            import app as ui_app

            pool = ui_app.pool
            pid = await pool.fetchval(
                """
                INSERT INTO projects (name, slug, description)
                VALUES ('Chat Backfill', 'chat-backfill', '')
                RETURNING id
                """
            )
            await pool.execute(
                """
                INSERT INTO sections (project_id, slug, title, section_type, sort_order, content, summary)
                VALUES
                    ($1, 's1', 'S1', 'general', 1, 'Section one content', 'S1 summary'),
                    ($1, 's2', 'S2', 'general', 2, 'Section two content', 'S2 summary')
                """,
                pid,
            )
            chat_id = await pool.fetchval(
                """
                INSERT INTO project_chats (project_id)
                VALUES ($1)
                RETURNING id
                """,
                pid,
            )
            await pool.execute(
                """
                INSERT INTO chat_messages (chat_id, role, content, metadata)
                VALUES ($1, 'user', 'Generate PRD', '{}'::jsonb)
                """,
                chat_id,
            )

            resp = await ui_client.get("/api/projects/chat-backfill")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["dependencies"]) == 1
            assert len(data["changelog"]) >= 2

    async def test_section_detail(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit/sections/data-model")
        assert resp.status_code == 200
        data = resp.json()
        assert "section" in data
        assert data["section"]["slug"] == "data-model"
        assert "depends_on" in data
        assert "depended_by" in data
        assert "revisions" in data

    async def test_section_not_found(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit/sections/nope")
        assert resp.status_code == 404

    async def test_export(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit/export")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        assert "# SnapHabit" in resp.text

    async def test_health(self, ui_client):
        resp = await ui_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["db"] == "connected"

    async def test_global_comments(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit/comments")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_global_comments_project_not_found(self, ui_client):
        resp = await ui_client.get("/api/projects/nonexistent/comments")
        assert resp.status_code == 404

    async def test_section_includes_comments(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit/sections/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "comments" in data
        assert isinstance(data["comments"], list)


class TestInlineComments:
    """Each test creates its own comment to avoid cleanup interference."""

    async def _create_comment(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/snaphabit/sections/overview/comments",
            json={
                "anchor_text": "mobile habit-tracking application",
                "anchor_prefix": "SnapHabit is a **",
                "anchor_suffix": "** that combines",
                "body": "Clarify target audience",
            },
        )
        assert resp.status_code == 200
        return resp.json()

    async def test_create_comment(self, ui_client):
        data = await self._create_comment(ui_client)
        assert data["anchor_text"] == "mobile habit-tracking application"
        assert data["body"] == "Clarify target audience"
        assert data["resolved"] is False
        assert "id" in data

    async def test_comment_appears_in_section(self, ui_client):
        created = await self._create_comment(ui_client)
        resp = await ui_client.get("/api/projects/snaphabit/sections/overview")
        data = resp.json()
        ids = [c["id"] for c in data["comments"]]
        assert created["id"] in ids

    async def test_resolve_comment(self, ui_client):
        created = await self._create_comment(ui_client)
        resp = await ui_client.post(
            f"/api/projects/snaphabit/sections/overview/comments/{created['id']}/resolve"
        )
        assert resp.status_code == 200
        assert resp.json()["resolved"] is True

    async def test_resolve_then_reopen(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        await ui_client.post(f"/api/projects/snaphabit/sections/overview/comments/{cid}/resolve")
        resp = await ui_client.post(f"/api/projects/snaphabit/sections/overview/comments/{cid}/resolve")
        assert resp.status_code == 200
        assert resp.json()["resolved"] is False

    async def test_delete_comment(self, ui_client):
        created = await self._create_comment(ui_client)
        resp = await ui_client.request(
            "DELETE",
            f"/api/projects/snaphabit/sections/overview/comments/{created['id']}",
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    async def test_delete_nonexistent_comment(self, ui_client):
        resp = await ui_client.request(
            "DELETE",
            "/api/projects/snaphabit/sections/overview/comments/00000000-0000-0000-0000-000000000000",
        )
        assert resp.status_code == 404

    async def test_comment_appears_in_global(self, ui_client):
        created = await self._create_comment(ui_client)
        resp = await ui_client.get("/api/projects/snaphabit/comments")
        data = resp.json()
        ids = [c["id"] for c in data]
        assert created["id"] in ids
        # Global comments include section info
        match = next(c for c in data if c["id"] == created["id"])
        assert "section_slug" in match
        assert "section_title" in match

    async def test_create_comment_section_not_found(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/snaphabit/sections/nonexistent/comments",
            json={"anchor_text": "test", "body": "test"},
        )
        assert resp.status_code == 404


class TestCommentRepliesUI:
    async def _create_comment(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/snaphabit/sections/overview/comments",
            json={
                "anchor_text": "mobile habit-tracking application",
                "anchor_prefix": "SnapHabit is a **",
                "anchor_suffix": "** that combines",
                "body": "Test comment for replies",
            },
        )
        return resp.json()

    async def test_post_reply(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        resp = await ui_client.post(
            f"/api/projects/snaphabit/sections/overview/comments/{cid}/replies",
            json={"body": "My reply"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["author"] == "user"
        assert data["body"] == "My reply"

    async def test_replies_in_section_detail(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        await ui_client.post(
            f"/api/projects/snaphabit/sections/overview/comments/{cid}/replies",
            json={"body": "Nested reply"},
        )
        resp = await ui_client.get("/api/projects/snaphabit/sections/overview")
        data = resp.json()
        comment = next(c for c in data["comments"] if c["id"] == cid)
        assert len(comment["replies"]) == 1
        assert comment["replies"][0]["body"] == "Nested reply"


class TestSettingsUI:
    async def test_get_defaults(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["claude_comment_replies"] is True
        assert data["chat_provider"] in {"claude_cli", "anthropic_api"}

    async def test_put_get_roundtrip(self, ui_client):
        resp = await ui_client.put(
            "/api/projects/snaphabit/settings",
            json={"claude_comment_replies": False, "chat_provider": "anthropic_api"},
        )
        assert resp.status_code == 200
        assert resp.json()["claude_comment_replies"] is False
        assert resp.json()["chat_provider"] == "anthropic_api"
        # Verify via GET
        resp2 = await ui_client.get("/api/projects/snaphabit/settings")
        assert resp2.json()["claude_comment_replies"] is False
        assert resp2.json()["chat_provider"] == "anthropic_api"

    async def test_invalid_setting(self, ui_client):
        resp = await ui_client.put(
            "/api/projects/snaphabit/settings",
            json={"unknown_key": True},
        )
        assert resp.status_code == 400

        resp2 = await ui_client.put(
            "/api/projects/snaphabit/settings",
            json={"chat_provider": "invalid_provider"},
        )
        assert resp2.status_code == 400

    async def test_settings_404_nonexistent_project(self, ui_client):
        resp = await ui_client.get("/api/projects/nonexistent/settings")
        assert resp.status_code == 404


class TestOwnershipFix:
    async def _create_comment(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/snaphabit/sections/overview/comments",
            json={"anchor_text": "mobile habit-tracking", "body": "Ownership test"},
        )
        return resp.json()

    async def test_resolve_wrong_project(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        # Try to resolve via a different section
        resp = await ui_client.post(
            f"/api/projects/snaphabit/sections/data-model/comments/{cid}/resolve"
        )
        assert resp.status_code == 404

    async def test_delete_wrong_section(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        resp = await ui_client.request(
            "DELETE",
            f"/api/projects/snaphabit/sections/data-model/comments/{cid}",
        )
        assert resp.status_code == 404

    async def test_reply_wrong_section(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        resp = await ui_client.post(
            f"/api/projects/snaphabit/sections/data-model/comments/{cid}/replies",
            json={"body": "Wrong section reply"},
        )
        assert resp.status_code == 404


class TestChatGateDisabled:
    """Chat endpoints return 403 when chat_enabled is false (default)."""

    async def test_chat_enabled_default_false(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("chat_enabled") is not True

    async def test_chat_messages_returns_403_when_disabled(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit/chat/messages")
        assert resp.status_code == 403

    async def test_chat_stream_returns_403_when_disabled(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/snaphabit/chat/stream",
            json={"message": "hello"},
        )
        assert resp.status_code == 403

    async def test_chat_clear_returns_403_when_disabled(self, ui_client):
        resp = await ui_client.post("/api/projects/snaphabit/chat/clear")
        assert resp.status_code == 403

    async def test_chat_approve_returns_403_when_disabled(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/snaphabit/chat/approve",
            json={"assistant_message_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 403


class TestChatGateEnabled:
    """Verify chat can be toggled on."""

    async def test_chat_enabled_toggle(self, ui_client):
        resp = await ui_client.put(
            "/api/projects/snaphabit/settings",
            json={"chat_enabled": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chat_enabled"] is True

    async def test_chat_messages_returns_200_when_enabled(self, ui_client):
        await ui_client.put(
            "/api/projects/snaphabit/settings",
            json={"chat_enabled": True},
        )
        resp = await ui_client.get("/api/projects/snaphabit/chat/messages")
        assert resp.status_code == 200

    async def test_chat_clear_returns_200_when_enabled(self, ui_client):
        await ui_client.put(
            "/api/projects/snaphabit/settings",
            json={"chat_enabled": True},
        )
        resp = await ui_client.post("/api/projects/snaphabit/chat/clear")
        assert resp.status_code == 200


class TestApprovalToolsParity:
    """APPROVAL_ALLOWED_TOOLS must be derived from CHAT_ALLOWED_MCP_TOOLS."""

    async def test_approval_tools_derived_from_chat_tools(self):
        import app as ui_app

        expected = {f"mcp__prd-forge__{k}" for k in ui_app.CHAT_ALLOWED_MCP_TOOLS}
        assert ui_app.APPROVAL_ALLOWED_TOOLS == expected


class TestChatUI:
    @pytest_asyncio.fixture(autouse=True)
    async def enable_chat(self, ui_client):
        """Enable chat for all tests in this class."""
        resp = await ui_client.put(
            "/api/projects/snaphabit/settings",
            json={"chat_enabled": True},
        )
        assert resp.status_code == 200

    async def test_chat_messages_empty(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit/chat/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["messages"] == []

    async def test_chat_messages_project_not_found(self, ui_client):
        resp = await ui_client.get("/api/projects/nonexistent/chat/messages")
        assert resp.status_code == 404

    async def test_chat_stream_requires_message(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/snaphabit/chat/stream",
            json={"message": "   "},
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "message required"

    async def test_chat_stream_invalid_json(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/snaphabit/chat/stream",
            content="not-json",
            headers={"content-type": "text/plain"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "invalid JSON body"

    async def test_chat_stream_rejects_invalid_attachments_payload(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/snaphabit/chat/stream",
            json={"message": "Analyze", "attachments": {"name": "file.txt"}},
        )
        assert resp.status_code == 400
        assert "attachments" in resp.json()["error"]

    async def test_chat_stream_and_persisted_transcript(self, ui_client, monkeypatch):
        import app as ui_app

        async def fake_agent(project_slug, history, user_message):
            assert project_slug == "snaphabit"
            assert user_message == "Summarize project"
            return (
                "Here is a short summary.",
                [{"name": "prd_get_overview", "result": {"ok": True}}],
            )

        monkeypatch.setattr(ui_app, "_run_chat_agent_turn", fake_agent)

        stream_resp = await ui_client.post(
            "/api/projects/snaphabit/chat/stream",
            json={"message": "Summarize project"},
        )
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers["content-type"]
        assert "event: delta" in stream_resp.text
        assert "event: done" in stream_resp.text

        transcript_resp = await ui_client.get("/api/projects/snaphabit/chat/messages")
        assert transcript_resp.status_code == 200
        messages = transcript_resp.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Summarize project"
        assert messages[1]["role"] == "assistant"
        assert "short summary" in messages[1]["content"]

    async def test_chat_stream_with_selection_context(self, ui_client, monkeypatch):
        import app as ui_app

        async def fake_agent(project_slug, history, user_message):
            assert project_slug == "snaphabit"
            assert "Clarify this" in user_message
            assert "Selected context from PRD Forge Web UI" in user_message
            assert "Section: User Onboarding" in user_message
            assert "Selected text:" in user_message
            assert "Use this selected context" in user_message
            return ("Context received.", [])

        monkeypatch.setattr(ui_app, "_run_chat_agent_turn", fake_agent)

        stream_resp = await ui_client.post(
            "/api/projects/snaphabit/chat/stream",
            json={
                "message": "Clarify this",
                "selection_context": {
                    "section_slug": "user-onboarding",
                    "section_title": "User Onboarding",
                    "selected_text": "Users should complete setup in under 90 seconds.",
                    "anchor_prefix": "Goal: ",
                    "anchor_suffix": " for activation",
                },
            },
        )
        assert stream_resp.status_code == 200
        assert "event: done" in stream_resp.text

        transcript_resp = await ui_client.get("/api/projects/snaphabit/chat/messages")
        assert transcript_resp.status_code == 200
        messages = transcript_resp.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Clarify this"
        assert messages[0]["metadata"]["selection_context"]["section_slug"] == "user-onboarding"
        assert messages[0]["metadata"]["selection_context"]["selected_text"].startswith("Users should")
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Context received."

    async def test_chat_stream_with_attachments(self, ui_client, monkeypatch):
        import app as ui_app

        async def fake_agent(project_slug, history, user_message):
            assert project_slug == "snaphabit"
            assert "Please review attached files." in user_message
            assert "[Attached files from PRD Forge Web UI]" in user_message
            assert "File: release-notes.txt" in user_message
            assert "MVP scope" in user_message
            return ("Attachment received.", [])

        monkeypatch.setattr(ui_app, "_run_chat_agent_turn", fake_agent)

        stream_resp = await ui_client.post(
            "/api/projects/snaphabit/chat/stream",
            json={
                "message": "",
                "attachments": [
                    {
                        "name": "release-notes.txt",
                        "mime_type": "text/plain",
                        "size_bytes": 28,
                        "content_text": "MVP scope\n- chat attachments",
                    }
                ],
            },
        )
        assert stream_resp.status_code == 200
        assert "event: done" in stream_resp.text

        transcript_resp = await ui_client.get("/api/projects/snaphabit/chat/messages")
        assert transcript_resp.status_code == 200
        messages = transcript_resp.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Please review attached files."
        assert len(messages[0]["metadata"]["attachments"]) == 1
        assert messages[0]["metadata"]["attachments"][0]["name"] == "release-notes.txt"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Attachment received."

    async def test_chat_clear(self, ui_client, monkeypatch):
        import app as ui_app

        async def fake_agent(project_slug, history, user_message):
            return ("Done", [])

        monkeypatch.setattr(ui_app, "_run_chat_agent_turn", fake_agent)

        await ui_client.post(
            "/api/projects/snaphabit/chat/stream",
            json={"message": "hello"},
        )
        before = await ui_client.get("/api/projects/snaphabit/chat/messages")
        assert len(before.json()["messages"]) == 2

        clear_resp = await ui_client.post("/api/projects/snaphabit/chat/clear")
        assert clear_resp.status_code == 200
        assert clear_resp.json()["ok"] is True

        after = await ui_client.get("/api/projects/snaphabit/chat/messages")
        assert after.status_code == 200
        assert after.json()["messages"] == []

    async def test_chat_approve_continues_blocked_turn(self, ui_client, monkeypatch):
        import app as ui_app

        pool = ui_app.pool
        pid = await pool.fetchval("SELECT id FROM projects WHERE slug='snaphabit'")
        chat_id = await pool.fetchval(
            """
            INSERT INTO project_chats (project_id)
            VALUES ($1)
            ON CONFLICT (project_id)
            DO UPDATE SET updated_at = now()
            RETURNING id
            """,
            pid,
        )

        await pool.execute(
            """
            INSERT INTO chat_messages (chat_id, role, content, metadata, created_at)
            VALUES ($1, 'user', 'Please update notes', '{}'::jsonb, now() - interval '1 second')
            """,
            chat_id,
        )

        approval_metadata = {
            "provider": "claude_cli",
            "approval_requests": [
                {
                    "kind": "manual_approval_required",
                    "tool": "prd_update_section",
                    "message": "Permission required",
                }
            ],
            "approval_resolved": False,
        }
        approval_row = await pool.fetchrow(
            """
            INSERT INTO chat_messages (chat_id, role, content, metadata, created_at)
            VALUES ($1, 'assistant', 'Permission required', $2::jsonb, now())
            RETURNING id
            """,
            chat_id,
            json.dumps(approval_metadata),
        )

        async def fake_cli_stream(
            project_slug,
            history,
            user_message,
            permission_mode_override=None,
            allowed_tools_override=None,
        ):
            assert project_slug == "snaphabit"
            assert permission_mode_override == "acceptEdits"
            assert isinstance(allowed_tools_override, list)
            assert "mcp__prd-forge__prd_update_section" in allowed_tools_override
            assert "Please update notes" in user_message
            yield {
                "type": "tool",
                "tool": {"name": "mcp__prd-forge__prd_update_section", "input": {"section": "tech-stack"}},
            }
            yield {"type": "delta", "text": "Applied update."}
            yield {"type": "done", "text": "Applied update."}

        monkeypatch.setattr(ui_app, "_claude_cli_turn_stream", fake_cli_stream)

        resp = await ui_client.post(
            "/api/projects/snaphabit/chat/approve",
            json={"assistant_message_id": str(approval_row["id"])},
        )
        assert resp.status_code == 200
        assert "event: done" in resp.text
        assert "Applied update." in resp.text

        transcript_resp = await ui_client.get("/api/projects/snaphabit/chat/messages")
        messages = transcript_resp.json()["messages"]
        assert messages[-1]["role"] == "assistant"
        assert messages[-1]["content"] == "Applied update."
        assert messages[-1]["metadata"]["approval_for_message_id"] == str(approval_row["id"])

        approval_msg = next(m for m in messages if m["id"] == str(approval_row["id"]))
        assert approval_msg["metadata"]["approval_resolved"] is True

    async def test_chat_approve_rejects_message_without_approval(self, ui_client):
        import app as ui_app

        pool = ui_app.pool
        pid = await pool.fetchval("SELECT id FROM projects WHERE slug='snaphabit'")
        chat_id = await pool.fetchval(
            """
            INSERT INTO project_chats (project_id)
            VALUES ($1)
            ON CONFLICT (project_id)
            DO UPDATE SET updated_at = now()
            RETURNING id
            """,
            pid,
        )
        plain_assistant = await pool.fetchrow(
            """
            INSERT INTO chat_messages (chat_id, role, content, metadata)
            VALUES ($1, 'assistant', 'No approval here', '{}'::jsonb)
            RETURNING id
            """,
            chat_id,
        )

        resp = await ui_client.post(
            "/api/projects/snaphabit/chat/approve",
            json={"assistant_message_id": str(plain_assistant["id"])},
        )
        assert resp.status_code == 400
        assert "approval" in resp.json()["error"]


class TestTokenStats:
    async def test_token_stats_success(self, ui_client):
        import app as ui_app
        pool = ui_app.pool
        pid = await pool.fetchval("SELECT id FROM projects WHERE slug='snaphabit'")
        await pool.execute(
            "INSERT INTO token_estimates (project_id, operation, full_doc_tokens, loaded_tokens) "
            "VALUES ($1, 'read_section', 15000, 1200), ($1, 'read_section', 15000, 800)",
            pid,
        )
        resp = await ui_client.get("/api/projects/snaphabit/token-stats")
        assert resp.status_code == 200
        d = resp.json()
        assert d["operations"] == 2
        assert d["total_full_doc_tokens"] == 30000
        assert d["total_loaded_tokens"] == 2000
        assert d["total_saved_tokens"] == 28000
        assert d["savings_percent"] == 93.3
        assert d["project_stats"]["sections"] >= 12
        assert d["project_stats"]["dependencies"] >= 1
        assert d["project_stats"]["revisions"] >= 0
        assert len(d["by_operation"]) >= 1
        ops = {o["operation"]: o for o in d["by_operation"]}
        assert ops["read_section"]["count"] == 2
        assert len(d["daily_trend"]) == 7
        days = [e["day"] for e in d["daily_trend"]]
        assert days == sorted(days)
        # At least one day with zero
        assert any(e["operations"] == 0 and e["tokens_saved"] == 0 for e in d["daily_trend"])

    async def test_token_stats_not_found(self, ui_client):
        resp = await ui_client.get("/api/projects/nonexistent/token-stats")
        assert resp.status_code == 404

    async def test_token_stats_empty(self, ui_client):
        resp = await ui_client.get("/api/projects/snaphabit/token-stats")
        assert resp.status_code == 200
        d = resp.json()
        assert d["operations"] == 0
        assert d["total_full_doc_tokens"] == 0
        assert d["total_loaded_tokens"] == 0
        assert d["total_saved_tokens"] == 0
        assert d["savings_percent"] == 0
        assert d["project_stats"]["sections"] >= 12
        assert d["project_stats"]["dependencies"] >= 1
        assert d["project_stats"]["revisions"] >= 0
        assert len(d["daily_trend"]) == 7
        assert all(e["operations"] == 0 and e["tokens_saved"] == 0 for e in d["daily_trend"])
        days = [e["day"] for e in d["daily_trend"]]
        assert days == sorted(days)
