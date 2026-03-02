# Surf Skills

Claude Code skills for Surf platform development.

## Available Skills

| Skill | Description | For |
|-------|-------------|-----|
| `odin-dev-golang` | Go development guide (muninn, argus) | Backend engineers |
| `odin-dev-kube` | Kubernetes operations — rollouts, ArgoCD refresh, sealed secrets, pod debugging | DevOps/Backend engineers |
| `odin-dev-repo-map` | Surf platform repo map — Norse names → purposes, dependencies, bug guide | All engineers |
| `odin-dev-dagster` | Dagster pipeline management — runs, logs, schedules, launch/retry | DevOps/Data engineers |
| `odin-dev-push-code` | Automate Git workflow (branch, commit, PR, merge) | All engineers |
| `odin-data-clickhouse` | Query ClickHouse Cloud for blockchain data and product analytics | Data/Analytics engineers |
| `odin-data-db` | Query staging/production databases via SSH bastion | All engineers |
| `odin-data-langfuse-trace` | Analyze Langfuse traces for debugging agent execution | AI/Agent engineers |
| `odin-op-bad-case-audit` | Audit AI bad cases from user feedback with Langfuse traces | AI/Agent engineers |
| `odin-op-dev-progress` | Daily team progress report from GitHub commits | Team leads |
| `odin-team-dev` | Team-based development — Goal mode (Architect+Developer+Tester+Pusher) and Parallel mode for M/L scope tasks | All engineers |

## Setup

```bash
# Install / update all skills (no prompts)
npx skills add cyberconnecthq/odin-skills --global --all
```

### Additional Setup for odin-data-db

The database debugging skill requires a private configuration file with your connection details. This file is **never committed to git**.

```bash
# Run setup check - Claude will guide you through configuration
odin-data-db/scripts/odin-db-query --check-setup
```

See `odin-data-db/references/setup.md` for detailed setup instructions.

## Contributing Learnings

When Claude suggests adding a learning:

1. Claude will update `learnings.md` in the appropriate skill
2. Commit and push the change
3. Team members get updates via `git pull`

## Development

For live editing while developing skills, use symlinks instead of `npx skills add`:

```bash
git clone git@github.com:cyberconnecthq/odin-skills.git
cd ~/.claude/skills
ln -s /path/to/odin-skills/odin-dev-golang odin-dev-golang
```

Changes to the repo are reflected immediately — no reinstall needed.

### Adding New Skills

1. Create directory with category prefix: `odin-dev-<name>/` or `odin-data-<name>/`
2. Add `SKILL.md` with YAML frontmatter
3. Add `references/` and `learnings.md` as needed
4. Update this README
