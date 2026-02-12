---
name: surf-dev-golang
description: Go development guide for Surf platform (muninn, argus repos). Use when working with Go code in these repos, including architecture decisions, code conventions, Ent ORM, CI/CD, testing. Also use when the user gives feedback or corrections about coding style - update the repo's CLAUDE.md to persist learnings.
---

<!-- Repository: https://github.com/cyberconnecthq/surf-skills -->

# Surf Go Development

Follow these guidelines when developing Go code for Surf platform backend services (muninn, argus).

## Quick Reference

### Build & Run

```bash
# muninn - REST API service
go build -o muninn main.go
./muninn                          # Default mode from config
exec.mode=api ./muninn            # API only
exec.mode=task ./muninn           # Background tasks only
exec.mode=dev ./muninn            # Both (local dev)

# argus - gRPC/data processing service
go build -o argus main.go
exec.mode=api go run main.go      # gRPC server
exec.mode=task go run main.go     # Kinesis consumers
exec.mode=cron go run main.go     # Scheduled jobs
exec.mode=dev go run main.go      # API + Task
```

### Code Generation

```bash
# Ent ORM (after modifying ent/schema/*.go)
cd ent && go generate

# Swagger docs (muninn only)
go generate ./...

# Proto updates
go get github.com/cyberconnecthq/proto@main

# Format & lint
pre-commit run --all-files
```

### Testing

```bash
go test ./...
go test -v ./internal/service -run TestSpecificTest
```

## Core Principles

1. **English only** in code and comments
2. **Read/Write separation**: Use `EntROClient` for reads, `EntWriteClient` for writes
3. **Ent is code-first**: Never manually create migrations, only modify `ent/schema/*.go`
4. **Worker pools**: Use `utils.ParallelExec()`, never raw goroutines with WaitGroup
5. **Error handling**: Always check `if ent.MaskNotFound(err) != nil`

## Reference Files

When encountering specific tasks, read the appropriate reference file:

| Task | Reference |
|------|-----------|
| Understanding multi-mode architecture, read/write split | [architecture.md](references/architecture.md) |
| Code style, naming, error handling, comments | [conventions.md](references/conventions.md) |
| Database schema changes, queries, indexes | [ent-orm.md](references/ent-orm.md) |
| Deployment, GitHub Actions, GitOps | [ci-cd.md](references/ci-cd.md) |

## Self-Learning Protocol

On user feedback or corrections about coding style, architecture decisions, or best practices:

1. Apply the feedback to the current task
2. Determine where to persist the learning:
   - General Go patterns → update `learnings.md` in this skill repo
   - Project-specific info → update that project's `CLAUDE.md`
3. Commit the update to the appropriate repository
4. Format learnings as: clear rule + rationale + code example if applicable

### Learning Categories

| Type | Destination | Example |
|------|-------------|---------|
| Go coding patterns | `learnings.md` | "Always use table-driven tests" |
| Ent ORM usage | `learnings.md` | "Use OnConflictColumns for upserts" |
| muninn API conventions | `muninn/CLAUDE.md` | "Use model.NewError for responses" |
| argus signal logic | `argus/CLAUDE.md` | "Dedup via Redis with 48h TTL" |

### Learning Format

```markdown
## [Category]

### [Brief Title]

**Rule**: [Clear statement of what to do/avoid]

**Rationale**: [Why this matters]

**Example**:
```go
// Correct approach
```
```

Always confirm with user before committing updates.
