"""
terminal_helpers.py — Terminal output and input prompt utilities.

Provides styled print helpers and interactive prompt functions used
across the health checker CLI (setup wizard and monitor mode).
"""

import socket
import sys

import psutil

# ---------------------------------------------------------------------------
# ANSI style constants
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def print_banner() -> None:
    """Print the wizard header banner."""
    width = 60
    print()
    print(f"{_BOLD}{_CYAN}{'─' * width}{_RESET}")
    print(f"{_BOLD}{_CYAN}{'Docker Health Checker — Setup Wizard':^{width}}{_RESET}")
    print(f"{_BOLD}{_CYAN}{'─' * width}{_RESET}")
    print()


def print_section(title: str) -> None:
    """Print a labelled section divider."""
    print(f"\n{_BOLD}{_YELLOW}  ◆ {title}{_RESET}")
    print(f"  {_DIM}{'─' * 50}{_RESET}")


def info(message: str) -> None:
    """Print an informational message."""
    print(f"  {_BOLD}{_GREEN}[INFO]{_RESET}  {message}")


def error(message: str) -> None:
    """Print an error message."""
    print(f"  {_BOLD}{_RED}[ERROR]{_RESET} {message}")


# ---------------------------------------------------------------------------
# Input prompt helpers
# ---------------------------------------------------------------------------


def prompt(label: str, hint: str = "") -> str:
    """
    Display a styled input prompt and return the stripped response.

    Args:
        label: The field name shown to the user.
        hint:  Optional sub-text shown below the label.
    """
    if hint:
        print(f"  {_DIM}{hint}{_RESET}")
    return input(f"  {_BOLD}{_CYAN}→{_RESET} {label}: ").strip()


def prompt_required(label: str, hint: str = "") -> str:
    """
    Repeatedly prompt until the user supplies a non-empty value.

    Args:
        label: The field name shown to the user.
        hint:  Optional sub-text shown below the label.
    """
    value = prompt(label, hint)
    while not value:
        error("This field is required. Please try again.")
        value = prompt(label)
    return value


def prompt_int(label: str, hint: str = "") -> int:
    """
    Prompt for a positive integer, exiting on non-numeric input.

    Args:
        label: The field name shown to the user.
        hint:  Optional sub-text shown below the label.
    """
    raw = prompt_required(label, hint)
    try:
        value = int(raw)
    except ValueError:
        error(f"'{raw}' is not a valid integer. Aborting.")
        sys.exit(1)

    while value <= 0:
        error("Value must be a positive integer.")
        raw = prompt(label)
        try:
            value = int(raw)
        except ValueError:
            error(f"'{raw}' is not a valid integer. Aborting.")
            sys.exit(1)

    return value


def prompt_email_list(label: str, hint: str = "") -> list[str]:
    """
    Collect a list of e-mail addresses, stopping on an empty entry.

    Args:
        label: Describes the email list being collected.
        hint:  Optional sub-text shown before the first prompt.
    """
    emails: list[str] = []
    if hint:
        print(f"  {_DIM}{hint}{_RESET}")
    while True:
        entry = input(
            f"  {_BOLD}{_CYAN}→{_RESET} {label} {_DIM}(leave blank to finish){_RESET}: "
        ).strip()
        if not entry:
            break
        emails.append(entry)
    return emails


def get_interface_ips() -> dict[str, str]:
    """Return a mapping of interface name to IPv4 address.

    Iterates all network interfaces reported by psutil and collects
    the first IPv4 address found for each. Interfaces with no IPv4
    address are omitted from the result.
    """
    interfaces: dict[str, str] = {}
    for name, addresses in psutil.net_if_addrs().items():
        for addr in addresses:
            if addr.family == socket.AF_INET:  # IPv4 only
                interfaces[name] = addr.address
                break
    return interfaces


def prompt_interface(interfaces: dict[str, str]) -> str:
    """Prompt the user to select a network interface by index.

    Prints a numbered list of available interfaces and their IPv4
    addresses, then reads a single integer selection. Exits with
    code 1 if the input is not a valid index.

    Args:
        interfaces: Mapping of interface name to IPv4 address,
                    as returned by ``get_interface_ips``.

    Returns:
        The name of the selected interface.
    """
    if not interfaces:
        error("No network interfaces with an IPv4 address were found.")
        sys.exit(1)

    interface_names = list(interfaces.keys())

    print()
    print(f"  {_DIM}{'─' * 50}{_RESET}")
    for idx, (name, address) in enumerate(interfaces.items()):
        print(
            f"  {_DIM}[{idx}]{_RESET}"
            f"  {_BOLD}{name:<20}{_RESET}"
            f"  {_CYAN}{address}{_RESET}"
        )
    print(f"  {_DIM}{'─' * 50}{_RESET}")

    raw = input(
        f"  {_BOLD}{_CYAN}→{_RESET} Select interface (0-{len(interfaces) - 1}): "
    ).strip()

    try:
        selected_idx = int(raw)
        if not (0 <= selected_idx < len(interfaces)):
            raise ValueError
    except ValueError:
        error(f"'{raw}' is not a valid interface number. Aborting.")
        sys.exit(1)

    return interface_names[selected_idx]


def prompt_containers(containers: list[str]) -> list[str]:
    """Prompt the user to select containers by index.

    Prints a numbered list of available containers, then reads a
    comma-separated selection of indices. Exits with code 1 if the
    input is invalid or any index is out of range.

    Args:
        containers: List of container name strings to display.

    Returns:
        The subset of container names chosen by the user.
    """
    if not containers:
        error("No containers were found. Aborting.")
        sys.exit(1)

    print()
    print(f"  {_DIM}{'─' * 50}{_RESET}")
    for idx, container in enumerate(containers):
        print(f"  {_DIM}[{idx}]{_RESET}  {_BOLD}{container}{_RESET}")
    print(f"  {_DIM}{'─' * 50}{_RESET}")

    while True:
        raw = input(
            f"  {_BOLD}{_CYAN}→{_RESET} Select containers (comma-separated): "
        ).strip()

        if not raw:
            error("No selection made. Please enter at least one index.")
            continue  # re-prompt instead of aborting

        try:
            selected_indices = [int(i.strip()) for i in raw.split(",")]
            if not all(0 <= i < len(containers) for i in selected_indices):
                raise ValueError
            break  # ← valid input, exit the loop
        except ValueError:
            error(f"'{raw}' is not a valid container selection. Try again.")

    return [containers[i] for i in selected_indices]
