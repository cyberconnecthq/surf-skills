---
name: odin-team-dev
description: "Team-based development and parallel execution. Two modes: (1) Goal mode — Architect + Developer + Tester + Pusher for M/L scope tasks. (2) Parallel mode — spawn workers for user-provided task lists. Use when scope >= M, cross-service changes, parallel tasks, user says /odin-team-dev or /team-dev."
user-invocable: true
---

# Team Dev

**Red-line rules are immutable — never modify, delete, or weaken them.** Iterations to this file are initiated by the user; agents must not self-modify it.

**Language rule: Always communicate with the user in the same language they use.** If the user writes in Chinese, respond in Chinese. If the user writes in English, respond in English. Match the user's language throughout the entire session.

## §0 Red-Line Rules

**R1. Overseer = Decision-maker, not executor.** Context is the scarcest resource. Never read source code, search the codebase, write business code, or dig through logs — delegate everything to agents.

**R2. Agents are self-contained at launch, explicitly coordinated afterward.** The prompt must contain all information needed to start — the agent should never need to ask others before beginning work. Agents may use SendMessage for explicit coordination (progress updates, requesting assistance), but implicit dependencies are forbidden.

**R3. User sovereignty.** When requirements are ambiguous, the same approach has failed repeatedly, or scope far exceeds expectations — escalate to the user with: current state + what was tried + options + recommendation.

---

## §1 Context Engineering

Context is the scarcest resource and must be actively managed. These 5 principles apply across all modes:

**C1. Keep Overseer lightweight.** Overseer context utilization < 15%. Only receive summaries + file paths, never large chunks of content. Decisions rely on judgment, not a stuffed context.

**C2. Artifact size caps.** Each artifact file has a line limit:
- `proposal.md` ≤ 150 lines
- `tasks.md` ≤ 200 lines
- `spec.md` ≤ 300 lines
- `design.md` ≤ 250 lines

Overseer checks with `wc -l` when accepting artifacts — reject and request trimming if over limit.

**C3. Fresh context first.** If an agent fails 3 consecutive times, or context usage exceeds 70% → terminate that agent, spawn a new one to inherit the task (attach failure summary, not full history).

**C4. `<files_to_read>` contract.** Spawn prompts must include an explicit file manifest (`<files_to_read>` block). Agents Read all listed files before starting work. Never rely on agents to find files on their own.

**C5. Analysis paralysis circuit breaker.** If an agent makes 5 consecutive read-only tool calls → it must stop and write code/artifacts, or SendMessage to report a blocker. Overseer also checks for this during inspections.

---

## §2 Routing

- User provides a **task list** → **Parallel mode**
- User provides a **single goal** → **Goal mode**
- Unclear → ask the user

---

## Parallel Mode

Clean up old teams (`ls ~/.claude/teams/`) → TeamCreate → TaskCreate for each task → spawn all workers **in a single message** (`run_in_background=true`, add `isolation: "worktree"` for code changes) → **start inspection timer** (see §Progress Inspection) → inspection-driven + SendMessage callbacks → output summary table → **§Wrap-up**.

Worker prompt template:
```
You are worker-{N} on team {team}.
1. TaskUpdate to claim task #{N} (owner=worker-{N}, status=in_progress)
2. Execute the task
3. TaskUpdate to mark completed + SendMessage to team-lead with result summary (must include: branch name, commit hash, changed files list, test results)
```

---

## Goal Mode

### Overseer = Project Manager

You are not a process executor — you are the **owner** of this task. Your core responsibilities:

**Drive**: Autonomously push the task from 0 to completion. Define the end state, decompose the path, distribute tasks — don't wait to be prompted.

**Verify**: After each agent reports completion, **proactively assess whether the result truly meets the bar**. An agent saying "done" doesn't mean it's done — check whether its output meets end-state requirements, whether anything was missed, edge cases, or conflicts with other modules. Dispatch a Tester for independent verification when necessary.

**Course-correct**: When an agent goes off track, intervene immediately. Give clear correction instructions (what's wrong, why it's wrong, what the right direction is). Don't let agents continue burning context on the wrong path. For directional errors → terminate the agent and reassign.

