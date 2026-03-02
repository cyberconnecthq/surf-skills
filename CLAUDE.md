# CLAUDE.md -- surf-core

restish-based CLI for the Surf data platform. All hermod API endpoints are auto-generated from the OpenAPI 3.1 spec via `restish` -- no hand-coded wrappers.

## Directory Structure

```
surf-core/
├── install.sh                 # Install restish config + skills + CLI tools
├── bin/
│   └── surf-auth              # restish External Tool auth script (JWT + refresh)
├── config/
│   └── apis.json.template     # restish API config template (__HERMOD_URL__, __SURF_AUTH_PATH__)
├── login/                     # Google OAuth login (preserved, not generated)
│   ├── SKILL.md
│   └── scripts/
│       ├── surf-session       # surf-session login/check
│       └── _oauth_browser.py
├── skills/
│   └── surf-api/
│       └── SKILL.md           # Agent skill: all hermod APIs via restish
├── CLAUDE.md
└── README.md
```

## Getting Started

```bash
brew install restish           # prerequisite
./install.sh                   # configures restish + symlinks skills + sets PATH
surf-session login             # Google Sign-In (one-time)
restish surf list-operations   # verify: lists all 87 commands
```

## Key Files

- **`bin/surf-auth`** -- restish external auth tool. Reads `~/.surf-core/session.json`, auto-refreshes JWT if <5 min to expiry, outputs `{"headers":{"authorization":["Bearer <token>"]}}` to stdout.
- **`config/apis.json.template`** -- Template for restish config. `install.sh` replaces `__HERMOD_URL__` and `__SURF_AUTH_PATH__` and writes to the OS-appropriate restish config directory.
- **`skills/surf-api/SKILL.md`** -- Single agent-discoverable skill for all hermod data APIs. Contains examples for all 8 domains, cost table, and full command reference.
- **`install.sh`** -- 4-step installer: check restish, write config, symlink skills, symlink bin + PATH.

## Adding New Endpoints

No surf-core changes needed. Add the endpoint in hermod -- restish discovers it automatically from the updated OpenAPI spec. `restish surf list-operations` will show the new command.

## Login Flow

1. `surf-session login` opens browser for Google OAuth
2. Callback writes JWT tokens to `~/.surf-core/session.json`
3. `bin/surf-auth` reads the session file on every `restish surf` call
4. If token expires in <5 min, `surf-auth` refreshes via `POST /v2/auth/refresh` to muninn
5. Fresh Bearer token is injected into the request by restish
