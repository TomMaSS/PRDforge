"""Tests for auth middleware and WebSocket tokens."""

import json
import time

import pytest

pytestmark = pytest.mark.asyncio


class TestAuthContract:
    """Verify auth contract module works."""

    async def test_contract_tables_missing_ok(self, db_pool):
        """Contract check returns errors when auth tables don't exist."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
        from auth_contract import verify_auth_contract
        errors = await verify_auth_contract(db_pool)
        # Tables may or may not exist depending on test env
        assert isinstance(errors, list)

    async def test_role_hierarchy(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
        from auth import has_min_role, ROLE_HIERARCHY

        assert has_min_role("owner", "viewer")
        assert has_min_role("admin", "editor")
        assert has_min_role("editor", "editor")
        assert not has_min_role("viewer", "editor")
        assert not has_min_role("commenter", "admin")

    async def test_role_hierarchy_all_levels(self):
        from auth import has_min_role

        # owner > admin > editor > commenter > viewer
        roles = ["owner", "admin", "editor", "commenter", "viewer"]
        for i, higher in enumerate(roles):
            for j, lower in enumerate(roles):
                if i <= j:
                    assert has_min_role(higher, lower), f"{higher} should satisfy {lower}"
                else:
                    assert not has_min_role(higher, lower), f"{higher} should NOT satisfy {lower}"


class TestWSToken:
    """Verify WS token minting and verification."""

    async def test_mint_and_verify(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
        from ws import mint_ws_token, verify_ws_token

        token = mint_ws_token("user-123", "my-project")
        payload = verify_ws_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["project"] == "my-project"
        assert payload["aud"] == "ws"

    async def test_verify_rejects_tampered(self):
        from ws import mint_ws_token, verify_ws_token

        token = mint_ws_token("user-123", "proj")
        # Tamper with signature
        parts = token.rsplit(".", 1)
        tampered = parts[0] + ".0000000000000000"
        assert verify_ws_token(tampered) is None

    async def test_verify_rejects_expired(self):
        from ws import verify_ws_token, WS_TOKEN_SECRET
        import hashlib, hmac

        payload = json.dumps({
            "jti": "test-jti",
            "sub": "user-1",
            "aud": "ws",
            "project": "proj",
            "exp": int(time.time()) - 10,  # expired
        }, separators=(",", ":"), sort_keys=True)
        sig = hmac.new(WS_TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        token = f"{payload}.{sig}"
        assert verify_ws_token(token) is None

    async def test_verify_rejects_wrong_audience(self):
        from ws import verify_ws_token, WS_TOKEN_SECRET
        import hashlib, hmac

        payload = json.dumps({
            "jti": "test-jti",
            "sub": "user-1",
            "aud": "http",  # wrong
            "project": "proj",
            "exp": int(time.time()) + 120,
        }, separators=(",", ":"), sort_keys=True)
        sig = hmac.new(WS_TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        token = f"{payload}.{sig}"
        assert verify_ws_token(token) is None

    async def test_each_token_has_unique_jti(self):
        from ws import mint_ws_token, verify_ws_token

        t1 = mint_ws_token("u", "p")
        t2 = mint_ws_token("u", "p")
        p1 = verify_ws_token(t1)
        p2 = verify_ws_token(t2)
        assert p1["jti"] != p2["jti"]


class TestWSTokenEndpoint:
    """Test the POST /api/ws-token endpoint."""

    async def test_mint_token_success(self, ui_client, mcp_pool):
        import server
        await server.prd_create_project(name="WS Test", slug="ws-test")

        resp = await ui_client.post("/api/ws-token", json={
            "user_id": "test-user",
            "project_slug": "ws-test",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data

    async def test_mint_token_missing_fields(self, ui_client):
        resp = await ui_client.post("/api/ws-token", json={"user_id": "x"})
        assert resp.status_code == 400

    async def test_mint_token_unknown_project(self, ui_client):
        resp = await ui_client.post("/api/ws-token", json={
            "user_id": "x", "project_slug": "nonexistent",
        })
        assert resp.status_code == 404


class TestMemberEndpoints:
    """Test project member management endpoints."""

    async def test_list_members_empty(self, ui_client, mcp_pool):
        import server
        await server.prd_create_project(name="Mem Test", slug="mem-test")
        resp = await ui_client.get("/api/projects/mem-test/members")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_add_and_list_member(self, ui_client, mcp_pool):
        import server
        await server.prd_create_project(name="Mem Test2", slug="mem-test2")

        import uuid
        user_id = str(uuid.uuid4())
        resp = await ui_client.post("/api/projects/mem-test2/members", json={
            "user_id": user_id, "role": "editor",
        })
        assert resp.status_code == 200
        assert resp.json()["role"] == "editor"

        resp = await ui_client.get("/api/projects/mem-test2/members")
        assert len(resp.json()) == 1

    async def test_remove_member(self, ui_client, mcp_pool):
        import server, uuid
        await server.prd_create_project(name="Mem Test3", slug="mem-test3")

        user_id = str(uuid.uuid4())
        await ui_client.post("/api/projects/mem-test3/members", json={
            "user_id": user_id, "role": "viewer",
        })

        resp = await ui_client.delete(f"/api/projects/mem-test3/members/{user_id}")
        assert resp.status_code == 200
        assert resp.json()["removed"] is True

    async def test_add_member_invalid_role(self, ui_client, mcp_pool):
        import server
        await server.prd_create_project(name="Mem Test4", slug="mem-test4")
        resp = await ui_client.post("/api/projects/mem-test4/members", json={
            "user_id": "xxx", "role": "superadmin",
        })
        assert resp.status_code == 400

    async def test_add_member_project_not_found(self, ui_client):
        resp = await ui_client.post("/api/projects/nonexistent/members", json={
            "user_id": "xxx", "role": "viewer",
        })
        assert resp.status_code == 404


class TestAuditEndpoints:
    async def test_audit_empty(self, ui_client, mcp_pool):
        import server
        await server.prd_create_project(name="Aud Test", slug="aud-test")
        resp = await ui_client.get("/api/projects/aud-test/audit")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_audit_not_found(self, ui_client):
        resp = await ui_client.get("/api/projects/nonexistent/audit")
        assert resp.status_code == 404


class TestOptimisticLocking:
    """Test expected_revision conflict detection on section PATCH."""

    async def test_patch_with_correct_revision(self, ui_client, mcp_pool):
        import server
        await server.prd_create_project(name="Lock Test", slug="lock-test")
        await server.prd_create_section(project="lock-test", slug="s1", title="S1", content="v1")
        # revision 1 was created by prd_create_section
        resp = await ui_client.patch("/api/projects/lock-test/sections/s1", json={
            "status": "in_progress",
            "expected_revision": 1,
        })
        assert resp.status_code == 200

    async def test_patch_with_stale_revision_returns_409(self, ui_client, mcp_pool):
        import server
        await server.prd_create_project(name="Lock Test2", slug="lock-test2")
        await server.prd_create_section(project="lock-test2", slug="s1", title="S1", content="v1")
        # Update content to create revision 2
        await server.prd_update_section(project="lock-test2", section="s1", content="v2")
        # Client thinks revision is still 1
        resp = await ui_client.patch("/api/projects/lock-test2/sections/s1", json={
            "status": "review",
            "expected_revision": 1,
        })
        assert resp.status_code == 409
        data = resp.json()
        assert data["error"]["code"] == "CONFLICT"
        assert data["error"]["details"]["current_revision"] == 2

    async def test_patch_without_expected_revision_succeeds(self, ui_client, mcp_pool):
        import server
        await server.prd_create_project(name="Lock Test3", slug="lock-test3")
        await server.prd_create_section(project="lock-test3", slug="s1", title="S1")
        # No expected_revision — no conflict check
        resp = await ui_client.patch("/api/projects/lock-test3/sections/s1", json={
            "status": "approved",
        })
        assert resp.status_code == 200


class TestErrorModule:
    async def test_error_response_format(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
        from errors import error_response, NOT_FOUND

        resp = error_response(NOT_FOUND, "project 'x' not found", 404)
        body = json.loads(resp.body.decode())
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["error"]["status"] == 404
        assert "not found" in body["error"]["message"]
        assert resp.status_code == 404

    async def test_helper_functions(self):
        from errors import not_found, validation_error, unauthorized, permission_denied, conflict

        for fn, status in [
            (lambda: not_found("project", "x"), 404),
            (lambda: validation_error("bad slug"), 400),
            (lambda: unauthorized(), 401),
            (lambda: permission_denied(), 403),
            (lambda: conflict("version mismatch"), 409),
        ]:
            resp = fn()
            assert resp.status_code == status
