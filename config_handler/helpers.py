"""Accessor functions for Docker health-checker configuration values."""

import docker

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


def get_network_interface() -> str:
    """Return the network interface name from the config."""
    data = cfh.get_config_file()
    return data["interface"]


def get_container_mapped_ports(
    container_name: str,
) -> dict[str, list[str]]:
    """Return all host ports mapped to each container port.

    Queries the Docker daemon for the live port bindings of the named
    container and returns only bindings on 0.0.0.0 (i.e. published to
    all interfaces).  Ports that are exposed but not published (whose
    binding list is None) are silently skipped.

    Args:
        container_name: The name or ID of the running container.

    Returns:
        A dict mapping each container port string (e.g. ``"80/tcp"``)
        to a list of host port strings (e.g. ``["8080", "8081"]``).
        Ports with no qualifying bindings are omitted from the result.
    """
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        port_bindings = container.attrs["NetworkSettings"]["Ports"]

        mapped_ports: dict[str, list[str]] = {}
        for port, bindings in port_bindings.items():
            if bindings is None:  # Exposed but not published — skip.
                continue

            host_ports: list[str] = []
            for binding in bindings:
                if binding and binding["HostIp"] == "0.0.0.0":
                    host_ports.append(binding["HostPort"])

            if host_ports:  # Only include ports with active bindings.
                mapped_ports[port] = host_ports
    finally:
        client.close()

    return mapped_ports
