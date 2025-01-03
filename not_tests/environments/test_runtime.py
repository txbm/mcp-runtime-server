"""Tests for runtime detection and management."""

import os
import pytest

from mcp_runtime_server.types import Runtime, PackageManager
from mcp_runtime_server.environments.runtime import (
    detect_runtime,
    make_runtime_env,
    find_binary,
    get_runtime_bin_dir,
)


def test_runtime_detection(tmp_path):
    """Test runtime detection from project files."""
    pkg_json = tmp_path / "package.json"
    pkg_json.touch()
    assert detect_runtime(tmp_path) == Runtime.NODE

    bun_lock = tmp_path / "bun.lockb"
    bun_lock.touch()
    assert detect_runtime(tmp_path) == Runtime.BUN

    pkg_json.unlink()
    bun_lock.unlink()

    for pyfile in ["pyproject.toml", "setup.py"]:
        f = tmp_path / pyfile
        f.touch()
        assert detect_runtime(tmp_path) == Runtime.PYTHON
        f.unlink()


def test_runtime_detection_nested(tmp_path):
    """Test detection with nested config files."""
    nested = tmp_path / "src" / "project"
    nested.mkdir(parents=True)

    pkg_json = nested / "package.json"
    pkg_json.touch()
    assert detect_runtime(tmp_path) == Runtime.NODE

    bun_lock = nested / "bun.lockb"
    bun_lock.touch()
    assert detect_runtime(tmp_path) == Runtime.BUN


def test_runtime_detection_fails(tmp_path):
    """Test detection with no config files."""
    with pytest.raises(ValueError, match="No supported runtime detected"):
        detect_runtime(tmp_path)


def test_package_manager_mapping():
    """Test runtime to package manager mapping."""
    assert PackageManager.for_runtime(Runtime.PYTHON) == PackageManager.UV
    assert PackageManager.for_runtime(Runtime.NODE) == PackageManager.NPM
    assert PackageManager.for_runtime(Runtime.BUN) == PackageManager.BUN


def test_find_binary(tmp_path):
    """Test binary finding logic."""
    sys_path = "/usr/bin:/usr/local/bin"
    test_binary = "test-binary"
    test_binary_path = tmp_path / test_binary
    test_binary_path.touch()
    test_binary_path.chmod(0o755)
    
    paths = [str(tmp_path)]
    found = find_binary(test_binary, paths, env_path=sys_path)
    assert found == test_binary_path


def test_find_binary_windows(tmp_path):
    """Test binary finding on Windows."""
    if os.name != "nt":
        pytest.skip("Windows-specific test")
        
    test_binary = "test-binary.exe"
    test_binary_path = tmp_path / test_binary
    test_binary_path.touch()
    
    paths = [str(tmp_path)]
    found = find_binary("test-binary", paths)
    assert found == test_binary_path


def test_runtime_bin_dir(tmp_path):
    """Test runtime binary directory resolution."""
    # Test Python venv
    venv = tmp_path / ".venv"
    bin_dir = "Scripts" if os.name == "nt" else "bin"
    venv_bin = venv / bin_dir
    venv_bin.mkdir(parents=True)

    result = get_runtime_bin_dir(tmp_path, Runtime.PYTHON)
    assert result == venv_bin

    # Test Node modules
    node_bin = tmp_path / "node_modules" / ".bin"
    node_bin.mkdir(parents=True)

    result = get_runtime_bin_dir(tmp_path, Runtime.NODE)
    assert result == node_bin


def test_make_runtime_env(tmp_path):
    """Test runtime environment variable setup."""
    base_env = {"PATH": "/usr/bin", "HOME": "/home/user"}

    # Test Python env
    venv = tmp_path / ".venv"
    bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
    bin_dir.mkdir(parents=True)

    env = make_runtime_env(Runtime.PYTHON, sandbox_work_dir=tmp_path, base_env=base_env)
    assert str(bin_dir) in env["PATH"]
    assert env["VIRTUAL_ENV"] == str(venv)
    assert env["PYTHONPATH"] == str(tmp_path)

    # Test Node env
    node_bin = tmp_path / "node_modules" / ".bin"
    node_bin.mkdir(parents=True)

    env = make_runtime_env(Runtime.NODE, sandbox_work_dir=tmp_path, base_env=base_env)
    assert str(node_bin) in env["PATH"]
    assert env["NODE_PATH"] == str(tmp_path / "node_modules")
    assert env["NODE_NO_WARNINGS"] == "1"
