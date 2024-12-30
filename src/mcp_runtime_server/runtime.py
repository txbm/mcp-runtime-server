"""Runtime environment management."""
import asyncio
import logging
import os
import shutil
import appdirs
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from mcp_runtime_server.types import RuntimeConfig, Environment
from mcp_runtime_server.logging import log_with_data
from mcp_runtime_server.testing import auto_run_tests

logger = logging.getLogger(__name__)

# Active environments
ENVIRONMENTS: Dict[str, Environment] = {}


async def create_environment(config: RuntimeConfig) -> Environment:
    """Create a new runtime environment."""
    try:
        # Create unique environment ID and root directory
        env_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        root_dir = Path(appdirs.user_cache_dir("mcp-runtime-server")) / "envs" / env_id
        
        # Create directory structure
        bin_dir = root_dir / "bin"
        tmp_dir = root_dir / "tmp"
        work_dir = root_dir / "work"
        
        for d in [bin_dir, tmp_dir, work_dir]:
            d.mkdir(parents=True)
        
        # Set up environment variables
        env_vars = os.environ.copy()
        env_vars.update({
            "HOME": str(work_dir),
            "TMPDIR": str(tmp_dir),
            "PATH": f"{bin_dir}:{env_vars.get('PATH', '')}"
        })
        
        for var in ["PYTHONPATH", "NODE_PATH", "LD_PRELOAD", "LD_LIBRARY_PATH"]:
            env_vars.pop(var, None)
        
        # Create environment
        env = Environment(
            id=env_id,
            config=config,
            created_at=datetime.utcnow(),
            root_dir=root_dir,
            bin_dir=bin_dir,
            work_dir=work_dir,
            tmp_dir=tmp_dir,
            env_vars=env_vars
        )
        
        # Clone repository
        process = await asyncio.create_subprocess_exec(
            "git", "clone", config.github_url, str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env.env_vars
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Failed to clone repository: {stderr.decode()}")

        ENVIRONMENTS[env.id] = env
        return env
        
    except Exception as e:
        if 'root_dir' in locals() and root_dir.exists():
            shutil.rmtree(str(root_dir))
        raise RuntimeError(f"Failed to create environment: {e}") from e


async def cleanup_environment(env_id: str) -> None:
    """Clean up a runtime environment."""
    if env_id not in ENVIRONMENTS:
        return
        
    env = ENVIRONMENTS[env_id]
    try:
        if env.root_dir.exists():
            shutil.rmtree(str(env.root_dir))
    finally:
        del ENVIRONMENTS[env_id]


async def run_command(env_id: str, command: str) -> asyncio.subprocess.Process:
    """Run a command in an environment."""
    if env_id not in ENVIRONMENTS:
        raise RuntimeError(f"Unknown environment: {env_id}")
        
    env = ENVIRONMENTS[env_id]
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=env.work_dir,
            env=env.env_vars
        )
        
        return process
        
    except Exception as e:
        raise RuntimeError(f"Failed to run command: {e}")