"""Tests for test results parsing."""

import json
import pytest
from dataclasses import asdict
from mcp.types import TextContent
from mcp_runtime_server.types import TestCase, RunTestResult
from mcp_runtime_server.testing.results import parse_pytest_json, format_test_results


def test_parse_pytest_json():
    """Test parsing of pytest JSON output."""
    report = {
        "summary": {
            "total": 3,
            "passed": 2,
            "failed": 0,
            "skipped": 1
        },
        "tests": [
            {
                "nodeid": "test_module.py::test_function",
                "outcome": "passed",
                "duration": 0.1,
                "stdout": "test output\nanother line"
            },
            {
                "nodeid": "test_module.py::TestClass::test_method",
                "outcome": "passed",
                "duration": 0.2,
                "stdout": "more output"
            },
            {
                "nodeid": "test_module.py::test_skipped",
                "outcome": "skipped",
                "duration": 0,
                "stdout": ""
            }
        ]
    }
    
    result = parse_pytest_json(report)
    
    assert result["success"] is True
    assert result["total"] == 3
    assert result["passed"] == 2
    assert result["failed"] == 0
    assert result["skipped"] == 1
    
    test_cases = result["test_cases"]
    assert len(test_cases) == 3
    
    # Create expected TestCase for comparison
    expected_case = asdict(TestCase(
        name="test_module.py::test_function",
        status="passed",
        output=["test output", "another line"],
        duration=0.1,
        failure_message=None
    ))
    
    # Check first test case matches expected structure
    assert test_cases[0] == expected_case


def test_format_test_results():
    """Test formatting of test results into MCP-compatible format."""
    # Create a proper RunTestResult
    test_case = TestCase(
        name="test_module.py::test_function",
        status="passed",
        output=["test output"],
        duration=0.1
    )
    
    test_output = RunTestResult(
        success=True,
        framework="pytest",
        total=1,
        passed=1,
        failed=0,
        skipped=0,
        test_cases=[asdict(test_case)]
    )
    
    result = format_test_results("pytest", asdict(test_output))
    
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    
    data = json.loads(result[0].text)
    assert data["success"] is True
    assert len(data["frameworks"]) == 1
    
    framework_result = data["frameworks"][0]
    assert framework_result["framework"] == "pytest"
    assert framework_result["success"] is True
    assert framework_result["total"] == 1
    assert framework_result["passed"] == 1
    assert framework_result["failed"] == 0
    assert framework_result["skipped"] == 0
    assert len(framework_result["test_cases"]) == 1
    
    # Verify the test case structure is preserved
    assert framework_result["test_cases"][0] == asdict(test_case)