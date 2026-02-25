---
name: surf-token-data
description: Query token data including holders, transfers, exchange flows, and reserves
tools: ["bash"]
---

# Token Data — Token-level Analytics

Access token-level data including holder distribution, transfers, exchange inflow/outflow, ETF flows, and exchange reserves via the Hermod API Gateway.

Hermod routes token endpoints to different upstreams:
- **holder / transfer** → Moralis/Etherscan (use `--token` address + `--chain`)
- **exchange-flow / exchange-reserve** → CryptoQuant (use `--asset` symbol)
- **etf-flow** → SoSoValue (use `--type`)

## When to Use

Use this skill when you need to:
- Analyze token holder distribution (by contract address)
- Track token transfers
- Monitor exchange inflow/outflow patterns
- Check ETF flow data
- View exchange reserve levels

## CLI Usage

```bash
# Check setup
surf-token-data/scripts/surf-token --check-setup

# Get holder data (Moralis — use token contract address + chain)
surf-token-data/scripts/surf-token holder --token 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth --limit 5

# Get transfer data (Etherscan — use token contract address + chain)
surf-token-data/scripts/surf-token transfer --token 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth --page 1 --offset 5

# Get exchange flow data (CryptoQuant — use asset symbol)
surf-token-data/scripts/surf-token exchange-flow --asset btc --flow-type netflow --exchange all_exchange --window day --limit 3

# Get ETF flow data (SoSoValue — use type)
surf-token-data/scripts/surf-token etf-flow --type us-btc-spot

# Get exchange reserve data (CryptoQuant)
surf-token-data/scripts/surf-token exchange-reserve --asset btc --exchange all_exchange --window day --limit 3
```

## Cost

1 credit per request.

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
