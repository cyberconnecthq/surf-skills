---
name: surf-project-data
description: Query crypto project data including overview, TVL, revenue, fees, and user metrics
tools: ["bash"]
---

# Project Data — Crypto Project Analytics

Access comprehensive project-level data including overview, token info, funding, team, contracts, social links, volume, fees, revenue, TVL, and user metrics via the Hermod API Gateway.

Hermod routes project endpoints to two upstreams:
- **overview / token-info / funding / team / social / contract-address** → Muninn (use `--query`)
- **volume / fee / revenue / tvl / users** → Token Terminal (use `--project-id`)

## When to Use

Use this skill when you need to:
- Get project overview and metadata
- Check token information for a project
- Look up funding rounds and investors
- Find team members
- Get contract addresses across chains
- View social media links
- Analyze volume, fees, revenue, TVL, and user metrics

## CLI Usage

```bash
# Check setup
skills/surf-project-data/scripts/surf-project --check-setup

# Get project overview (Muninn — use --query)
skills/surf-project-data/scripts/surf-project overview --query aave

# Get token info (Muninn)
skills/surf-project-data/scripts/surf-project token-info --query uniswap

# Get funding data (Muninn)
skills/surf-project-data/scripts/surf-project funding --query aave

# Get team info (Muninn)
skills/surf-project-data/scripts/surf-project team --query aave

# Get contract addresses (Muninn)
skills/surf-project-data/scripts/surf-project contract-address --query aave

# Get social links (Muninn)
skills/surf-project-data/scripts/surf-project social --query aave

# Get volume data (Token Terminal — use --project-id)
skills/surf-project-data/scripts/surf-project volume --project-id uniswap

# Get fee data (Token Terminal)
skills/surf-project-data/scripts/surf-project fee --project-id uniswap

# Get revenue data (Token Terminal)
skills/surf-project-data/scripts/surf-project revenue --project-id lido

# Get TVL data (Token Terminal)
skills/surf-project-data/scripts/surf-project tvl --project-id aave

# Get user metrics (Token Terminal)
skills/surf-project-data/scripts/surf-project users --project-id opensea
```

## Cost

1 credit per request.

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
