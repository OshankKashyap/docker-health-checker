"""Accessor functions for Docker health-checker configuration values."""

import config_handler.config_handler as cfh


def get_global_recipients() -> list[str]:
    """Return the global recipient list, or an empty list if unset."""
    data = cfh.get_config_file()
    return data.get("global_recipients") or []


def get_all_containers() -> list[str]:
    """Return the names of all containers defined in the config."""
    data = cfh.get_config_file()
    return [container.get("name") for container in data["containers"]]


def get_container_recipients(container_name: str) -> list[str]:
    """Return the recipient list for a specific container.

    Falls back to the global recipient list when the container defines
    no recipients, or when the container is not found in the config.
    """
    data = cfh.get_config_file()
    for container in data["containers"]:
        if container.get("name") == container_name:
            recipients = container.get("recipients")
            if not recipients:
                return get_global_recipients()
            return recipients

    # Container not found in config — fall back to global recipients.
    return get_global_recipients()


def get_app_password() -> str:
    """Return the email app password from the config."""
    data = cfh.get_config_file()
    return data["app_password"]


def get_sender_email() -> str:
    """Return the sender email address from the config."""
    data = cfh.get_config_file()
    return data["sender_email"]


def get_watch_interval() -> int:
    """Return the container polling interval in seconds."""
    data = cfh.get_config_file()
    return data["watch_interval"]


def get_max_consecutive_errors() -> int:
    """Return the maximum allowed consecutive errors before alerting."""
    data = cfh.get_config_file()
    return data["max_consecutive_errors"]
