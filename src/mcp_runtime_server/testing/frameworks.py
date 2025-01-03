"""Test framework utilities."""

import json
import os
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Set

from mcp_runtime_server.environments.sandbox import run_sandboxed_command
from mcp_runtime_server.types import Environment
from mcp_runtime_server.testing.results import parse_pytest_json
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


class TestFramework(str, Enum):
    PYTEST = "pytest"


def _has_test_files(directory: Path, pattern: str) -> bool:
    """Check if directory contains files matching the test pattern."""
    if not directory.exists():
        logger.debug(
            {
                "event": "checking_test_directory",
                "directory": str(directory),
                "exists": False,
            }
        )
        return False

    for root, _, files in os.walk(directory):
        test_files = [f for f in files if f.startswith("test_") and f.endswith(pattern)]
        logger.debug(
            {
                "event": "scanning_directory",
                "directory": root,
                "test_files_found": test_files,
            }
        )
        if test_files:
            return True
    return False


def _check_file_imports(file_path: Path, import_names: List[str]) -> bool:
    """Check if a Python file imports any of the specified modules."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            logger.debug(
                {
                    "event": "checking_file_imports",
                    "file": str(file_path),
                    "searching_for": import_names,
                    "content_preview": content[:200],  # First 200 chars for context
                }
            )
            found_imports = [
                name
                for name in import_names
                if f"import {name}" in content or f"from {name}" in content
            ]
            if found_imports:
                logger.debug(
                    {
                        "event": "imports_found",
                        "file": str(file_path),
                        "found": found_imports,
                    }
                )
                return True
            logger.debug(
                {
                    "event": "no_imports_found",
                    "file": str(file_path),
                    "searched_for": import_names,
                }
            )
            return False
    except Exception as e:
        logger.error(
            {
                "event": "file_import_check_error",
                "file": str(file_path),
                "error": str(e),
            }
        )
        return False


def _find_test_dirs(project_dir: Path) -> Set[Path]:
    """Find all potential test directories in the project."""
    test_dirs = set()
    test_dir_names = ["tests", "test", "testing", "unit_tests", "integration_tests"]

    logger.debug(
        {
            "event": "searching_test_directories",
            "project_dir": str(project_dir),
            "looking_for": test_dir_names,
        }
    )

    for root, dirs, _ in os.walk(project_dir):
        root_path = Path(root)

        matched_dirs = [d for d in dirs if d.lower() in test_dir_names]
        if matched_dirs:
            logger.debug(
                {
                    "event": "found_test_dir_names",
                    "root": str(root_path),
                    "matches": matched_dirs,
                }
            )
            test_dirs.update(root_path / d for d in matched_dirs)

        test_file_dirs = [d for d in dirs if _has_test_files(root_path / d, ".py")]
        if test_file_dirs:
            logger.debug(
                {
                    "event": "found_dirs_with_test_files",
                    "root": str(root_path),
                    "matches": test_file_dirs,
                }
            )
            test_dirs.update(root_path / d for d in test_file_dirs)

    logger.debug(
        {
            "event": "test_directory_search_complete",
            "found_directories": [str(d) for d in test_dirs],
        }
    )

    return test_dirs


def detect_frameworks(env: Environment) -> List[TestFramework]:
    """Detect test frameworks in a project directory."""
    path = env.sandbox.work_dir
    frameworks = set()

    logger.info({"event": "framework_detection_start", "project_dir": str(path)})

    test_dirs = _find_test_dirs(path)
    if not test_dirs:
        logger.warning({"event": "no_test_directories_found", "project_dir": str(path)})
        return list(frameworks)

    for test_dir in test_dirs:
        logger.info({"event": "test_directory_found", "path": str(test_dir)})

        pytest_indicators = [
            test_dir / "conftest.py",
            path / "pytest.ini",
            path / "setup.cfg",
            path / "tox.ini",
        ]

        existing_indicators = [p for p in pytest_indicators if p.exists()]
        if existing_indicators:
            frameworks.add(TestFramework.PYTEST)
            logger.info(
                {
                    "event": "pytest_config_found",
                    "indicators": [str(p) for p in existing_indicators],
                }
            )

        for root, _, files in os.walk(test_dir):
            logger.debug(
                {
                    "event": "scanning_directory",
                    "directory": str(root),
                    "python_files": [f for f in files if f.endswith(".py")],
                }
            )

            for file in files:
                if not file.endswith(".py"):
                    continue

                file_path = Path(root) / file
                logger.debug({"event": "checking_python_file", "file": str(file_path)})

                if _check_file_imports(file_path, ["pytest"]):
                    frameworks.add(TestFramework.PYTEST)
                    logger.info(
                        {"event": "pytest_import_found", "file": str(file_path)}
                    )

    # Check pyproject.toml
    pyproject_path = path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.debug(
                    {
                        "event": "checking_pyproject_toml",
                        "file": str(pyproject_path),
                        "content_preview": content[:200],
                    }
                )
                if "pytest" in content:
                    frameworks.add(TestFramework.PYTEST)
                    logger.info(
                        {
                            "event": "pytest_dependency_found",
                            "file": str(pyproject_path),
                        }
                    )
        except Exception as e:
            logger.warning({"event": "pyproject_toml_read_error", "error": str(e)})

    logger.info(
        {
            "event": "framework_detection_complete",
            "detected_frameworks": [f.value for f in frameworks],
            "test_directories": [str(d) for d in test_dirs],
        }
    )

    return list(frameworks)


async def run_pytest(env: Environment) -> dict[str, Any]:
    """Run pytest in the environment."""
    result: dict[str, Any] = {"framework": TestFramework.PYTEST.value}

    pytest_cmd = "pytest -vv --no-header --json-report"

    test_dirs = _find_test_dirs(env.sandbox.work_dir)
    if not test_dirs:
        raise RuntimeError("No test directories found")

    all_results = []

    for test_dir in test_dirs:
        process = await run_sandboxed_command(
            env.sandbox,
            f"{pytest_cmd} {test_dir}",
            env.env_vars,
        )
        stdout, stderr = await process.communicate()

        try:
            report = json.loads(stdout)
            summary = parse_pytest_json(report)
            all_results.append(summary)
        except json.JSONDecodeError:
            all_results.append(
                {
                    "success": process.returncode == 0,
                    "error": f"Failed to parse test output for {test_dir}",
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                }
            )

    if all_results:
        result.update(
            {
                "success": all(r.get("success", False) for r in all_results),
                "test_dirs": [str(d) for d in test_dirs],
                "results": all_results,
            }
        )
    else:
        result.update({"success": False, "error": "No test results generated"})

    return result


async def run_framework_tests(
    framework: TestFramework, env: Environment
) -> Dict[str, Any]:
    """Run tests for a specific framework in the environment."""
    logger.info(
        {
            "event": "framework_test_start",
            "framework": framework.value,
            "working_dir": str(env.sandbox.work_dir),
        }
    )

    if framework == TestFramework.PYTEST:
        result = await run_pytest(env)
    else:
        error = f"Unsupported framework: {framework}"
        logger.error({"event": "framework_test_error", "error": error})
        raise ValueError(error)

    logger.info(
        {
            "event": "framework_test_complete",
            "framework": framework.value,
            "success": result.get("success", False),
        }
    )

    return result
