---
name: surf-wallet
description: Investigate wallets, track whale activity, analyze DeFi positions, and monitor smart money movements
tools: ["bash"]
---

# Wallet Data — Wallet Intelligence & Whale Tracking

Query wallet balances, token holdings, transaction history, transfers, PnL, labels, and NFTs. Identify whales, track smart money, and investigate on-chain activity. All data via Hermod API Gateway.

## Quick Reference

| Command | Description | Key Params | Cost |
|---------|-------------|------------|------|
| `balance` | Total USD balance across chains | `--address` | 1 |
| `tokens` | Token holdings with prices | `--address`, `--chain`, `--limit`, `--offset` | 1 |
| `transfers` | Recent token transfers | `--address`, `--chain`, `--limit` | 1 |
| `history` | Full transaction history | `--address`, `--chain`, `--limit` | 1 |
| `labels` | Wallet identity labels | `--address` | 1 |
| `labels-batch` | Batch label lookup | `--addresses` (JSON array) | 1 |
| `pnl` | Realized + unrealized PnL | `--address` | 1 |
| `nft` | NFT holdings | `--address`, `--chain`, `--limit` | 1 |
| `search` | Search wallets by name/ENS | `--query`, `--limit`, `--offset` | 1 |
| `top` | Ranked wallets by metric | `--metric`, `--limit` | 1 |

## Common Tasks

### Task: Investigate a Wallet

Full profile of any wallet — who it is, what it holds, and what it has been doing.

```bash
# Step 1: Check total balance
surf-wallet balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Step 2: Identify the wallet (exchange, fund, whale, protocol, etc.)
surf-wallet labels --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Step 3: See all token holdings
surf-wallet tokens --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Step 4: Recent transfers — what tokens are moving?
surf-wallet transfers --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth --limit 10

# Step 5: Check PnL performance
surf-wallet pnl --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
```

**What to look for:** Large stablecoin holdings suggest dry powder for buying. Recent transfers to exchanges may indicate upcoming sells. Labels reveal if the wallet belongs to a known entity (exchange hot wallet, fund, protocol treasury).

### Task: Whale Watching

Find and monitor the largest wallets by balance or PnL.

```bash
# Step 1: Top wallets by total balance
surf-wallet top --metric balance --limit 10

# Step 2: Top wallets by PnL (most profitable traders)
surf-wallet top --metric pnl --limit 10

# Step 3: Hyperliquid whale positions
surf-wallet top --metric hyperliquid_whales --limit 10

# Step 4: Investigate a specific whale from the results
surf-wallet tokens --address <whale_address>
surf-wallet transfers --address <whale_address> --chain eth --limit 10
```

**What to look for:** Compare top-balance vs top-PnL lists — wallets on both are consistently successful. Track what top PnL wallets are currently holding for alpha. Hyperliquid whales show leveraged positioning sentiment.

### Task: Smart Money Tracking

Identify what profitable wallets are buying and selling.

```bash
# Step 1: Find top PnL wallets (the "smart money")
surf-wallet top --metric pnl --limit 5

# Step 2: Check each wallet's current holdings
surf-wallet tokens --address <smart_money_address>

# Step 3: Check recent transfers for new positions
surf-wallet transfers --address <smart_money_address> --chain eth --limit 10

# Step 4: Label them to understand if they are funds, MEV bots, etc.
surf-wallet labels --address <smart_money_address>

# Step 5: Batch label multiple wallets at once
surf-wallet labels-batch --addresses '["0xaddr1...", "0xaddr2...", "0xaddr3..."]'
```

**What to look for:** Multiple smart money wallets accumulating the same token = strong signal. Check if holdings overlap with `surf-token top --metric exchange_outflow` (tokens leaving exchanges). Ignore wallets labeled as exchanges or MEV bots — focus on funds and individual whales.

### Task: DeFi Position Check

Analyze a wallet's DeFi exposure and portfolio composition.

```bash
# Step 1: Get all token holdings (includes DeFi positions across chains)
surf-wallet tokens --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Step 2: Filter to specific chain
surf-wallet tokens --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth

# Step 3: Check NFT holdings
surf-wallet nft --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth --limit 10

# Step 4: Total balance for portfolio overview
surf-wallet balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
```

**What to look for:** Tokens with `price_usd` and `value_usd` fields show valued positions. Tokens without prices may be LP tokens, receipt tokens, or airdrops. Compare chain distribution to understand multi-chain exposure. High stablecoin % = defensive positioning.

### Task: Whale Alert Analysis (Cross-Domain)

When a large transfer is detected, quickly assess the full picture.

```bash
# 1. Identify the wallet
surf-wallet labels --address <whale_address>
surf-wallet balance --address <whale_address>

# 2. See full transfer context
surf-wallet transfers --address <whale_address> --chain eth --limit 20

# 3. Check the token being moved
surf-token info --address <token_address> --chain eth
surf-token holders --address <token_address> --chain eth --limit 10

# 4. Check exchange flow for the token (is this part of a larger trend?)
surf-token metrics --asset <symbol> --metric exchange_flow --window hour --limit 24

# 5. Check recent market price action
surf-market price --ids <coingecko_id> --vs usd

# 6. Check for related news
surf-news search --query "<token_name>"
```

**What to look for:** Transfers TO exchanges = potential sell. Transfers FROM exchanges = accumulation. Large transfers between unknown wallets may be OTC deals. Compare transfer size to daily volume for market impact estimate.

## Cross-Domain Workflows

- **Wallet + Token**: Use `tokens` to see holdings, then `surf-token info` for metadata on interesting positions. Use `surf-token holders` to see if this wallet is a top holder of any token.
- **Wallet + Market**: Combine `balance` (portfolio value) with `surf-market price` for individual position sizing. Use `surf-market chart` to see if the wallet timed entries well.
- **Wallet + Social**: Cross-reference wallet labels with `surf-social search` to find the wallet owner's social activity and sentiment.
- **Wallet + Onchain**: For deep transaction analysis, use `surf-onchain` SQL queries to trace specific transaction patterns that `transfers` and `history` cannot capture.

## Valid Parameter Values

| Parameter | Valid Values |
|-----------|-------------|
| `--chain` (tokens, history) | `eth`, `bsc`, `matic`, `avax`, `ftm`, `arb`, `op` |
| `--chain` (nft) | `eth`, `bsc`, `polygon`, `avalanche`, `fantom`, `arbitrum`, `optimism` |
| `--chain` (transfers) | `eth`, `solana` |
| `--metric` (top) | `balance`, `pnl`, `hyperliquid_whales` |

## Tips

- Addresses must be hex format (`0x...`). ENS names are not resolved — use `search` to find addresses.
- `balance` returns total USD value across all chains. Use `tokens` for per-asset breakdown.
- `tokens` returns holdings across all chains by default. Use `--chain` to filter to one chain.
- `labels-batch` accepts a JSON array: `--addresses '["0xaddr1", "0xaddr2"]'` — use this to identify multiple wallets efficiently in a single call.
- `top --metric hyperliquid_whales` shows leveraged positions on Hyperliquid DEX — useful for gauging whale sentiment on perpetual markets.
- `transfers` shows token transfers (ERC-20). For full transaction history including contract interactions, use `history`.
- Use `--limit` on all list commands to control response size and save context window space.
- All output is JSON. Data to stdout, errors to stderr.
