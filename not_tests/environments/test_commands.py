"""Tests for environment command execution."""

import os
import pytest
from pathlib import Path

from mcp_runtime_server.environments.environment import create_environment
from mcp_runtime_server.environments.commands import (
    run_install,
)


@pytest.mark.asyncio
async def test_run_install_node():
    """Test running install for Node.js environment."""
    env = await create_environment("https://github.com/txbm/mcp-node-repo-fixture")

    await run_install(env)
    assert (env.sandbox.work_dir / "node_modules").exists()


@pytest.mark.asyncio
async def test_run_install_python():
    """Test running install for Python environment."""
    env = await create_environment("https://github.com/txbm/mcp-python-repo-fixture")

    await run_install(env)
    assert (env.sandbox.work_dir / ".venv").exists()
    assert (env.sandbox.work_dir / ".venv" / "bin" / "python").exists() or (
        env.sandbox.work_dir / ".venv" / "Scripts" / "python.exe"
    ).exists()


@pytest.mark.asyncio
async def test_github_clone():
    """Test GitHub repository cloning during environment creation."""
    env = await create_environment("https://github.com/txbm/mcp-runtime-server")

    # Verify clone success
    assert (env.sandbox.work_dir / ".git").exists()
    assert (env.sandbox.work_dir / "pyproject.toml").exists()


@pytest.mark.asyncio
async def test_invalid_url():
    """Test environment creation with invalid Git URL."""
    with pytest.raises(RuntimeError):
        await create_environment("not-a-url")
