"""Tests for MCP server tools against real database."""

import asyncio
import json

import pytest
import pytest_asyncio


pytestmark = pytest.mark.asyncio


class TestProjectManagement:
    async def test_list_projects(self, mcp_pool):
        import server
        result = json.loads(await server.prd_list_projects())
        assert isinstance(result, list)
        assert any(p["slug"] == "contentforge" for p in result)

    async def test_create_and_delete_project(self, mcp_pool):
        import server
        # Create
        result = json.loads(await server.prd_create_project(
            name="Test Project", slug="test-proj", description="A test"
        ))
        assert "created" in result
        assert result["created"]["slug"] == "test-proj"

        # Verify it appears in list
        projects = json.loads(await server.prd_list_projects())
        assert any(p["slug"] == "test-proj" for p in projects)

        # Delete
        result = json.loads(await server.prd_delete_project(project="test-proj"))
        assert result["deleted"] == "test-proj"

    async def test_create_duplicate_slug(self, mcp_pool):
        import server
        await server.prd_create_project(name="Dup1", slug="dup-test")
        result = json.loads(await server.prd_create_project(name="Dup2", slug="dup-test"))
        assert "error" in result
        assert "already exists" in result["error"]


class TestSectionCRUD:
    async def test_list_sections(self, mcp_pool):
        import server
        result = json.loads(await server.prd_list_sections(project="contentforge"))
        assert isinstance(result, list)
        assert len(result) == 12

    async def test_read_section_with_deps(self, mcp_pool):
        import server
        result = json.loads(await server.prd_read_section(
            project="contentforge", section="data-model"
        ))
        assert "section" in result
        assert result["section"]["slug"] == "data-model"
        assert "depends_on" in result
        assert "depended_by" in result
        # data-model depends on tech-stack
        dep_slugs = [d["slug"] for d in result["depends_on"]]
        assert "tech-stack" in dep_slugs

    async def test_read_section_not_found(self, mcp_pool):
        import server
        result = json.loads(await server.prd_read_section(
            project="contentforge", section="nonexistent"
        ))
        assert "error" in result

    async def test_create_section(self, mcp_pool):
        import server
        # Create a test project first
        await server.prd_create_project(name="SecTest", slug="sec-test")
        result = json.loads(await server.prd_create_section(
            project="sec-test", slug="intro", title="Introduction",
            content="Hello world", summary="An intro", tags=["test"]
        ))
        assert "created" in result
        assert result["created"]["slug"] == "intro"

    async def test_update_section_with_revision(self, mcp_pool):
        import server
        await server.prd_create_project(name="UpdTest", slug="upd-test")
        await server.prd_create_section(
            project="upd-test", slug="s1", title="Section 1",
            content="Original content", summary="Original summary"
        )
        # Update content — should create revision
        result = json.loads(await server.prd_update_section(
            project="upd-test", section="s1",
            content="Updated content", change_description="Test update"
        ))
        assert "updated" in result
        assert "revision_created" in result
        assert result["revision_created"] == 1

        # Verify revision exists
        revs = json.loads(await server.prd_get_revisions(
            project="upd-test", section="s1"
        ))
        assert len(revs["revisions"]) == 1
        assert revs["revisions"][0]["change_description"] == "Test update"

    async def test_update_section_metadata_only(self, mcp_pool):
        import server
        await server.prd_create_project(name="MetaTest", slug="meta-test")
        await server.prd_create_section(
            project="meta-test", slug="s1", title="Section 1"
        )
        result = json.loads(await server.prd_update_section(
            project="meta-test", section="s1",
            status="approved", tags=["done"]
        ))
        assert "updated" in result
        assert "revision_created" not in result

    async def test_update_section_invalid_status(self, mcp_pool):
        import server
        result = json.loads(await server.prd_update_section(
            project="contentforge", section="vision-and-overview", status="invalid"
        ))
        assert "error" in result

    async def test_update_section_empty(self, mcp_pool):
        import server
        result = json.loads(await server.prd_update_section(
            project="contentforge", section="vision-and-overview"
        ))
        assert "error" in result
        assert "nothing to update" in result["error"]

    async def test_delete_section_with_warning(self, mcp_pool):
        import server
        await server.prd_create_project(name="DelTest", slug="del-test")
        await server.prd_create_section(project="del-test", slug="base", title="Base")
        await server.prd_create_section(project="del-test", slug="child", title="Child")
        await server.prd_add_dependency(
            project="del-test", section="child", depends_on="base"
        )
        result = json.loads(await server.prd_delete_section(
            project="del-test", section="base"
        ))
        assert result["deleted"] == "base"
        assert "warning" in result
        assert "child" in result["affected_sections"]

    async def test_duplicate_section(self, mcp_pool):
        import server
        await server.prd_create_project(name="DupSec", slug="dup-sec")
        await server.prd_create_section(
            project="dup-sec", slug="orig", title="Original",
            content="Some content", tags=["tag1"]
        )
        result = json.loads(await server.prd_duplicate_section(
            project="dup-sec", section="orig", new_slug="copy", new_title="Copy"
        ))
        assert "duplicated" in result
        assert result["from"] == "orig"
        assert result["duplicated"]["title"] == "Copy"


