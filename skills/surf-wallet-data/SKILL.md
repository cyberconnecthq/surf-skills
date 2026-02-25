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
- Check wallet balance and token holdings
- View transfer and transaction history for an address
- Look up address labels (exchange, whale, smart money, etc.)
- Search for entities by name
- Batch query labels for multiple addresses

## CLI Usage

```bash
# Check setup
skills/surf-wallet-data/scripts/surf-wallet --check-setup

# Get wallet balance (DeBank)
skills/surf-wallet-data/scripts/surf-wallet balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# List token holdings (DeBank)
skills/surf-wallet-data/scripts/surf-wallet token-list --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Get transfer history (Etherscan — supports chain & pagination)
skills/surf-wallet-data/scripts/surf-wallet transfer --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth

# Get trading history (DeBank)
skills/surf-wallet-data/scripts/surf-wallet trading-history --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Get transaction history (Etherscan)
skills/surf-wallet-data/scripts/surf-wallet transaction-history --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth

# Look up address label (Recon)
skills/surf-wallet-data/scripts/surf-wallet label --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Batch label lookup (Recon)
skills/surf-wallet-data/scripts/surf-wallet label-batch --addresses '["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045","0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503"]'

# Search entity by name (Recon — GET request)
skills/surf-wallet-data/scripts/surf-wallet entity-search --query "binance"
```

## Cost

1-2 credits per request.

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
