# surf-core -- Surf Data CLI

CLI for querying crypto data — markets, projects, tokens, wallets, on-chain data, social, news, prediction markets, and funds. 66 commands across 11 domains, auto-generated from hermod's OpenAPI 3.1 spec.

## Quick Start

```bash
# Install
curl -fsSL https://agent.asksurf.ai/cli/releases/install.sh | sh

# Login
surf login

# Go
surf market-ranking --metric market_cap --limit 10
surf search-project --q uniswap
surf wallet-detail --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
```

## For Agents

The agent skill is at `skills/surf/SKILL.md`. It teaches AI agents how to use `surf` for crypto research, wallet investigation, and building pages with live data. Includes recipes for common workflows and a full command index.

## Adding New Endpoints

No changes needed in surf-core. When hermod adds a new API endpoint:

1. The OpenAPI spec updates automatically
2. `surf list-operations` shows the new command
3. `surf <new-command> --help` shows its parameters
