---
name: surf-trading-data
description: Query crypto trading data including prices, futures, options, liquidations, and market indicators
tools: ["bash"]
---

# Trading Data (CLI Runtime)

## CLI Usage

```bash
surf-trading-data/scripts/surf-trading --check-setup
surf-trading-data/scripts/surf-trading price --ids bitcoin --vs usd
surf-trading-data/scripts/surf-trading future --symbol BTC --limit 5
surf-trading-data/scripts/surf-trading indicator --name rsi --symbol BTC/USDT --interval 1d --exchange binance
# ... see full command list via --help
```

## Cost

- Semantic endpoints: 1 credit
- CoinGlass proxy: 3 credits
- CoinGecko proxy: 2 credits

## Knowledge

<!-- TODO: after hermod refactor, reference knowledge/ layer directly -->
See `knowledge/trading-data/` for:
- `endpoints.md` — full endpoint & parameter reference
- `responses.md` — verified response JSON & field docs
- `patterns.md` — defensive coding, gotchas, usage patterns
