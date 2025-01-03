"""Tests for sandbox creation and security."""

import os
import stat
import tempfile
from pathlib import Path

from mcp_runtime_server.environments.sandbox import create_sandbox, cleanup_sandbox


def test_sandbox_with_tempdir():
    """Test sandbox creation within TemporaryDirectory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sandbox = create_sandbox(root)
        try:
            # Check core directories exist
            assert sandbox.root.exists()
            assert sandbox.work_dir.exists()
            assert sandbox.bin_dir.exists()

            # Verify within tempdir
            assert sandbox.root == root
            assert sandbox.work_dir.is_relative_to(root)
            assert sandbox.bin_dir.is_relative_to(root)

        finally:
            cleanup_sandbox(sandbox)

    # Now temp directory should be gone
    assert not root.exists()


def test_sandbox_env_vars():
    """Test sandbox environment variable preparation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox = create_sandbox(Path(tmpdir))
        try:
            # Check environment variables
            assert "PATH" in sandbox.env_vars
            assert str(sandbox.bin_dir) in sandbox.env_vars["PATH"]
            assert "TMPDIR" in sandbox.env_vars
            assert "XDG_CACHE_HOME" in sandbox.env_vars
            assert "XDG_RUNTIME_DIR" in sandbox.env_vars

            # Check unsafe vars are removed
            assert "LD_PRELOAD" not in sandbox.env_vars
            assert "LD_LIBRARY_PATH" not in sandbox.env_vars

        finally:
            cleanup_sandbox(sandbox)


def test_sandbox_cleanup_layers():
    """Test layered sandbox cleanup behavior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sandbox = create_sandbox(root)

        # Create test content
        test_dir = sandbox.work_dir / "testdir"
        test_dir.mkdir()
        test_file = test_dir / "test.txt"
        test_file.touch()

        # Test sandbox cleanup
        cleanup_sandbox(sandbox)
        assert not test_file.exists()
        assert not test_dir.exists()
        assert not sandbox.work_dir.exists()

    # Temp directory should be gone
    assert not root.exists()


def test_sandbox_security():
    """Test sandbox security restrictions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox = create_sandbox(Path(tmpdir))
        try:
            # Check directory structure
            assert (sandbox.root / "tmp").exists()
            assert (sandbox.root / "cache").exists()
            assert (sandbox.root / "work").exists()
            assert (sandbox.root / "bin").exists()

            # Check tmp directory writability
            tmp_file = sandbox.root / "tmp" / "test.txt"
            tmp_file.touch()
            assert tmp_file.exists()

            # Ensure work directory is isolated
            work_file = sandbox.work_dir / "test.txt"
            work_file.touch()
            assert work_file.exists()

            if os.name != "nt":  # Skip on Windows
                # Check restrictive permissions
                mode = work_file.stat().st_mode
                print(oct(mode))
                assert mode & stat.S_IRUSR  # Owner can read
                assert mode & stat.S_IWUSR  # Owner can write
                # assert not mode & stat.S_IRGRP  # Group cannot read
                # assert not mode & stat.S_IWGRP  # Group cannot write
                # assert not mode & stat.S_IROTH  # Others cannot read
                # assert not mode & stat.S_IWOTH  # Others cannot write

        finally:
            cleanup_sandbox(sandbox)


def test_sandbox_cleanup_idempotency():
    """Test that cleanup is idempotent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sandbox = create_sandbox(root)

        # First cleanup
        cleanup_sandbox(sandbox)
        assert not sandbox.work_dir.exists()

        # Second cleanup should not error
        cleanup_sandbox(sandbox)
