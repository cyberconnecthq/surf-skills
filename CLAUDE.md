# CLAUDE.md -- surf-skills

Agent skill and code generation tools for the Surf data API.

## Directory Structure

```
surf-skills/
├── skills/
│   ├── surf/
│   │   └── SKILL.md           # Agent skill: research, investigate, fetch crypto data via CLI
│   └── surf-app/
│       └── SKILL.md           # Agent skill: scaffold and build crypto data web apps
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
- **`skills/surf-app/SKILL.md`** -- Agent-discoverable skill for building crypto data web apps. Guides agents to scaffold projects with `npx create-surf-app` and use the `@surf-ai/sdk` for data hooks and server-side API access.

## Adding New Endpoints

No surf-skills changes needed. Add the endpoint in hermod — the surf CLI discovers it automatically from the updated OpenAPI spec. `surf list-operations` will show the new command. Update `skills/surf/SKILL.md` if the new endpoint belongs to a new domain or changes existing recipes.
