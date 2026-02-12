# Surf Skills

Claude Code skills for Surf platform development.

## Available Skills

| Skill | Description | For |
|-------|-------------|-----|
| `surf-dev-golang` | Go development guide (muninn, argus) | Backend engineers |
| `surf-dev-push-code` | Automate Git workflow (branch, commit, PR, merge) | All engineers |
| `surf-data-clickhouse` | Query ClickHouse Cloud for blockchain data and product analytics | Data/Analytics engineers |
| `surf-data-db-debug` | Query staging/production databases via SSH bastion | All engineers |
| `surf-data-langfuse-trace` | Analyze Langfuse traces for debugging agent execution | AI/Agent engineers |

## Setup

```bash
npx skills add cyberconnecthq/surf-skills
```

### Additional Setup for surf-data-db-debug

The database debugging skill requires a private configuration file with your connection details. This file is **never committed to git**.

```bash
# Run setup check - Claude will guide you through configuration
~/.claude/skills/surf-data-db-debug/scripts/surf-db-query --check-setup
```

See `surf-data-db-debug/references/setup.md` for detailed setup instructions.

## Contributing Learnings

When Claude suggests adding a learning:

1. Claude will update `learnings.md` in the appropriate skill
2. Commit and push the change
3. Team members get updates via `git pull`

## Development

For live editing while developing skills, use symlinks instead of `npx skills add`:

```bash
git clone git@github.com:cyberconnecthq/surf-skills.git
cd ~/.claude/skills
ln -s /path/to/surf-skills/surf-dev-golang surf-dev-golang
```

Changes to the repo are reflected immediately — no reinstall needed.

### Adding New Skills

1. Create directory with category prefix: `surf-dev-<name>/` or `surf-data-<name>/`
2. Add `SKILL.md` with YAML frontmatter
3. Add `references/` and `learnings.md` as needed
4. Update this README
