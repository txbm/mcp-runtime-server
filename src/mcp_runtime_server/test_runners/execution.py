"""Test execution module."""

import json

import mcp.types as types
from mcp_runtime_server.environments.environment import Environment
from mcp_runtime_server.test_runners.frameworks import (
    detect_frameworks,
    run_framework_tests
)
from mcp_runtime_server.types import RunConfig, FrameworkType
from mcp_runtime_server.test_runners.results import format_test_results
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


async def auto_run_tests(
    env: Environment,
) -> list[types.TextContent]:
    """Auto-detect and run tests in the environment."""
    frameworks = detect_frameworks(env)
    if not frameworks:
        logger.info(
            {"event": "no_frameworks_detected", "working_dir": str(env.sandbox.work_dir)}
        )
        return [
            types.TextContent(
                text=json.dumps(
                    {"success": False, "error": "No test frameworks detected"}
                ),
                type="text",
            )
        ]

    results = []
    for framework in frameworks:
        config = RunConfig(framework=framework, env=env, test_dirs=[env.sandbox.work_dir])
        result = await run_framework_tests(config)
        results.append(result)

    all_passed = all(r.get("success", False) for r in results)
    logger.info(
        {
            "event": "test_run_complete",
            "all_passed": all_passed,
            "framework_count": len(frameworks),
        }
    )
    return format_test_results(frameworks[0].value, results[0] if results else {})