class TestDependencies:
    async def test_add_and_remove_dependency(self, mcp_pool):
        import server
        await server.prd_create_project(name="DepTest", slug="dep-test")
        await server.prd_create_section(project="dep-test", slug="a", title="A")
        await server.prd_create_section(project="dep-test", slug="b", title="B")

        result = json.loads(await server.prd_add_dependency(
            project="dep-test", section="a", depends_on="b",
            dependency_type="implements", description="A implements B"
        ))
        assert "dependency" in result
        assert result["dependency"]["type"] == "implements"

        # Remove
        result = json.loads(await server.prd_remove_dependency(
            project="dep-test", section="a", depends_on="b"
        ))
        assert result["removed"] is True

    async def test_idempotent_add(self, mcp_pool):
        import server
        await server.prd_create_project(name="IdempTest", slug="idemp-test")
        await server.prd_create_section(project="idemp-test", slug="a", title="A")
        await server.prd_create_section(project="idemp-test", slug="b", title="B")

        # Add twice — should not error
        await server.prd_add_dependency(
            project="idemp-test", section="a", depends_on="b"
        )
        result = json.loads(await server.prd_add_dependency(
            project="idemp-test", section="a", depends_on="b",
            dependency_type="blocks", description="Updated"
        ))
        assert "dependency" in result
        assert result["dependency"]["type"] == "blocks"

    async def test_self_dependency_rejected(self, mcp_pool):
        import server
        result = json.loads(await server.prd_add_dependency(
            project="contentforge", section="vision-and-overview", depends_on="vision-and-overview"
        ))
        assert "error" in result

    async def test_cross_project_dependency_rejected(self, mcp_pool):
        import server
        # Create a second project with a section
        await server.prd_create_project(name="Other", slug="other-proj")
        await server.prd_create_section(
            project="other-proj", slug="foreign", title="Foreign Section"
        )
        # Try to create dep between contentforge section and other-proj section
        result = json.loads(await server.prd_add_dependency(
            project="contentforge", section="vision-and-overview", depends_on="foreign"
        ))
        assert "error" in result


class TestContextSearch:
    async def test_overview(self, mcp_pool):
        import server
        result = json.loads(await server.prd_get_overview(project="contentforge"))
        assert "project" in result
        assert "stats" in result
        assert result["stats"]["sections"] == 12
        assert "sections" in result
        assert "dependencies" in result

    async def test_fts_search(self, mcp_pool):
        import server
        result = json.loads(await server.prd_search(
            project="contentforge", query="PostgreSQL"
        ))
        assert "results" in result
        assert len(result["results"]) > 0

    async def test_tag_search(self, mcp_pool):
        import server
        result = json.loads(await server.prd_search(
            project="contentforge", query="tag:backend"
        ))
        assert "tag" in result
        assert result["tag"] == "backend"
        assert len(result["results"]) > 0

    async def test_changelog(self, mcp_pool):
        import server
        result = json.loads(await server.prd_get_changelog(project="contentforge"))
        assert "changelog" in result
        assert "total" in result


