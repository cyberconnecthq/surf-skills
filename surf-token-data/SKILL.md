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
- Search tokens by name/symbol, find trending tokens, top gainers/losers
- Get token price with DEX liquidity data
- Discover blue-chip tokens with strong on-chain fundamentals
- Get DEX pair stats (price, liquidity, volume, trades)
- View global crypto market cap rankings
- Get Solana SPL token holders, transfers, or prices
- Look up Solana token metadata (name, symbol, supply, market cap)
- Find trending tokens on Solana
- Discover DEX trading pairs/pools for Solana tokens

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

# Moralis token price with DEX data (proxy, 2 credits)
surf-token-data/scripts/surf-token moralis-price --token 0xdac17f958d2ee523a2206206994597c13d831ec7 --chain eth

# Moralis search tokens by name/symbol (proxy, 2 credits)
surf-token-data/scripts/surf-token moralis-search --query pepe --chain eth --limit 5

# Moralis trending tokens (proxy, 2 credits)
surf-token-data/scripts/surf-token moralis-trending --chain eth --limit 10

# Moralis top gaining tokens on-chain (proxy, 2 credits)
surf-token-data/scripts/surf-token moralis-top-gainers --chain eth

# Moralis top losing tokens on-chain (proxy, 2 credits)
surf-token-data/scripts/surf-token moralis-top-losers --chain eth

# Moralis blue-chip tokens with strong fundamentals (proxy, 2 credits)
surf-token-data/scripts/surf-token moralis-blue-chip --chain eth

# Moralis DEX pair stats — price, liquidity, volume (proxy, 2 credits)
surf-token-data/scripts/surf-token moralis-pair-stats --pair 0x11b815efB8f581194ae79006d24E0d814B7697F6 --chain eth

# Moralis global crypto market cap rankings (proxy, 2 credits)
surf-token-data/scripts/surf-token moralis-global-market-cap

# Solscan token holders (proxy, 4 credits — Solana SPL tokens, page_size: 10/20/30/40)
surf-token-data/scripts/surf-token sol-holders --token EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v --page 1 --page-size 10

# Solscan token transfers (proxy, 4 credits — page_size: 10/20/30/40/60/100)
surf-token-data/scripts/surf-token sol-transfers --token EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v --page 1 --page-size 10

# Solscan token price history (proxy, 4 credits)
surf-token-data/scripts/surf-token sol-price --token EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

# Solscan token metadata — name, symbol, supply, market cap, price (proxy, 4 credits)
surf-token-data/scripts/surf-token sol-meta --token EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

# Solscan trending tokens on Solana (proxy, 4 credits — limit: 10/20/30/40/60/100)
surf-token-data/scripts/surf-token sol-trending --limit 10

# Solscan DEX trading pairs/pools for a token (proxy, 4 credits — page_size: 10/20/30/40)
surf-token-data/scripts/surf-token sol-markets --token So11111111111111111111111111111111111111112 --page 1 --page-size 10

# DeBank top token holders with USD values (proxy, 5 credits)
surf-token-data/scripts/surf-token debank-top-holders --token 0xdac17f958d2ee523a2206206994597c13d831ec7 --chain eth --limit 10
```

## Important Notes

- **Use `--limit` on exchange-flow and exchange-reserve** — these return time series data that can be large.
- **flow-type values**: `netflow`, `inflow`, `outflow` for exchange-flow command.
- **ETF types**: `us-btc-spot`, `us-eth-spot`
- **Solana tokens**: Use `sol-*` commands with SPL mint address instead of `holder`/`transfer`.
- **Solscan page_size**: Fixed values only — `sol-holders`: 10/20/30/40; `sol-transfers`/`sol-trending`: 10/20/30/40/60/100.
- **debank-top-holders**: Returns top holders with USD values, useful for whale analysis. `--chain` uses DeBank chain IDs (eth, bsc, matic, etc.).

### Moralis Chain Support

`--chain` accepts chain names (e.g. `eth`) or hex chain IDs (e.g. `0x1`). Invalid chains return `chain must be a valid enum value`.

| Command | Supported Chains |
|---------|-----------------|
| moralis-price | eth, bsc, polygon, arbitrum, base, avalanche, optimism, linea, fantom, cronos |
| moralis-search | All EVM + solana |
| moralis-trending | All EVM + solana (eth, bsc, polygon, arbitrum, base, avalanche, optimism, linea, fantom, cronos, moonbeam, moonriver, gnosis, flow, solana) |
| moralis-top-gainers/losers | eth, bsc, polygon, arbitrum, base |
| moralis-blue-chip | eth, bsc |
| moralis-pair-stats | All EVM |
| moralis-global-market-cap | No chain param (global) |

### Moralis Pagination

Moralis uses **cursor-based pagination**. Responses with more data include a `cursor` field — pass it via `--cursor` to get the next page. Example:
```bash
# Page 1
surf-token-data/scripts/surf-token moralis-search --query pepe --limit 5
# Page 2 (use cursor from previous response)
surf-token-data/scripts/surf-token moralis-search --query pepe --limit 5 --cursor eyJhbGci...
```

## Cost

- Semantic endpoints (holder, transfer, exchange-flow, etc.): 1 credit
- Moralis proxy (moralis-*): 2 credits
- Solscan proxy (sol-*): 4 credits
- DeBank proxy (debank-*): 5 credits

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
