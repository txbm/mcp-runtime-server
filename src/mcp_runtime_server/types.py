"""Core type definitions."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, NamedTuple
from tempfile import TemporaryDirectory


class Runtime(str, Enum):
    """Runtime environment types."""

    PYTHON = "python"
    NODE = "node"
    BUN = "bun"


class PackageManager(str, Enum):
    """Package manager types."""

    UV = "uv"  # Python
    NPM = "npm"  # Node.js
    BUN = "bun"  # Bun

    @classmethod
    def for_runtime(cls, runtime: Runtime) -> "PackageManager":
        """Get default package manager for runtime."""
        if runtime == Runtime.PYTHON:
            return cls.UV
        elif runtime == Runtime.NODE:
            return cls.NPM
        elif runtime == Runtime.BUN:
            return cls.BUN
        raise ValueError(f"No package manager for runtime: {runtime}")


@dataclass(frozen=True)
class PlatformInfo:
    """Platform information."""

    os_name: str
    arch: str
    format: str
    node_platform: str
    bun_platform: str
    uv_platform: str


class PlatformMapping(NamedTuple):
    """Platform-specific values."""

    node: str
    bun: str
    uv: str
    archive_format: str
    platform_template: str
    binary_location: str


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime configuration details."""

    name: Runtime
    config_files: List[str]  # Files that indicate this runtime
    package_manager: PackageManager  # Default package manager
    env_setup: Dict[str, str]  # Base environment variables
    bin_paths: List[str]  # Possible binary paths in priority order
    binary_name: str  # Name of the runtime binary
    url_template: str  # Download URL template
    checksum_template: str
    platform_style: str = "simple"  # Platform string style (simple or composite)
    version_prefix: str = "v"  # Version number prefix in URLs


@dataclass(frozen=True)
class Sandbox:
    root: Path
    work_dir: Path
    bin_dir: Path
    tmp_dir: Path
    cache_dir: Path
    temp_dir: TemporaryDirectory
    env_vars: Dict[str, str]


@dataclass(frozen=True)
class Environment:
    """Runtime environment instance."""

    id: str
    runtime_config: RuntimeConfig
    created_at: datetime
    sandbox: Sandbox
    pkg_bin: Path
    runtime_bin: Path
    test_bin: Path


@dataclass
class TestCase:
    """Test case execution result."""

    name: str
    status: str
    output: List[str]
    failure_message: Optional[str] = None
    duration: Optional[float] = None


@dataclass
class RunTestResult:
    """Results from a test framework run."""

    success: bool
    framework: str
    passed: Optional[int] = None
    failed: Optional[int] = None
    skipped: Optional[int] = None
    total: Optional[int] = None
    failures: List[Dict[str, Any]] = None
    warnings: List[str] = None
    test_cases: List[Dict[str, Any]] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.failures is None:
            self.failures = []
        if self.warnings is None:
            self.warnings = []
        if self.test_cases is None:
            self.test_cases = []
