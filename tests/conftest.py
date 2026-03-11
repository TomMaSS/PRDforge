"""Shared fixtures for PRDforge tests."""

import os
import sys

# Add project root + subpackages to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ui"))

try:
    import asyncpg
    import pytest_asyncio

    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "postgresql://prdforge:prdforge@localhost:5432/prdforge"
    )

    @pytest_asyncio.fixture(scope="session")
    async def db_pool():
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)
        yield pool
        await pool.close()

    @pytest_asyncio.fixture(autouse=True)
    async def clean_test_data(db_pool):
        """Clean up test-created data after each test, preserving seed data."""
        await db_pool.execute("DELETE FROM chat_messages")
        await db_pool.execute("DELETE FROM project_chats")
        await db_pool.execute("DELETE FROM comment_replies")
        await db_pool.execute("DELETE FROM section_comments")
        await db_pool.execute("DELETE FROM project_settings")
        await db_pool.execute("DELETE FROM token_estimates")
        await db_pool.execute("DELETE FROM projects WHERE slug != 'snaphabit'")
        yield
        await db_pool.execute("DELETE FROM chat_messages")
        await db_pool.execute("DELETE FROM project_chats")
        await db_pool.execute("DELETE FROM comment_replies")
        await db_pool.execute("DELETE FROM section_comments")
        await db_pool.execute("DELETE FROM project_settings")
        await db_pool.execute("DELETE FROM token_estimates")
        await db_pool.execute("DELETE FROM projects WHERE slug != 'snaphabit'")

    @pytest_asyncio.fixture(scope="session")
    async def mcp_pool(db_pool):
        """Patch the MCP server's pool to use our test pool."""
        import server
        server._pool = db_pool
        yield db_pool

    @pytest_asyncio.fixture(scope="session")
    async def ui_client(db_pool):
        """Create httpx AsyncClient for UI testing."""
        import app as ui_app
        from httpx import ASGITransport, AsyncClient

        ui_app.pool = db_pool
        transport = ASGITransport(app=ui_app.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

except ImportError:
    # Smoke tests don't need asyncpg/pytest_asyncio
    pass
