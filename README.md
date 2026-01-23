# Surf Skills

Claude Code skills for Surf platform development.

## Available Skills

| Skill | Description | For |
|-------|-------------|-----|
| `surf-golang-dev` | Go development guide (muninn, argus) | Backend engineers |
| `surf-push-code` | Automate Git workflow (branch, commit, PR, merge) | All engineers |
| `surf-db-debug` | Query staging/production databases via SSH bastion | All engineers |
| `langfuse-trace-analysis` | Analyze Langfuse traces for debugging agent execution | AI/Agent engineers |

## Setup

### 1. Clone this repo

```bash
cd ~/.claude/skills
git clone git@github.com:cyberconnecthq/surf-skills.git
```

### 2. Enable the skills you need

Create symlinks only for the skills relevant to your role:

```bash
cd ~/.claude/skills

# All engineers - enable push workflow skill
ln -s surf-skills/surf-push-code surf-push-code

# Backend engineers - enable Go skill
ln -s surf-skills/surf-golang-dev surf-golang-dev

# Database debugging - enable db skill (requires additional setup)
ln -s surf-skills/surf-db-debug surf-db-debug

# AI/Agent engineers - enable trace analysis skill
ln -s surf-skills/langfuse-trace-analysis langfuse-trace-analysis

# Frontend engineers - enable frontend skill (coming soon)
# ln -s surf-skills/surf-frontend-dev surf-frontend-dev
```

### 4. Additional Setup for surf-db-debug

The database debugging skill requires a private configuration file with your connection details. This file is **never committed to git**.

```bash
# Run setup check - Claude will guide you through configuration
~/.claude/skills/surf-db-debug/scripts/surf-db-query --check-setup
```

No external dependencies needed - uses Python3's built-in `json` module.

See `surf-db-debug/references/setup.md` for detailed setup instructions.

### 3. Sync updates

Periodically pull to get team learnings:

```bash
cd ~/.claude/skills/surf-skills
git pull
```

## Contributing Learnings

When Claude suggests adding a learning:

1. Claude will update `learnings.md` in the appropriate skill
2. Commit and push the change
3. Team members get updates via `git pull`

## Adding New Skills

To add a new skill (e.g., `surf-frontend-dev`):

1. Create directory: `surf-frontend-dev/`
2. Add `SKILL.md` with YAML frontmatter
3. Add `references/` and `learnings.md` as needed
4. Update this README
