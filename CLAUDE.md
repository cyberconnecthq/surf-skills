# CLAUDE.md -- surf-core

Agent skill for the Surf data CLI. Teaches AI agents how to use `surf` for crypto research, wallet investigation, market analysis, and building pages with live data.

## Directory Structure

```
surf-core/
├── skills/
│   └── surf/
│       └── SKILL.md           # Agent skill: research, investigate, build with crypto data
├── CLAUDE.md
└── README.md
```

## Getting Started

```bash
curl -fsSL https://agent.asksurf.ai/cli/releases/install.sh | sh
surf login
surf list-operations           # verify: lists all 66 commands
```

## Key Files

- **`skills/surf/SKILL.md`** -- Agent-discoverable skill for all surf CLI commands. Contains recipes for common research tasks, parameter conventions, command index, and credit costs.

## Adding New Endpoints

No surf-core changes needed. Add the endpoint in hermod -- restish discovers it automatically from the updated OpenAPI spec. `surf list-operations` will show the new command. Update `skills/surf/SKILL.md` if the new endpoint belongs to a new domain or changes existing recipes.
