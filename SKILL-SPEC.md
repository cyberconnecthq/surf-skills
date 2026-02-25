# Skill Specification

Rules for building and maintaining surf-core skills. Derived from real agent testing — every rule exists because an agent failed without it.

## Directory Structure

```
surf-{name}/
├── SKILL.md                  # Required — skill manifest + usage docs
├── scripts/
│   └── surf-{cmd}            # Required — main CLI executable (bash, chmod +x)
└── references/
    └── endpoints.md          # Required for data skills — full API parameter docs
```

- One executable per skill. Helper scripts (Python, etc.) go in `scripts/` with `_` prefix (e.g., `_oauth_browser.py`).
- `references/` contains detailed docs the agent reads when it needs deeper parameter info. SKILL.md is the quick-start; references are the full manual.

## SKILL.md Format

```yaml
---
name: surf-{name}                    # Must match directory name
description: One-line description    # What an agent sees in skill discovery
tools: ["bash"]                      # Always ["bash"] for CLI skills
---
```

### Required Sections

```markdown
# {Title} — {Domain}

{One sentence: what data source, what it covers.}

## When to Use

Use this skill when you need to:
- {Bullet per use case — be specific, agents match on these}

## CLI Usage

{Complete examples for every subcommand. Show ALL flags including --limit.}

## Important Notes

- {Gotchas, warnings about large responses, required flag combos}
- {Which commands need --limit and why}

## Cost

{Credit costs per command type.}

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
```

### SKILL.md Rules

1. **Examples must be copy-pasteable.** Agent will run them verbatim. No placeholders like `<YOUR_ADDRESS>` — use real examples (`0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045`).
2. **Show --limit in examples** for any command that returns large responses. Agent won't guess optional flags.
3. **"When to Use" must be specific.** Don't write "get market data" — write "check futures funding rates and OI/market cap ratios." Agent does semantic matching.
4. **Cost must be per-command**, not per-skill. Agent uses cost to decide which command to call.

## CLI Script Conventions

### Boilerplate

```bash
#!/usr/bin/env bash
set -euo pipefail

_resolve_path() { python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$1" 2>/dev/null || echo "$1"; }
SCRIPT_DIR="$(cd "$(dirname "$(_resolve_path "${BASH_SOURCE[0]}")")" && pwd)"
source "$SCRIPT_DIR/../../lib/config.sh"
source "$SCRIPT_DIR/../../lib/http.sh"

API_PREFIX="/v1/{domain}"
```

### Usage (--help)

Must be valid JSON. Agent parses this programmatically.

```bash
usage() {
  cat <<'EOF'
{"usage": {
  "command": "surf-{cmd}",
  "subcommands": {
    "subcmd1": {"args": "--flag1 VALUE [--limit N]", "description": "What it does (N credits)"},
    "subcmd2": {"args": "--flag2 VALUE", "description": "What it does (N credits)"},
    "--check-setup": {"args": "", "description": "Verify environment configuration"}
  }
}}
EOF
}
```

Rules:
- Show `[--limit N]` in args for commands that support it.
- Description must include credit cost: `"(1 credit)"`, `"(3 credits, proxy)"`.
- Include `WARNING: returns large JSON, use --limit` for commands that can return >50KB.

### Dispatch Pattern

```bash
case "${1:---help}" in
  --check-setup) surf_check_setup ;;
  --help|-h) usage ;;

  subcmd1|subcmd2)
    ...
    ;;

  *) echo "{\"error\": \"Unknown command: $1. Available: subcmd1, subcmd2\"}" >&2; exit 1 ;;
esac
```

### Error Messages

**Every error MUST list valid options.** This is the single most impactful rule — without it, agents enter retry loops guessing flags.

```bash
# Unknown subcommand — list ALL available commands
echo "{\"error\": \"Unknown command: $1. Available: price, future, cg-markets, option, ...\"}" >&2

# Unknown flag — list valid flags for THIS subcommand
echo "{\"error\": \"Unknown flag: $1. Valid: --address, --chain, --limit\"}" >&2

# Missing required flag — state what's required and give example
echo "{\"error\": \"--address is required (e.g. 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045)\"}" >&2
```

### Output

- **All output is JSON.** No plain text, no mixed formats.
- **Data to stdout, errors to stderr.** Agent relies on exit code + stderr for error detection.
- **Errors return non-zero exit code** and `{"error": "message"}` to stderr.

### Response Size Control

Any command that can return >50KB MUST support `--limit` to truncate results.

Two implementation patterns:

**Pattern A: Server-side limit** (preferred — when API supports `limit` param)
```bash
# --limit passed as query parameter
query="${query:+$query&}limit=$2"
surf_get "${API_PREFIX}/${subcmd}" "$query"
```

**Pattern B: Client-side truncation** (when API has no limit param)
```bash
# Parse --limit separately, truncate JSON arrays in response
surf_get "${API_PREFIX}/${subcmd}" "$query" | python3 -c "
import json,sys
d=json.load(sys.stdin)
limit=int(sys.argv[1])
if isinstance(d,dict):
    for k,v in d.items():
        if isinstance(v,list) and len(v)>limit:
            d[k]=v[:limit]
json.dump(d,sys.stdout)
" "$_limit"
```

Which commands need `--limit`:
- Any endpoint returning a list (holders, transfers, transactions, futures positions, etc.)
- NOT needed for single-object lookups (price, user profile, balance summary)

### --check-setup

Every skill MUST have `--check-setup`. Data skills use the shared helper:

```bash
--check-setup) surf_check_setup ;;
```

This verifies `HERMOD_URL` and `HERMOD_TOKEN` are set and the session is valid.

## Compliance Checklist

Before merging any skill change, verify:

- [ ] `SKILL.md` frontmatter has `name`, `description`, `tools`
- [ ] `SKILL.md` "When to Use" bullets are specific enough for semantic matching
- [ ] `SKILL.md` examples show `--limit` for large-response commands
- [ ] `SKILL.md` cost section lists per-command credits
- [ ] CLI `usage()` is valid JSON with credit costs in descriptions
- [ ] CLI has `--check-setup` subcommand
- [ ] Unknown command error lists all available commands
- [ ] Unknown flag error lists valid flags for that subcommand
- [ ] Missing required flag error includes example value
- [ ] Commands returning lists support `--limit`
- [ ] All output is JSON (stdout for data, stderr for errors)
- [ ] `references/endpoints.md` exists for data skills

## Anti-Patterns

| Don't | Do | Why |
|-------|-----|-----|
| `"Unknown flag: $1"` | `"Unknown flag: $1. Valid: --address, --chain"` | Agent guesses random flags without guidance |
| Return 200KB JSON with no truncation | Support `--limit` | Agent context window fills up, loses track |
| `"Use --help for usage."` | List commands inline | Agent wastes a tool call on --help |
| Use `<ADDR>` placeholders in SKILL.md | Use real example values | Agent passes `<ADDR>` literally |
| Put all details in SKILL.md | Keep SKILL.md short, details in `references/` | SKILL.md is always loaded; references are read on demand |
| Different field names in session.json | Use both `hermod_token` and `access_token` | Different agents expect different field names |
