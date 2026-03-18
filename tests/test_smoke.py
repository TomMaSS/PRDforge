"""Smoke / CI contract tests — requires full Docker stack running.

Run with: docker compose up -d && pytest tests/test_smoke.py -v
"""

import httpx
import pytest

MCP_URL = "http://localhost:8080"
API_URL = "http://localhost:8088"
FRONTEND_URL = "http://localhost:3000"


@pytest.fixture(scope="session")
def http_client():
    with httpx.Client(timeout=10) as client:
        yield client


class TestMCPLiveness:
    def test_mcp_port_open(self, http_client):
        """MCP server responds on port 8080."""
        resp = http_client.post(
            f"{MCP_URL}/mcp/",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke-test", "version": "0.1"}
            }},
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            follow_redirects=True,
        )
        assert resp.status_code == 200


class TestDBReadiness:
    def test_api_health_endpoint(self, http_client):
        """Python API /health endpoint confirms DB connection."""
        resp = http_client.get(f"{API_URL}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["db"] == "connected"


class TestAPIEndpoints:
    def test_api_projects(self, http_client):
        resp = http_client.get(f"{API_URL}/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestSeedData:
    def test_snaphabit_project_exists(self, http_client):
        resp = http_client.get(f"{API_URL}/api/projects/snaphabit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["slug"] == "snaphabit"
        assert data["stats"]["sections"] >= 10

    def test_seed_sections_have_content(self, http_client):
        resp = http_client.get(f"{API_URL}/api/projects/snaphabit/sections/data-model")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["section"]["content"]) > 100

    def test_seed_dependencies_exist(self, http_client):
        resp = http_client.get(f"{API_URL}/api/projects/snaphabit")
        assert resp.status_code == 200
        assert len(resp.json()["dependencies"]) >= 5

    def test_export_produces_markdown(self, http_client):
        resp = http_client.get(f"{API_URL}/api/projects/snaphabit/export")
        assert resp.status_code == 200
        assert "# SnapHabit" in resp.text
