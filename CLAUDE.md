# CLAUDE.md -- surf-skills

Agent skill and code generation tools for the Surf data API.

## Directory Structure

```
surf-skills/
├── skills/
│   └── surf/
│       └── SKILL.md           # Agent skill: research, investigate, fetch crypto data via CLI
├── CLAUDE.md
└── README.md
```

## Prerequisites

Install the Surf CLI:

```bash
curl -fsSL https://downloads.asksurf.ai/cli/releases/install.sh | sh
export SURF_API_KEY=<your-api-key>
surf list-operations           # verify: lists all available commands
```

## Key Files

- **`skills/surf/SKILL.md`** -- Agent-discoverable skill for all surf CLI commands. Contains recipes for common research tasks, parameter conventions, command index, and credit costs.

## Adding New Endpoints

No surf-skills changes needed. Add the endpoint in hermod — the surf CLI discovers it automatically from the updated OpenAPI spec. `surf list-operations` will show the new command. Update `skills/surf/SKILL.md` if the new endpoint belongs to a new domain or changes existing recipes.
