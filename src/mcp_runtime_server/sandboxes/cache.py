"""Binary cache management."""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Optional

from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

CACHE_DIR = Path(os.path.expanduser("~/.cache/mcp_runtime_server/binaries"))
MAX_CACHE_SIZE = 1024 * 1024 * 1024  # 1 GB

CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_path(url_hash: str) -> Path:
    return CACHE_DIR / url_hash


def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""

    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def check_binary_cache(url_hash: str, archive_name: str) -> Optional[Path]:
    """Get cached binary path if it exists."""

    cache_path = _get_cache_path(url_hash) / archive_name
    hash_path = cache_path.with_suffix(".sha256")

    logger.debug(
        {"event": "checking_cache", "cache_path": cache_path, "hash_path": hash_path}
    )

    if not cache_path.exists() or not hash_path.exists():
        return None

    stored_hash = hash_path.read_text().strip()
    current_hash = compute_file_hash(cache_path)

    if stored_hash != current_hash:
        logger.error(
            {
                "event": "cache_validation_failed",
                "archive": archive_name,
                "stored_hash": stored_hash,
                "computed_hash": current_hash,
            }
        )
        return None

    return cache_path


def cache_binary(url_hash: str, archive_path: Path, checksum: str) -> Path:
    """Cache a binary file with version and checksum."""

    cache_path = _get_cache_path(url_hash)
    cache_path.mkdir(parents=True, exist_ok=True)
    cache_path = cache_path / archive_path.name

    logger.debug(
        {
            "event": "caching_archive",
            "archive_path": archive_path,
            "cache_path": cache_path,
        }
    )
    shutil.copy2(archive_path, cache_path)

    hash_path = cache_path.with_suffix(".sha256")
    computed_hash = compute_file_hash(cache_path)
    hash_path.write_text(computed_hash)

    # Verify checksum if provided
    if checksum and computed_hash != checksum:
        logger.error(
            {
                "event": "checksum_verification_failed",
                "archive_path": archive_path,
                "computed": computed_hash,
                "expected": checksum,
            }
        )
        raise RuntimeError(f"Checksum mismatch for {archive_path}")

    logger.info(
        {
            "event": "binary_cached",
            "archive_name": archive_path,
            "path": cache_path,
            "hash": computed_hash,
        }
    )

    return cache_path


def cleanup_cache() -> None:
    """Remove old cache entries if total size exceeds limit."""

    if not CACHE_DIR.exists():
        return

    total_size = sum(f.stat().st_size for f in CACHE_DIR.rglob("*") if f.is_file())

    if total_size > MAX_CACHE_SIZE:
        # Get list of binaries sorted by modification time
        cache_files = sorted(
            [(f, f.stat().st_mtime) for f in CACHE_DIR.rglob("*")],
            key=lambda x: x[1],
        )

        # Remove oldest files until under limit
        for cache_file, _ in cache_files:
            if total_size <= MAX_CACHE_SIZE:
                break

            file_size = cache_file.stat().st_size
            cache_file.unlink()
            cache_file.with_suffix(".sha256").unlink()
            total_size -= file_size

            logger.info(
                {
                    "event": "cache_file_removed",
                    "path": str(cache_file),
                    "size": file_size,
                }
            )
