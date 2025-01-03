"""Tests for test validation functionality."""

import pytest

from mcp_runtime_server.testing.validation import (
    validate_test_results,
)


def test_validate_test_results_basic():
    """Test basic validation of test results."""
    # Test None results
    with pytest.raises(ValueError, match="cannot be None"):
        validate_test_results(None)

    # Test non-dict results
    with pytest.raises(ValueError, match="must be a dictionary"):
        validate_test_results(["not", "a", "dict"])

    # Test missing framework
    with pytest.raises(ValueError, match="missing framework"):
        validate_test_results({"success": True})

    # Test missing success
    with pytest.raises(ValueError, match="missing success indicator"):
        validate_test_results({"framework": "pytest"})

    # Test unknown framework
    with pytest.raises(ValueError, match="unknown framework"):
        validate_test_results({"framework": "unknown", "success": True})


def test_validate_pytest_results():
    """Test validation of pytest results."""
    # Valid pytest results
    valid_results = {
        "framework": "pytest",
        "success": True,
        "total": 5,
        "passed": 4,
        "failed": 1,
        "skipped": 0,
        "test_cases": [],
    }
    assert validate_test_results(valid_results) is True

    # Test missing required fields
    invalid_results = {
        "framework": "pytest",
        "success": True,
        "total": 5,
        # missing other required fields
    }
    with pytest.raises(ValueError, match="missing fields"):
        validate_test_results(invalid_results)


def test_validate_unittest_results():
    """Test validation of unittest results."""
    # Valid unittest results
    valid_results = {
        "framework": "unittest",
        "success": True,
        "test_dirs": ["/path/to/tests"],
        "results": [
            {
                "success": True,
                "test_dir": "/path/to/tests",
                "stdout": "OK",
                "stderr": "",
            }
        ],
    }
    assert validate_test_results(valid_results) is True

    # Test missing required fields
    invalid_results = {
        "framework": "unittest",
        "success": True,
        # missing test_dirs and results
    }
    with pytest.raises(ValueError, match="missing fields"):
        validate_test_results(invalid_results)
