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
- Get wallet net worth across all chains
- Analyze wallet profitability (P&L, realized profit, trade volume)
- View wallet activity stats (NFTs, transactions, transfers)
- Track wallet DEX swap history
- Get wallet DeFi positions summary
- Resolve ENS domain to address and reverse lookup
- Query Solana wallet details, token holdings, transactions, and DeFi activities
- Track Solana wallet balance changes over time

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

# Etherscan contract ABI (proxy, 4 credits)
surf-wallet-data/scripts/surf-wallet etherscan-abi --address 0xdac17f958d2ee523a2206206994597c13d831ec7

# Etherscan contract source code (proxy, 4 credits)
surf-wallet-data/scripts/surf-wallet etherscan-sourcecode --address 0xdac17f958d2ee523a2206206994597c13d831ec7

# Etherscan contract creation info (proxy, 4 credits)
surf-wallet-data/scripts/surf-wallet etherscan-contract-creation --address 0xdac17f958d2ee523a2206206994597c13d831ec7

# Moralis wallet net worth across all chains (proxy, 2 credits)
surf-wallet-data/scripts/surf-wallet moralis-net-worth --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Moralis wallet P&L summary (proxy, 2 credits)
surf-wallet-data/scripts/surf-wallet moralis-profitability --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth

# Moralis wallet stats — NFTs, collections, txs (proxy, 2 credits)
surf-wallet-data/scripts/surf-wallet moralis-stats --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth

# Moralis wallet DEX swaps (proxy, 2 credits — supports --limit)
surf-wallet-data/scripts/surf-wallet moralis-swaps --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth --limit 10

# Moralis wallet DeFi positions summary (proxy, 2 credits)
surf-wallet-data/scripts/surf-wallet moralis-defi --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth

# Moralis ENS domain to address (proxy, 2 credits)
surf-wallet-data/scripts/surf-wallet moralis-ens --domain vitalik.eth

# Moralis address to ENS reverse lookup (proxy, 2 credits)
surf-wallet-data/scripts/surf-wallet moralis-ens-reverse --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Solscan account detail (proxy, 4 credits — Solana addresses)
surf-wallet-data/scripts/surf-wallet sol-account --address vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg

# Solscan account SPL token holdings (proxy, 4 credits — page_size: 10/20/30/40)
surf-wallet-data/scripts/surf-wallet sol-account-tokens --address vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg --page 1 --page-size 10

# Solscan account transactions (proxy, 4 credits — limit: 10/20/30/40/60/100)
surf-wallet-data/scripts/surf-wallet sol-account-txs --address vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg --limit 10

# Solscan account token transfers (proxy, 4 credits — page_size: 10/20/30/40/60/100)
surf-wallet-data/scripts/surf-wallet sol-account-transfers --address vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg --page 1 --page-size 10

# Solscan account DeFi activities (proxy, 4 credits)
surf-wallet-data/scripts/surf-wallet sol-account-defi --address vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg --page 1 --page-size 10

# Solscan account balance changes (proxy, 4 credits)
surf-wallet-data/scripts/surf-wallet sol-balance-change --address vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg --page 1 --page-size 10
```

## Important Notes

- **Semantic vs proxy**: Semantic endpoints (balance, label, etc.) cost 1 credit. Proxy endpoints (debank-*, etherscan-*, sol-*) cost 4-5 credits.
- **Use semantic endpoints first** — they're cheaper and often sufficient.
- **Etherscan chainid**: Default is `1` (Ethereum mainnet). Other chains: `56` (BSC), `137` (Polygon), `42161` (Arbitrum).
- **debank-history** supports `--chain` filter and `--limit` to control result count.
- **etherscan-abi** returns the ABI JSON as a string in the `result` field — useful for contract interaction.
- **Solana wallets**: Use `sol-*` commands with Solana address. Solscan page_size is fixed: 10/20/30/40 (some endpoints also allow 60/100).

### Moralis Chain Support

`--chain` accepts chain names (e.g. `eth`) or hex chain IDs (e.g. `0x1`). Invalid chains return `chain must be a valid enum value`.

| Command | Supported Chains |
|---------|-----------------|
| moralis-net-worth | Auto scans all EVM chains (no `--chain` needed) |
| moralis-profitability | eth, polygon, base (bsc/arbitrum not supported) |
| moralis-stats | eth, bsc, polygon, arbitrum, base |
| moralis-swaps | All EVM (eth, bsc, polygon, arbitrum, base, optimism, etc.) |
| moralis-defi | eth, bsc, polygon, arbitrum, base (optimism not supported) |
| moralis-ens/ens-reverse | Ethereum only (no `--chain` param) |

### Moralis Pagination

`moralis-swaps` uses **cursor-based pagination**. Responses include a `cursor` field — pass it via `--cursor` for the next page:
```bash
# Page 1
surf-wallet-data/scripts/surf-wallet moralis-swaps --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth --limit 10
# Page 2 (use cursor from previous response)
surf-wallet-data/scripts/surf-wallet moralis-swaps --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth --limit 10 --cursor eyJhbGci...
```

## Cost

- Semantic endpoints (balance, token-list, transfer, etc.): 1 credit
- Moralis proxy (moralis-*): 2 credits
- DeBank proxy (debank-*): 5 credits
- Etherscan proxy (etherscan-*): 4 credits
- Solscan proxy (sol-*): 4 credits

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