class TestRevisions:
    async def test_get_revisions_empty(self, mcp_pool):
        import server
        result = json.loads(await server.prd_get_revisions(
            project="contentforge", section="vision-and-overview"
        ))
        assert result["section"] == "vision-and-overview"
        assert isinstance(result["revisions"], list)

    async def test_read_revision(self, mcp_pool):
        import server
        # Create a section and update it to generate a revision
        await server.prd_create_project(name="RevRead", slug="rev-read")
        await server.prd_create_section(
            project="rev-read", slug="s1", title="S1",
            content="V1 content", summary="V1 summary"
        )
        await server.prd_update_section(
            project="rev-read", section="s1",
            content="V2 content", change_description="Update to v2"
        )
        result = json.loads(await server.prd_read_revision(
            project="rev-read", section="s1", revision=1
        ))
        assert result["content"] == "V1 content"
        assert result["summary"] == "V1 summary"

    async def test_rollback_with_backup(self, mcp_pool):
        import server
        await server.prd_create_project(name="Rollback", slug="rollback-test")
        await server.prd_create_section(
            project="rollback-test", slug="s1", title="S1",
            content="Original", summary="Orig summary"
        )
        # Update twice
        await server.prd_update_section(
            project="rollback-test", section="s1",
            content="V2", change_description="to v2"
        )
        await server.prd_update_section(
            project="rollback-test", section="s1",
            content="V3", change_description="to v3"
        )
        # Rollback to revision 1 (original content)
        result = json.loads(await server.prd_rollback_section(
            project="rollback-test", section="s1", revision=1
        ))
        assert result["rolled_back_to"] == 1
        assert result["backup_revision"] == 3

        # Verify content is restored
        sec = json.loads(await server.prd_read_section(
            project="rollback-test", section="s1"
        ))
        assert sec["section"]["content"] == "Original"


class TestRevisionConcurrency:
    async def test_concurrent_updates_no_collision(self, mcp_pool):
        """Simulate concurrent updates — revision numbers must not collide."""
        import server
        await server.prd_create_project(name="ConcTest", slug="conc-test")
        await server.prd_create_section(
            project="conc-test", slug="s1", title="S1",
            content="Base content"
        )

        async def do_update(i):
            return json.loads(await server.prd_update_section(
                project="conc-test", section="s1",
                content=f"Content v{i}",
                change_description=f"Update {i}"
            ))

        results = await asyncio.gather(*[do_update(i) for i in range(5)])
        rev_numbers = [r["revision_created"] for r in results if "revision_created" in r]
        # All revision numbers should be unique
        assert len(rev_numbers) == len(set(rev_numbers))

    async def test_concurrent_no_content_loss(self, mcp_pool):
        """After concurrent updates, all revisions should be present."""
        import server
        await server.prd_create_project(name="ConcLoss", slug="conc-loss")
        await server.prd_create_section(
            project="conc-loss", slug="s1", title="S1",
            content="Initial"
        )

        async def do_update(i):
            return await server.prd_update_section(
                project="conc-loss", section="s1",
                content=f"Version {i}",
                change_description=f"Concurrent update {i}"
            )

        await asyncio.gather(*[do_update(i) for i in range(3)])

        revs = json.loads(await server.prd_get_revisions(
            project="conc-loss", section="s1"
        ))
        assert len(revs["revisions"]) == 3


