---
name: odin-dev-datadog
description: Query Datadog logs for production debugging. Use when user says /odin-dev-datadog, asks to check logs, debug a session, investigate user issues, trace production errors, or view recent logs for urania/hermod/odin-flow or any Surf service.
---

# Datadog Log Viewer

Query Datadog logs for Surf platform production debugging. Supports filtering by session_id, user_id, service, log level, and raw Datadog query syntax.

## Prerequisites

- **Python package**: `datadog-api-client` (installed via uv in skill directory)
- **Credentials** (priority order):
  1. AWS Secrets Manager: `datadog/prd-general` (auto-fetched with 5s timeout)
  2. Env vars: `DD_API_KEY` + `DD_APP_KEY`
  3. Config file: `~/.ddlog.json` → `{"api_key":"...","app_key":"...","site":"datadoghq.com"}`

## CLI Tool

Script: `surf-skills/odin-dev-datadog/scripts/ddlog.py`

Run with uv from the skill directory:

```bash
cd surf-skills/odin-dev-datadog

# By session — trace full session execution flow
uv run python scripts/ddlog.py session <session_id> [--service urania] [--time 2h] [--verbose]

# By user — see all activity for a user
uv run python scripts/ddlog.py user <user_id> [--service hermod] [--level error]

# Raw Datadog query — full flexibility
uv run python scripts/ddlog.py query "service:odin-flow*" [--time 30m] [-n 50]
uv run python scripts/ddlog.py query "service:urania* AND status:error" --time 2h --verbose
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-s, --service` | all | `urania`, `hermod`, or omit for all services |
| `-t, --time` | `1h` | Time range: `30m`, `2h`, `1d`, `7d` |
| `-l, --level` | all | `debug`, `info`, `warn`, `error` |
| `-n, --limit` | 500 | Max logs to fetch (pagination handled automatically) |
| `-v, --verbose` | off | Show full log attributes as JSON |
| `--sort` | `asc` | `asc` (oldest first) or `desc` (newest first) |
| `--json` | off | Raw JSON output (one object per line) |
| `--stats-only` | off | Only show counts summary |
| `--extra` | - | Additional query to AND with (e.g. `"@endpoint:/v1/*"`) |

### Output Format

kubectl-like compact single line, color-coded by level:

```
03-10 10:30:00 [urania-api] ERROR  Task timed out after 60s  session_id=abc user_id=123
03-10 10:30:01 [hermod]     INFO   Request completed         duration_ms=45
```

With `--verbose`, full attributes are dumped as indented JSON below each line.

## Debugging Playbook

### 1. Session deep-dive (most common)

```bash
# Overview — scan all logs for the session
uv run python scripts/ddlog.py session <session_id> --time 4h

# Errors only
uv run python scripts/ddlog.py session <session_id> --level error --verbose --time 4h

# Cross-service (omit --service to see urania + hermod interleaved)
uv run python scripts/ddlog.py session <session_id> --time 4h
```

### 2. User issue investigation

```bash
# Recent errors for a user
uv run python scripts/ddlog.py user <user_id> --level error --time 24h

# All activity on a specific service
uv run python scripts/ddlog.py user <user_id> --service urania --time 2h --verbose
```

### 3. Service health check

```bash
# Recent errors
uv run python scripts/ddlog.py query "service:urania* AND (status:error OR status:warn)" --time 1h

# Specific endpoint
uv run python scripts/ddlog.py query "service:hermod AND @path:/gateway/v1/market/*" --level error --time 1h
```

## Surf Services on Datadog

| Service name | Repo | Notes |
|-------------|------|-------|
| `urania-api` | urania | Main API (FastAPI) |
| `urania-agent` | urania | Agent sidecar |
| `hermod` | hermod | Data API gateway |
| `odin-flow` | odin-flow | AI agent orchestrator |
| `odin-flow-task` | odin-flow | Background tasks |
| `muninn-api` | muninn | Main API gateway |

Use wildcards: `service:urania*`, `service:odin-flow*`.

## Datadog Query Syntax

- Custom attributes: `@session_id:abc`, `@user_id:123`, `@duration_ms:>1000`
- Reserved fields: `service:urania-api`, `status:error`, `host:prod-*`
- Boolean: `AND`, `OR`, `NOT` (uppercase)
- Wildcards: `service:uran*`, `@path:/v1/*`
- Range: `@http.status_code:[400 TO 499]`
- Facets must be created in Datadog UI for frequently queried custom attributes
- High-cardinality fields (user_id) — use narrow time windows (< 4h)
