# Summarization Guide

## Output Format

Default to **standard markdown**. The summary is posted to Notion (which needs markdown). Slack only receives a title + link, not the full summary.

### Structure

```
# Team Progress — YYYY-MM-DD

## By Repo

**repo-name** — Contributor1, Contributor2
Summary of what happened

**repo-name** — Contributor1
Summary of what happened

---

## By Person

**Person Name** — repo1, repo2
Summary of what they did
```

Example:

```
## By Repo

**muninn** — Darclindy, HappySean
Built vibe coding mode with live preview (proxy + iframe, replaced Sandpack); added tabbed Preview/Debug panel; coupon mapping CRUD

**swell** — Ryan Li, Zhimao Liu, PengDeng
Kalshi prediction market integration; converted daily models to incremental; dbt test framework; CH parquet imports

---

## By Person

**Darclindy** — muninn, urania, odin-flow
Built vibe coding mode end-to-end: live preview proxy, iframe approach, tabbed debug panel, design skills; unified Bithumb report templates

**Ryan Li** — diver, swell
Session/trace detail pages with Langfuse; UUID lookup page; L3 incident investigation; ClickHouse query fixes; dbt test framework; incremental model refactor
```

## Summarization Rules

Raw commit messages like:
> fix: escape single quotes in bot_classification SQL query (#69); fix: ClickHouse 25.x FINAL alias syntax and bot_classification OOM (#70); fix: add missing aiohttp dependency for bot_classification (#71)

Become: **"Bot classification fixes (SQL escaping, OOM, dependency)"**

Rules:
- No metadata in the summary — no commit counts, no timestamps, no window descriptions
- Write like telling a teammate what someone worked on today
- Group related commits into one theme (don't list 5 separate fix commits)
- Lead with the most impactful work, not chores
- Use plain language — "built X", "fixed Y", "added Z"
- Keep each cell to 1-2 lines
- Don't lose meaningful work — every feature/fix should be reflected
- Separate themes with semicolons
