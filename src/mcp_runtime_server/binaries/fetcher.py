"""Binary fetching and verification."""
import asyncio
import aiohttp
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import Optional, Tuple

from . import RUNTIME_BINARIES
from .platforms import get_platform_info
from .cache import (
    get_binary_path,
    cache_binary,
    cleanup_cache,
    verify_checksum
)


async def download_file(url: str, dest: Path) -> None:
    """Download a file from a URL.
    
    Args:
        url: URL to download from
        dest: Destination path
        
    Raises:
        RuntimeError: If download fails
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Failed to download {url}: {response.status}"
                )
            
            with open(dest, 'wb') as f:
                while True:
                    chunk = await response.content.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)


async def get_checksum(url: str, filename: str) -> str:
    """Get checksum for a binary from checksum file.
    
    Args:
        url: URL to checksum file
        filename: Binary filename to find checksum for
        
    Returns:
        Checksum string
        
    Raises:
        RuntimeError: If checksum not found
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Failed to fetch checksums: {response.status}"
                )
            
            content = await response.text()
            
            for line in content.splitlines():
                try:
                    checksum, name = line.strip().split(maxsplit=1)
                    if name.endswith(filename):
                        return checksum
                except ValueError:
                    continue
                    
    raise RuntimeError(f"Checksum not found for {filename}")


def extract_binary(
    archive_path: Path,
    binary_path: str,
    dest_dir: Path
) -> Path:
    """Extract binary from archive.
    
    Args:
        archive_path: Path to archive
        binary_path: Path to binary within archive
        dest_dir: Destination directory
        
    Returns:
        Path to extracted binary
        
    Raises:
        RuntimeError: If extraction fails
    """
    if archive_path.suffix == '.zip':
        with zipfile.ZipFile(archive_path) as zf:
            # Find the binary path in the archive
            binary_name = Path(binary_path).name
            binary_files = [
                f for f in zf.namelist()
                if f.endswith(binary_name)
            ]
            
            if not binary_files:
                raise RuntimeError(f"Binary {binary_name} not found in archive")
                
            # Extract the binary
            zf.extract(binary_files[0], dest_dir)
            return dest_dir / binary_files[0]
            
    else:  # Assume tar.gz
        with tarfile.open(archive_path) as tf:
            # Find the binary path in the archive
            binary_name = Path(binary_path).name
            binary_files = [
                f for f in tf.getnames()
                if f.endswith(binary_name)
            ]
            
            if not binary_files:
                raise RuntimeError(f"Binary {binary_name} not found in archive")
                
            # Extract the binary
            tf.extract(binary_files[0], dest_dir)
            return dest_dir / binary_files[0]


async def fetch_binary(name: str) -> Path:
    """Fetch a binary, downloading if necessary.
    
    Args:
        name: Binary name (e.g. 'node', 'bun', 'uv')
        
    Returns:
        Path to binary
        
    Raises:
        RuntimeError: If binary fetch fails
    """
    if name not in RUNTIME_BINARIES:
        raise ValueError(f"Unknown binary: {name}")
        
    spec = RUNTIME_BINARIES[name]
    version = spec["version"]
    
    # Check cache first
    cached = get_binary_path(name, version)
    if cached:
        return cached
        
    # Get platform info
    platform_info = get_platform_info()
    platform_map = {
        "node": platform_info.node_platform,
        "bun": platform_info.bun_platform,
        "uv": platform_info.uv_platform
    }
    
    # Build URLs
    download_url = spec["url_template"].format(
        version=version,
        platform=platform_map[name].split("-")[0],
        arch=platform_map[name].split("-")[1]
    )
    checksum_url = spec["checksum_template"].format(
        version=version
    )
    
    # Create temporary directory for download
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Download archive
        archive_name = Path(download_url).name
        archive_path = tmp_path / archive_name
        await download_file(download_url, archive_path)
        
        # Get and verify checksum
        checksum = await get_checksum(checksum_url, archive_name)
        if not verify_checksum(archive_path, checksum):
            raise RuntimeError(f"Checksum verification failed for {name}")
        
        # Extract binary
        binary = extract_binary(
            archive_path,
            spec["binary_path"],
            tmp_path
        )
        
        # Cache the binary
        cached_path = cache_binary(name, version, binary, checksum)
        
        # Clean up old cached versions
        cleanup_cache()
        
        return cached_path


async def ensure_binary(name: str) -> Path:
    """Ensure a binary is available, fetching if needed.
    
    Args:
        name: Binary name
        
    Returns:
        Path to binary
        
    Raises:
        RuntimeError: If binary cannot be ensured
    """
    try:
        return await fetch_binary(name)
    except Exception as e:
        raise RuntimeError(f"Failed to ensure binary {name}: {e}") from e