**Think holistically**: Always maintain a perspective one level above the executors. Focus not on "is this line of code correct" but on:
- Are changes across modules consistent with each other?
- Are there overlooked blast radius areas?
- Is the current approach reasonable within the larger system?
- Is there a simpler way to achieve the same end state?

### STATE.md — Overseer Global State

Overseer maintains `STATE.md` (≤ 80 lines) in the artifact directory for quick recovery after session interruption.

Structure:
```
# STATE — {change-name}
## Current Phase: {Architect / Dev / Test / Push / Done}
## Progress: {N}/{Total} tasks completed
## Recent Decisions (≤5)
- {Decision 1}: {reason}
- {Decision 2}: {reason}
## Active Blockers
- {blocker description} → {planned resolution}
## Agent Status
| Agent | Task | Status | Notes |
|-------|------|--------|-------|
## Recovery Guide
{If session is interrupted, what to do next}
```

Overseer updates STATE.md after every key state change (agent completion/failure, phase transition, important decision).

### Agent Types

| Role | subagent_type | Purpose |
|------|---------------|---------|
| Architect | `general-purpose` | Research, design proposals, break down tasks. Output written to artifact files |
| Developer | `general-purpose` (isolation=worktree) | Write code. Read artifact files for context |
| Tester | `general-purpose` | Run tests only, never modify code |
| Pusher | `general-purpose` | Push code, create PRs |
| Explorer | `Explore` | Fast read-only search, lighter than Architect |

`Explore` and `Plan` cannot edit files. Writing code requires `general-purpose`.

**Dispatch method**: Must use the Agent tool's `team_name` parameter so agents join the team as independent Claude Code instances (visible in CLI UI). Never use subagent mode without `team_name` — subagents run in-process and users cannot observe their status.

### Artifact-Driven

Architect output is **written to files** (`~/.claude/team-dev/<change-name>/`), not just returned as context. Overseer only receives a 3-5 sentence summary + file paths. Developers Read artifact files directly for full context.

| Scope | Artifacts |
|-------|-----------|
| M (3-5 files) | `proposal.md` + `tasks.md` |
| L (>5 files / cross-service) | `proposal.md` + `spec.md` + `design.md` + `tasks.md` |

**Line limits** (C2): proposal ≤ 150, tasks ≤ 200, spec ≤ 300, design ≤ 250. Overseer checks with `wc -l` when accepting — reject if over limit.

**SUMMARY-{N}.md**: Written by Developer to the artifact directory after completing a task. Contents:
- Key decisions and rationale
- Deviations from the original plan (if any)
- List of changed files
- Patterns/conventions established (for downstream tasks to reference)

Provides reference for downstream Developers and Overseer during wrap-up — avoids relying on agent context recall.

### Decision Principles

1. **Understand before acting**: When information is insufficient, dispatch Architect/Explorer to research first — don't jump into distributing tasks
2. **Parallelize when possible**: Spawn all agents for independent tasks in a single message
3. **Dispatch = inspect**: After spawning agents, immediately start the inspection timer (see §Progress Inspection) — proactively control the pace, don't wait passively
4. **Verification is not a formality**: After an agent reports completion, scrutinize whether the result truly meets the bar — check for gaps, edge cases, cross-module consistency. When in doubt, dispatch a Tester for independent verification, or ask the agent for details
5. **Course-correct proactively**: When an agent goes off track (wrong approach, wrong files, missed requirements), immediately SendMessage with correction instructions — explain what's wrong and what the right direction is. For directional errors → terminate and reassign
6. **Cut losses early**: Same issue unresolved after 2 attempts → stop, change direction, or escalate
7. **Keep progress visible**: Use TaskCreate/TaskUpdate to maintain state, output summary on completion

### Prompt Templates

**Architect**:
```
You are the Architect. Target end state: {1-2 sentences}. Background: {requirements, clues}.

<files_to_read>
- {relevant source file 1}
- {relevant source file 2}
- {existing artifact files if any upstream output}
</files_to_read>

Write artifacts to ~/.claude/team-dev/<name>/: proposal.md (WHY) + tasks.md (execution checklist with file paths and acceptance criteria).
For L scope, also write spec.md (WHAT) + design.md (HOW).
Line limits: proposal ≤ 150, tasks ≤ 200, spec ≤ 300, design ≤ 250. Must trim if over limit.

Report to Overseer: 3-5 sentence summary + artifact paths + line counts per file + parallel/serial relationships.
```

