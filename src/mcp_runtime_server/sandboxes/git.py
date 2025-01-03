from typing import Optional
from pathlib import Path


from mcp_runtime_server.types import Sandbox
from mcp_runtime_server.logging import get_logger
from mcp_runtime_server.sandboxes.sandbox import run_sandboxed_command

logger = get_logger(__name__)


async def clone_github_repository(
    sandbox: Sandbox, url: str, branch: Optional[str], subdir: Optional[str] = None
) -> Path:
    target_dir = sandbox.work_dir

    logger.debug(
        {"event": "clone_github_repository", "url": url, "target_dir": str(target_dir)}
    )

    # Ensure HTTPS URL
    if not url.startswith("https://"):
        if url.startswith("http://") or url.startswith("git@"):
            raise ValueError("Only HTTPS URLs are supported")
        url = f"https://{url}"

    logger.debug({"event": "clone_url_processed", "final_url": url})

    # Build command
    cmd = f"git clone {url} {target_dir}"
    if branch:
        cmd += f" -b {branch}"

    logger.debug(
        {
            "event": "cloning_repository",
            "command": cmd,
            "target_dir": str(target_dir),
            "parent_dir": str(Path(target_dir).parent),
        }
    )

    process = await run_sandboxed_command(sandbox, cmd)
    stdout, stderr = await process.communicate()

    if stdout:
        logger.debug({"event": "clone_stdout", "output": stdout.decode()})
    if stderr:
        logger.debug({"event": "clone_stderr", "output": stderr.decode()})

    if process.returncode != 0:
        logger.error(
            {
                "event": "clone_failed",
                "return_code": process.returncode,
                "stderr": stderr.decode(),
            }
        )
        raise RuntimeError(f"Failed to clone repository: {stderr.decode()}")

    logger.info(
        {"event": "repository_cloned", "url": url, "target_dir": str(target_dir)}
    )

    return target_dir
