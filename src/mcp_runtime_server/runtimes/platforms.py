"""Platform detection and mapping."""

import platform

from typing import Optional

from mcp_runtime_server.types import PlatformMapping, PlatformInfo

ARCH_MAPPINGS = {
    "x86_64": {"node": "x64", "bun": "x64", "uv": "x86_64"},
    "aarch64": {"node": "arm64", "bun": "aarch64", "uv": "aarch64"},
    "arm64": {"node": "arm64", "bun": "aarch64", "uv": "aarch64"},
}

# Platform mappings with composite configuration
PLATFORM_MAPPINGS = {
    "Linux": PlatformMapping(
        node="linux",
        bun="linux",
        uv="unknown-linux-gnu",
        archive_format="tar.gz",
        platform_template="{arch}-{platform}",  # For UV-style composites
        binary_location="bin",  # No extension for Unix binaries
    ),
    "Darwin": PlatformMapping(
        node="darwin",
        bun="darwin",
        uv="apple-darwin",
        archive_format="tar.gz",
        platform_template="{arch}-{platform}",
        binary_location="bin",
    ),
    "Windows": PlatformMapping(
        node="win",
        bun="windows",
        uv="pc-windows-msvc",
        archive_format="zip",
        platform_template="{arch}-{platform}",
        binary_location="bin/{name}.exe",  # Windows executables need .exe
    ),
}


def get_platform_info() -> PlatformInfo:
    """Get current platform information."""
    system = platform.system()
    machine = platform.machine().lower()

    if system not in PLATFORM_MAPPINGS:
        raise RuntimeError(f"Unsupported operating system: {system}")

    # Handle ARM64 naming variations
    if machine in ("arm64", "aarch64"):
        machine = "aarch64"

    if machine not in ARCH_MAPPINGS:
        raise RuntimeError(f"Unsupported architecture: {machine}")

    platform_map = PLATFORM_MAPPINGS[system]
    arch_map = ARCH_MAPPINGS[machine]

    # Now we can compose platform strings based on the template
    uv_platform = platform_map.platform_template.format(
        arch=arch_map["uv"], platform=platform_map.uv
    )

    return PlatformInfo(
        os_name=system.lower(),
        arch=machine,
        format=platform_map.archive_format,
        node_platform=f"{platform_map.node}-{arch_map['node']}",
        bun_platform=f"{platform_map.bun}-{arch_map['bun']}",
        uv_platform=uv_platform,
    )


def get_binary_location(runtime_name: str, system: Optional[str] = None) -> str:
    """Get the appropriate binary path pattern for a runtime."""
    if system is None:
        system = platform.system()

    if system not in PLATFORM_MAPPINGS:
        raise RuntimeError(f"Unsupported operating system: {system}")

    platform_map = PLATFORM_MAPPINGS[system]
    return platform_map.binary_location.format(name=runtime_name)


def is_platform_supported() -> bool:
    """Check if current platform is supported."""
    try:
        get_platform_info()
        return True
    except RuntimeError:
        return False
