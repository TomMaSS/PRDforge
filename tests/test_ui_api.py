"""Tests for FastAPI UI endpoints."""

import json

import pytest

pytestmark = pytest.mark.asyncio


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
