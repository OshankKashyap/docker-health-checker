"""
terminal_helpers.py — Terminal output and input prompt utilities.

Provides styled print helpers and interactive prompt functions used
across the health checker CLI (setup wizard and monitor mode).
"""

import sys


# ---------------------------------------------------------------------------
# ANSI style constants
# ---------------------------------------------------------------------------

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_RED    = "\033[31m"
_GREEN  = "\033[32m"
_YELLOW = "\033[33m"
_CYAN   = "\033[36m"


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
            f"  {_BOLD}{_CYAN}→{_RESET} {label}"
            f" {_DIM}(leave blank to finish){_RESET}: "
        ).strip()
        if not entry:
            break
        emails.append(entry)
    return emails
