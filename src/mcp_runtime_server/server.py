"""MCP server implementation."""

import asyncio
import json
import signal
import sys
from typing import Dict, Any, List, cast

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server import stdio

from mcp_runtime_server.types import Environment
from mcp_runtime_server.environments.environment import (
    create_environment,
    cleanup_environment,
)
from mcp_runtime_server.testing.execution import auto_run_tests
from mcp_runtime_server.logging import configure_logging, get_logger

logger = get_logger("server")

ENVIRONMENTS: Dict[str, Environment] = {}

tools = [
    types.Tool(
        name="create_environment",
        description="Create a new runtime environment with sandbox isolation",
        inputSchema={
            "type": "object",
            "properties": {
                "github_url": {"type": "string", "description": "GitHub repository URL"}
            },
            "required": ["github_url"],
        },
    ),
    types.Tool(
        name="run_tests",
        description="Auto-detect and run tests in a sandboxed environment",
        inputSchema={
            "type": "object",
            "properties": {
                "env_id": {"type": "string", "description": "Environment identifier"}
            },
            "required": ["env_id"],
        },
    ),
    types.Tool(
        name="cleanup",
        description="Clean up a sandboxed environment",
        inputSchema={
            "type": "object",
            "properties": {
                "env_id": {"type": "string", "description": "Environment identifier"}
            },
            "required": ["env_id"],
        },
    ),
]


async def init_server() -> Server:
    logger.info(f"Registered tools: {', '.join(t.name for t in tools)}")

    server = Server("mcp-runtime-server")

    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        logger.debug("Tools requested")
        return tools

    @server.call_tool()
    async def call_tool(
        name: str, arguments: Dict[str, Any]
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        try:
            logger.debug(f"Tool called: {name} with args: {arguments}")

            if name == "create_environment":
                env = await create_environment(arguments["github_url"])
                ENVIRONMENTS[env.id] = env
                result = {
                    "id": env.id,
                    "working_dir": str(env.work_dir),
                    "created_at": env.created_at.isoformat(),
                    "runtime": env.runtime.value,
                }
                return [types.TextContent(text=json.dumps(result), type="text")]

            elif name == "run_tests":
                if arguments["env_id"] not in ENVIRONMENTS:
                    return [
                        types.TextContent(
                            text=json.dumps(
                                {
                                    "success": False,
                                    "error": f"Unknown environment: {arguments['env_id']}",
                                }
                            ),
                            type="text",
                        )
                    ]

                env = ENVIRONMENTS[arguments["env_id"]]
                return cast(
                    list[
                        types.TextContent | types.ImageContent | types.EmbeddedResource
                    ],
                    await auto_run_tests(env),
                )

            elif name == "cleanup":
                env_id = arguments["env_id"]
                if env_id in ENVIRONMENTS:
                    env = ENVIRONMENTS.pop(env_id)
                    cleanup_environment(env)
                return [
                    types.TextContent(text=json.dumps({"success": True}), type="text")
                ]

            return [
                types.TextContent(
                    text=json.dumps(
                        {"success": False, "error": f"Unknown tool: {name}"}
                    ),
                    type="text",
                )
            ]

        except Exception as e:
            logger.exception(f"Tool invocation failed: {str(e)}")
            return [
                types.TextContent(
                    text=json.dumps({"success": False, "error": str(e)}), type="text"
                )
            ]

    @server.progress_notification()
    async def handle_progress(
        progress_token: str | int, progress: float, total: float | None = None
    ) -> None:
        """Handle progress notifications."""
        logger.debug(f"Progress notification: {progress}/{total if total else '?'}")

    return server


async def cleanup_all_environments():
    for env_id, env in list(ENVIRONMENTS.items()):
        try:
            cleanup_environment(env)
            ENVIRONMENTS.pop(env_id)
        except Exception as e:
            logger.error(f"Failed to cleanup environment {env_id}: {e}")


async def serve() -> None:
    configure_logging()
    logger.info("Starting MCP runtime server")

    server = await init_server()
    try:
        async with stdio.stdio_server() as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name="mcp-runtime-server",
                server_version="0.1.0",
                capabilities=types.ServerCapabilities(
                    tools=types.ToolsCapability(listChanged=False),
                    logging=types.LoggingCapability(),
                ),
            )
            await server.run(read_stream, write_stream, init_options)
    except asyncio.CancelledError:
        logger.info("Server shutdown initiated")
        await cleanup_all_environments()
    except Exception as e:
        logger.exception(f"Server error: {e}")
        await cleanup_all_environments()
        raise
    finally:
        await cleanup_all_environments()


def handle_shutdown(signum, frame):
    logger.info(f"Shutting down on signal {signum}")
    sys.exit(0)


def setup_handlers() -> None:
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)


def main() -> None:
    setup_handlers()
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception:
        logger.exception("Fatal server error")
        sys.exit(1)