import socket

import psutil

from config_handler.helpers import (
    get_container_mapped_ports,
    get_network_interface,
)


def get_ip_address() -> str | None:
    """Return the IPv4 address of the configured network interface.

    Looks up the interface name from config, then iterates over all
    network interfaces to find a matching IPv4 address.

    Returns:
        str | None: The IPv4 address string, or None if the interface
        is not found or carries no IPv4 address.
    """
    ip_interface = get_network_interface()
    for name, addresses in psutil.net_if_addrs().items():
        if name == ip_interface:
            for addr in addresses:
                if addr.family == socket.AF_INET:  # IPv4 only
                    return addr.address

    return None


def get_hostname() -> str:
    """Return the hostname of the current machine."""
    return socket.gethostname()


def _fetch_net_interface() -> str:
    """Return the configured network interface name, or a fallback label.

    Returns:
        str: The interface name from config (e.g. ``eth0``), or the
        string ``"Unknown interface"`` when none is configured.
    """
    net_interface = get_network_interface()
    if not net_interface:
        return "Unknown interface"

    return net_interface


def _fetch_mapped_ports(container_name: str) -> dict[str, list[str]]:
    """Return mapped ports for a container, or an empty dict on failure.

    Failures are swallowed intentionally: a down container may not be
    reachable via the Docker API, and the alert email must still send.
    """
    try:
        return get_container_mapped_ports(container_name)
    except Exception:
        return {}


def _render_port_rows(
    mapped_ports: dict[str, list[str]],
    accent: str,
) -> str:
    """Return an HTML snippet of port-mapping rows for the info table.

    Each container port is rendered as its own row, listing all host
    ports it is bound to. When no ports are available a single fallback
    row is returned instead.

    Args:
        mapped_ports: Dict mapping container port strings to lists of
            host port strings, as returned by
            ``get_container_mapped_ports``.
        accent: A CSS colour string applied to the value text, matching
            the surrounding template's colour scheme.
    """
    if not mapped_ports:
        return f"""\
                                <tr>
                                    <td style="padding: 0 18px 14px;">
                                        <span style="color: #666; font-size: 10px;">
                                            Mapped Ports
                                        </span><br>
                                        <span style="color: {accent}; font-size: 16px;">
                                            Unavailable
                                        </span>
                                    </td>
                                </tr>"""

    rows = []
    for container_port, host_ports in mapped_ports.items():
        host_ports_str = ", ".join(host_ports)
        rows.append(f"""\
                                <tr>
                                    <td style="padding: 0 18px 14px;">
                                        <span style="color: #666; font-size: 10px;">
                                            {container_port}
                                        </span><br>
                                        <span style="color: {accent}; font-size: 16px;">
                                            &#8594;&nbsp;{host_ports_str}
                                        </span>
                                    </td>
                                </tr>""")

    return "\n".join(rows)


def _render_interface_row(net_interface: str, accent: str) -> str:
    """Return an HTML snippet for the network interface info-table row.

    Args:
        net_interface: The interface name string (e.g. ``eth0``), as
            returned by ``_fetch_net_interface``.
        accent: A CSS colour string applied to the value text, matching
            the surrounding template's colour scheme.
    """
    return f"""\
                                <tr>
                                    <td style="padding: 0 18px 14px;">
                                        <span style="color: #666; font-size: 10px;">
                                            Network Interface
                                        </span><br>
                                        <span style="color: {accent}; font-size: 16px;">
                                            {net_interface}
                                        </span>
                                    </td>
                                </tr>"""


def get_plain_template(container_name: str, project_name: str) -> str:
    """Return a plain-text alert body for a container-down event.

    Args:
        container_name: The name of the Docker container that is down.
        project_name: The project group the container belongs to.
    """
    hostname = get_hostname()
    net_interface = _fetch_net_interface()
    return (
        f"Container '{container_name}' in project '{project_name}' is down at IP: {get_ip_address()}\n"
        f"Hostname: {hostname}\n"
        f"Network Interface: {net_interface}"
    )


def get_plain_up_template(container_name: str, project_name: str, downtime: str) -> str:
    """Return a plain-text alert body for a container-recovered event.

    Args:
        container_name: The name of the Docker container that recovered.
        project_name: The project group the container belongs to.
        downtime: A human-readable string describing the outage duration
            (e.g. ``"5 minutes"``).
    """
    hostname = get_hostname()
    net_interface = _fetch_net_interface()
    return (
        f"Container '{container_name}' in project '{project_name}' is back up at IP: {get_ip_address()} "
        f"after {downtime} of downtime.\n"
        f"Hostname: {hostname}\n"
        f"Network Interface: {net_interface}"
    )


