---
name: surf-wallet-data
description: Query wallet data including balances, holdings, transaction history, and address labels
tools: ["bash"]
---

# Wallet Data — On-chain Wallet Analysis

Access wallet-level data including balances, token holdings, transfers, trading history, portfolio curves, and address labels via the Hermod API Gateway.

## When to Use

Use this skill when you need to:
- Check wallet balance and token holdings for an address
- View transfer and transaction history for an address
- Look up address labels (exchange, whale, smart money, etc.)
- Track portfolio value over time for a wallet
- Get cross-chain DeFi positions for a wallet
- Check current gas prices

## CLI Usage

```bash
# Check setup
surf-wallet-data/scripts/surf-wallet --check-setup

# Get wallet balance (semantic, 1 credit)
surf-wallet-data/scripts/surf-wallet balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# List token holdings (semantic, 1 credit)
surf-wallet-data/scripts/surf-wallet token-list --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Get transfer history (semantic, 1 credit — supports --chain, --limit)
surf-wallet-data/scripts/surf-wallet transfer --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth

# Look up address label and entity (semantic, 1 credit)
surf-wallet-data/scripts/surf-wallet label --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# DeBank cross-chain balance (proxy, 5 credits)
surf-wallet-data/scripts/surf-wallet debank-balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# DeBank DeFi positions (proxy, 5 credits)
surf-wallet-data/scripts/surf-wallet debank-defi --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# DeBank full transaction history (proxy, 5 credits — supports --chain, --limit)
surf-wallet-data/scripts/surf-wallet debank-history --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --limit 10

# DeBank portfolio value over time (proxy, 5 credits)
surf-wallet-data/scripts/surf-wallet debank-net-curve --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Etherscan tx history (proxy, 4 credits — supports --chainid)
surf-wallet-data/scripts/surf-wallet etherscan-txs --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chainid 1

# Etherscan gas prices (proxy, 4 credits)
surf-wallet-data/scripts/surf-wallet etherscan-gas
```

## Important Notes

- **Semantic vs proxy**: Semantic endpoints (balance, label, etc.) cost 1 credit. Proxy endpoints (debank-*, etherscan-*) cost 4-5 credits.
- **Use semantic endpoints first** — they're cheaper and often sufficient.
- **Etherscan chainid**: Default is `1` (Ethereum mainnet). Other chains: `56` (BSC), `137` (Polygon), `42161` (Arbitrum).
- **debank-history** supports `--chain` filter and `--limit` to control result count.

## Cost

- Semantic endpoints (balance, token-list, transfer, etc.): 1 credit
- DeBank proxy (debank-*): 5 credits
- Etherscan proxy (etherscan-*): 4 credits

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
