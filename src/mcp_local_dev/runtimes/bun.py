"""Bun runtime implementation."""

import shutil
from pathlib import Path

from mcp_local_dev.types import Runtime, PackageManager, RuntimeConfig, Sandbox
from mcp_local_dev.sandboxes.commands import install_packages
from mcp_local_dev.sandboxes.sandbox import add_package_manager_bin_path

CONFIG = RuntimeConfig(
    name=Runtime.BUN,
    config_files=["bun.lockb", "package.json"],
    package_manager=PackageManager.BUN,
    env_setup={"NO_INSTALL_HINTS": "1"},
    binary_name="bun",
)

async def setup_bun(sandbox: Sandbox) -> None:
    """Set up Bun runtime environment."""
    # Verify and symlink bun
    bun_path = shutil.which('bun')
    if not bun_path:
        raise RuntimeError("Required runtime/package manager not found: bun")

    bunx_path = shutil.which('bunx')
    if not bunx_path:
        raise RuntimeError("Required package manager not found: bunx")

    # Symlink bun for both runtime and package manager
    bun_target = sandbox.bin_dir / 'bun'
    if not bun_target.exists():
        bun_target.symlink_to(bun_path)

    # Symlink bunx
    bunx_target = sandbox.bin_dir / 'bunx'
    if not bunx_target.exists():
        bunx_target.symlink_to(bunx_path)

    # Also symlink as node for compatibility
    node_target = sandbox.bin_dir / 'node'
    if not node_target.exists():
        node_target.symlink_to(bun_path)

    # Set up environment variables
    for key, value in CONFIG.env_setup.items():
        sandbox.env_vars[key] = value

    # Add package manager bin paths before installing packages
    add_package_manager_bin_path(sandbox, CONFIG.package_manager)

    # Install project dependencies
    await install_packages(sandbox, CONFIG.package_manager)