class TestExportImport:
    async def test_export(self, mcp_pool):
        import server
        result = await server.prd_export_markdown(project="contentforge")
        assert "# ContentForge" in result
        assert "## Vision" in result

    async def test_import_new(self, mcp_pool):
        import server
        await server.prd_create_project(name="ImportTest", slug="import-test")
        md = "# Test\n\n## Introduction\n\nHello world.\n\n## Data Model\n\nSome schema here.\n"
        result = json.loads(await server.prd_import_markdown(
            project="import-test", markdown=md
        ))
        assert result["imported"] == 2
        assert result["sections"][0]["slug"] == "introduction"
        assert result["sections"][0]["action"] == "created"

    async def test_import_replace(self, mcp_pool):
        import server
        await server.prd_create_project(name="ReplTest", slug="repl-test")
        await server.prd_create_section(
            project="repl-test", slug="intro", title="Intro",
            content="Old content"
        )
        md = "# Test\n\n## Intro\n\nNew content here.\n"
        result = json.loads(await server.prd_import_markdown(
            project="repl-test", markdown=md, replace_existing=True
        ))
        assert result["imported"] == 1
        assert result["sections"][0]["action"] == "updated"

    async def test_import_preserves_nested_headings(self, mcp_pool):
        import server
        await server.prd_create_project(name="NestTest", slug="nest-test")
        md = "# Doc\n\n## Section One\n\nContent here.\n\n### Subsection\n\nMore content.\n\n## Section Two\n\nAnother section.\n"
        result = json.loads(await server.prd_import_markdown(
            project="nest-test", markdown=md
        ))
        assert result["imported"] == 2
        # Section One should include the ### subsection
        sec = json.loads(await server.prd_read_section(
            project="nest-test", section="section-one"
        ))
        assert "### Subsection" in sec["section"]["content"]


class TestBatch:
    async def test_bulk_status(self, mcp_pool):
        import server
        await server.prd_create_project(name="Batch", slug="batch-test")
        await server.prd_create_section(project="batch-test", slug="a", title="A")
        await server.prd_create_section(project="batch-test", slug="b", title="B")

        result = json.loads(await server.prd_bulk_status(
            project="batch-test",
            sections=["a", "b", "nonexistent"],
            status="approved"
        ))
        assert set(result["updated"]) == {"a", "b"}
        assert result["not_found"] == ["nonexistent"]


class TestAutoResolve:
    async def _setup(self, server):
        await server.prd_create_project(name="AR", slug="ar-test")
        await server.prd_create_section(
            project="ar-test", slug="s1", title="S1", content="Original"
        )
        result = json.loads(await server.prd_add_comment(
            project="ar-test", section="s1",
            anchor_text="Original", body="Fix this"
        ))
        return result["created"]["id"]

    async def test_update_with_resolve(self, mcp_pool):
        import server
        cid = await self._setup(server)
        result = json.loads(await server.prd_update_section(
            project="ar-test", section="s1",
            content="Updated", change_description="Fixed it",
            resolve_comments=[cid]
        ))
        assert "updated" in result
        assert cid in result["resolved_comments"]
        # Verify comment is resolved
        sec = json.loads(await server.prd_read_section(project="ar-test", section="s1"))
        comment = next(c for c in sec["comments"] if c["id"] == cid)
        assert comment["resolved"] is True

    async def test_resolve_wrong_section(self, mcp_pool):
        import server
        cid = await self._setup(server)
        await server.prd_create_section(project="ar-test", slug="s2", title="S2", content="Other")
        result = json.loads(await server.prd_update_section(
            project="ar-test", section="s2",
            content="Updated s2", change_description="Trying wrong section",
            resolve_comments=[cid]
        ))
        assert "updated" in result
        assert result.get("resolved_comments", []) == []
        # Comment should still be unresolved
        sec = json.loads(await server.prd_read_section(project="ar-test", section="s1"))
        comment = next(c for c in sec["comments"] if c["id"] == cid)
        assert comment["resolved"] is False

    async def test_bad_uuid_skipped(self, mcp_pool):
        import server
        cid = await self._setup(server)
        result = json.loads(await server.prd_update_section(
            project="ar-test", section="s1",
            content="Updated", change_description="Bad UUID test",
            resolve_comments=["not-a-uuid", cid]
        ))
        assert "updated" in result
        assert cid in result["resolved_comments"]

    async def test_already_resolved_idempotent(self, mcp_pool):
        import server
        cid = await self._setup(server)
        # Resolve it first
        await server.prd_resolve_comment(project="ar-test", section="s1", comment_id=cid)
        # Try to resolve again via update
        result = json.loads(await server.prd_update_section(
            project="ar-test", section="s1",
            content="Updated again", change_description="Already resolved",
            resolve_comments=[cid]
        ))
        assert "updated" in result
        assert result.get("resolved_comments", []) == []


