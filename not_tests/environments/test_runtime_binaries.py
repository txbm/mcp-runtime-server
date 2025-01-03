"""Tests for runtime binary management."""

import os
import tempfile
import zipfile
import tarfile

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from mcp_runtime_server.types import Runtime
from mcp_runtime_server.environments.runtime import RUNTIME_CONFIGS
from mcp_runtime_server.environments.runtime_binaries import (
    download_binary,
    extract_binary,
    verify_checksum,
    ensure_binary,
    get_archive_files,
)


def test_get_archive_files(tmp_path):
    """Test listing files from different archive types."""
    test_binary = "test-binary"

    # Test zip archive
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(test_binary, "content")

    with zipfile.ZipFile(zip_path) as archive:
        files = get_archive_files(archive, ".zip")
        assert test_binary in files

    # Test tar.gz archive
    tar_path = tmp_path / "test.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"content")
            tmp.flush()
            tf.add(tmp.name, arcname=test_binary)

    with tarfile.open(tar_path) as archive:
        files = get_archive_files(archive, ".tar.gz")
        assert test_binary in files


def test_extract_binary_zip(tmp_path):
    """Test binary extraction from zip archive."""
    test_binary = "test-binary"
    zip_path = tmp_path / "test.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(test_binary, "content")

    extracted = extract_binary(zip_path, test_binary, tmp_path)
    assert extracted.exists()
    assert extracted.name == test_binary
    if os.name != "nt":
        assert extracted.stat().st_mode & 0o755 == 0o755


def test_extract_binary_tar(tmp_path):
    """Test binary extraction from tar.gz archive."""
    test_binary = "test-binary"
    tar_path = tmp_path / "test.tar.gz"

    with tarfile.open(tar_path, "w:gz") as tf:
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"content")
            tmp.flush()
            tf.add(tmp.name, arcname=test_binary)

    extracted = extract_binary(tar_path, test_binary, tmp_path)
    assert extracted.exists()
    assert extracted.name == test_binary
    if os.name != "nt":
        assert extracted.stat().st_mode & 0o755 == 0o755


def test_extract_binary_not_found(tmp_path):
    """Test extraction fails when binary not in archive."""
    test_binary = "test-binary"
    wrong_binary = "wrong-binary"
    zip_path = tmp_path / "test.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(wrong_binary, "content")

    with pytest.raises(ValueError, match=f"Binary {test_binary} not found in archive"):
        extract_binary(zip_path, test_binary, tmp_path)


@pytest.mark.asyncio
async def test_verify_checksum(tmp_path):
    """Test checksum verification."""
    test_binary = "test-binary"
    test_path = tmp_path / test_binary
    test_content = b"test content"

    with open(test_path, "wb") as f:
        f.write(test_content)

    import hashlib

    expected_sha = hashlib.sha256(test_content).hexdigest()
    checksum_content = f"{expected_sha}  {test_binary}"

    mock_response = MagicMock()
    mock_response.text = AsyncMock(return_value=checksum_content)
    mock_response.raise_for_status = MagicMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await verify_checksum(test_path, "mock_url", test_binary)
        assert result is True


@pytest.mark.asyncio
async def test_ensure_binary(tmp_path):
    """Test ensuring binary is available."""
    test_binary = "test-binary"
    test_content = b"test content"
    test_version = "1.0.0"

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.content.read = AsyncMock(return_value=test_content)
    mock_response.raise_for_status = MagicMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)

    with (
        patch("aiohttp.ClientSession", return_value=mock_session),
        patch(
            "mcp_runtime_server.environments.runtime_binaries.get_binary_release_version",
            new_callable=AsyncMock,
            return_value=test_version,
        ),
        patch(
            "mcp_runtime_server.environments.runtime_binaries.get_binary_path",
            return_value=None,
        ),
        patch(
            "mcp_runtime_server.environments.runtime_binaries.cache_binary",
            return_value=tmp_path / test_binary,
        ),
    ):

        config = RUNTIME_CONFIGS[Runtime.NODE]
        binary_path = await ensure_binary(Runtime.NODE, config)
        assert binary_path.name == test_binary


@pytest.mark.asyncio
async def test_ensure_binary_cached(tmp_path):
    """Test ensuring binary uses cache when available."""
    test_binary = "test-binary"
    test_version = "1.0.0"
    cached_path = tmp_path / test_binary

    with (
        patch(
            "mcp_runtime_server.environments.runtime_binaries.get_binary_release_version",
            new_callable=AsyncMock,
            return_value=test_version,
        ),
        patch(
            "mcp_runtime_server.environments.runtime_binaries.get_binary_path",
            return_value=cached_path,
        ),
    ):

        config = RUNTIME_CONFIGS[Runtime.NODE]
        binary_path = await ensure_binary(Runtime.NODE, config)
        assert binary_path == cached_path


@pytest.mark.asyncio
async def test_download_binary(tmp_path):
    """Test binary download."""
    test_content = b"test content"
    dest_path = tmp_path / "test-binary"

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.content.read = AsyncMock(return_value=test_content)
    mock_response.raise_for_status = MagicMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await download_binary("mock_url", dest_path)
        assert dest_path.exists()
        with open(dest_path, "rb") as f:
            assert f.read() == test_content
