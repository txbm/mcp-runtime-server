"""Runtime detection and configuration."""

from pathlib import Path
from typing import Dict

from mcp_runtime_server.types import Runtime, PackageManager, RuntimeConfig, Sandbox
from mcp_runtime_server.logging import get_logger
from mcp_runtime_server.runtimes import (
    python,
)

logger = get_logger(__name__)


RUNTIME_CONFIGS: Dict[Runtime, RuntimeConfig] = {
    Runtime.NODE: RuntimeConfig(
        name=Runtime.NODE,
        config_files=["package.json"],
        package_manager=PackageManager.NPM,
        env_setup={"NODE_NO_WARNINGS": "1", "NPM_CONFIG_UPDATE_NOTIFIER": "false"},
        bin_paths=["node_modules/.bin"],
        binary_name="node",
        url_template="https://nodejs.org/dist/{version_prefix}{version}/node-{version_prefix}{version}-{platform}.{format}",
        checksum_template="https://nodejs.org/dist/{version_prefix}{version}/SHASUMS256.txt",
    ),
    Runtime.BUN: RuntimeConfig(
        name=Runtime.BUN,
        config_files=["bun.lockb", "package.json"],
        package_manager=PackageManager.BUN,
        env_setup={"NO_INSTALL_HINTS": "1"},
        bin_paths=["node_modules/.bin"],
        binary_name="bun",
        url_template="https://github.com/oven-sh/bun/releases/download/bun-{version_prefix}{version}/bun-{platform}-{arch}.{format}",
        checksum_template="https://github.com/oven-sh/bun/releases/download/bun-{version_prefix}{version}/SHASUMS.txt",
    ),
    Runtime.PYTHON: RuntimeConfig(
        name=Runtime.PYTHON,
        config_files=["pyproject.toml", "setup.py", "requirements.txt"],
        package_manager=PackageManager.UV,
        env_setup={
            "PIP_NO_CACHE_DIR": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        bin_paths=[".venv/bin", ".venv/Scripts"],  # Scripts for Windows
        binary_name="uv",
        url_template="https://github.com/astral-sh/uv/releases/download/{version_prefix}{version}/uv-{platform}.{format}",
        checksum_template="https://github.com/astral-sh/uv/releases/download/{version}/uv-{platform}.{format}.sha256",
        platform_style="composite",
        version_prefix="",
    ),
}


def detect_runtime(sandbox: Sandbox) -> RuntimeConfig:
    """Detect runtime from project files."""

    work_dir = sandbox.work_dir
    logger.debug({"event": "detecting_runtime", "work_dir": str(work_dir)})

    files = set(str(p) for p in work_dir.rglob("*"))
    logger.debug({"event": "found_project_files", "files": list(files)})

    for runtime, config in RUNTIME_CONFIGS.items():
        if runtime == Runtime.BUN:
            if all(any(f.endswith(c) for f in files) for c in config.config_files):
                logger.info(
                    {
                        "event": "runtime_detected",
                        "runtime": runtime.value,
                        "matched_files": config.config_files,
                    }
                )
                return config
        else:
            if any(any(f.endswith(c) for f in files) for c in config.config_files):
                matched_file = next(
                    c for c in config.config_files if any(f.endswith(c) for f in files)
                )
                logger.info(
                    {
                        "event": "runtime_detected",
                        "runtime": runtime.value,
                        "matched_file": matched_file,
                        "files_checked": config.config_files,
                    }
                )
                return config

    logger.error(
        {
            "event": "no_runtime_detected",
            "work_dir": str(work_dir),
            "files_found": list(files),
        }
    )
    raise ValueError("No supported runtime detected")


async def install_runtime(
    sandbox: Sandbox, config: RuntimeConfig
) -> tuple[Path, Path, Path]:
    match config.name:
        case Runtime.PYTHON:
            return await python.install_runtime(sandbox, config)

    raise RuntimeError(f"Unsupported runtime name {config.name}")
