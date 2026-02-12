# Push Code Workflow Details

## Error Handling

| Error | Action |
|-------|--------|
| No changes to commit | Inform user, stop workflow |
| CI fails | Show failure details, stop workflow |
| Merge conflicts | Inform user, provide resolution steps |
| Push rejected | Pull latest main, rebase, retry |

## Example Session

User: `/surf-dev-push-code`

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
