"""Runner implementation for Vitest"""

from typing import Dict, Any
import json
from mcp_local_dev.types import Environment, RunnerType, Runtime
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command, is_command_available

logger = get_logger(__name__)

async def run_vitest(env: Environment) -> Dict[str, Any]:
    """Run Vitest and parse results"""
    cmd_prefix = "bun" if env.runtime_config.name == Runtime.BUN else "node --experimental-vm-modules"
    cmd = f"{cmd_prefix} node_modules/vitest/vitest.mjs run --reporter json"
    returncode, stdout, stderr = await run_sandboxed_command(env.sandbox, cmd)

    if returncode not in (0, 1):
        return {
            "runner": RunnerType.VITEST.value,
            "success": False,
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            "tests": [],
            "error": "Vitest execution failed",
        }

    result = json.loads(stdout.decode())
    
    tests = []
    summary = {
        "total": result["numTotalTests"],
        "passed": result["numPassedTests"],
        "failed": result["numFailedTests"],
        "skipped": result["numPendingTests"],
    }

    for test_file in result["testResults"]:
        for test in test_file["assertionResults"]:
            tests.append({
                "nodeid": test["title"],
                "outcome": test["status"],
            })

    return {
        "runner": RunnerType.VITEST.value,
        "success": result["success"],
        "summary": summary,
        "tests": tests,
    }

async def check_vitest(env: Environment) -> bool:
    """Check if Vitest can run in this environment."""
    if env.runtime_config.name not in (Runtime.NODE, Runtime.BUN):
        return False
        
    config_exists = any(
        env.sandbox.work_dir.glob(p)
        for p in ["vitest.config.js", "vitest.config.ts", "vite.config.js"]
    )
    return config_exists and await is_command_available(env.sandbox, "vitest")
