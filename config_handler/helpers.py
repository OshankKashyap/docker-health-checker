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


def get_project_recipients(project: str) -> list[str]:
    """Return the recipient list for a specific project.

    Falls back to the global recipient list when the project defines
    no recipients, or when the project is not found in the config.
    """
    data = cfh.get_config_file()
    projects = data.get("projects", {})
    project_data = projects.get(project)

    if not project_data:
        return get_global_recipients()

    recipients = project_data.get("recipients")

    if not recipients:
        return get_global_recipients()

    return recipients


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
    return data.get("interface", None)


def get_project_containers(project_name: str) -> list[str]:
    data = cfh.get_config_file()
    projects = data.get("projects", {})
    proj_data = projects.get(project_name)
    if proj_data is None:
        return []
    return proj_data.get("containers", [])


def get_all_projects() -> dict[str, dict[str, str]]:
    """Returns all projects"""
    data = cfh.get_config_file()
    return data["projects"]


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
    mapped_ports = {}
    try:
        container = client.containers.get(container_name)
        port_bindings = container.attrs.get("HostConfig", {}).get("PortBindings")
        if port_bindings:
            for container_port, host_bindings in port_bindings.items():
                for binding in host_bindings:
                    host_port = binding.get("HostPort")
                    mapped_ports[host_port] = [container_port]
    finally:
        client.close()

    return mapped_ports


def get_all_current_containers() -> list[str]:
    """Return the names of all containers known to the Docker daemon.

    Queries Docker with ``all=True`` so stopped containers are included
    alongside running ones — consistent with setup-wizard usage where a
    user may want to monitor a container that is currently stopped.
    """
    client = docker.from_env()
    try:
        containers = client.containers.list(all=True)
        return [container.name for container in containers]
    finally:
        client.close()
