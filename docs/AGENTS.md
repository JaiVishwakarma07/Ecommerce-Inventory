# AGENTS.md

## Project: ECOM_OPPO
FastAPI REST API + React frontend — see `specs/` for requirements, `docs/architecture.md` for system context.

## Project layout
```
backend/app/     # FastAPI source (run server commands from backend/)
frontend/        # React + Vite UI
tests/           # pytest (run from project root)
specs/           # Feature specs
docs/            # Architecture and harness traces
openspec/changes/ # OpenSpec change records
.cursor/         # Cursor skills, agents, rules
```

## Primary Spec
Read specs/*/spec.md before starting any task.
Read docs/architecture.md for system context.
Read .cursor/rules/common/project.mdc for coding conventions.

## Spec And Plan Layout (Project Standard)
- For every feature, use one folder: `specs/<feature-name>/`
- Keep `spec.md` and `plan.md` in that same folder
- Keep planning details consolidated inside `plan.md` (research, data model,
  quickstart) unless explicitly requested otherwise
- Keep API contracts under `specs/<feature-name>/contracts/`

## Active Harness
Tools: ECC + GitHub Spec Kit + OpenSpec + Superpowers
Always follow the Brainstorm → Plan → Implement → Verify cycle.
Use Superpowers skills at each phase — do not skip phases.

## Subagents in Use
- code-reviewer (Superpowers + ECC): After every implementation task
- test-writer (ECC): When writing tests for existing functions
- security-scan (ECC): Before every PR

## Superpowers Skills Active
- /brainstorming — required before any feature work
- /writing-plans — required before touching code
- /test-driven-development — required before any implementation
- /verification-before-completion — required before any commit
- /systematic-debugging — required when any test fails

## Change Management
All changes follow OpenSpec workflow. See openspec/changes/ for active changes.
Reference change-id in commit messages: feat(auth): add JWT refresh #CHG-001

## Do Not
- Write synchronous DB access
- Return passwords or secrets in any response
- Use print() for logging
- Skip the brainstorm or planning phase
- Claim work is complete without running verification commands
- Commit without passing tests
