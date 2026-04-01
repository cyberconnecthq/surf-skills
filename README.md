# surf-skills — Agent Skill & Tools for Surf Data API

Agent skill and code generation tools for the Surf crypto data platform.

## Prerequisites

Install the Surf CLI:

```bash
curl -fsSL https://agent.asksurf.ai/cli/releases/install.sh | sh
surf login
```

## For Agents

The agent skill is at `skills/surf/SKILL.md`. It teaches AI agents how to use `surf` for crypto research, wallet investigation, and building pages with live data. Includes recipes for common workflows and a full command index.

## Code Generation

`scripts/gen_client.py` generates typed TypeScript or Python API clients from the Surf CLI's schema output. See `skills/surf/SKILL.md` § Code Generation for details.

## Adding New Endpoints

No changes needed in surf-skills. When hermod adds a new API endpoint:

1. The OpenAPI spec updates automatically
2. `surf list-operations` shows the new command
3. `surf <new-command> --help` shows its parameters
