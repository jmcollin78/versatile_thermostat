# Principles (binding)

Rules stated by the maintainers. An agent that finds a task conflicting with one of them stops and asks. The user may waive a rule for one task; it applies again once that task is done.

## Architecture

- **Plugin first.** A feature that can live behind a `vtherm_api` contract is built as a plugin, not in the core. The core offers generic contracts and hooks, never feature-specific code paths for one plugin.
- **Lean core.** Extracting a feature removes its core code, constants, config steps, translations and tests in the same change set (with a migration path for existing users). Dead code is deleted, not commented out or flagged off.
- **Stable contracts.** A `vtherm_api` contract change is backward compatible or versioned; both sides get tests. Plugins use only the public runtime surface, never private VT modules or attributes.
- **No growth of the large files.** New logic goes into a focused module or manager, not into `base_thermostat.py`, `underlyings.py`, `config_flow.py`, `thermostat_climate.py` or `llm/__init__.py`.
- **One mechanism per job.** Reuse the existing manager, scheduler or helper instead of a parallel path doing the same thing.

## Code quality

- Simple, readable code that a non-specialist can follow. Clear names, small functions, early returns.
- English comments and docstrings on every public method; they explain intent and constraints, not history.
- Elegant solutions only: fix the root cause; no shortcut taken because it is easier (swallowed exceptions, special-case flags, `if testing`, copy-paste, monkeypatching, sleeps to dodge races).
- Performance matters in Home Assistant: async code never blocks, work per tick stays light, state writes are not repeated needlessly, listeners and timers are released on unload.
- Type hints on new code; constants in `const.py` (or the owning module), no magic numbers.

## Process

- Plan before coding; the user validates the plan of a non-trivial task (`workflows/task-lifecycle.md`).
- Proceed step by step; validate each step before the next.
- Change only what the task requires; re-read the diff after each edit.
- No commit, push or tag without an express request.
- Evidence before claims: say what was verified and how; mark the rest "unverified".
- Token economy: grep and partial reads, the cheapest adequate sub-agent, concise answers.

## Documentation and translations

- Docs describe the current state only, as if never published; only release notes list changes.
- A user-visible change updates the docs in every documentation language and every translation file.
- Code, commands, file names, YAML keys and proper names are never translated.

## Repository hygiene

- Nothing private or install-specific in versioned files: no plan or review references, people names, credentials, private URLs, real entity ids, absolute or machine paths.
- Commit messages are brief, informative, in English, without links or file paths.
