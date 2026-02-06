# Setup Guide

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package runner)
- Langfuse account with API keys

## Configuration

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

Environment variables (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`) override the config file if set.

## Install the Skill

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/surf-skills/langfuse-trace-analysis ~/.claude/skills/langfuse-trace-analysis
```

## Verify

```bash
# Should print usage without errors
uv run /path/to/surf-skills/langfuse-trace-analysis/fetch_trace.py --list
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No module named 'langfuse'` | Use `uv run fetch_trace.py` not `uv run python fetch_trace.py` |
| `Authentication error: ... without public_key` | Check `~/.config/langfuse/config.json` has correct keys |
| `Could not find trace <id>` | Verify the trace ID exists in your Langfuse project |
| Permission denied on config | `chmod 600 ~/.config/langfuse/config.json` |
