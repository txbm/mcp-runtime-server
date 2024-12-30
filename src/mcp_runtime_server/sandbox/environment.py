"""Sandbox environment creation and cleanup."""
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Optional, NamedTuple
import appdirs

from mcp_runtime_server.errors import SandboxError
from mcp_runtime_server.sandbox.security import apply_restrictions, remove_restrictions


class Sandbox(NamedTuple):
    """Information about a sandbox environment."""
    id: str
    root: Path
    bin_dir: Path
    env_vars: Dict[str, str]


def get_sandbox_root() -> Path:
    """Get the root directory for sandbox environments.
    
    Returns:
        Path to sandbox root directory
    """
    sandbox_dir = Path(appdirs.user_cache_dir("mcp-runtime-server")) / "sandboxes"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    return sandbox_dir


def create_directories(root: Path) -> Dict[str, Path]:
    """Create standard sandbox directory structure.
    
    Args:
        root: Sandbox root directory
        
    Returns:
        Dict mapping directory names to paths
    """
    dirs = {
        "bin": root / "bin",
        "tmp": root / "tmp",
        "home": root / "home",
        "cache": root / "cache",
        "work": root / "work"
    }
    
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
        
    return dirs


def prepare_environment(
    root: Path,
    dirs: Dict[str, Path],
    base_env: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """Prepare environment variables for sandbox.
    
    Args:
        root: Sandbox root directory
        dirs: Sandbox directory structure
        base_env: Base environment variables to extend
        
    Returns:
        Dict of environment variables
    """
    env = base_env.copy() if base_env else os.environ.copy()
    
    # Set up basic environment
    env.update({
        "HOME": str(dirs["home"]),
        "TMPDIR": str(dirs["tmp"]),
        "XDG_CACHE_HOME": str(dirs["cache"]),
        "XDG_RUNTIME_DIR": str(dirs["tmp"]),
        "PATH": f"{dirs['bin']}:{env.get('PATH', '')}"
    })
    
    # Remove potentially dangerous variables
    for var in [
        "PYTHONPATH",
        "NODE_PATH",
        "LD_PRELOAD",
        "LD_LIBRARY_PATH"
    ]:
        env.pop(var, None)
        
    return env


def create_sandbox(
    base_env: Optional[Dict[str, str]] = None
) -> Sandbox:
    """Create a new sandbox environment.
    
    Args:
        base_env: Optional base environment variables
        
    Returns:
        Sandbox with environment details
    """
    sandbox_id = str(uuid.uuid4())
    root = get_sandbox_root() / sandbox_id
    
    try:
        # Create directory structure
        dirs = create_directories(root)
        
        # Prepare environment
        env_vars = prepare_environment(root, dirs, base_env)
        
        # Apply security restrictions
        apply_restrictions(root)
        
        return Sandbox(
            id=sandbox_id,
            root=root,
            bin_dir=dirs["bin"],
            env_vars=env_vars
        )
        
    except Exception as e:
        # Clean up on failure
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        raise SandboxError(f"Failed to create sandbox: {e}")


def cleanup_sandbox(sandbox: Sandbox) -> None:
    """Clean up a sandbox environment.
    
    Args:
        sandbox: Sandbox to clean up
    """
    try:
        # Remove security restrictions
        remove_restrictions(sandbox.root)
        
        # Clean up files
        if sandbox.root.exists():
            shutil.rmtree(sandbox.root, ignore_errors=True)
            
    except Exception as e:
        raise SandboxError(f"Failed to clean up sandbox {sandbox.id}: {e}")