"""
configure.py — Interactive setup wizard for the Docker Health Checker.

Handles first-time configuration by prompting the user for settings
and writing them to the JSON config file at /etc/healthchecker/config.json.
"""

import json
import os
import sys
from pathlib import Path

from config_handler.helpers import get_all_current_containers
from config_handler.terminal_helpers import (
    error,
    get_interface_ips,
    info,
    print_banner,
    print_section,
    prompt,
    prompt_containers,  # ← new, alphabetically placed
    prompt_email_list,
    prompt_int,
    prompt_interface,
    prompt_required,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_DIR_PATH = Path("/etc/healthchecker")
CONFIG_FILE = CONFIG_DIR_PATH / "config.json"

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_config_cache: dict | None = None  # None = not yet loaded

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_config(config: dict) -> None:
    """Validate the loaded config dict before entering monitor mode.

    Checks for required keys, correct types, and sensible values.
    Exits with code 1 on the first validation failure encountered.

    Args:
        config: The deserialised contents of config.json.
    """
    # ── Required top-level string fields ─────────────────────────────────
    required_str_fields = ("sender_email", "app_password", "interface")
    for field in required_str_fields:
        if field not in config:
            error(f"Missing required field: '{field}'")
            sys.exit(1)
        if not isinstance(config[field], str) or not config[field].strip():
            error(f"'{field}' must be a non-empty string.")
            sys.exit(1)

    # ── Positive integer fields ───────────────────────────────────────────
    required_int_fields = ("watch_interval", "max_consecutive_errors")
    for field in required_int_fields:
        if field not in config:
            error(f"Missing required field: '{field}'")
            sys.exit(1)
        if not isinstance(config[field], int) or config[field] <= 0:
            error(f"'{field}' must be a positive integer.")
            sys.exit(1)

    # ── global_recipients ────────────────────────────────────────────────
    if "global_recipients" not in config:
        error("Missing required field: 'global_recipients'")
        sys.exit(1)
    if not isinstance(config["global_recipients"], list):
        error("'global_recipients' must be a list.")
        sys.exit(1)

    # ── projects ─────────────────────────────────────────────────────────
    if "projects" not in config:
        error("Missing required field: 'projects'")
        sys.exit(1)
    if not isinstance(config["projects"], dict):
        error("'projects' must be a dict.")
        sys.exit(1)
    if not config["projects"]:
        error("'projects' must contain at least one entry.")
        sys.exit(1)

    for proj_name, proj_data in config["projects"].items():
        if not isinstance(proj_data, dict):
            error(f"Project '{proj_name}' must be a dict.")
            sys.exit(1)
        if (
            not isinstance(proj_data.get("containers"), list)
            or not proj_data["containers"]
        ):
            error(f"Project '{proj_name}': 'containers' must be a non-empty list.")
            sys.exit(1)
        if not isinstance(proj_data.get("recipients"), list):
            error(f"Project '{proj_name}': 'recipients' must be a list.")
            sys.exit(1)


# ---------------------------------------------------------------------------
# Config accessors
# ---------------------------------------------------------------------------


def check_config_exists() -> None:
    """Exit with an error if the config file is missing or invalid.

    On success, loads the validated config into the module-level
    ``config_data`` dict and prints a confirmation message.
    """
    global config_data

    if not CONFIG_FILE.exists():
        error(f"Config file not found at {CONFIG_FILE}")
        sys.exit(1)

    with open(CONFIG_FILE, "r") as f:
        loaded = json.load(f)

    validate_config(loaded)
    config_data = loaded  # Promote to module scope only after validation.
    print(f"Config file at {CONFIG_FILE} is valid.")


def get_config_file() -> dict:
    """Return the cached config, loading from disk only on first call."""
    global _config_cache

    if _config_cache is None:
        with open(CONFIG_FILE, "r") as f:
            _config_cache = json.load(f)
        validate_config(_config_cache)  # validate once, on first load

    return _config_cache


# ---------------------------------------------------------------------------
# Interactive setup wizard
# ---------------------------------------------------------------------------


def configure_settings() -> None:
    """Run the interactive setup wizard and write the config file.

    Prompts the user for all required settings, then serialises them
    to CONFIG_FILE as JSON. Exits with code 0 on success.
    """
    # Ensure the config directory exists before writing the file.
    if not CONFIG_DIR_PATH.exists():
        info(f"Creating config directory at {CONFIG_DIR_PATH}")
        os.mkdir(CONFIG_DIR_PATH)

    print_banner()

    # ── Email credentials ─────────────────────────────────────────────────
    print_section("Email Credentials")
    sender_email = prompt_required(
        "Sender email",
        "The Gmail address alerts will be sent from.",
    )
    app_password = prompt_required(
        "App password",
        "Generate one at myaccount.google.com → Security → App passwords.",
    )

    # ── Monitoring settings ───────────────────────────────────────────────
    print_section("Monitoring Settings")
    watch_interval = prompt_int(
        "Watch interval (seconds)",
        "How often the health checker polls Docker.",
    )
    max_consecutive_errors = prompt_int(
        "Max consecutive errors",
        "Suppress repeated alerts after this many back-to-back failures.",
    )

    # ── Network interface ─────────────────────────────────────────────────
    print_section("Network Interface")
    interfaces = get_interface_ips()
    interface = prompt_interface(interfaces)

    # ── Recipients ────────────────────────────────────────────────────────
    print_section("Global Recipients")
    global_recipients = prompt_email_list(
        "Global recipient email",
        "These addresses receive alerts for every container.",
    )

    # ── Project configuration ─────────────────────────────────────────────
    print_section("Projects Settings")
    projects: dict[str, dict] = {}
    available_containers = get_all_current_containers()
    while True:
        project_name = prompt("Project name")
        if not project_name.strip():
            break
        project_containers = prompt_containers(available_containers)
        project_emails = prompt_email_list(
            "Project recipient email",
            "These addresses receive alerts for every container in this project.",
        )
        projects[project_name] = {
            "containers": project_containers,
            "recipients": project_emails,
        }

    # ── Per-container configuration ───────────────────────────────────────
    print_section("Container Configuration")
    print(
        "  Add each container to monitor, then assign"
        " optional per-container recipients."
    )

    # ── Write config ──────────────────────────────────────────────────────
    json_data = {
        "sender_email": sender_email,
        "app_password": app_password,
        "watch_interval": watch_interval,
        "max_consecutive_errors": max_consecutive_errors,
        "interface": interface,
        "global_recipients": global_recipients,
        "projects": projects,
    }

    with open(CONFIG_FILE, "w") as json_file:
        json.dump(json_data, json_file, indent=4)

    print()
    print(f"  \033[1m\033[32m{'─' * 50}\033[0m")
    info(f"Configuration saved to {CONFIG_FILE}")
    info("Setup complete. You may now start the health checker.")
    print(f"  \033[1m\033[32m{'─' * 50}\033[0m\n")
    sys.exit(0)
