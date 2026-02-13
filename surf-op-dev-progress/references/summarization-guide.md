# Summarization Guide

## Output Format

Default to **Slack format** (mrkdwn). Use markdown tables only if the user explicitly asks for markdown.

### Slack format (default)

Use Slack mrkdwn — no tables, since Slack doesn't render them. Structure:

```
*Team Progress — YYYY-MM-DD*
_Window description · N commits_

*By Repo*

*repo-name* — Contributor1, Contributor2
Summary of what happened

*repo-name* — Contributor1
Summary of what happened

———

*By Person*

*Person Name* — repo1, repo2
Summary of what they did
```

Example:

```
*By Repo*

*muninn* — Darclindy, HappySean
Built vibe coding mode with live preview (proxy + iframe, replaced Sandpack); added tabbed Preview/Debug panel; coupon mapping CRUD

*swell* — Ryan Li, Zhimao Liu, PengDeng
Kalshi prediction market integration; converted daily models to incremental; dbt test framework; CH parquet imports

———

*By Person*

*Darclindy* — muninn, urania, odin-flow
Built vibe coding mode end-to-end: live preview proxy, iframe approach, tabbed debug panel, design skills; unified Bithumb report templates

*Ryan Li* — diver, swell
Session/trace detail pages with Langfuse; UUID lookup page; L3 incident investigation; ClickHouse query fixes; dbt test framework; incremental model refactor
```

### Markdown table format (on request)

| Repo | Contributors | What happened |
|------|-------------|---------------|
| muninn | Darclindy, HappySean | Built vibe coding mode with live preview |
| swell | Ryan Li, PengDeng | Kalshi integration; dbt test framework |

## Summarization Rules

Raw commit messages like:
> fix: escape single quotes in bot_classification SQL query (#69); fix: ClickHouse 25.x FINAL alias syntax and bot_classification OOM (#70); fix: add missing aiohttp dependency for bot_classification (#71)

Become: **"Bot classification fixes (SQL escaping, OOM, dependency)"**

Rules:
- Write like telling a teammate what someone worked on today
- Group related commits into one theme (don't list 5 separate fix commits)
- Lead with the most impactful work, not chores
- Use plain language — "built X", "fixed Y", "added Z"
- Keep each cell to 1-2 lines
- Don't lose meaningful work — every feature/fix should be reflected
- Separate themes with semicolons
