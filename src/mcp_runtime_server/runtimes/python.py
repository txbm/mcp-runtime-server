"""Installer for the Python runtime; uses UV btw"""

import os
from pathlib import Path

from mcp_runtime_server.utils.github import fetch_latest_release_version
from mcp_runtime_server.runtimes.platforms import get_platform_info
from mcp_runtime_server.sandboxes.sandbox import (
    run_sandboxed_command,
)
from mcp_runtime_server.sandboxes.cache import (
    check_binary_cache,
    cache_binary,
    cleanup_cache,
)
from mcp_runtime_server.types import PlatformInfo, RuntimeConfig, Sandbox
from mcp_runtime_server.logging import get_logger
from mcp_runtime_server.utils.fetching import (
    download_url,
    download_checksum,
    extract_archive,
)
from mcp_runtime_server.utils.generic import dict_to_hash, move_files

logger = get_logger(__name__)


async def _fetch_latest_uv(
    sandbox: Sandbox, config: RuntimeConfig, platform_info: PlatformInfo
):
    owner = "astral-sh"
    repo = "uv"
    version = await fetch_latest_release_version(owner, repo)
    url_vars = {
        "version": version,
        "version_prefix": config.version_prefix,
        "platform": platform_info.uv_platform,
        "format": platform_info.format,
        "arch": platform_info.arch,
        "owner": owner,
        "repo": repo,
    }
    url_hash = dict_to_hash(url_vars)
    archive_url = config.url_template.format(**url_vars)
    archive_name = Path(archive_url).name
    cached = check_binary_cache(url_hash, archive_name)

    logger.debug(
        {
            "event": "fetch_latest_uv",
            "latest_version": version,
            "cached_archive": cached,
        }
    )

    if not cached:
        checksum_url = config.checksum_template.format(**url_vars)
        archive_path = sandbox.tmp_dir / archive_name

        logger.debug(
            {
                "event": "fetching_uv",
                "archive_url": archive_url,
                "archive_path": archive_path,
                "checksum_url": checksum_url,
            }
        )

        await download_url(archive_url, archive_path)
        checksum = await download_checksum(checksum_url, archive_path)
        cached = cache_binary(url_hash, archive_path, checksum)

    extract_archive(cached, sandbox.tmp_dir)
    move_files(
        sandbox.tmp_dir / archive_name.removesuffix(f".{platform_info.format}"),
        sandbox.bin_dir,
    )

    logger.debug({"event": "installed_uv", "bin_dir": sandbox.bin_dir})


async def install_runtime(
    sandbox: Sandbox, config: RuntimeConfig
) -> tuple[Path, Path, Path]:

    platform_info = get_platform_info()

    await _fetch_latest_uv(sandbox, config, platform_info)

    process = await run_sandboxed_command(sandbox, "uv sync --all-extras")
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"Python runtime install failed {process.returncode}"
            f"stdout: {stdout.decode()}"
            f"stderr: {stderr.decode()}"
        )

    return (
        sandbox.bin_dir / "python",
        sandbox.bin_dir / "uv",
        sandbox.bin_dir / "pytest",
    )
