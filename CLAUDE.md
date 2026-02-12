# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Claude Code skills repository for Surf platform development. Skills are specialized knowledge modules organized by category (`surf-dev-*` for development, `surf-data-*` for data/analytics).

## Repository Structure

```
surf-skills/
├── surf-dev-golang/              # Go development skill
│   ├── SKILL.md                  # Skill definition with YAML frontmatter
│   ├── learnings.md              # Team-shared learnings (updated by Claude)
│   └── references/               # Detailed reference documentation
├── surf-dev-push-code/           # Git workflow automation skill
│   ├── SKILL.md
│   └── references/
├── surf-data-clickhouse/         # ClickHouse query skill
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
├── surf-data-db-debug/           # Database debugging skill
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
├── surf-data-langfuse-trace/     # Langfuse trace analysis skill
│   ├── SKILL.md
│   ├── references/
│   └── fetch_trace.py
└── README.md
```

## Adding New Skills

1. Create a directory with category prefix: `surf-dev-<name>/` or `surf-data-<name>/`
2. Add `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: surf-<category>-<skill-name>
   description: <description for when to activate this skill>
   ---
   ```
3. Add `references/` directory for detailed documentation
4. Add `learnings.md` for team-shared learnings
5. Update root README.md

## Self-Learning Protocol

When working on Surf platform code and receiving user feedback:

1. **Apply the feedback** to the current task
2. **Persist the learning**:
   - General Go patterns → Update `learnings.md` in this repo
   - Project-specific info → Update that project's `CLAUDE.md`
3. **Commit the update** to the appropriate repository

Learning format:
```markdown
## [Category]

### [Brief Title]

**Rule**: [Clear statement]
**Rationale**: [Why this matters]
**Example**: [Code if applicable]
```

## Shell Scripting

All bash scripts in skills must work on **macOS default bash (3.x)**. Avoid bash 4+ syntax:

| Avoid (bash 4+) | Use instead (POSIX-compatible) |
|---|---|
| `${var^^}` (uppercase) | `$(printf '%s' "$var" \| tr '[:lower:]' '[:upper:]')` |
| `${var,,}` (lowercase) | `$(printf '%s' "$var" \| tr '[:upper:]' '[:lower:]')` |
| Associative arrays `declare -A` | Use `case` statements or JSON with `python3 -c` |

## Credential Handling

All skills that need secrets must follow these rules:

1. **AWS Secrets Manager is always #1 priority.** When AWS credentials are available, they override env vars and config files.
2. **Secrets only live in memory.** Never write credentials to disk (no temp files, no logs, no caches). Use shell variables or `os.environ` (process-scoped) only.
3. **Fallback order:** AWS Secrets Manager → environment variables → config file.

## Skill Installation

Install via CLI:
```bash
npx skills add cyberconnecthq/surf-skills
```

Or manually via symlinks:
```bash
cd ~/.claude/skills
ln -s /path/to/surf-skills/surf-dev-golang surf-dev-golang
```
