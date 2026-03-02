# surf-core -- Surf Data CLI

restish-powered CLI auto-generated from hermod's OpenAPI 3.1 spec. No hand-coded wrappers -- every hermod endpoint is instantly available as a CLI command.

## Quick Start

```bash
# 1. Install restish (if not already)
brew install restish          # macOS
# or: go install github.com/danielgtaylor/restish@latest

# 2. Install surf-core
git clone git@github.com:cyberconnecthq/surf-core.git
cd surf-core && ./install.sh

# 3. Login and go
surf-session login            # One-click Google Sign-In
restish surf get-market-price --ids bitcoin --vs-currencies usd
```

## Architecture

```
User / Agent
    |
    |--- restish surf <command>
    |        |
    |        |--- bin/surf-auth (reads JWT, auto-refreshes)
    |        |        |
    |        |        v
    |        |   ~/.surf-core/session.json
    |        |
    |        +--- OpenAPI 3.1 spec (auto-discovered)
    |                 |
    |                 v
    |         Hermod Gateway (api.stg.ask.surf)
    |              |-- JWT verification
    |              |-- Credit deduction
    |              +-- Upstream APIs (CoinGecko, DeBank, etc.)
    |
    +--- surf-session login (Google OAuth -> JWT)
```

**How it works:** `restish` reads hermod's OpenAPI 3.1 spec at startup, generates CLI commands for all endpoints, and uses `bin/surf-auth` as an external auth tool to inject the Bearer token into every request. When hermod adds new APIs, they appear automatically -- no surf-core changes needed.

## Directory Structure

```
surf-core/
├── install.sh                 # Install restish config + skills + CLI tools
├── bin/
│   └── surf-auth              # restish external auth script (JWT read + refresh)
├── config/
│   └── apis.json.template     # restish API config template
├── login/                     # Google OAuth login
│   ├── SKILL.md
│   └── scripts/
│       ├── surf-session       # Login/check/refresh session
│       └── _oauth_browser.py  # OAuth browser flow
├── skills/
│   └── surf-api/
│       └── SKILL.md           # Agent skill: all hermod APIs via restish
├── CLAUDE.md
└── README.md
```

## For Agents

Agent-discoverable skills are in `skills/surf-api/SKILL.md`. After `./install.sh`, the skill is symlinked to `~/.claude/skills/surf-api` for automatic discovery by Claude Code and other agent platforms. See the SKILL.md for command examples, cost tables, and the full 87-command reference.

## Session Management

```bash
surf-session login    # Google Sign-In (opens browser)
surf-session check    # Verify session is valid
```

Session is stored at `~/.surf-core/session.json`. Tokens auto-refresh for 30 days. `bin/surf-auth` handles refresh transparently on every `restish surf` call.

## Install Management

```bash
./install.sh           # Install everything
./install.sh --check   # Verify installation status
./install.sh --remove  # Uninstall everything
./install.sh --help    # Show help
```

## Adding New Endpoints

No changes needed in surf-core. When hermod adds a new API endpoint:

1. The OpenAPI spec updates automatically
2. `restish surf list-operations` shows the new command
3. `restish surf <new-command> --help` shows its parameters

The CLI stays in sync with hermod at all times.
