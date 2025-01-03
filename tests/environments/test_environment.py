"""Tests for environment creation and lifecycle."""

import pytest
import pytest_asyncio
from mcp_runtime_server.sandboxes.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.environments.environment import (
    create_environment_from_github,
)


@pytest_asyncio.fixture
async def staging_sandbox():
    sandbox = await create_sandbox("staging-")
    yield sandbox
    # cleanup_sandbox(sandbox)


@pytest.mark.asyncio
async def test_environment_creation_from_github(staging_sandbox):
    """Test environment creation from Github."""

    env = await create_environment_from_github(
        staging_sandbox, "https://github.com/txbm/mcp-runtime-server.git"
    )

    assert env
