---
name: surf-login
description: Connect to Hermod API Gateway — login, session management, auto-refresh
tools: ["bash"]
---

# Hermod Session — API Gateway Connection

Login and manage the Hermod API Gateway session. **This is the prerequisite for all other surf-core skills.**

## When to Use

Use this skill **first**, before any other surf-core skill, when:
- Agent is freshly configured and needs to connect to Hermod
- Session token has expired and needs renewal
- Need to verify the current session is still valid
- Need to check credit balance

## Login

```bash
# Open browser for Google Sign-In (one-click)
surf-login/scripts/surf-session login
# → Opens browser, user clicks Google account, session saved automatically.
```

Agent workflow:
1. Run `surf-session login` — browser opens Google Sign-In
2. User clicks their Google account
3. Session is saved automatically — done

### Manual JWT (Advanced, no auto-refresh)

```bash
surf-login/scripts/surf-session configure --token <JWT>
```

## Session Management

```bash
# Verify connectivity (auto-refreshes if needed)
surf-login/scripts/surf-session check

# View session info (decoded JWT, expiry, refresh token status)
surf-login/scripts/surf-session status

# Manually refresh access token
surf-login/scripts/surf-session refresh

# Check credit balance
surf-login/scripts/surf-session credits

# Remove session
surf-login/scripts/surf-session logout
```

## Auto-Refresh

When a session has a `refresh_token` (from `login`):
- `lib/config.sh` auto-refreshes the access token when it's within 5 minutes of expiry
- `check` and `credits` also auto-refresh before API calls
- Access tokens: 1 hour. Refresh tokens: 30 days.
- Login once, use for 30 days with no manual intervention.

## Session File

`~/.surf-core/session.json`:
```json
{
  "hermod_url": "https://api.stg.ask.surf/gateway",
  "hermod_token": "<access_token>",
  "refresh_token": "<refresh_token>"
}
```

Environment variables (`HERMOD_TOKEN`, `HERMOD_URL`) override the file.

## Staging

```bash
surf-login/scripts/surf-session login --url https://api.stg.ask.surf/gateway
```

See `references/auth.md` for full authentication architecture.
