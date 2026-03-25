---
name: surf
description: Research crypto markets, investigate wallets, analyze tokens, track prediction markets, and fetch live data for building pages — all via the `surf` CLI. Use when the user asks about crypto prices, projects, DeFi metrics, on-chain activity, social sentiment, news, Kalshi/Polymarket, or wants to build a site with crypto data.
tools:
  - bash
---

# Surf Data API

`surf` is a CLI for querying crypto data — markets, projects, tokens, wallets, on-chain data, social, news, prediction markets, and funds.

## Setup

```bash
curl -fsSL https://agent.asksurf.ai/cli/releases/install.sh | sh
surf login
```

## Using Surf

```bash
surf sync                  # Update local API schema (run if commands seem missing)
surf list-operations       # Discover all available commands with params
surf <command> --help      # Full params, enums, defaults for any command
```

Always run `surf list-operations` to discover available commands — don't assume a fixed set. Always check `--help` before calling a command — it shows every flag with its type, enum values, and defaults.

### Getting clean data

```bash
surf <command> --flags -o json -f body.data      # JSON array, ready to use in code
surf <command> --flags -o json -f body.data -r   # Raw strings, not escaped
```

Use `-o json -f body.data` whenever you need data for building pages or piping to other tools.

## Discovering Commands

Don't rely on a hardcoded list — commands are added frequently. Use discovery:

```bash
surf list-operations                    # All available commands
surf list-operations | grep wallet      # Find commands in a domain
surf sync                               # Refresh local schema if a command seems missing
```

Commands are grouped by domain prefix: `market-*`, `exchange-*`, `search-*`, `wallet-*`, `social-*`, `kalshi-*`, `polymarket-*`, `prediction-market-*`, `onchain-*`, `token-*`, `project-*`, `fund-*`, `news-*`, `web-*`.

## Troubleshooting

- **Auth errors**: Run `surf refresh` to renew an expired token, or `surf login` to re-authenticate
- **Unknown command**: Run `surf sync` to update schema, then `surf list-operations` to verify
- **Empty results**: Check `--help` for required params and valid enum values
- **Stale schema**: Run `surf sync` to pull the latest API spec

## Gotchas

Things `--help` won't tell you:

- **Never use `-q` for search.** `-q` is a global restish flag (`--rsh-query`), not the `--q` search parameter. Always use `--q` (double dash).
- **Chains require canonical long-form names.** `eth` → `ethereum`, `sol` → `solana`, `matic` → `polygon`, `avax` → `avalanche`, `arb` → `arbitrum`, `op` → `optimism`, `ftm` → `fantom`, `bnb` → `bsc`. Short forms fail with a validation error.
- **POST endpoints (`onchain-sql`, `onchain-structured-query`) take JSON on stdin.** Pipe JSON: `echo '{"sql":"SELECT ..."}' | surf onchain-sql`. Always filter on `block_date` — it's the partition key.
- **Ignore `--rsh-*` global flags in `--help` output.** Only the command-specific flags matter. The `--rsh-*` flags are restish internals.

## API Feedback

When a surf command fails, returns confusing results, or the API doesn't support something the user naturally expects, log a suggestion to `~/.surf/api-feedback/`. This helps the Surf team improve the API based on real usage.

```bash
mkdir -p ~/.surf/api-feedback
```

Write one file per issue: `~/.surf/api-feedback/<YYYY-MM-DD>-<slug>.md`

Use this template:

```markdown
# <Short title>

**Command tried:** `surf <command> --flags`
**What the user wanted:** <what they were trying to accomplish>
**What happened:** <error message, empty results, or confusing behavior>

## Suggested API fix

<How the API could change to make this work naturally — e.g., add a parameter,
accept an alias, improve the error message, return more useful defaults>
```

Examples of things worth logging:
- A parameter the user expected but doesn't exist
- Chain aliases that fail (`eth` instead of `ethereum`)
- Error messages that don't explain what went wrong
- Commands that feel like they should exist but don't