def get_html_template(container_name: str, project_name: str) -> str:
    """Return an HTML alert body for a container-down event.

    Assembles server IP, hostname, network interface, and port-mapping
    rows into a styled dark-theme email template.

    Args:
        container_name: The name of the Docker container that is down.
        project_name: The project group the container belongs to.
    """
    ip = get_ip_address()
    hostname = get_hostname()
    net_interface = _fetch_net_interface()
    port_rows = _render_port_rows(
        _fetch_mapped_ports(container_name),
        accent="#ff4444",
    )
    interface_row = _render_interface_row(net_interface, accent="#ff4444")
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Container Alert — Server Down</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f0f0f; font-family: 'Courier New', Courier, monospace;">
    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"
           style="min-height: 100vh; background-color: #0f0f0f;">
        <tr>
            <td align="center" style="padding: 48px 20px;">

                <table role="presentation" width="100%"
                       style="max-width: 580px; background-color: #1a0000;
                              border: 1px solid #ff3333;
                              border-radius: 4px;
                              box-shadow: 0 0 32px rgba(255,51,51,0.25), 0 0 2px #ff3333;">

                    <tr>
                        <td style="background-color: #ff2222; padding: 12px 28px;
                                   border-radius: 3px 3px 0 0;">
                            <table role="presentation" width="100%">
                                <tr>
                                    <td style="color: #fff; font-size: 11px; font-weight: bold;">
                                        &#9632;&nbsp;&nbsp;CRITICAL ALERT
                                    </td>
                                    <td align="right" style="color: rgba(255,255,255,0.6); font-size: 10px;">
                                        DOCKER HEALTH CHECKER
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 36px 28px 28px;">

                            <p style="color: #ff6666; font-size: 22px; font-weight: bold;">
                                {container_name} ({project_name}) is down
                            </p>

                            <p style="color: #aaaaaa; font-size: 13px;">
                                Hostname: {hostname}
                            </p>

                            <table width="100%" style="background-color: #110000;">
                                <tr>
                                    <td style="padding: 14px 18px;">
                                        <span style="color: #666; font-size: 10px;">
                                            Server IP
                                        </span><br>
                                        <span style="color: #ff4444; font-size: 16px;">
                                            {ip}
                                        </span>
                                    </td>
                                </tr>
{interface_row}
{port_rows}
                            </table>

                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def get_html_up_template(container_name: str, project_name: str, downtime: str) -> str:
    """Return an HTML alert body for a container-recovered event.

    Assembles server IP, hostname, network interface, downtime duration,
    and port-mapping rows into a styled dark-theme email template.

    Args:
        container_name: The name of the Docker container that recovered.
        project_name: The project group the container belongs to.
        downtime: A human-readable string describing the outage duration
            (e.g. ``"5 minutes"``).
    """
    ip = get_ip_address()
    hostname = get_hostname()
    net_interface = _fetch_net_interface()
    port_rows = _render_port_rows(
        _fetch_mapped_ports(container_name),
        accent="#44ee66",
    )
    interface_row = _render_interface_row(net_interface, accent="#44ee66")
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Container Alert — Server Restored</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f0f0f; font-family: 'Courier New', Courier, monospace;">
    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"
           style="min-height: 100vh; background-color: #0f0f0f;">
        <tr>
            <td align="center" style="padding: 48px 20px;">

                <table role="presentation" width="100%"
                       style="max-width: 580px; background-color: #001a04;
                              border: 1px solid #33ff66;
                              border-radius: 4px;
                              box-shadow: 0 0 32px rgba(51,255,102,0.25), 0 0 2px #33ff66;">

                    <tr>
                        <td style="background-color: #22cc44; padding: 12px 28px;
                                   border-radius: 3px 3px 0 0;">
                            <table role="presentation" width="100%">
                                <tr>
                                    <td style="color: #fff; font-size: 11px; font-weight: bold;">
                                        &#9632;&nbsp;&nbsp;SERVER RESTORED
                                    </td>
                                    <td align="right" style="color: rgba(255,255,255,0.6); font-size: 10px;">
                                        DOCKER HEALTH CHECKER
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 36px 28px 28px;">

                            <p style="color: #44ee66; font-size: 22px; font-weight: bold;">
                                {container_name} ({project_name}) is back up
                            </p>

                            <p style="color: #aaaaaa; font-size: 13px;">
                                Hostname: {hostname}
                            </p>

                            <table width="100%" style="background-color: #001100;">
                                <tr>
                                    <td style="padding: 14px 18px;">
                                        <span style="color: #666; font-size: 10px;">
                                            Server IP
                                        </span><br>
                                        <span style="color: #44ee66; font-size: 16px;">
                                            {ip}
                                        </span>
                                    </td>
                                </tr>
{interface_row}
                                <tr>
                                    <td style="padding: 0 18px 14px;">
                                        <span style="color: #666; font-size: 10px;">
                                            Downtime
                                        </span><br>
                                        <span style="color: #44ee66; font-size: 16px;">
                                            {downtime}
                                        </span>
                                    </td>
                                </tr>
{port_rows}
                            </table>

                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
