---
name: surf-market-data
description: Query crypto market data including prices, futures, options, liquidations, and market indicators
tools: ["bash"]
---

# Market Data (CLI Runtime)

## CLI Usage

```bash
surf-market-data/scripts/surf-market --check-setup
surf-market-data/scripts/surf-market price --ids bitcoin --vs usd
surf-market-data/scripts/surf-market futures --symbol BTC --limit 5
surf-market-data/scripts/surf-market indicator --name rsi --symbol BTC/USDT --interval 1d --exchange binance
# ... see full command list via --help
```

## Cost

- Standard endpoints: 1 credit

## Knowledge

<!-- TODO: CLI script (scripts/surf-market) will be updated when hermod market endpoints are finalized -->
See `knowledge/market/` for:
- `endpoints.md` — full endpoint & parameter reference
- `responses.md` — unified response envelope & field docs
- `patterns.md` — defensive coding, gotchas, usage patterns
