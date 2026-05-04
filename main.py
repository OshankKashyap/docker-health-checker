"""
Docker Health Checker
=====================
Monitors the Docker daemon and one or more named containers, logging their
health status at a configurable interval. All settings are read from the JSON
config file at /etc/healthchecker/config.json (written by --setup-config).

CLI flags
---------
--start-checker, -s  : Validate config and start the health-check loop.
--setup-config,  -c  : Run the interactive first-time setup wizard.
--help,          -h  : Print usage information and exit.
"""

import os
import smtplib
import subprocess
import sys
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import docker

import config_handler.config_handler as cfh
import templates.templates
from config_handler import helpers
from logger import get_logger

# ── Configuration ─────────────────────────────────────────────────────────────

# Log file path — override via PRUNE_LOG_FILE env var if needed.
LOG_FILE = os.environ.get(
    "PRUNE_LOG_FILE",
    Path("/var/log/healthchecker.log"),
)


# ── Health-check functions ────────────────────────────────────────────────────


def check_docker_daemon() -> tuple[bool, str]:
    """
    Verify that the Docker daemon is active via systemctl.

    Returns
    -------
    (True,  "Docker is running")     — daemon is active.
    (False, "Docker is not running") — daemon is inactive or unreachable.
    """
    result = subprocess.run(
        ["systemctl", "is-active", "docker"],
        capture_output=True,
    )
    # decode() defaults to utf-8; strip() removes the trailing newline.
    state = result.stdout.strip().decode()

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
    (True,  "Container <name> is running")    — container found and running.
    (False, "Container <name> not found")      — container does not exist.
    (False, "Container <name> is not running") — container exists but stopped/paused/etc.
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
    Execute the full set of health checks (Docker daemon + named container).

    Logs each step and short-circuits on the first failure so the caller can
    decide whether to alert or simply continue the watch loop.

    Parameters
    ----------
    container_name : Name of the Docker container to verify.
    logger         : Logger instance used for output.

    Returns
    -------
    True  — all checks passed.
    False — at least one check failed (error already logged).
    """
    checks = [
        ("Checking if Docker daemon is running", check_docker_daemon, []),
        (
            "Checking if Docker container is running",
            check_docker_container,
            [container_name],
        ),
    ]

    for description, check_fn, args in checks:
        logger.info(description)
        success, message = check_fn(*args)
        if not success:
            logger.error(message)
            return False
        logger.info(message)

    return True


# ── Email functions ───────────────────────────────────────────────────────────


def send_alert_emails(
    sender: str,
    recipients: list[str],
    logger,
    plain_template: str,
    html_template: str,
    subject: str,
) -> None:
    """
    Send an HTML + plain-text alert email to all recipients.

    Parameters
    ----------
    sender         : Gmail address the alert is sent from.
    recipients     : List of email addresses to notify.
    logger         : Logger instance used for outcome logging.
    plain_template : Plain-text body of the alert email.
    html_template  : HTML body of the alert email.
    subject        : Subject line of the alert email.
    """
    app_password = helpers.get_app_password()

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(plain_template, "plain"))
    msg.attach(MIMEText(html_template, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, app_password)
        server.sendmail(sender, recipients, msg.as_string())

    logger.info(f"Alert email sent to {len(recipients)} recipient(s)")


def handle_health_failure(
    container_name: str,
    logger,
    send_email: bool,
    plain_template: str = "",
    html_template: str = "",
) -> None:
    """
    Centralised response to a failed health check: log a critical event and
    optionally dispatch alert emails.

    Parameters
    ----------
    container_name : Name of the container that failed its health check.
    logger         : Logger instance used for output.
    send_email     : When False, suppresses email dispatch (consecutive-error
                     threshold has been reached).
    plain_template : Plain-text email body. Ignored when send_email is False.
    html_template  : HTML email body. Ignored when send_email is False.
    """
    if send_email:
        recipients: list[str] = helpers.get_container_recipients(container_name)
        logger.critical(
            f"Health check failed for '{container_name}' — "
            f"sending alert emails to {len(recipients)} recipient(s)"
        )
        send_alert_emails(
            helpers.get_sender_email(),
            recipients,
            logger,
            plain_template,
            html_template,
            subject=f"Health check failed: {container_name}",
        )


def handle_health_recovery(
    container_name: str,
    downtime_diff,
    logger,
    timestamp: str,
) -> None:
    """
    Respond to a container recovering after one or more failures: log the
    recovery and dispatch a 'service back up' email to the relevant recipients.

    Parameters
    ----------
    container_name : Name of the container that has recovered.
    downtime_diff  : timedelta representing how long the container was down.
    logger         : Logger instance used for output.
    timestamp      : Formatted timestamp string for log prefixing.
    """
    logger.info(
        f"[{timestamp}] '{container_name}' recovered — "
        f"was down for {downtime_diff} (HH:MM:SS)"
    )
    recipients: list[str] = helpers.get_container_recipients(container_name)
    send_alert_emails(
        helpers.get_sender_email(),
        recipients,
        logger,
        templates.templates.get_plain_up_template(downtime_diff),
        templates.templates.get_html_up_template(downtime_diff),
        subject=f"Service is back up: {container_name}",
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print("Usage:")
        print("  --start-checker, -s  : Start the health checker")
        print("  --setup-config,  -c  : Run the interactive setup wizard")
        sys.exit(0)
    elif args[0] not in ("--start-checker", "-s", "--setup-config", "-c"):
        print(f"Unknown argument: {args[0]}")
        print("\nUsage:")
        print("  --start-checker, -s  : Start the health checker")
        print("  --setup-config,  -c  : Run the interactive setup wizard")
        sys.exit(1)

    try:
        if args[0] in ("--start-checker", "-s"):
            cfh.check_config_exists()
        elif args[0] in ("--setup-config", "-c"):
            cfh.configure_settings()  # exits with code 0 on success
    except Exception as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    logger = get_logger("HealthChecker", log_file=LOG_FILE)
    logger.info("Health checker starting up")

    containers = helpers.get_all_containers()
    logger.info(f"Monitoring {len(containers)} container(s): {', '.join(containers)}")

    # ── Step 1: Initial health check before entering the watch loop ───────────
    logger.info(f"Running initial health checks for {len(containers)} container(s)")
    for container in containers:
        if not run_health_checks(container, logger):
            handle_health_failure(
                container,
                logger,
                send_email=True,
                plain_template=templates.templates.get_plain_template(),
                html_template=templates.templates.get_html_template(),
            )

    logger.info("Initial health checks complete — starting watcher")

    # ── Step 2: Per-container state for the watch loop ────────────────────────
    # Each container independently tracks its consecutive failure count and the
    # moment it first went down, so a failure in one does not affect another.
    container_state: dict[str, dict] = {
        container: {"consecutive_errors": 0, "downtime": None}
        for container in containers
    }

    max_consecutive_errors = helpers.get_max_consecutive_errors()

    # ── Step 3: Continuous watch loop ─────────────────────────────────────────
    while True:
        time.sleep(helpers.get_watch_interval())

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{timestamp}] Running scheduled health checks")

        for container in containers:
            state = container_state[container]

            if not run_health_checks(container, logger):
                state["consecutive_errors"] += 1

                # Record the moment this container first went down.
                if state["downtime"] is None:
                    state["downtime"] = datetime.now()

                if state["consecutive_errors"] > max_consecutive_errors:
                    # Threshold exceeded — log only, do not send another email.
                    handle_health_failure(container, logger, send_email=False)
                    logger.error(
                        f"[{timestamp}] '{container}': maximum consecutive errors reached "
                        f"({max_consecutive_errors}). Emails suppressed."
                    )
                else:
                    handle_health_failure(
                        container,
                        logger,
                        send_email=True,
                        plain_template=templates.templates.get_plain_template(),
                        html_template=templates.templates.get_html_template(),
                    )

                # Do not fall through to the success block below.
                continue

            # ── Container is healthy ──────────────────────────────────────────
            if state["consecutive_errors"] != 0:
                # Container has just recovered — notify and reset its state.
                downtime_diff = datetime.now() - state["downtime"]
                logger.info(
                    f"[{timestamp}] '{container}' recovered after "
                    f"{state['consecutive_errors']} consecutive failure(s)."
                )
                handle_health_recovery(container, downtime_diff, logger, timestamp)
                state["consecutive_errors"] = 0
                state["downtime"] = None

            logger.info(f"[{timestamp}] '{container}': all checks passed")
