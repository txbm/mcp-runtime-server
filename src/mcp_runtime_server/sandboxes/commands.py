"""Environment command execution."""

import asyncio
from typing import Dict, Optional
from pathlib import Path

from mcp_runtime_server.types import PackageManager, Environment
from mcp_runtime_server.logging import get_logger
from mcp_runtime_server.sandboxes import run_sandboxed_command

logger = get_logger(__name__)


async def run_install(env: Environment) -> None:
    """Run install command for environment runtime."""
    pkg_manager = PackageManager.for_runtime(env.runtime)

    # Get the appropriate install command for package manager
    if pkg_manager == PackageManager.UV:
        cmd = "uv sync --all-extras"
    elif pkg_manager == PackageManager.NPM:
        cmd = "npm install"
    elif pkg_manager == PackageManager.BUN:
        cmd = "bun install"
    else:
        raise RuntimeError(f"Unsupported package manager: {pkg_manager}")

    process = await run_sandboxed_command(env.sandbox, cmd)
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"Install failed with code {process.returncode}\n"
            f"stdout: {stdout.decode()}\n"
            f"stderr: {stderr.decode()}"
        )
