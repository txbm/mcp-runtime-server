"""Tests for test execution functionality."""

import json
import pytest
from mcp.types import TextContent
from mcp_runtime_server.types import Environment, RunTestResult
from mcp_runtime_server.environments.environment import create_environment
from mcp_runtime_server.testing.execution import auto_run_tests


@pytest.mark.asyncio
@pytest.mark.skip()
async def test_auto_run_tests_success():
    """Test running tests with pytest on the actual repo."""
    env = await create_environment("https://github.com/txbm/mcp-runtime-server")
    result = await auto_run_tests(env)

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"

    data = json.loads(result[0].text)
    assert data["success"] is True
    assert len(data["frameworks"]) == 1

    framework = data["frameworks"][0]
    assert framework["framework"] == "pytest"
    assert framework["success"] is True

    # Basic test metrics should be present
    assert "total" in framework
    assert "passed" in framework
    assert "failed" in framework
    assert "skipped" in framework
    assert "test_cases" in framework
