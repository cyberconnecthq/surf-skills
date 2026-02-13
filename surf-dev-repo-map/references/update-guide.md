# Updating the Repo Map

This skill should be refreshed periodically as repos are added, archived, or change purpose.

## When to Update

- **Monthly** — run the refresh script to catch new/archived repos
- **On new service** — when a new backend service or data pipeline is created
- **On service retirement** — when a repo is archived or deprecated
- **On ownership change** — when a repo moves between product lines (e.g., Surf ↔ Cyber)

## Refresh Script

Run the script to generate a fresh snapshot of active repos:

```bash
surf-dev-repo-map/scripts/refresh-repos
```

The script outputs a markdown report of all active `cyberconnecthq` repos with:
- Repo name, language, description, last push date
- Flagging of repos not yet in the skill (new repos)
- Flagging of repos in the skill that are now archived/inactive

## Manual Update Steps

After running the script:

1. **Review new repos** — determine if they belong to Surf or Cyber/Link3
2. **Add Surf repos** to the appropriate category in `SKILL.md`
3. **For backend services** — read the repo's README.md and CLAUDE.md to write a description:
   ```bash
   gh api repos/cyberconnecthq/<repo>/contents/README.md --jq '.content' | base64 -d
   gh api repos/cyberconnecthq/<repo>/contents/CLAUDE.md --jq '.content' | base64 -d
   ```
4. **Update service-details.md** if the repo is a significant service
5. **Remove archived repos** from the skill
6. **Update the service map diagram** in SKILL.md if dependencies changed
7. **Update the "Not Surf" exclusion list** if new Cyber/Link3 repos appeared

## What to Capture for Each Repo

| Field | Where to Find |
|---|---|
| Purpose (one line) | README.md first paragraph, or CLAUDE.md "Project Overview" |
| Language | `gh repo view cyberconnecthq/<repo> --json primaryLanguage` |
| What it owns | Look at `internal/service/` (Go) or main modules (Python/TS) |
| What it talks to | Look at gRPC client imports, config files, or CLAUDE.md |
| Ports / API paths | README.md or `internal/start/` directory |

## Exclusion Rules

These product lines are **not Surf** — do not add them:

- **Cyber/CyberConnect**: Repos for the Cyber L2 chain, CyberID, CyberWallet, staking, bridging
  - Key indicators: talks to `rhea`, `hades` over gRPC; mentions CCV3, CyberID, CyberWallet
  - Known repos: `thor`, `hades`, `heracles`, `balder`, `phantasos`, `hermes`, `demeter`, `rhea`, `ladon`
- **Link3**: Social/professional platform repos
  - Known repos: `link3`, `link3-web-v2`, `link3-notification-tg-bot`, `link3-org-verify-bot`, `nox-backend`

## Commit Convention

When updating this skill:

```bash
docs: update surf-dev-repo-map with new repos from <month> <year>
```
