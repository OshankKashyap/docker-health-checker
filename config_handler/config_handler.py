"""
configure.py — Interactive setup wizard for the Docker Health Checker.

Handles first-time configuration by prompting the user for settings
and writing them to the JSON config file at /etc/healthchecker/config.json.
"""

import json
import os
import sys
from pathlib import Path

from config_handler.terminal_helpers import (
    error,
    info,
    print_banner,
    print_section,
    prompt_email_list,
    prompt_int,
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
    required_str_fields = ("sender_email", "app_password")
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

    # ── containers ───────────────────────────────────────────────────────
    if "containers" not in config:
        error("Missing required field: 'containers'")
        sys.exit(1)
    if not isinstance(config["containers"], list):
        error("'containers' must be a list.")
        sys.exit(1)
    if not config["containers"]:
        error("'containers' must contain at least one entry.")
        sys.exit(1)

    for idx, container in enumerate(config["containers"]):
        label = container.get("name") or f"containers[{idx}]"
        if not isinstance(container.get("name"), str) or not container["name"].strip():
            error(f"Container at index {idx} is missing a valid 'name'.")
            sys.exit(1)
        if not isinstance(container.get("recipients"), list):
            error(f"Container '{label}': 'recipients' must be a list.")
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

    # ── Recipients ────────────────────────────────────────────────────────
    print_section("Global Recipients")
    global_recipients = prompt_email_list(
        "Global recipient email",
        "These addresses receive alerts for every container.",
    )

    # ── Per-container configuration ───────────────────────────────────────
    print_section("Container Configuration")
    print(
        "  Add each container to monitor, then assign"
        " optional per-container recipients."
    )

    containers: list[dict] = []
    while True:
        container_name = input(
            "\n  \033[1m\033[36m→\033[0m Container name"
            " \033[2m(leave blank to finish)\033[0m: "
        ).strip()
        if not container_name:
            break
        recipients = prompt_email_list(
            f"Recipient for {container_name}",
        )
        containers.append({"name": container_name, "recipients": recipients})

    # ── Write config ──────────────────────────────────────────────────────
    json_data = {
        "sender_email": sender_email,
        "app_password": app_password,
        "watch_interval": watch_interval,
        "max_consecutive_errors": max_consecutive_errors,
        "global_recipients": global_recipients,
        "containers": containers,
    }

    with open(CONFIG_FILE, "w") as json_file:
        json.dump(json_data, json_file, indent=4)

    print()
    print(f"  \033[1m\033[32m{'─' * 50}\033[0m")
    info(f"Configuration saved to {CONFIG_FILE}")
    info("Setup complete. You may now start the health checker.")
    print(f"  \033[1m\033[32m{'─' * 50}\033[0m\n")
    sys.exit(0)
