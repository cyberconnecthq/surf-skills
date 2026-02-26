# Authentication — Reference

## Overview

All Hermod API endpoints require JWT Bearer authentication: `Authorization: Bearer <access_token>`

## Session Management

Session persists to `~/.surf-core/session.json`:
- Access token: 1 hour TTL
- Refresh token: 30 days TTL
- Login once, use for 30 days with auto-refresh

## Login Flow

```bash
# Login (opens browser for Google Sign-In)
runtimes/cli/login/scripts/surf-session login

# Check session status
runtimes/cli/login/scripts/surf-session check

# View credit balance
runtimes/cli/login/scripts/surf-session credits

# Manual refresh
runtimes/cli/login/scripts/surf-session refresh
```

## Auto-Refresh

The shared `lib/config.sh` automatically checks JWT expiry before each API call and refreshes if needed. No manual intervention required after initial login.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SURF_SESSION_FILE` | Override session file path (default: `~/.surf-core/session.json`) |
| `SURF_API_BASE` | Override API base URL |
