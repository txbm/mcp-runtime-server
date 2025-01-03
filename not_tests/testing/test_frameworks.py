"""Tests for test framework detection and execution."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from tempfile import TemporaryDirectory

from mcp_runtime_server.types import Environment, Runtime, Sandbox
from mcp_runtime_server.testing.frameworks import (
    TestFramework,
    detect_frameworks,
    run_pytest,
    _has_test_files,
    _check_file_imports,
    _find_test_dirs,
)


def test_has_test_files(tmp_path: Path):
    """Test detection of test files in a directory."""
    # Create test files
    test_dir = tmp_path / "tests"
    test_dir.mkdir()

    (test_dir / "test_one.py").write_text("# Test file")
    (test_dir / "test_two.py").write_text("# Another test")
    (test_dir / "not_a_test.py").write_text("# Not a test")

    assert _has_test_files(test_dir, ".py")
    assert not _has_test_files(test_dir, ".java")
    assert not _has_test_files(tmp_path / "nonexistent", ".py")


def test_check_file_imports(tmp_path: Path):
    """Test detection of imports in Python files."""
    test_file = tmp_path / "test_imports.py"

    # Test pytest import
    test_file.write_text("import pytest\nfrom pytest import fixture")
    assert _check_file_imports(test_file, ["pytest"])

    # Test multiple imports
    test_file.write_text(
        """
import pytest
from pytest import fixture
import unittest
from unittest import TestCase
"""
    )
    assert _check_file_imports(test_file, ["pytest"])
    assert _check_file_imports(test_file, ["unittest"])

    # Test no matching imports
    test_file.write_text("import other\nfrom other import thing")
    assert not _check_file_imports(test_file, ["pytest", "unittest"])


def test_find_test_dirs(tmp_path: Path):
    """Test finding test directories in a project."""
    # Create test directory structure
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/unit").mkdir()
    (tmp_path / "src/test").mkdir(parents=True)

    # Create test files
    (tmp_path / "tests/test_main.py").write_text("# Test file")
    (tmp_path / "tests/unit/test_utils.py").write_text("# Unit test")
    (tmp_path / "src/test/test_module.py").write_text("# Module test")

    test_dirs = _find_test_dirs(tmp_path)

    # Convert to set of relative paths for easier comparison
    relative_dirs = {str(p.relative_to(tmp_path)) for p in test_dirs}

    assert "tests" in relative_dirs
    assert "tests/unit" in relative_dirs
    assert "src/test" in relative_dirs


def test_detect_frameworks(tmp_path: Path):
    """Test framework detection with various configurations."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    # Test pytest detection via conftest
    (tests_dir / "conftest.py").write_text("# Pytest config")
    (tests_dir / "test_something.py").write_text(
        """
import pytest
def test_function():
    pass
"""
    )

    frameworks = detect_frameworks(str(tmp_path))
    assert TestFramework.PYTEST in frameworks

    # Test detection via imports only
    (tests_dir / "conftest.py").unlink()
    frameworks = detect_frameworks(str(tmp_path))
    assert TestFramework.PYTEST in frameworks

    # Test detection via pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.pytest]
testpaths = ["tests"]
"""
    )
    frameworks = detect_frameworks(str(tmp_path))
    assert TestFramework.PYTEST in frameworks


@pytest.mark.asyncio
@pytest.mark.skip()
async def test_run_pytest():
    """Test running pytest tests."""
    # Create mock environment with all required fields
    tempdir = TemporaryDirectory()
    work_dir = Path("/path/to/work")
    bin_dir = Path("/path/to/bin")

    sandbox = Sandbox(
        root=Path("/path/to/root"), work_dir=work_dir, bin_dir=bin_dir, env_vars={}
    )

    env = Mock(spec=Environment)
    env.id = "test-env"
    env.runtime = Runtime.PYTHON
    env.created_at = datetime.now()
    env.env_vars = {}
    env.sandbox = sandbox
    env.tempdir = tempdir

    # Mock pytest executable existence
    pytest_path = sandbox.bin_dir / "pytest"
    pytest_path = Mock(spec=pytest_path)
    pytest_path.exists.return_value = True

    # Mock successful test run
    process_mock = AsyncMock()
    process_mock.returncode = 0
    process_mock.communicate.return_value = (
        b"",  # stdout
        b'{"summary": {"total": 1, "passed": 1, "failed": 0, "skipped": 0}, "tests": []}',  # stderr
    )

    with patch(
        "mcp_runtime_server.testing.frameworks.run_command", return_value=process_mock
    ):
        result = await run_pytest(env)
        print(result)

    assert result["success"] is True
    assert result["framework"] == "pytest"
    assert result["total"] == 1
    assert result["passed"] == 1
    assert result["failed"] == 0
    assert result["skipped"] == 0

    tempdir.cleanup()
