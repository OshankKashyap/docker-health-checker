"""
Docker Health Checker
=====================
Monitors a Docker daemon and a specific container, logging their health status
at a configurable interval. Reads configuration from environment variables and
uses a rotating log file alongside coloured terminal output (via logger.py).

Environment variables
---------------------
CONTAINER_NAME          : (required) Name of the Docker container to watch.
SENDER_EMAIL            : (required) Gmail address used to send alert emails.
APP_PASSWORD            : (required) Gmail App Password for SMTP authentication.
PRUNE_LOG_FILE          : (optional) Override the default log file path.
ALERT_RECIPIENTS        : (required) Comma-separated list of email addresses to notify.
WATCH_INTERVAL_SECONDS  : (required) Seconds to wait between health checks.
MAX_CONSECUTIVE_ERRORS  : (required) Failure threshold before alerts are suppressed.
"""

import os
import re
import smtplib
import subprocess
import time
import templates.templates
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import docker
from dotenv import load_dotenv

from logger import get_logger

# Load .env file into the process environment before reading any variables.
load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

# In-memory store for validated environment variables, populated by load_env_vars().
env_vars: dict[str, str | int] = {}

# Log file path — override via PRUNE_LOG_FILE env var if needed.
LOG_FILE = os.environ.get(
    "PRUNE_LOG_FILE",
    Path().joinpath("/", "var", "log", "healthchecker.log"),
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
    required_str = [
        "CONTAINER_NAME",
        "SENDER_EMAIL",
        "APP_PASSWORD",
        "ALERT_RECIPIENTS",
        "WATCH_INTERVAL_SECONDS",
        "MAX_CONSECUTIVE_ERRORS",
    ]
    int_vars = ["WATCH_INTERVAL_SECONDS", "MAX_CONSECUTIVE_ERRORS"]

    for var in required_str:
        value = os.getenv(var)

        if value is None:
            return False, f"Environment variable '{var}' is not set"

        if not value.strip() and value not in int_vars:
            return False, f"Environment variable '{var}' is empty"
        elif var in int_vars:
            try:
                value = int(value)
            except ValueError:
                return False, f"Environment variable '{var}' is not an integer"

        env_vars[var] = value

    return True, f"Loaded {len(required_str)} environment variable(s)"


def validate_recipients() -> tuple[bool, str]:
    """
    Validate each email address in the ALERT_RECIPIENTS env var.

    Addresses must pass a basic RFC-5321-style regex. Validation halts and
    returns False on the first invalid address so startup fails fast with a
    clear error rather than silently dropping bad addresses at send time.

    Returns
    -------
    (True, summary_message)   — all addresses are well-formed.
    (False, error_message)    — at least one address is malformed.
    """
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    recipients = [r.strip() for r in env_vars["ALERT_RECIPIENTS"].split(",")]

    for recipient in recipients:
        if not email_pattern.match(recipient):
            return False, f"Invalid email address: '{recipient}'"

    return True, f"Validated {len(recipients)} recipient(s)"


def check_docker_daemon() -> tuple[bool, str]:
    """
    Verify that the Docker daemon is active via systemctl.

    Returns
    -------
    (True,  "Docker is running")      — daemon is active.
    (False, "Docker is not running")  — daemon is inactive or unreachable.
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
    Execute the full set of health checks (Docker daemon + named container).

    Logs each step and short-circuits on the first failure so the caller can
    decide whether to alert and exit or simply continue the watch loop.

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


def send_alert_emails(
    recipients: list[str],
    logger,
    plain_template: str,
    html_template: str,
    subject: str,
) -> None:
    """
    Send an HTML + plain-text alert email to all recipients when a health
    check failure is detected.

    Parameters
    ----------
    recipients     : List of email addresses to notify.
    logger         : Logger instance used for outcome logging.
    plain_template : Plain-text body of the alert email.
    html_template  : HTML body of the alert email.
    subject        : Subject line of the alert email.
    """
    sender = env_vars["SENDER_EMAIL"]
    app_password = env_vars["APP_PASSWORD"]

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
    container_name : Passed through to the email templates.
    logger         : Logger instance used for output.
    send_email     : When False, suppresses email dispatch after the
                     consecutive-error threshold has been reached.
    plain_template : Plain-text body rendered before calling this function.
                     Ignored when send_email is False.
    html_template  : HTML body rendered before calling this function.
                     Ignored when send_email is False.
    """
    if send_email:
        logger.critical("Health check failed — sending alert emails")

        # strip() guards against whitespace padding that would cause SMTP delivery failures.
        recipients = [r.strip() for r in env_vars["ALERT_RECIPIENTS"].split(",")]
        send_alert_emails(recipients, logger, plain_template, html_template, subject="Health check failed")


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

    logger.info("Validating email recipients")
    success, message = validate_recipients()
    if not success:
        logger.error(message)
        exit(1)
    logger.info(message)

    container_name = env_vars["CONTAINER_NAME"]

    # ── Step 2: Initial health check before entering the watch loop ───────────
    logger.info("Running initial health checks")
    if not run_health_checks(container_name, logger):
        handle_health_failure(
            container_name,
            logger,
            True,
            templates.templates.get_plain_template(),
            templates.templates.get_html_template(),
        )
        exit(1)
    logger.info("Initial health checks passed — starting watcher")

    # ── Step 3: Continuous watch loop ─────────────────────────────────────────
    downtime = None
    consecutive_error_count = 0
    while True:
        time.sleep(env_vars["WATCH_INTERVAL_SECONDS"])

        # Stamp each iteration so log files clearly show when each check ran.
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{timestamp}] Running scheduled health check")

        if not run_health_checks(container_name, logger):
            consecutive_error_count += 1
            if downtime is None:
                downtime = datetime.now()
            if consecutive_error_count > env_vars["MAX_CONSECUTIVE_ERRORS"]:
                handle_health_failure(container_name, logger, False)
                logger.error(
                    f"[{timestamp}] Maximum consecutive errors reached "
                    f"({env_vars['MAX_CONSECUTIVE_ERRORS']}). Emails suppressed."
                )
            else:
                handle_health_failure(
                    container_name,
                    logger,
                    True,
                    templates.templates.get_plain_template(),
                    templates.templates.get_html_template(),
                )
            # Skip the success log and counter reset — checks did not pass.
            continue

        # Checks passed: clear any accumulated failure streak.
        if consecutive_error_count != 0:
            logger.info(
                f"[{timestamp}] Service recovered after "
                f"{consecutive_error_count} consecutive failure(s). "
                "Resetting error count."
            )
            downtime_diff = datetime.now() - downtime
            logger.info(
                f"[{timestamp}] Service was down for "
                f"{downtime_diff} (HH:MM:SS)"
            )
            consecutive_error_count = 0
            # Parse recipients the same way the failure path does, to avoid
            # passing the raw comma-separated string to sendmail.
            recipients = [
                r.strip()
                for r in env_vars["ALERT_RECIPIENTS"].split(",")
            ]
            send_alert_emails(
                recipients,
                logger,
                templates.templates.get_plain_up_template(downtime_diff),
                templates.templates.get_html_up_template(downtime_diff),
                subject="Service is back up",
            )
            downtime = None

        logger.info(f"[{timestamp}] All checks passed")