class TestCommentReplies:
    async def _setup(self, server):
        await server.prd_create_project(name="CR", slug="cr-test")
        await server.prd_create_section(
            project="cr-test", slug="s1", title="S1", content="Content"
        )
        result = json.loads(await server.prd_add_comment(
            project="cr-test", section="s1",
            anchor_text="Content", body="Please clarify"
        ))
        return result["created"]["id"]

    async def test_add_reply(self, mcp_pool):
        import server
        cid = await self._setup(server)
        result = json.loads(await server.prd_add_comment_reply(
            project="cr-test", section="s1", comment_id=cid,
            body="Clarified!", author="claude"
        ))
        assert "created" in result
        assert result["created"]["author"] == "claude"
        assert result["created"]["body"] == "Clarified!"

    async def test_reply_in_read_section(self, mcp_pool):
        import server
        cid = await self._setup(server)
        await server.prd_add_comment_reply(
            project="cr-test", section="s1", comment_id=cid,
            body="Reply text", author="claude"
        )
        sec = json.loads(await server.prd_read_section(project="cr-test", section="s1"))
        comment = next(c for c in sec["comments"] if c["id"] == cid)
        assert len(comment["replies"]) == 1
        assert comment["replies"][0]["body"] == "Reply text"

    async def test_reply_nonexistent_comment(self, mcp_pool):
        import server
        await server.prd_create_project(name="CRN", slug="crn-test")
        await server.prd_create_section(project="crn-test", slug="s1", title="S1")
        result = json.loads(await server.prd_add_comment_reply(
            project="crn-test", section="s1",
            comment_id="00000000-0000-0000-0000-000000000000",
            body="Ghost reply"
        ))
        assert "error" in result


class TestProjectSettings:
    async def test_get_defaults(self, mcp_pool):
        import server
        result = json.loads(await server.prd_get_settings(project="contentforge"))
        assert result["settings"]["claude_comment_replies"] is True

    async def test_update_and_get(self, mcp_pool):
        import server
        await server.prd_create_project(name="Set", slug="set-test")
        result = json.loads(await server.prd_update_settings(
            project="set-test", settings={"claude_comment_replies": False}
        ))
        assert result["settings"]["claude_comment_replies"] is False
        # Verify via get
        result2 = json.loads(await server.prd_get_settings(project="set-test"))
        assert result2["settings"]["claude_comment_replies"] is False

    async def test_partial_update(self, mcp_pool):
        import server
        await server.prd_create_project(name="Partial", slug="partial-test")
        await server.prd_update_settings(
            project="partial-test", settings={"claude_comment_replies": False}
        )
        # Update same key
        result = json.loads(await server.prd_update_settings(
            project="partial-test", settings={"claude_comment_replies": True}
        ))
        assert result["settings"]["claude_comment_replies"] is True

    async def test_invalid_setting(self, mcp_pool):
        import server
        result = json.loads(await server.prd_update_settings(
            project="contentforge", settings={"unknown_key": True}
        ))
        assert "error" in result
        # Wrong type
        result2 = json.loads(await server.prd_update_settings(
            project="contentforge", settings={"claude_comment_replies": "yes"}
        ))
        assert "error" in result2
