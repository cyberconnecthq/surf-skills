# Setup Guide

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package runner)
- Langfuse account with API keys

## Credential Priority

Credentials are resolved in this order (first found wins per key):

1. **Environment variables** — `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
2. **Config file** — `~/.config/langfuse/config.json`
3. **AWS Secrets Manager** — secret `langfuse/surf-ai/bot` (requires `aws` CLI)

Config file takes priority over AWS because it represents explicit local intent, while the AWS secret may be stale (e.g. after the cloud → self-hosted migration).

## Proxy Handling

The script automatically handles proxy issues:
- **SOCKS proxy** (`all_proxy`): Always removed — httpx crashes without the `socksio` package.
- **HTTP proxy** (`http_proxy`/`https_proxy`): Removed for internal hosts (`*.ask.surf`, `*.svc.cluster.local`) — they are reachable directly and proxying causes timeouts.

## Configuration

### Option A: AWS Secrets Manager (recommended)

If your team stores Langfuse credentials in AWS Secrets Manager under `langfuse/surf-ai/bot`, no local configuration is needed — just ensure the AWS CLI is configured:

```bash
aws configure
```

The secret should contain JSON keys: `public_key`, `secret_key`, `base_url`.

### Option B: Config file

Create the config file:

```bash
mkdir -p ~/.config/langfuse && chmod 700 ~/.config/langfuse
touch ~/.config/langfuse/config.json && chmod 600 ~/.config/langfuse/config.json
```

Edit `~/.config/langfuse/config.json`:

```json
{
  "langfuse_public_key": "pk-lf-...",
  "langfuse_secret_key": "sk-lf-...",
  "langfuse_host": "https://cloud.langfuse.com"
}
```

### Option C: Environment variables

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

## Install the Skill

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/odin-skills/odin-data-langfuse-trace ~/.claude/skills/odin-data-langfuse-trace
```

## Verify

```bash
# Should print usage without errors
uv run /path/to/odin-skills/odin-data-langfuse-trace/fetch_trace.py --list
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No module named 'langfuse'` | Use `uv run fetch_trace.py` not `uv run python fetch_trace.py` |
| `Authentication error: ... without public_key` | Check credentials: AWS secret, env vars, or config file |
| `Could not find trace <id>` | Verify the trace ID exists in your Langfuse project |
| Permission denied on config | `chmod 600 ~/.config/langfuse/config.json` |
