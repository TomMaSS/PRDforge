"""Tests for FastAPI UI endpoints."""

import json


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
        assert any(p["slug"] == "contentforge" for p in data)

    async def test_project_detail(self, ui_client):
        resp = await ui_client.get("/api/projects/contentforge")
        assert resp.status_code == 200
        data = resp.json()
        assert "project" in data
        assert "stats" in data
        assert "sections" in data
        assert "dependencies" in data
        assert "changelog" in data
        assert data["stats"]["sections"] == 13

    async def test_project_not_found(self, ui_client):
        resp = await ui_client.get("/api/projects/nonexistent")
        assert resp.status_code == 404

    async def test_section_detail(self, ui_client):
        resp = await ui_client.get("/api/projects/contentforge/sections/data-model")
        assert resp.status_code == 200
        data = resp.json()
        assert "section" in data
        assert data["section"]["slug"] == "data-model"
        assert "depends_on" in data
        assert "depended_by" in data
        assert "revisions" in data

    async def test_section_not_found(self, ui_client):
        resp = await ui_client.get("/api/projects/contentforge/sections/nope")
        assert resp.status_code == 404

    async def test_export(self, ui_client):
        resp = await ui_client.get("/api/projects/contentforge/export")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        assert "# ContentForge" in resp.text

    async def test_health(self, ui_client):
        resp = await ui_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["db"] == "connected"

    async def test_global_comments(self, ui_client):
        resp = await ui_client.get("/api/projects/contentforge/comments")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_global_comments_project_not_found(self, ui_client):
        resp = await ui_client.get("/api/projects/nonexistent/comments")
        assert resp.status_code == 404

    async def test_section_includes_comments(self, ui_client):
        resp = await ui_client.get("/api/projects/contentforge/sections/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "comments" in data
        assert isinstance(data["comments"], list)


class TestInlineComments:
    """Each test creates its own comment to avoid cleanup interference."""

    async def _create_comment(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/contentforge/sections/overview/comments",
            json={
                "anchor_text": "AI-powered content creation",
                "anchor_prefix": "ContentForge is an ",
                "anchor_suffix": " platform",
                "body": "Clarify target audience",
            },
        )
        assert resp.status_code == 200
        return resp.json()

    async def test_create_comment(self, ui_client):
        data = await self._create_comment(ui_client)
        assert data["anchor_text"] == "AI-powered content creation"
        assert data["body"] == "Clarify target audience"
        assert data["resolved"] is False
        assert "id" in data

    async def test_comment_appears_in_section(self, ui_client):
        created = await self._create_comment(ui_client)
        resp = await ui_client.get("/api/projects/contentforge/sections/overview")
        data = resp.json()
        ids = [c["id"] for c in data["comments"]]
        assert created["id"] in ids

    async def test_resolve_comment(self, ui_client):
        created = await self._create_comment(ui_client)
        resp = await ui_client.post(
            f"/api/projects/contentforge/sections/overview/comments/{created['id']}/resolve"
        )
        assert resp.status_code == 200
        assert resp.json()["resolved"] is True

    async def test_resolve_then_reopen(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        await ui_client.post(f"/api/projects/contentforge/sections/overview/comments/{cid}/resolve")
        resp = await ui_client.post(f"/api/projects/contentforge/sections/overview/comments/{cid}/resolve")
        assert resp.status_code == 200
        assert resp.json()["resolved"] is False

    async def test_delete_comment(self, ui_client):
        created = await self._create_comment(ui_client)
        resp = await ui_client.request(
            "DELETE",
            f"/api/projects/contentforge/sections/overview/comments/{created['id']}",
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    async def test_delete_nonexistent_comment(self, ui_client):
        resp = await ui_client.request(
            "DELETE",
            "/api/projects/contentforge/sections/overview/comments/00000000-0000-0000-0000-000000000000",
        )
        assert resp.status_code == 404

    async def test_comment_appears_in_global(self, ui_client):
        created = await self._create_comment(ui_client)
        resp = await ui_client.get("/api/projects/contentforge/comments")
        data = resp.json()
        ids = [c["id"] for c in data]
        assert created["id"] in ids
        # Global comments include section info
        match = next(c for c in data if c["id"] == created["id"])
        assert "section_slug" in match
        assert "section_title" in match

    async def test_create_comment_section_not_found(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/contentforge/sections/nonexistent/comments",
            json={"anchor_text": "test", "body": "test"},
        )
        assert resp.status_code == 404


class TestCommentRepliesUI:
    async def _create_comment(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/contentforge/sections/overview/comments",
            json={
                "anchor_text": "AI-powered content creation",
                "anchor_prefix": "ContentForge is an ",
                "anchor_suffix": " platform",
                "body": "Test comment for replies",
            },
        )
        return resp.json()

    async def test_post_reply(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        resp = await ui_client.post(
            f"/api/projects/contentforge/sections/overview/comments/{cid}/replies",
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
            f"/api/projects/contentforge/sections/overview/comments/{cid}/replies",
            json={"body": "Nested reply"},
        )
        resp = await ui_client.get("/api/projects/contentforge/sections/overview")
        data = resp.json()
        comment = next(c for c in data["comments"] if c["id"] == cid)
        assert len(comment["replies"]) == 1
        assert comment["replies"][0]["body"] == "Nested reply"


class TestSettingsUI:
    async def test_get_defaults(self, ui_client):
        resp = await ui_client.get("/api/projects/contentforge/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["claude_comment_replies"] is True

    async def test_put_get_roundtrip(self, ui_client):
        resp = await ui_client.put(
            "/api/projects/contentforge/settings",
            json={"claude_comment_replies": False},
        )
        assert resp.status_code == 200
        assert resp.json()["claude_comment_replies"] is False
        # Verify via GET
        resp2 = await ui_client.get("/api/projects/contentforge/settings")
        assert resp2.json()["claude_comment_replies"] is False

    async def test_invalid_setting(self, ui_client):
        resp = await ui_client.put(
            "/api/projects/contentforge/settings",
            json={"unknown_key": True},
        )
        assert resp.status_code == 400

    async def test_settings_404_nonexistent_project(self, ui_client):
        resp = await ui_client.get("/api/projects/nonexistent/settings")
        assert resp.status_code == 404


class TestOwnershipFix:
    async def _create_comment(self, ui_client):
        resp = await ui_client.post(
            "/api/projects/contentforge/sections/overview/comments",
            json={"anchor_text": "AI-powered", "body": "Ownership test"},
        )
        return resp.json()

    async def test_resolve_wrong_project(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        # Try to resolve via a different section
        resp = await ui_client.post(
            f"/api/projects/contentforge/sections/data-model/comments/{cid}/resolve"
        )
        assert resp.status_code == 404

    async def test_delete_wrong_section(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        resp = await ui_client.request(
            "DELETE",
            f"/api/projects/contentforge/sections/data-model/comments/{cid}",
        )
        assert resp.status_code == 404

    async def test_reply_wrong_section(self, ui_client):
        created = await self._create_comment(ui_client)
        cid = created["id"]
        resp = await ui_client.post(
            f"/api/projects/contentforge/sections/data-model/comments/{cid}/replies",
            json={"body": "Wrong section reply"},
        )
        assert resp.status_code == 404
