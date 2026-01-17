---
name: surf-push-code
description: Automate the Git workflow for pushing code changes. Creates feature branch, commits, pushes, creates PR, waits for CI, squash merges, and cleans up. Use when user says /surf-push-code or asks to push/merge their changes.
---

# Surf Push Code Workflow

Automated Git workflow for pushing code changes to production.

## Usage

```
/surf-push-code [branch-name] [commit-message]
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

Use GitHub MCP tool:
```
mcp__plugin_github_github__create_pull_request
```

PR body format:
```markdown
## Summary
- <bullet points of changes>

## Test plan
- [ ] <test items>
```

### 6. Wait for CI

```bash
# Poll CI status every 5-10 seconds
gh pr checks <pr-number> --repo <owner>/<repo>
```

- Wait for `auto-approve` check to pass
- If CI fails, inform user and stop

### 7. Squash & Merge

Use GitHub MCP tool:
```
mcp__plugin_github_github__merge_pull_request
  merge_method: squash
  commit_title: "<original-title> (#<pr-number>)"
```

### 8. Cleanup

```bash
# Switch to main and pull latest
git checkout main
git pull

# Delete local feature branch
git branch -d <branch-name>
```

## Error Handling

| Error | Action |
|-------|--------|
| No changes to commit | Inform user, stop workflow |
| CI fails | Show failure details, stop workflow |
| Merge conflicts | Inform user, provide resolution steps |
| Push rejected | Pull latest main, rebase, retry |

## Example Session

User: `/surf-push-code`

Claude:
1. Analyzes diff: "3 files changed - adding filtered tags for signal processing"
2. Creates branch: `feature/add-filtered-tags-for-signal`
3. Commits with message: `[FIX] Add filtered tags for signal processing`
4. Pushes and creates PR
5. Waits for CI (shows: "CI passed in 5s")
6. Squash merges
7. Cleans up: "Done! PR #123 merged. Local branch deleted."

## Tips

- Always verify the generated branch name and commit message make sense
- If the repo has specific commit message requirements, adjust accordingly
- For large changes, consider splitting into multiple PRs
