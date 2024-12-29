"""Binary management package."""
from pathlib import Path
from typing import Dict

from .fetcher import ensure_binary
from .cache import get_cache_dir
from .platforms import get_platform_info

# Export main functions
__all__ = ['ensure_binary', 'get_cache_dir', 'get_platform_info']

# Runtime binary specifications
RUNTIME_BINARIES = {
    "node": {
        "version": "20.10.0",
        "url_template": "https://nodejs.org/dist/v{version}/node-v{version}-{platform}-{arch}.tar.gz",
        "checksum_template": "https://nodejs.org/dist/v{version}/SHASUMS256.txt",
        "binary_path": "bin/node",
        "npx_path": "bin/npx"
    },
    "bun": {
        "version": "1.0.21",
        "url_template": "https://github.com/oven-sh/bun/releases/download/bun-v{version}/bun-{platform}-{arch}.zip",
        "checksum_template": "https://github.com/oven-sh/bun/releases/download/bun-v{version}/SHASUMS256.txt",
        "binary_path": "bun"
    },
    "uv": {
        "version": "0.1.13",
        "url_template": "https://github.com/astral-sh/uv/releases/download/{version}/uv-{platform}-{arch}.tar.gz",
        "checksum_template": "https://github.com/astral-sh/uv/releases/download/{version}/checksums.txt",
        "binary_path": "uv"
    }
}