"""
Custom Python Logger
====================
Logs to both terminal (with colors) and a rotating log file simultaneously.

Usage:
    from logger import get_logger

    log = get_logger("my_app")
    log.debug("Debug message")
    log.info("Server started on port 8080")
    log.warning("Config file missing, using defaults")
    log.error("Failed to connect to database")
    log.critical("Unrecoverable error — shutting down")
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── ANSI color codes ────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[41m",  # Red background
}

# ── Colored formatter (terminal only) ───────────────────────────────────────


class ColorFormatter(logging.Formatter):
    """Applies ANSI colors to log level names for terminal output."""

    FMT = "{asctime}  {levelname:<9}  {name}  —  {message}"
    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        color = COLORS.get(record.levelname, RESET)
        record.levelname = f"{color}{BOLD}{record.levelname}{RESET}"
        record.name = f"{DIM}{record.name}{RESET}"
        record.asctime = f"{DIM}{self.formatTime(record, self.DATE_FMT)}{RESET}"
        record.message = record.getMessage()
        return self.FMT.format(**record.__dict__)


# ── Plain formatter (log file) ───────────────────────────────────────────────


class FileFormatter(logging.Formatter):
    """Plain-text formatter — no ANSI codes, suitable for log files."""

    FMT = "{asctime}  {levelname:<8}  {name}  —  {message}"
    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        formatter = logging.Formatter(self.FMT, datefmt=self.DATE_FMT, style="{")
        return formatter.format(record)


# ── Factory function ─────────────────────────────────────────────────────────


def get_logger(
    name: str,
    *,
    log_file: str | Path = "app.log",
    level: int = logging.DEBUG,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB per file
    backup_count: int = 3,  # keep 3 rotated files
) -> logging.Logger:
    """
    Create (or retrieve) a named logger that writes to both terminal and file.

    Parameters
    ----------
    name         : Logger name — use __name__ in modules for clarity.
    log_file     : Path to the log file (created automatically).
    level        : Minimum log level (default: DEBUG — captures everything).
    max_bytes    : Max size of each log file before rotation.
    backup_count : Number of rotated backups to retain.

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if the logger already exists
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # ── Terminal handler ──────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColorFormatter())

    # ── Rotating file handler ─────────────────────────────────────────────
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)  # create dirs if needed

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(FileFormatter())

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Don't propagate to root logger (avoids duplicate output)
    logger.propagate = False

    return logger


# ── Quick demo ───────────────────────────────────────────────────────────────
# log = get_logger("demo", log_file=LOG_FILE)

# log.debug("Initialising application…")
# log.info("Server listening on http://localhost:8080")
# log.warning("RATE_LIMIT env var not set — defaulting to 100 req/min")
# log.error("Could not connect to Redis at localhost:6379")
# log.critical("Out of disk space — halting write operations")
