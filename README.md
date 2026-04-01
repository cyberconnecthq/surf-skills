# surf-skills — Agent Skills for the Surf Data API

Agent-discoverable skills and code generation tools for the Surf crypto data platform.

## Skills

| Skill | Path | Purpose |
|-------|------|---------|
| **surf** | `skills/surf/SKILL.md` | Research, investigate, and fetch crypto data via the `surf` CLI |
| **surf-app** | `skills/surf-app/SKILL.md` | Scaffold and build full-stack crypto data web apps |

## Prerequisites

Install the Surf CLI:

```bash
curl -fsSL https://agent.asksurf.ai/cli/releases/install.sh | sh
surf login
```

## Adding New Endpoints

No changes needed in surf-skills. When hermod adds a new API endpoint:

1. The OpenAPI spec updates automatically
2. `surf list-operations` shows the new command
3. `surf <new-command> --help` shows its parameters
