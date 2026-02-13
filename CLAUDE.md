# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Claude Code skills repository for Surf platform development. Skills are specialized knowledge modules organized by category (`surf-dev-*` for development, `surf-data-*` for data/analytics, `surf-op-*` for operations).

## Repository Structure

```
surf-skills/
├── surf-dev-golang/              # Go development skill
│   ├── SKILL.md                  # Skill definition with YAML frontmatter
│   ├── learnings.md              # Team-shared learnings (updated by Claude)
│   └── references/               # Detailed reference documentation
├── surf-dev-repo-map/            # Surf platform repo map (~41 active repos)
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
├── surf-dev-push-code/           # Git workflow automation skill
│   ├── SKILL.md
│   └── references/
├── surf-data-clickhouse/         # ClickHouse query skill
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
├── surf-data-db/           # Database debugging skill
│   ├── SKILL.md
│   ├── references/
│   │   ├── setup.md
│   │   └── surf-tables.md  # Key table schemas & gotchas (shared with ClickHouse)
│   └── scripts/
├── surf-data-langfuse-trace/     # Langfuse trace analysis skill
│   ├── SKILL.md
│   ├── references/
│   └── fetch_trace.py
├── surf-op-dev-progress/         # Daily team progress report skill
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
└── README.md
```

## Adding or Modifying Skills

**Always use the `skill-creator` skill** (at `~/.agents/skills/skill-creator/`) when adding new skills or making changes to existing ones. It enforces best practices:

- **Concise SKILL.md** — only add what Claude doesn't already know; challenge every token
- **Progressive disclosure** — metadata (~100 words) → SKILL.md body (<5k words) → `references/` (unlimited)
- **Description is the trigger** — include WHAT the skill does and specific WHEN/WHERE triggers. Do NOT add "When to Use" sections in the body.
- **Validate** before committing: `python3 ~/.agents/skills/skill-creator/scripts/quick_validate.py <path/to/skill-folder>`

Steps:
1. Create a directory with category prefix: `surf-dev-<name>/`, `surf-data-<name>/`, or `surf-op-<name>/`
2. Add `SKILL.md` with YAML frontmatter (name: kebab-case, max 64 chars)
3. Move detailed docs to `references/` — link from SKILL.md with clear guidance on when to read
4. Add `learnings.md` for team-shared learnings if applicable
5. Update root README.md and CLAUDE.md structure tree

## Self-Learning Protocol

When working on Surf platform code and receiving user feedback:

1. **Apply the feedback** to the current task
2. **Persist the learning**:
   - General Go patterns → Update `learnings.md` in this repo
   - Project-specific info → Update that project's `CLAUDE.md`
   - Data/schema discoveries (table gotchas, column value enums, query patterns) → Update the relevant skill's `references/` docs (e.g., `analytics-tables.md`, `surf-tables.md`). Keep both `surf-data-clickhouse` and `surf-data-db` in sync since they query the same underlying data.
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
