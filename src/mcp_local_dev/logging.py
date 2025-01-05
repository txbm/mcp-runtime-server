"""Logging configuration and test output formatting."""
import json
import logging
import sys
from typing import Any, Dict
from pathlib import Path

# Don't modify root logger - MCP server uses it for stdout
root = logging.getLogger()
root.handlers = []

class ColorCodes:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"

LEVEL_COLORS = {
    "DEBUG": ColorCodes.BLUE,
    "INFO": ColorCodes.GREEN,
    "WARNING": ColorCodes.YELLOW,
    "ERROR": ColorCodes.RED + ColorCodes.BOLD,
    "CRITICAL": ColorCodes.MAGENTA + ColorCodes.BOLD
}

def format_json_log(record: logging.LogRecord) -> str:
    """Format log record as color-coded JSON."""
    color = LEVEL_COLORS.get(record.levelname, "")
    
    output = {
        "ts": record.asctime if hasattr(record, 'asctime') else '',
        "level": record.levelname,
        "msg": record.getMessage()
    }

    if hasattr(record, "data"):
        output["data"] = record.data

    json_str = json.dumps(output)
    return f"{color}{json_str}{ColorCodes.RESET}"

def configure_logging():
    """Set up application logging with JSON formatting."""
    # Create a custom Formatter class that uses our format function
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            return format_json_log(record)
    
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler.setLevel(logging.INFO)

    app_logger = logging.getLogger("mcp_local_dev")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(handler)
    app_logger.propagate = False

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"mcp_runtime_server.{name}")

def log_with_data(logger: logging.Logger, level: int, msg: str, data: Dict[str, Any] = None):
    """Log a message with optional structured data."""
    if data:
        record = logger.makeRecord(
            logger.name, level, "(unknown)", 0, msg, (), None, extra={"data": data}
        )
        logger.handle(record)
    else:
        logger.log(level, msg)