"""Environment lifecycle management."""

from pathlib import Path
import shutil
from datetime import datetime, timezone
from typing import Optional

from fuuid import b58_fuuid

from mcp_runtime_server.types import Environment, Sandbox
from mcp_runtime_server.runtimes.runtime import detect_runtime, install_runtime
from mcp_runtime_server.sandboxes.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.sandboxes.git import clone_github_repository
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


async def create_environment_from_github(
    staging: Sandbox, github_url: str, branch: Optional[str] = None
) -> Environment:

    repo = await clone_github_repository(staging, github_url, branch)
    env = await create_environment(repo)

    return env


async def create_environment(path: Path) -> Environment:
    """Create new environment from a filesystem path."""

    env_id = b58_fuuid()
    logger.info(
        {
            "event": "creating_environment",
            "env_id": env_id,
            "path": path,
        }
    )
    sandbox = await create_sandbox(f"mcp-{env_id}-")
    shutil.copytree(path, sandbox.work_dir, dirs_exist_ok=True)

    runtime_config = detect_runtime(sandbox)
    runtime_bin, pkg_bin, test_bin = await install_runtime(sandbox, runtime_config)

    env = Environment(
        id=env_id,
        runtime_config=runtime_config,
        sandbox=sandbox,
        created_at=datetime.now(timezone.utc),
        runtime_bin=runtime_bin,
        pkg_bin=pkg_bin,
        test_bin=test_bin,
    )

    logger.info(
        {
            "event": "environment_created",
            "env_id": env_id,
            "runtime": runtime_config.name.value,
            "work_dir": sandbox.work_dir,
        }
    )

    return env


def cleanup_environment(env: Environment) -> None:
    """Clean up environment and its resources."""

    cleanup_sandbox(env.sandbox)
