"""Core type definitions"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List
from tempfile import TemporaryDirectory

Runtime = Enum('Runtime', ['PYTHON', 'NODE', 'BUN'])
PackageManager = Enum('PackageManager', ['UV', 'NPM', 'BUN'])
class RunnerType(Enum):
    """Available test runner types"""
    PYTEST = 'pytest'
    UNITTEST = 'unittest'
    JEST = 'jest'
    VITEST = 'vitest'

@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime configuration"""
    name: Runtime
    config_files: list[str]
    package_manager: PackageManager
    env_setup: dict[str, str]
    binary_name: str

@dataclass(frozen=True)
class Sandbox:
    """Isolated execution environment"""
    root: Path
    work_dir: Path
    bin_dir: Path
    tmp_dir: Path
    cache_dir: Path
    temp_dir: TemporaryDirectory
    env_vars: dict[str, str]

@dataclass(frozen=True)
class Environment:
    """Runtime environment"""
    id: str
    runtime_config: RuntimeConfig
    created_at: datetime
    sandbox: Sandbox

@dataclass(frozen=True)
class RunConfig:
    """Test run configuration"""
    runner: RunnerType
    env: Environment
    test_dirs: List[Path]

@dataclass(frozen=True)
class CoverageResult:
    """Test coverage results"""
    lines: float  # Percentage of lines covered
    statements: float  # Percentage of statements covered
    branches: float  # Percentage of branches covered
    functions: float  # Percentage of functions covered
    files: dict[str, float]  # Per-file line coverage percentages

@dataclass(frozen=True)
class TestCase:
    """Test execution result"""
    name: str
    status: str
    output: list[str]
    failure_message: str | None = None
    duration: float | None = None
    coverage: CoverageResult | None = None
