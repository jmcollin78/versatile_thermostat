# .agents - shared project memory for AI agents

Versioned, tool-neutral memory of Versatile Thermostat. `AGENTS.md` (repo root) is the entry point and holds the binding rules; this tree holds the knowledge and the procedures. Everything versioned here is current-state, English, free of personal data and of machine-specific paths.

## Layout

| Path | Content | Budget |
|------|---------|--------|
| `context/principles.md` | Binding product, architecture and process rules of the maintainers | 80 lines |
| `context/project.md` | What VT is, plugin ecosystem, versions, languages, repository conventions | 80 lines |
| `context/architecture.md` | Verified code map, "where do I change X", large files | 300 lines |
| `context/runtime-flow.md` | Setup, startup, listeners, control cycle, services, events | 300 lines |
| `context/plugin-api.md` | `vtherm_api` contracts, what VT exposes, how to externalize | 300 lines |
| `context/config-flow.md` | Config flow, options, central config, migrations, adding an option | 300 lines |
| `context/diagnostics.md` | Reading attributes, events, logs, LLM diagnostics; symptom table | 300 lines |
| `context/pitfalls.md` | Durable traps by theme | 150 lines |
| `context/decisions.md` | Adopted and rejected approaches, and why | 150 lines |
| `context/status.md` | Long-running workstreams and externalization roadmap | 60 lines |
| `workflows/` | task-lifecycle, develop, plugin-extraction, testing, debugging-user-reports, docs-i18n, release, delegation, memory-maintenance | |
| `templates/` | plan, handoff, issue-report, review | |
| `scripts/check_memory.py` | Consistency check (paths, symbols, budgets, privacy, profiles, local tier) | |
| `scripts/gen_profiles.py` | Generates the `vt-*` agent profiles for Claude, Codex and Copilot from one list | |
| `local/` | Short-term memory, gitignored, one folder per task | |

## The two memory tiers

| | Long-term (`context/`) | Short-term (`local/tasks/<task-slug>/`) |
|---|---|---|
| Versioned | yes, shared with all developers | no, local to one checkout |
| Content | current truths useful to future, different tasks | plan, findings, dead ends, measurements, resumption state |
| Lifetime | until the code changes | the task; deleted at close |
| Written by | the agent that changed the code, at task end | any agent, during the task |

Admission test, promotion step and pruning rules: `workflows/memory-maintenance.md`.

## Conventions

- Code references are backticked repo-relative paths, optionally `path::Symbol`; `check_memory.py` verifies they exist.
- The external package is named "the `vtherm_api` package (separate repository)"; never cite a local path to it.
- No dates, issue or pull-request numbers, plan or review identifiers, people names, URLs or entity ids of real installations.
- `documentation/tech-docs/` and `documentation/specs/` are historical design records of the project. They are not part of this memory: read one only when the task concerns that topic, and verify against the code.
