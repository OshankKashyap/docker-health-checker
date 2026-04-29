"""
Docker Health Checker
=====================
Monitors a Docker daemon and a specific container, logging their health status
at a configurable interval. Reads configuration from environment variables and
uses a rotating log file alongside coloured terminal output (via logger.py).

Environment variables
---------------------
CONTAINER_NAME   : (required) Name of the Docker container to watch.
PRUNE_LOG_FILE   : (optional) Override the default log file path.

Usage
-----
    CONTAINER_NAME=my_app python healthchecker.py
"""

import os
import time
import docker
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from logger import get_logger

# Load .env file into the process environment before reading any variables.
load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

# In-memory store for validated environment variables populated by load_env_vars().
env_vars: dict[str, str] = {}

# How long (seconds) the watcher sleeps between health checks.
WATCH_INTERVAL_SECONDS = 10

# Log file path — override via PRUNE_LOG_FILE env var if needed.
LOG_FILE = os.environ.get(
    "PRUNE_LOG_FILE",
    Path(os.environ.get("HOME", "/tmp")).joinpath("var", "log", "healthchecker.log"),
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def load_env_vars() -> tuple[bool, str]:
    """
    Validate and cache required environment variables into `env_vars`.

    Returns
    -------
    (True, summary_message)   — all variables present and non-empty.
    (False, error_message)    — a required variable is missing or blank.
    """
    required = ["CONTAINER_NAME"]

    for var in required:
        value = os.getenv(var)

        if value is None:
            return False, f"Environment variable '{var}' is not set"

        if value.strip() == "":
            return False, f"Environment variable '{var}' is empty"

        env_vars[var] = value

    return True, f"Loaded {len(required)} environment variable(s)"


def check_docker_running() -> tuple[bool, str]:
    """
    Verify that the Docker daemon is active via systemctl.

    Returns
    -------
    (True,  "Docker is running")          — daemon is active.
    (False, "Docker is not running")      — daemon is inactive or unreachable.
    """
    result = subprocess.run(
        ["systemctl", "is-active", "docker"],
        capture_output=True,
    )
    state = result.stdout.strip().decode("utf-8")

    if state != "active":
        return False, "Docker is not running"

    return True, "Docker is running"


def check_docker_container(container_name: str) -> tuple[bool, str]:
    """
    Check whether a named Docker container exists and is in the 'running' state.

    Parameters
    ----------
    container_name : Name (or ID) of the container to inspect.

    Returns
    -------
    (True,  "Container <name> is running")      — container found and running.
    (False, "Container <name> not found")        — container does not exist.
    (False, "Container <name> is not running")   — container exists but stopped/paused/etc.
    """
    client = docker.from_env()

    try:
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        return False, f"Container '{container_name}' not found"

    if container.status != "running":
        return (
            False,
            f"Container '{container_name}' is not running (status: {container.status})",
        )

    return True, f"Container '{container_name}' is running"


def run_health_checks(container_name: str, logger) -> bool:
    """
    Execute the full set of health checks (Docker daemon + container).

    Logs each step and returns False immediately on the first failure so the
    caller can decide whether to exit or continue the watch loop.

    Parameters
    ----------
    container_name : Name of the Docker container to verify.
    logger         : Logger instance used for output.

    Returns
    -------
    True  — all checks passed.
    False — at least one check failed (error already logged).
    """
    # Check 1: Docker daemon
    logger.info("Checking if Docker is running")
    success, message = check_docker_running()
    if not success:
        logger.error(message)
        return False
    logger.info(message)

    # Check 2: Target container
    logger.info("Checking if Docker container is running")
    success, message = check_docker_container(container_name)
    if not success:
        logger.error(message)
        return False
    logger.info(message)

    return True


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger = get_logger("HealthChecker", log_file=LOG_FILE)
    logger.info("Health checker starting up")

    # ── Step 1: Validate environment ──────────────────────────────────────────
    logger.info("Loading environment variables")
    success, message = load_env_vars()
    if not success:
        logger.error(message)
        exit(1)
    logger.info(message)

    container_name = env_vars["CONTAINER_NAME"]

    # ── Step 2: Initial health check before entering the watch loop ───────────
    logger.info("Running initial health checks")
    if not run_health_checks(container_name, logger):
        exit(1)
    logger.info("Initial health checks passed — starting watcher")

    # ── Step 3: Continuous watch loop ─────────────────────────────────────────
    while True:
        time.sleep(WATCH_INTERVAL_SECONDS)

        # Stamp each iteration so log files clearly show when each check ran.
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{timestamp}] Running scheduled health check")

        if not run_health_checks(container_name, logger):
            logger.critical("Health check failed — stopping watcher")
            break

        logger.info(f"[{timestamp}] All checks passed")

    logger.critical("Something terrible has happened — shutting down")
    exit(1)
