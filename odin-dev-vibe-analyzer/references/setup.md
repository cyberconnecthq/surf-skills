# Credential Setup Guide

Read this when data collection commands fail with auth errors (missing keys, 401, connection refused).

## Datadog (`~/.ddlog.json`)

Error signature: `ERROR: DD_API_KEY and DD_APP_KEY required`

Check: `cat ~/.ddlog.json 2>/dev/null`

If missing, ask the user for keys and write:
```json
{"api_key": "<user_provided>", "app_key": "<user_provided>", "site": "datadoghq.com"}
```

> Where to get keys: Datadog → Organization Settings → API Keys / Application Keys

## Langfuse (`~/.config/langfuse/config.json`)

Error signature: Langfuse SDK init failure, 401, connection timeout

Check: `cat ~/.config/langfuse/config.json 2>/dev/null`

If missing, ask the user for keys and write:
```json
{
  "langfuse_public_key": "<user_provided>",
  "langfuse_secret_key": "<user_provided>",
  "langfuse_host": "https://langfuse.ask.surf"
}
```

> Where to get keys: https://langfuse.ask.surf → Settings → API Keys

## kubectl context

Error signature: `efs-pull.sh` cannot connect to pod, `kubectl` command not found

Check: `kubectl config current-context 2>/dev/null`

EFS access requires `prd-app` context. If unavailable, skip the EFS dimension and analyze with Datadog + Langfuse only.
