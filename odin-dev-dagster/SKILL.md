---
name: odin-dev-dagster
description: >
  Dagster pipeline management — view run status, analyze failures, check schedules/sensors,
  and trigger jobs. Accesses Dagster GraphQL API via kubectl exec into the webserver pod.
  Use when user asks about pipeline status, failed jobs, Dagster runs, or says /odin-dev-dagster.
---

# Dagster Pipeline Management

All paths below are relative to this skill's base directory. Resolve to absolute paths before executing.

Manage and debug Dagster pipelines running on EKS. The script talks to the Dagster GraphQL API by exec-ing into the webserver pod — no port-forward or public access needed.

## Environment Selection

Two EKS clusters are available as kubectl contexts:

| Environment | Context Name | EKS Cluster |
|-------------|-------------|-------------|
| **Staging** | `stg` | `stg-app` |
| **Production** | `prd` | `prd-app` |

**Before running ANY command, determine the target environment:**
1. If the user explicitly says "stg", "staging", "prd", "prod", or "production" → use that.
2. If the context implies an environment → use that.
3. **If ambiguous → ASK the user. Do NOT assume.**

The `dagster-query` script supports a `--context` flag (must come before the subcommand):

```bash
# Example: list runs on staging
scripts/dagster-query --context stg --runs

# Example: list runs on production
scripts/dagster-query --context prd --runs
```

**Always pass `--context stg` or `--context prd`** to every `dagster-query` invocation.

## First-Time Setup Check

```bash
scripts/dagster-query --context prd --check-setup
```

Requirements:
- `kubectl` configured with access to both EKS clusters
- Run `aws eks update-kubeconfig --region us-west-2 --name prd-app --alias prd` if not configured
- Run `aws eks update-kubeconfig --region us-west-2 --name stg-app --alias stg` if not configured

## Cluster Info

- **Namespace**: `dagster`
- **Webserver service**: `dagster-core-dagster-webserver` (ClusterIP, port 80)
- **Access method**: `kubectl exec` into webserver pod → GraphQL at `localhost:80/graphql`
- **Public UI**: Requires GitHub SSO — not accessible from CLI

## Code Locations

| Location | Repo | Purpose |
|----------|------|---------|
| `odin-prod` | odin | News crawlers, project discovery, token mappings, Dune dashboards |
| `odin-flow-prod` | odin-flow | Token metadata, eval pipelines, CMS, trending, signal jobs |
| `swell` | swell | ETH data pipeline — BigQuery → ClickHouse, prediction markets |
| `helios` | helios | Solana blockchain ingestion into ClickHouse |
| `diver` | diver | Product analytics eval — Langfuse ingest, sentiment, faithfulness |

## Available Commands

Script: `scripts/dagster-query`

### Job Runs (Primary Command)

**Start from a job name** — shows job overview (location, sensor, schedule) + recent runs. This is the main entry point.

```bash
# Show job overview + recent runs
scripts/dagster-query --job-runs daily_base_ingestion

# Filter by status
scripts/dagster-query --job-runs daily_base_ingestion --status FAILURE

# More results
scripts/dagster-query --job-runs daily_base_ingestion --limit 20
```

Output includes: run ID, status, who launched it (sensor name or "Manual"), created time, duration. If the job name doesn't match exactly, suggests similar job names.

### View Code Locations & Jobs

```bash
# List all code locations, their jobs, schedules, and sensors
scripts/dagster-query --locations
```

### List Runs (Global View)

```bash
# Recent runs across all jobs (default: 10)
scripts/dagster-query --runs

# Filter by status
scripts/dagster-query --runs --status FAILURE

# Filter by job name (exact match, server-side)
scripts/dagster-query --runs --job daily_base_ingestion

# Combined filters
scripts/dagster-query --runs --job daily_base_ingestion --status FAILURE --limit 20
```

### Analyze a Run (Detail + Logs)

```bash
# Run detail with step stats + last 50 log events
scripts/dagster-query --run-detail <run-id>

# Filter to a specific step's logs only
scripts/dagster-query --run-detail <run-id> --step helios_dbt_refresh

# With more log events
scripts/dagster-query --run-detail <run-id> --log-limit 100
```

Failure events include:
- **failureMetadata**: dbt output, custom metadata entries (the detailed error output)
- **error**: Python exception class, message, and full stack trace
- **cause**: Chained exception details

### Full Run Logs

```bash
# Full logs (last 200 events)
scripts/dagster-query --run-logs <run-id>

# Only failure/error events (with full stack traces + metadata)
scripts/dagster-query --run-logs <run-id> --failures-only

# Filter to a specific step
scripts/dagster-query --run-logs <run-id> --step helios_dbt_refresh

# More events
scripts/dagster-query --run-logs <run-id> --log-limit 500
```

