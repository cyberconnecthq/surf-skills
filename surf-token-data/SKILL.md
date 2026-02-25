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
- Analyze token holder distribution by contract address
- Track token transfer activity
- Monitor exchange inflow/outflow patterns (netflow, inflow, outflow)
- Check BTC/ETH ETF flow data
- View exchange reserve levels for an asset
- Get Solana SPL token holders, transfers, or prices

## CLI Usage

```bash
# Check setup
surf-token-data/scripts/surf-token --check-setup

# Get holder data (Moralis — use token contract address + chain, --limit controls count)
surf-token-data/scripts/surf-token holder --token 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth --limit 5

# Get transfer data (Etherscan — use token contract address + chain)
surf-token-data/scripts/surf-token transfer --token 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth --page 1 --offset 5

# Get exchange flow data (CryptoQuant — use asset symbol, --limit controls data points)
surf-token-data/scripts/surf-token exchange-flow --asset btc --flow-type netflow --exchange all_exchange --window day --limit 3

# Get ETF flow data (SoSoValue — types: us-btc-spot, us-eth-spot)
surf-token-data/scripts/surf-token etf-flow --type us-btc-spot

# Get exchange reserve data (CryptoQuant — --limit controls data points)
surf-token-data/scripts/surf-token exchange-reserve --asset btc --exchange all_exchange --window day --limit 3

# Moralis top holders (proxy, 2 credits)
surf-token-data/scripts/surf-token moralis-holders --token 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth

# Moralis token metadata (proxy, 2 credits)
surf-token-data/scripts/surf-token moralis-meta --token 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth

# Moralis token transfers (proxy, 2 credits — supports --limit)
surf-token-data/scripts/surf-token moralis-transfers --token 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth --limit 50

# Solscan token holders (proxy, 4 credits — Solana SPL tokens)
surf-token-data/scripts/surf-token sol-holders --token EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v --page 1

# Solscan token price (proxy, 4 credits)
surf-token-data/scripts/surf-token sol-price --token EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

# DeBank top token holders with USD values (proxy, 5 credits)
surf-token-data/scripts/surf-token debank-top-holders --token 0xdac17f958d2ee523a2206206994597c13d831ec7 --chain eth --limit 10
```

## Important Notes

- **Use `--limit` on exchange-flow and exchange-reserve** — these return time series data that can be large.
- **flow-type values**: `netflow`, `inflow`, `outflow` for exchange-flow command.
- **ETF types**: `us-btc-spot`, `us-eth-spot`
- **Solana tokens**: Use `sol-*` commands with SPL mint address instead of `holder`/`transfer`.
- **debank-top-holders**: Returns top holders with USD values, useful for whale analysis. `--chain` uses DeBank chain IDs (eth, bsc, matic, etc.).

## Cost

- Semantic endpoints (holder, transfer, exchange-flow, etc.): 1 credit
- Moralis proxy (moralis-*): 2 credits
- Solscan proxy (sol-*): 4 credits
- DeBank proxy (debank-*): 5 credits

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
