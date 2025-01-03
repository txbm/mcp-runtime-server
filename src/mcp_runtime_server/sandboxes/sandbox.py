"""Sandbox directory and security management."""

import tempfile
import asyncio
import os
import shutil
import platform
from pathlib import Path
from typing import Dict, Tuple, Optional

from mcp_runtime_server.types import Sandbox
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


def _make_sandbox_dirs(root: Path) -> Tuple[Dict[str, Path], Dict[str, str]]:
    """Create sandbox directory structure and environment variables.

    Args:
        root: Root directory for sandbox

    Returns:
        Tuple of (directory paths dict, environment variables dict)

    Raises:
        RuntimeError: If directory creation fails
    """
    logger.debug({"event": "creating_sandbox_directories", "root": str(root)})

    try:
        # Define directory structure
        dirs = {
            "bin": root / "bin",
            "tmp": root / "tmp",
            "work": root / "work",
            "cache": root / "cache",
        }

        # Create directories
        for name, path in dirs.items():
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(
                {"event": "created_sandbox_directory", "name": name, "path": str(path)}
            )

        # Set base environment variables
        base_env = os.environ.copy()
        sandbox_env = {
            "TMPDIR": str(dirs["tmp"]),
            "XDG_CACHE_HOME": str(dirs["cache"]),
            "XDG_RUNTIME_DIR": str(dirs["tmp"]),
            "PATH": f"{dirs['bin']}",
        }
        base_env.update(sandbox_env)

        # Remove unsafe environment variables
        unsafe_vars = ["LD_PRELOAD", "LD_LIBRARY_PATH"]
        for var in unsafe_vars:
            base_env.pop(var, None)

        logger.debug(
            {
                "event": "sandbox_env_prepared",
                "sandbox_vars": sandbox_env,
                "removed_vars": unsafe_vars,
            }
        )

        return dirs, base_env

    except Exception as e:
        logger.error(
            {"event": "sandbox_creation_failed", "error": str(e), "root": str(root)}
        )
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        raise RuntimeError(f"Failed to create sandbox directories: {e}")


async def _copy_system_binaries(sandbox: Sandbox):

    process = await run_system_command("which git", sandbox.work_dir)
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        bin_path = Path(stdout.decode().strip())
        if bin_path.exists():
            logger.debug(
                {
                    "event": "found_git",
                    "git_path": bin_path,
                }
            )
            shutil.copy2(bin_path, sandbox.bin_dir)


def _apply_security(sandbox: Sandbox) -> None:
    """Apply security restrictions to sandbox directory."""

    root = sandbox.root
    try:
        if platform.system() == "Linux":
            logger.debug({"event": "applying_unix_permissions", "root": str(root)})
            _apply_unix_permissions(root)
            logger.info({"event": "unix_permissions_applied", "root": str(root)})
    except Exception as e:
        logger.error(
            {"event": "security_application_failed", "error": str(e), "root": str(root)}
        )
        raise RuntimeError(f"Failed to apply sandbox security: {e}")


def _apply_unix_permissions(path: Path) -> None:
    """Apply restrictive Unix permissions recursively.

    Args:
        path: Path to apply permissions to
    """
    os.chmod(path, 0o700)  # Changed to 700 to allow execution of binaries

    if path.is_dir():
        for child in path.iterdir():
            _apply_unix_permissions(child)


async def create_sandbox(prefix: str) -> Sandbox:
    """Create new sandbox environment within root directory.

    Args:
        root: Root directory for sandbox

    Returns:
        Sandbox instance

    Raises:
        RuntimeError: If sandbox creation fails
    """
    try:

        temp_dir = tempfile.TemporaryDirectory(prefix=prefix, delete=False)
        root = Path(temp_dir.name)
        dirs, env_vars = _make_sandbox_dirs(root)

        sandbox = Sandbox(
            root=root,
            work_dir=dirs["work"],
            bin_dir=dirs["bin"],
            tmp_dir=dirs["tmp"],
            cache_dir=dirs["cache"],
            env_vars=env_vars,
            temp_dir=temp_dir,
        )

        await _copy_system_binaries(sandbox)
        _apply_security(sandbox)

        logger.info(
            {
                "event": "sandbox_created",
                "root": str(root),
                "work_dir": str(sandbox.work_dir),
                "bin_dir": str(sandbox.bin_dir),
                "temp_dir": str(temp_dir),
            }
        )

        return sandbox

    except Exception as e:
        logger.error(
            {"event": "sandbox_creation_failed", "error": str(e), "root": str(root)}
        )
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        raise RuntimeError(f"Failed to create sandbox: {e}")


def cleanup_sandbox(sandbox: Sandbox) -> None:
    """Clean up sandbox environment.

    Args:
        sandbox: Sandbox instance to clean up

    Raises:
        RuntimeError: If cleanup fails
    """
    logger.debug({"event": "cleaning_sandbox", "root": str(sandbox.root)})

    sandbox.temp_dir.cleanup()
    if sandbox.root.exists():
        shutil.rmtree(sandbox.root, ignore_errors=True)
    logger.info({"event": "sandbox_cleaned", "root": str(sandbox.root)})


async def run_system_command(
    cmd: str, cwd: Path, env_vars: Optional[Dict[str, str]] = None
):

    try:
        return await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            env=env_vars,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as e:
        raise RuntimeError(f"System command execution failed: {e}")


async def run_sandboxed_command(
    sandbox: Sandbox, cmd: str, env_vars: Optional[Dict[str, str]] = None
) -> asyncio.subprocess.Process:
    """Run a command inside a sandbox."""

    sandbox_env_vars = sandbox.env_vars
    if env_vars:
        sandbox_env_vars.update(env_vars)

    try:
        return await asyncio.create_subprocess_shell(
            cmd,
            cwd=sandbox.work_dir,
            env=sandbox_env_vars,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as e:
        raise RuntimeError(f"Sandbox command execution failed: {e}")
