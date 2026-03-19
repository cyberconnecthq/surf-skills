---
name: odin-dev-push-code
description: Automate the Git workflow for pushing code changes. Creates feature branch, commits, pushes, and creates PR. Use when user says /odin-dev-push-code or asks to push their changes.
---

# Surf Push Code Workflow

Automated Git workflow for pushing code changes up to PR creation. Merge is left to the user.

## Usage

```
/odin-dev-push-code [branch-name] [commit-message]
```

If branch-name or commit-message not provided, Claude will:
1. Generate branch name from the changes (e.g., `feature/add-user-auth`)
2. Generate commit message by analyzing the diff

## Workflow Steps

Execute these steps in order:

### 1. Pre-flight Checks

```bash
# Ensure we're on main and it's up to date
git status
git diff --stat
```

- Verify there are uncommitted changes
- If no changes, inform user and stop

### 2. Create Feature Branch

```bash
# Generate descriptive branch name from changes
git checkout -b feature/<descriptive-name>
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `chore/` - Maintenance tasks

### 3. Commit Changes

```bash
git add -A
git commit -m "<commit-message>"
```

Commit message format:
- `[FEATURE]` - New features
- `[FIX]` - Bug fixes
- `[REFACTOR]` - Code refactoring
- `[CHORE]` - Maintenance

### 4. Push to Remote

```bash
git push -u origin <branch-name>
```

### 5. Create Pull Request

```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
- <bullet points of changes>

## Test plan
- [ ] <test items>
EOF
)"
```

### 6. Done

- Print the PR URL for the user
- Workflow stops here — merge is left to the user after reviewing CI results

For error handling, examples, and tips, see [references/workflow.md](references/workflow.md).
