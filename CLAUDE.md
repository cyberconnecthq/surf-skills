# CLAUDE.md -- surf-core

Agent skill and code generation tools for the Surf data API.

## Directory Structure

```
surf-core/
├── skills/
│   └── surf/
│       ├── SKILL.md           # Agent skill: research, investigate, build with crypto data
│       └── scripts/
│           └── gen_client.py  # Typed client code generator (TypeScript / Python)
├── CLAUDE.md
└── README.md
```

## Prerequisites

Install the Surf CLI:

```bash
curl -fsSL https://agent.asksurf.ai/cli/releases/install.sh | sh
surf login
surf list-operations           # verify: lists all available commands
```

## Key Files

- **`skills/surf/SKILL.md`** -- Agent-discoverable skill for all surf CLI commands. Contains recipes for common research tasks, parameter conventions, command index, and credit costs.
- **`skills/surf/scripts/gen_client.py`** -- Generates typed TypeScript or Python API clients from `surf <op> --help` output.

## Adding New Endpoints

No surf-core changes needed. Add the endpoint in hermod — the surf CLI discovers it automatically from the updated OpenAPI spec. `surf list-operations` will show the new command. Update `skills/surf/SKILL.md` if the new endpoint belongs to a new domain or changes existing recipes.
