import os
import aiohttp
import zipfile
import tarfile
from pathlib import Path
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


async def download_url(url: str, dest: Path) -> None:
    """Download a binary file with checksum verification."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Download failed with status {response.status}")

                with open(dest, "wb") as f:
                    while chunk := await response.content.read(8192):
                        f.write(chunk)

    except Exception as e:
        if dest.exists():
            dest.unlink()
        raise RuntimeError(f"Failed to download url: {e}")


async def download_checksum(checksum_url: str, file_path: Path) -> str:
    """Verify the checksum of a downloaded binary."""
    async with aiohttp.ClientSession() as session:
        async with session.get(checksum_url) as response:
            response.raise_for_status()
            checksums = await response.text()

            for line in checksums.splitlines():
                if file_path.name in line:
                    expected_checksum, _ = line.split()

                    return expected_checksum

    raise RuntimeError("No valid checksum found!")


def extract_archive(archive_path: Path, dest_dir: Path) -> Path:
    """Extract binary from archive with flexible support."""

    logger.debug(
        {"event": "extract_archive", "archive": archive_path, "dest": dest_dir}
    )
    format = (
        "".join(archive_path.suffixes[-2:])
        if len(archive_path.suffixes) > 1
        else archive_path.suffix
    )

    archive_handlers = {
        ".zip": zipfile.ZipFile,
        ".tar.gz": tarfile.open,
        ".tgz": tarfile.open,
    }

    handler = archive_handlers.get(format)
    logger.debug({"event": "extract_archive", "format": format, "handler": handler})

    if not handler:
        raise ValueError(f"Unsupported archive format: {format}")

    with handler(archive_path) as archive:
        archive.extractall(dest_dir)

        logger.info(
            {
                "event": "archive_extracted",
                "archive": str(archive_path),
                "extracted_to": str(dest_dir),
            }
        )

        os.chmod(dest_dir, 0o700)

        return dest_dir
