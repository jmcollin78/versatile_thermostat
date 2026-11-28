# AGENTS.md - Versatile Thermostat

Instructions for any AI coding or debugging agent (Claude Code, Codex, Copilot, others) working in this repository. They are meant to be sufficient on their own: a new session needs only the problem statement. Deeper knowledge lives in `.agents/` (versioned, shared memory). Answer in the language the user writes in; code, comments, commit messages and `.agents/` are in English.

## What this is

Versatile Thermostat (VT) is a Home Assistant custom integration (`custom_components/versatile_thermostat`) that creates thermostats on top of switches, valves or other climates, with presets, window/motion/presence/power features, central configuration, central boiler, safety, and proportional algorithms (TPI, Auto TPI). Features and algorithms can be provided by external plugins through the `vtherm_api` package (separate repository). Direction of the project: **move features out of the core into plugins and keep the core lean**.

## Start of a session: what to read

Always read `.agents/README.md` (index) and `.agents/context/principles.md` (binding rules). Then, by task:

| Task | Read |
| --- | --- |
| Any code change | `workflows/task-lifecycle.md`, `workflows/develop.md`, `context/architecture.md`, `context/pitfalls.md` |
| Behaviour of a thermostat at runtime | `context/runtime-flow.md` |
| New feature, or a feature that could leave the core | `context/plugin-api.md`, `workflows/plugin-extraction.md`, `context/status.md` |
| Configuration options, config flow, migrations | `context/config-flow.md` |
| User problem / bug analysis | `workflows/debugging-user-reports.md`, `context/diagnostics.md` |
| Tests | `workflows/testing.md` |
| Docs, translations, release | `workflows/docs-i18n.md`, `workflows/release.md` |
| Past choices (do not re-propose rejected ideas) | `context/decisions.md` |
| Which sub-agent to use | `workflows/delegation.md` (`vt-*` profiles in `.claude/agents/`, `.codex/agents/`, `.github/agents/`) |
| Finishing any task | `workflows/memory-maintenance.md` |

Load only what the task needs. The code base is large: use grep and partial reads; never read the large files listed in `context/architecture.md` whole.

## Hard rules

1. **No hallucination.** Every claim rests on code, docs, observed data or a demonstrable argument; mark the rest "unverified". When a decision is not certain, stop and ask.
2. **Plan first.** A non-trivial task starts with a written plan (`.agents/templates/plan.md`) in the local task folder, validated by the user before any code. Trivial tasks (one file, obvious fix) get a three-line plan in the conversation. See `workflows/task-lifecycle.md`.
3. **Plugin first, lean core.** Before adding a feature to the core, answer in the plan: can it live behind a `vtherm_api` contract? If yes, build a plugin and add only a generic contract or hook to the core. Plugins never import private VT modules. Every extraction removes the dead core code. The large core files must not grow.
4. **Quality, no shortcuts.** Simple, readable code; English comments and docstrings that explain why. Fix root causes. No swallowed exceptions, special-case flags, test-only branches, duplicated logic or monkeypatching to reach a goal. Think about performance in the Home Assistant event loop (no blocking I/O in async code, no heavy work per tick, no state-write storms). Details: `workflows/develop.md`.
5. **Stay in scope.** Change only what the task needs; do not fix other things unasked. Re-read every diff you produced. Always `git --no-pager`.
6. **No commits.** Never commit, push, tag or amend unless the user expressly asks. After a change, give a brief English commit message (no links, no file paths).
7. **Tests.** pytest, targeted files first (`workflows/testing.md`). The full suite is slow: run it in the background and wait for the completion notification. Never poll a running job.
8. **Docs and translations.** Documentation describes the current state only, as if never published (no "new/now/fixed/changed" wording). After a user-visible change update the docs in every language and the translation files.
9. **No private context in the repository.** Code, comments, docs, tests and `.agents/` never mention plans, phases, review identifiers, personal names, credentials, URLs of private systems, real entity ids or machine-specific paths. They describe the code on its own terms.
10. **Cost discipline.** Cheapest adequate model per sub-task, tight briefs, short reports, a fresh sub-agent per task (`workflows/delegation.md`).

## Commands

```bash
pytest -q tests/test_window.py            # one file
pytest -q tests -k "preset"               # by keyword
pytest -q tests                           # full suite (slow, background)
python3 .agents/scripts/check_memory.py   # memory consistency check
git --no-pager status --short ; git --no-pager diff --stat
```

Python version: the one required by the Home Assistant release pinned in `requirements_dev.txt`. Test dependencies: `requirements_test.txt` (see `workflows/testing.md`).

## Repository map (short)

- `custom_components/versatile_thermostat/` - the integration: thermostat classes (`base_thermostat.py`, `thermostat_*.py`), feature managers (`feature_*_manager.py`), underlyings (`underlyings.py`), cycle scheduler and proportional algorithms, config flow, platforms, `llm/`, `translations/`.
- `tests/` - pytest suite. `documentation/<lang>/` user docs, `documentation/tech-docs/` and `documentation/specs/` per-topic technical notes (historical design records, not agent memory; read one only when the task is about that topic). `README*.md`, `CONTRIBUTING*.md`.
- Full map: `.agents/context/architecture.md`.

## Two memory tiers

- **Long-term, versioned**: `.agents/context/` - the current truth about the project, shared with every developer. A fact enters it only if it passes the admission test of `workflows/memory-maintenance.md`.
- **Short-term, local, never versioned**: `.agents/local/tasks/<task-slug>/` with `plan.md`, `notes.md`, `handoff.md`. Work in progress, findings, dead ends, resumption state. Deleted when the task closes, after promoting the few durable facts.

Every task ends with the checklist of `workflows/memory-maintenance.md` and a line "memory: updated X" or "memory: nothing to update because ...".

## Debug mode for users

If a user launched you to find why their thermostat misbehaves: follow `workflows/debugging-user-reports.md`, stay read-only on their system, never change their configuration without consent, ask them to redact personal data, and report in the `templates/issue-report.md` format.