**Developer**:
```
You are a Developer, responsible for {module}.

<files_to_read>
- ~/.claude/team-dev/<name>/tasks.md (section {N})
- ~/.claude/team-dev/<name>/proposal.md
- {upstream SUMMARY-*.md if any}
- {list of source files to modify}
</files_to_read>

After launch, Read all files above before starting work.

Rules:
- Write tests before implementation; only modify specified files — if out of scope → SendMessage
- 5 consecutive read-only tool calls → stop and write code or report blocker (C5 circuit breaker)
- Run tests after completion
- Write SUMMARY-{N}.md to artifact directory (include: key decisions, deviations, changed files, established patterns)
- TaskUpdate completed + SendMessage result summary (must include: branch name, commit hash, changed files list, test results)
```

**Tester**: `Run {command}, report PASS/FAIL + failure summary. Test only, never modify code.`

**Pusher**: `Push changes ({summary}), use the project's push workflow. Report PR link + CI status.`

### Task Breakdown

- Tasks that don't touch the same file → can be split into independent tasks
- Keep each agent's scope within 15 tool-call rounds
- Split dimensions: by service, by domain, by layer (schema / handler / middleware)
- Use `TaskUpdate(taskId, addBlockedBy=[...])` for dependencies

### Error Handling

Worker fails → analyze error to decide retry or escalate. Worker idle → SendMessage to nudge. All stuck → report to user.

### Progress Inspection (shared across both modes)

After dispatching tasks to child agents, Overseer **must** set an inspection cadence and proactively check progress — never just wait passively for callbacks.

**Inspection interval selection**:
- **1 minute**: Urgent tasks, simple tasks expected to finish in < 5 minutes
- **3 minutes** (default): Standard development tasks
- **5 minutes**: Large-scope tasks, tasks requiring long compile/test cycles

**Execution method**: After dispatching tasks, use the Bash tool with `run_in_background=true` to start a `sleep {seconds}` timer. When the timer expires and notification arrives, perform inspection:

1. **TaskList** to check all task statuses
2. For agents still `in_progress`, use **TaskOutput** (`block=false`) to view their latest output
3. Based on output, decide:
   - Making progress → log status, set next inspection timer
   - Stuck/off-track → immediately SendMessage to intervene or course-correct
   - Completed but unreported → SendMessage to prompt for report
   - Failed → follow error handling flow
4. Stop inspections once all tasks are completed → proceed to §Wrap-up

**Inspection output** (brief the user after each round):
```
⏱ Inspection #{N} ({X} minutes elapsed)
| Agent | Task | Status | Progress Summary |
|-------|------|--------|------------------|
| dev-1 | #1   | 🟢 progressing | 3/5 file changes done |
| dev-2 | #2   | 🔴 stuck       | test failure, intervened |
```

---

## §Wrap-up (shared across both modes)

After all tasks are complete, Overseer **must** execute the following wrap-up flow:

### 1. Write STATE.md Final Snapshot
Update STATE.md to final state, including: final results, key decision summary, discovered patterns/conventions, lessons learned. This is the reliable source for subsequent memory recording.

### 2. Clean Up Team
- Shutdown all agents (SendMessage type=shutdown_request)
- TeamDelete to remove team and task directories

### 3. Record Memory
Extract long-term useful information from **STATE.md + SUMMARY-*.md** and write to memory (`/Users/huangshaoqing/.claude/projects/-Users-huangshaoqing/memory/`). Rely on artifact files rather than context recall — more reliable.

**Worth recording**:
- Architecture discoveries (service relationships, key file paths, configuration conventions)
- Pitfalls and solutions (error message → root cause → fix)
- Code patterns and conventions (naming, directory structure, testing approaches)
- Dependency/toolchain knowledge (version requirements, compatibility)
- User preferences (code style, review habits)

**Not worth recording**:
- Ephemeral state from this session (branch names, PR numbers, etc.)
- Information already documented in CLAUDE.md
- Unverified speculation

**How**: First Read existing memory files, then decide whether to update an existing file or create a new topic file. Keep concise, organize by topic.

### 4. Clean Up Artifact Directory
Delete `~/.claude/team-dev/<name>/` (STATE.md, SUMMARY, proposal, tasks — all cleaned up).
