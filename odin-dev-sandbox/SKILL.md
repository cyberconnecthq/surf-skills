---
name: odin-dev-sandbox
description: Inspect and pull EFS workspace files from urania sandbox pods. Use when user asks to view sandbox files, pull user workspace code, check EFS file structure, download vibe coding projects, or analyze sandbox outputs by user_id or session_id.
---

# Sandbox EFS Inspector

Browse and download workspace files from urania-agent sandbox pods (EFS-backed `/workspaces/`).

## CLI Tool

Script: `surf-skills/odin-dev-sandbox/scripts/efs-pull.sh`

```bash
SCRIPT="surf-skills/odin-dev-sandbox/scripts/efs-pull.sh"

# Show file tree for a user
bash $SCRIPT <user_id> tree
bash $SCRIPT <user_id> tree --project 20260313_160659

# List all projects with sizes
bash $SCRIPT <user_id> list

# Show disk usage
bash $SCRIPT <user_id> du

# Pull project to local
bash $SCRIPT <user_id> pull --project 20260313_160659
bash $SCRIPT <user_id> pull --code-only    # all projects, skip .claude/
bash $SCRIPT <user_id> pull                 # entire workspace

# Resolve session_id → user_id automatically
bash $SCRIPT --session <session_id> tree
bash $SCRIPT --session <session_id> pull --project 20260313_160659
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--session ID` | - | Resolve user from session_id |
| `--project TS` | - | Target specific project (e.g. `20260313_160659`) |
| `--output DIR` | `/tmp/efs-pull/<user_id>/` | Local output directory |
| `--context CTX` | `prd` | kubectl context (`prd` or `stg`) |
| `--code-only` | off | Skip `.claude/` metadata, only pull code |

### Output

Downloaded files go to `/tmp/efs-pull/<user_id>/` by default. Excludes `node_modules/`, `.git/`, `.vite/`, `dist/`, `.cache/`.

## EFS Workspace Structure

```
/workspaces/{user_id}/
├── .claude/                          # Claude SDK config
│   ├── settings.local.json           # Skills, model settings
│   ├── skills/                       # Injected skills
│   └── projects/.../                 # Session JSONL conversation logs
└── workspace/
    └── outputs/
        └── {YYYYMMDD_HHMMSS}/        # Each vibe session's generated project
            ├── frontend/             # React/Vite app
            ├── backend/              # Node.js API
            ├── package.json
            └── ...
```

## Prerequisites

- `kubectl` configured with `prd` (or `stg`) context
- Access to `app` namespace
- At least one running `urania-agent` pod