### Schedules & Sensors

```bash
# List all schedules with cron expressions and next tick
scripts/dagster-query --schedules

# List all sensors with status
scripts/dagster-query --sensors
```

### Inspect Job Config (before launching)

```bash
# Show presets, config schema, resource configs, and tags
scripts/dagster-query --job-info <job-name>

# Specify code location if ambiguous
scripts/dagster-query --job-info <job-name> --location odin-flow-prod
```

### Launch a Job

**IMPORTANT**: Launching is a multi-step interactive process. NEVER launch blindly.

**Required workflow:**
1. Run `--job-info <job>` first to discover presets and config schema
2. Show the user what presets/config options are available
3. Ask the user which preset to use, or what config values to provide
4. Confirm the exact launch parameters with the user
5. Only then execute `--launch`

```bash
# Launch with a named preset (most common)
scripts/dagster-query --launch <job-name> --preset default

# Launch with custom run config (JSON format matching Dagster's runConfigData)
scripts/dagster-query --launch <job-name> --run-config '{"ops": {"my_op": {"config": {"key": "value"}}}}'

# Launch with default config (no preset, no custom config)
scripts/dagster-query --launch <job-name>

# Specify code location explicitly
scripts/dagster-query --launch <job-name> --location odin-flow-prod --preset default
```

### Retry a Failed Run (from failure)

**IMPORTANT**: Always confirm with the user before retrying.

```bash
# Re-execute from the failed step (skips already-succeeded steps)
scripts/dagster-query --retry <run-id>

# Re-execute all steps from scratch
scripts/dagster-query --retry <run-id> --all-steps
```

### Terminate a Run

**IMPORTANT**: Always confirm with the user before terminating.

```bash
# Graceful termination (sends SIGTERM, waits for cleanup)
scripts/dagster-query --terminate <run-id>

# Force cancel immediately (SIGKILL, no cleanup)
scripts/dagster-query --terminate <run-id> --force
```

### Toggle Schedules

```bash
# Start a schedule
scripts/dagster-query --schedule-on <schedule-name>

# Stop a schedule
scripts/dagster-query --schedule-off <schedule-name>

# Specify code location if schedule name is ambiguous
scripts/dagster-query --schedule-on <schedule-name> --location odin-prod
```

### Toggle Sensors

```bash
# Start a sensor
scripts/dagster-query --sensor-on <sensor-name>

# Stop a sensor
scripts/dagster-query --sensor-off <sensor-name>

# Specify code location if sensor name is ambiguous
scripts/dagster-query --sensor-on <sensor-name> --location odin-prod
```

## Debugging Workflow

**Always start from the job name**, not from global runs.

### 1. Check a job's recent runs

```bash
scripts/dagster-query --job-runs <job-name>
# e.g. scripts/dagster-query --job-runs daily_base_ingestion
```

### 2. See only failures for that job

```bash
scripts/dagster-query --job-runs <job-name> --status FAILURE
```

### 3. Get failure details for a specific run

```bash
scripts/dagster-query --run-detail <run-id>
```

### 4. Get full failure logs

```bash
scripts/dagster-query --run-logs <run-id> --failures-only
```

### 5. Check pod-level issues (OOM, eviction)

For pod-level issues not visible in Dagster logs, use kubectl directly (always pass `--context`):

```bash
# Check for OOMKilled pods
kubectl --context <ENV> get pods -n dagster -o json | jq '.items[] | select(.status.containerStatuses[]?.lastState.terminated.reason == "OOMKilled") | .metadata.name'

# Check run pod logs
kubectl --context <ENV> logs -n dagster dagster-run-<uuid>-<suffix> --tail=200

# User code server logs (asset-level errors)
kubectl --context <ENV> get pods -n dagster | grep user-deployments
kubectl --context <ENV> logs -n dagster <user-code-pod> --tail=200
```

## Common Failure Patterns

| Pattern | Log Signal | Root Cause |
|---------|-----------|------------|
| SIGKILL in step | "terminated by signal 9" | OOM — pod exceeded memory limit |
| Step dependencies failed | "Dependencies for step X failed" | Upstream step failed, cascade |
| Run FAILURE immediately | Very short duration, few events | Config error or code location issue |
| Stuck in STARTED for hours | No new log events | Deadlock or external dependency timeout |

## Safety Rules

- **Read operations** (--runs, --run-detail, --run-logs, --locations, --schedules, --sensors): Safe, run anytime
- **Write operations** (--launch, --retry, --terminate, --schedule-on/off, --sensor-on/off): **Always ask the user for confirmation first**
- Never launch, retry, terminate, or toggle schedules/sensors automatically without explicit user approval
