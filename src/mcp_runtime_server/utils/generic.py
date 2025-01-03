import shutil
import json
from pathlib import Path
import hashlib

from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


def dict_to_hash(d):
    json_string = json.dumps(d, sort_keys=True).encode()
    return hashlib.sha256(json_string).hexdigest()


def move_files(src: Path, dst: Path):

    for item in src.iterdir():
        if item.is_file():
            logger.debug({"event": "moving_file", "file": item, "dst": dst})
            shutil.move(str(item), str(dst))
