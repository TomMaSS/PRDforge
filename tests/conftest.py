"""Shared fixtures for PRDforge tests."""

import asyncio
import os
import sys

import asyncpg
import pytest
import pytest_asyncio

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ui"))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://prdforge:prdforge@localhost:5432/prdforge"
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_pool():
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)
    yield pool
    await pool.close()


@pytest_asyncio.fixture(autouse=True)
async def clean_test_data(db_pool):
    """Clean up test-created data after each test, preserving seed data."""
    yield
    # Delete any projects that aren't the seed contentforge project
    await db_pool.execute(
        "DELETE FROM projects WHERE slug != 'contentforge'"
    )
    # Reset any modified seed data by ensuring contentforge exists
    exists = await db_pool.fetchval(
        "SELECT COUNT(*) FROM projects WHERE slug = 'contentforge'"
    )
    if not exists:
        # If seed was deleted, tests that need it will fail — that's expected
        pass


@pytest_asyncio.fixture
async def mcp_pool(db_pool, monkeypatch):
    """Patch the MCP server's pool to use our test pool."""
    import server
    monkeypatch.setattr(server, "_pool", db_pool)
    yield db_pool


@pytest_asyncio.fixture
async def ui_client(db_pool):
    """Create httpx AsyncClient for UI testing."""
    import app as ui_app
    from httpx import ASGITransport, AsyncClient

    ui_app.pool = db_pool
    transport = ASGITransport(app=ui_app.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
