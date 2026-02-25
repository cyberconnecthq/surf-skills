---
name: surf-wallet-data
description: Query wallet data including balances, holdings, transaction history, and address labels
tools: ["bash"]
---

# Wallet Data — On-chain Wallet Analysis

Access wallet-level data including balances, token holdings, transfers, trading history, and address labels via the Hermod API Gateway.

Hermod routes wallet endpoints to different upstreams:
- **balance / token-list / trading-history** → DeBank
- **transfer / transaction-history** → Etherscan
- **label / label-batch / entity-search** → Recon

## When to Use

Use this skill when you need to:
- Check wallet balance and token holdings for an address
- View transfer and transaction history for an address
- Look up address labels (exchange, whale, smart money, etc.)
- Search for entities by name (e.g. "binance", "jump trading")
- Batch query labels for multiple addresses
- Get cross-chain DeFi positions for a wallet

## CLI Usage

```bash
# Check setup
surf-wallet-data/scripts/surf-wallet --check-setup

# Get wallet balance (DeBank — supports --limit)
surf-wallet-data/scripts/surf-wallet balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# List token holdings (DeBank — supports --limit)
surf-wallet-data/scripts/surf-wallet token-list --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Get transfer history (Etherscan — supports --chain, --limit)
surf-wallet-data/scripts/surf-wallet transfer --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth

# Get trading history (DeBank)
surf-wallet-data/scripts/surf-wallet trading-history --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Get transaction history (Etherscan — supports --chain, --limit)
surf-wallet-data/scripts/surf-wallet transaction-history --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth

# Look up address label (Recon)
surf-wallet-data/scripts/surf-wallet label --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Batch label lookup (Recon)
surf-wallet-data/scripts/surf-wallet label-batch --addresses '["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045","0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503"]'

# Search entity by name (Recon)
surf-wallet-data/scripts/surf-wallet entity-search --query "binance"

# DeBank cross-chain balance (proxy, 5 credits)
surf-wallet-data/scripts/surf-wallet debank-balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# DeBank DeFi positions (proxy, 5 credits)
surf-wallet-data/scripts/surf-wallet debank-defi --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Etherscan tx history (proxy, 4 credits — supports --chainid)
surf-wallet-data/scripts/surf-wallet etherscan-txs --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chainid 1
```

## Important Notes

- **Semantic vs proxy**: Semantic endpoints (balance, label, etc.) cost 1-2 credits. Proxy endpoints (debank-*, etherscan-*, recon-*) cost 1-5 credits.
- **Use semantic endpoints first** — they're cheaper and often sufficient.
- **Etherscan chainid**: Default is `1` (Ethereum mainnet). Other chains: `56` (BSC), `137` (Polygon), `42161` (Arbitrum).

## Cost

- Semantic endpoints (balance, token-list, transfer, etc.): 1-2 credits
- DeBank proxy (debank-*): 5 credits
- Etherscan proxy (etherscan-*): 4 credits
- Recon proxy (recon-*): 1 credit

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
