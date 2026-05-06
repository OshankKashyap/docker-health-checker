# Docker Container Health Checker

A lightweight Python daemon that monitors the Docker daemon and one or more named containers, dispatching HTML alert emails via Gmail when a health check fails. Configured through an interactive setup wizard and runs as a `systemd` service with structured, rotating logs.

---

## Features

- Monitors Docker daemon status via `systemctl`
- Monitors **multiple named containers** independently via the Docker SDK
- Sends multi-part HTML + plain-text alert emails via Gmail SMTP on failure
- Sends a **recovery email** when a container comes back up, including total downtime
- Supports **per-container recipient lists** with a global fallback
- Suppresses repeated alert emails after a configurable consecutive-failure threshold (per container)
- Structured logging with coloured terminal output and rotating JSON log files
- Interactive **setup wizard** (`--setup-config`) writes config to `/etc/healthchecker/config.json`
- Validates config file at startup before entering the watch loop
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

Key dependencies: `docker`, `structlog`

---

## Configuration

Configuration is stored at `/etc/healthchecker/config.json`. The easiest way to create it is through the interactive setup wizard:

```bash
python main.py --setup-config
```

The wizard will prompt for all required values and write the file. To edit settings later, either re-run the wizard or edit the JSON file directly.

### config.json structure

```json
{
    "sender_email": "alerts@example.com",
    "app_password": "xxxx xxxx xxxx xxxx",
    "watch_interval": 60,
    "max_consecutive_errors": 5,
    "global_recipients": [
        "admin@example.com"
    ],
    "containers": [
        {
            "name": "my-app",
            "recipients": [
                "oncall@example.com"
            ]
        },
        {
            "name": "my-db",
            "recipients": []
        }
    ]
}
```

### Config fields

| Field                   | Type            | Required | Description                                                                                     |
|-------------------------|-----------------|----------|-------------------------------------------------------------------------------------------------|
| `sender_email`          | string          | Yes      | Gmail address used to send alert emails                                                         |
| `app_password`          | string          | Yes      | Gmail App Password for SMTP authentication                                                      |
| `watch_interval`        | integer         | Yes      | Polling interval in seconds (e.g. `60`)                                                         |
| `max_consecutive_errors`| integer         | Yes      | Consecutive failures before alert emails are suppressed (e.g. `5`)                              |
| `global_recipients`     | list of strings | Yes      | Fallback recipient list used when a container has no recipients of its own                      |
| `containers`            | list of objects | Yes      | One entry per container to monitor; must contain at least one entry                             |
| `containers[].name`     | string          | Yes      | Name of the Docker container (must match `docker ps` exactly)                                   |
| `containers[].recipients` | list of strings | Yes    | Per-container recipients; leave empty (`[]`) to use `global_recipients`                         |

> **Security note:** `/etc/healthchecker/config.json` contains credentials. Restrict its permissions:
> ```bash
> sudo chmod 600 /etc/healthchecker/config.json
> ```

### Log file path

The log file defaults to `/var/log/healthchecker.log`. Override it with the `PRUNE_LOG_FILE` environment variable — this is the only value still read from the environment:

```bash
export PRUNE_LOG_FILE=/home/oshank/logs/healthchecker.log
```

---

## Running Manually

### First-time setup

```bash
python main.py --setup-config
```

### Start the health checker

```bash
python main.py --start-checker
```

The checker will:

1. Validate the config file at `/etc/healthchecker/config.json`
2. Run an initial health check for every configured container — sends an alert for any that fail
3. Enter a watch loop, polling every `watch_interval` seconds

### Help

```bash
python main.py --help
```

---

## Running as a systemd Service

### 1. Update paths in the unit file
Copy the example service file and edit it with your actual project directory:

```bash
cp health_checker_example.service health_checker.service
```

Edit `health_checker.service` and replace the placeholder paths with your actual project directory:

```ini
WorkingDirectory=/path/to/your/directory/
ExecStart=/path/to/your/directory/start.sh
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
  ├─ Validate config file (/etc/healthchecker/config.json)
  ├─ Load all container names and settings
  ├─ Run initial health checks (all containers)
  │     ├─ Docker daemon active? (systemctl)
  │     └─ Container running? (Docker SDK)
  │
  ├─ [FAIL] → Log critical, send alert email → continue to next container
  └─ [PASS] → Enter watch loop
                │
                └─ Every watch_interval seconds, for each container independently:
                      ├─ Run health checks
                      ├─ [FAIL] → Increment this container's consecutive error count
                      │     ├─ count ≤ max_consecutive_errors → send alert email → continue
                      │     └─ count > max_consecutive_errors → suppress email, log error → continue
                      └─ [PASS]
                            ├─ Previously failing? → Send recovery email with downtime duration
                            │                      → Reset this container's error count and downtime
                            └─ Log success → continue
```

Each container maintains its own independent failure streak and downtime timer, so a prolonged outage on one container does not affect alerting for any other.

On failure, an HTML + plain-text email is sent to the container's configured recipients (or `global_recipients` if none are set). Once `max_consecutive_errors` is exceeded, further emails for that container are suppressed to avoid flooding recipients during a prolonged outage. When the container recovers, the counter resets and a single recovery email is sent.

---

## Recipient Resolution

Alert emails are sent to the resolved recipient list for each container:

1. If the container entry has a non-empty `recipients` list → use those addresses.
2. If the container's `recipients` list is empty → fall back to `global_recipients`.

Recovery emails use the same resolution logic as failure emails.

---

## Logging

Logs are written to two destinations simultaneously:

- **Console** — coloured, human-readable output with ANSI-styled level names and dimmed timestamps
- **Rotating JSON file** — plain-text, machine-readable output, defaults to `/var/log/healthchecker.log`

Override the log file path with the `PRUNE_LOG_FILE` environment variable.

### Log rotation

The log file is managed by a `RotatingFileHandler` with the following configuration:

| Parameter      | Value   | Description                                              |
|----------------|---------|----------------------------------------------------------|
| `max_bytes`    | 5 MB    | Maximum size of a single log file before rotation        |
| `backup_count` | 3       | Number of rotated backup files to retain                 |
| `encoding`     | UTF-8   | File encoding                                            |

Once `healthchecker.log` reaches 5 MB, it is rotated as follows:

```
healthchecker.log    →  healthchecker.log.1
healthchecker.log.1  →  healthchecker.log.2
healthchecker.log.2  →  healthchecker.log.3
healthchecker.log.3  →  (deleted)
```

At most **4 files** exist on disk at any time (the active file + 3 backups), capping total log storage at roughly **20 MB**.

---

## Gmail App Password Setup

Standard Gmail passwords will not work. You must generate an App Password:

1. Enable 2-Step Verification on your Google account
2. Go to **Google Account → Security → App Passwords**
3. Create a new app password and paste it into `app_password` in your config

---

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| `Config file not found at /etc/healthchecker/config.json` | Run `python main.py --setup-config` first |
| `Missing required field: 'X'` | Config file is incomplete — re-run setup or add the field manually |
| `Container 'X' not found` | Container name mismatch — verify with `docker ps -a` |
| `Docker is not running` | Docker daemon is stopped — run `sudo systemctl start docker` |
| No emails received | Check `sender_email`/`app_password`, verify App Password is active, check spam folder |
| Emails stopped after repeated failures | Expected behaviour — `max_consecutive_errors` threshold reached; check logs for details |
| Service fails to start | Check `journalctl -u health_checker` and verify `start.sh` is executable (`chmod +x start.sh`) |
