"""Runtime detection and configuration."""
import shutil
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

class Runtime(str, Enum):
    PYTHON = "uv"
    NODE = "npm"
    BUN = "bun"

@dataclass(frozen=True)
class RuntimeSignature:
    config_files: List[str]
    env_vars: Dict[str, str]
    bin_path: str

SIGNATURES = {
    Runtime.NODE: RuntimeSignature(
        config_files=["package.json"],
        env_vars={
            "NODE_NO_WARNINGS": "1",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false"
        },
        bin_path="node_modules/.bin"
    ),
    Runtime.BUN: RuntimeSignature(
        config_files=["bun.lockb", "package.json"],
        env_vars={"NO_INSTALL_HINTS": "1"},
        bin_path="node_modules/.bin"
    ),
    Runtime.PYTHON: RuntimeSignature(
        config_files=["pyproject.toml", "setup.py"],
        env_vars={
            "VIRTUAL_ENV": "",
            "PIP_NO_CACHE_DIR": "1"
        },
        bin_path=".venv/bin"
    )
}

def detect_runtime(work_dir: Path) -> Runtime:
    """Detect runtime from project files."""
    try:
        files = set(str(p) for p in work_dir.rglob("*"))
        
        # Check Bun first (requires both files)
        if all(any(f.endswith(c) for f in files) 
              for c in SIGNATURES[Runtime.BUN].config_files):
            return Runtime.BUN
            
        # Then Node
        if any(f.endswith("package.json") for f in files):
            return Runtime.NODE
            
        # Finally Python
        if any(any(f.endswith(c) for f in files) 
              for c in SIGNATURES[Runtime.PYTHON].config_files):
            return Runtime.PYTHON
            
        raise ValueError("No supported runtime detected")
        
    except Exception as e:
        raise RuntimeError(f"Runtime detection failed: {e}")

def get_runtime_binary(runtime: Runtime) -> str:
    """Get runtime binary path."""
    binary = shutil.which(runtime.value)
    if not binary:
        raise RuntimeError(f"Runtime {runtime.value} not found")
    return binary

def get_runtime_bin_dir(work_dir: Path, runtime: Runtime) -> Path:
    """Get runtime binary directory."""
    bin_path = work_dir / SIGNATURES[runtime].bin_path
    platform_bin = bin_path / "Scripts" if os.name == "nt" else bin_path
    return platform_bin if platform_bin.exists() else bin_path

def setup_runtime_env(
    base_env: Dict[str, str],
    runtime: Runtime,
    work_dir: Path
) -> Dict[str, str]:
    """Setup runtime environment variables."""
    env = base_env.copy()
    bin_dir = get_runtime_bin_dir(work_dir, runtime)
    
    # Base PATH setup
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    
    # Runtime-specific vars
    runtime_vars = SIGNATURES[runtime].env_vars
    if runtime == Runtime.PYTHON:
        venv = work_dir / ".venv"
        runtime_vars["VIRTUAL_ENV"] = str(venv)
        runtime_vars["PYTHONPATH"] = str(work_dir)
    elif runtime in (Runtime.NODE, Runtime.BUN):
        runtime_vars["NODE_PATH"] = str(work_dir / "node_modules")
        
    env.update(runtime_vars)
    return env