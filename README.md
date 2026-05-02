# Docker Container Health Checker

A lightweight Python daemon that monitors a Docker daemon and a specific container, dispatching HTML alert emails via Gmail when a health check fails. Runs as a `systemd` service with structured, rotating logs.

---

## Features

- Monitors Docker daemon status via `systemctl`
- Monitors a named container's running state via the Docker SDK
- Sends multi-part HTML + plain-text alert emails via Gmail SMTP on failure
- Configurable polling interval via environment variable
- Suppresses repeated alert emails after a configurable consecutive-failure threshold
- Structured logging with coloured terminal output and rotating JSON log files
- Validates all environment variables and recipient email addresses at startup
- Runs as a `systemd` service with automatic restart on failure

---

## Requirements

- Python 3.10+
- Docker daemon running on the host
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) configured
- `systemd` (for running as a service)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Key dependencies: `docker`, `python-dotenv`, `structlog`

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable                  | Required | Description                                                                              |
|---------------------------|----------|------------------------------------------------------------------------------------------|
| `CONTAINER_NAME`          | Yes      | Name of the Docker container to monitor                                                  |
| `SENDER_EMAIL`            | Yes      | Gmail address used to send alert emails                                                  |
| `APP_PASSWORD`            | Yes      | Gmail App Password for SMTP authentication                                               |
| `ALERT_RECIPIENTS`        | Yes      | Comma-separated list of recipient email addresses                                        |
| `WATCH_INTERVAL_SECONDS`  | Yes      | Polling interval in seconds (e.g. `60`)                                                  |
| `MAX_CONSECUTIVE_ERRORS`  | Yes      | Number of consecutive failures before alert emails are suppressed (e.g. `5`)            |
| `PRUNE_LOG_FILE`          | No       | Override the default log path (`/var/log/healthchecker.log`)                             |

> **Security note:** Never commit `.env` to version control. It contains credentials.

### Example `.env`

```env
CONTAINER_NAME="my-app"
SENDER_EMAIL="alerts@example.com"
APP_PASSWORD="xxxx xxxx xxxx xxxx"
ALERT_RECIPIENTS="admin@example.com,oncall@example.com"
WATCH_INTERVAL_SECONDS=60
MAX_CONSECUTIVE_ERRORS=5
```

---

## Running Manually

```bash
python health_checker.py
```

The checker will:

1. Validate all environment variables and recipient addresses
2. Run an initial health check — exits with code `1` and sends an alert if it fails
3. Enter a watch loop, polling every `WATCH_INTERVAL_SECONDS` seconds

---

## Running as a systemd Service

### 1. Update paths in the unit file

Edit `health_checker.service` and replace the placeholder paths with your actual project directory:

```ini
WorkingDirectory=/path/to/docker_container_health_checker/
ExecStart=/path/to/docker_container_health_checker/start.sh
EnvironmentFile=/path/to/docker_container_health_checker/.env
```

### 2. Install and enable the service

```bash
sudo cp health_checker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable health_checker
sudo systemctl start health_checker
```

### 3. Check service status

```bash
sudo systemctl status health_checker
```

### 4. View logs

```bash
# Journal (live)
sudo journalctl -u health_checker -f

# Rotating log file
tail -f /var/log/healthchecker.log
```

---

## How It Works

```
Startup
  │
  ├─ Load & validate environment variables
  ├─ Validate recipient email addresses
  ├─ Run initial health checks
  │     ├─ Docker daemon active? (systemctl)
  │     └─ Container running? (Docker SDK)
  │
  ├─ [FAIL] → Log critical, send alert email → exit(1)
  └─ [PASS] → Enter watch loop
                │
                └─ Every WATCH_INTERVAL_SECONDS
                      ├─ Run health checks
                      ├─ [FAIL] → Increment consecutive error count
                      │     ├─ count < MAX_CONSECUTIVE_ERRORS → send alert email → continue
                      │     └─ count ≥ MAX_CONSECUTIVE_ERRORS → suppress email, log error → continue
                      └─ [PASS] → Reset consecutive error count → log success → continue
```

On failure, an HTML + plain-text email is sent to all configured recipients via Gmail SMTP over SSL (port 465). Once `MAX_CONSECUTIVE_ERRORS` is reached, emails are suppressed to avoid flooding recipients during a prolonged outage. The counter resets automatically when checks pass again.

---

## Logging

Logs are written to two destinations simultaneously:

- **Console** — coloured, human-readable output via `structlog`
- **Rotating JSON file** — machine-readable, defaults to `/var/log/healthchecker.log`

Override the log file path with the `PRUNE_LOG_FILE` environment variable.

---

## Gmail App Password Setup

Standard Gmail passwords will not work. You must generate an App Password:

1. Enable 2-Step Verification on your Google account
2. Go to **Google Account → Security → App Passwords**
3. Create a new app password and paste it into `APP_PASSWORD` in your `.env`

---

## Troubleshooting

| Symptom | Likely cause |
|--------|-------------|
| `Environment variable 'X' is not set` | Missing entry in `.env` or `EnvironmentFile` path is wrong in the service unit |
| `Invalid email address: '...'` | Malformed address in `ALERT_RECIPIENTS` — check for extra spaces or typos |
| `Container 'X' not found` | Container name mismatch — verify with `docker ps -a` |
| `Docker is not running` | Docker daemon is stopped — run `sudo systemctl start docker` |
| No emails received | Check `SENDER_EMAIL`/`APP_PASSWORD`, verify App Password is active, check spam folder |
| Emails stopped after repeated failures | Expected behaviour — `MAX_CONSECUTIVE_ERRORS` threshold reached; check logs for details |
| Service fails to start | Check `journalctl -u health_checker` and verify `start.sh` is executable (`chmod +x start.sh`) |
