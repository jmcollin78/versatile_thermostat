# Development rules

## Where code goes

- Feature logic lives in its manager (`feature_*_manager.py`) or a focused module, not in the thermostat classes. Thermostat classes wire managers together.
- A behaviour that a plugin could provide goes behind a `vtherm_api` contract (`plugin-extraction.md`). The core adds only a generic hook, named for what it does, never for the plugin that uses it.
- Constants in `const.py` (or the owning module when private to it). Configuration keys follow the `CONF_*` conventions of `config-flow.md`.
- Do not grow the large files listed in `architecture.md`. When a change there is unavoidable, prefer extracting a helper and calling it.

## How code is written

- Simple and readable first. Small functions with one job, clear names, early returns, no clever one-liners.
- Every public class and method has an English docstring stating its intent and its contract (inputs, outputs, side effects). Comments explain why, never what changed or which ticket asked for it.
- Type hints on new and modified signatures.
- Root-cause fixes only. Not allowed as a way to reach a goal: swallowing exceptions, `hasattr`/`getattr` probing to dodge a design problem, special-case flags for one situation, branches that exist for tests, sleeps or retries to hide a race, monkeypatching, duplicating a block instead of factoring it.
- Remove what the change made obsolete: dead code, unused constants, translations and tests of removed behaviour.
- Keep public behaviour, attribute names, events and service schemas stable unless the task changes them; such a change is a contract change (docs, translations, release note, migration).

## Home Assistant and performance

- Never block the event loop: no synchronous I/O, network or heavy computation in async code; use the executor for unavoidable blocking work.
- Keep per-tick and per-state-change work light; compute once, cache when the input has not changed.
- Avoid redundant `async_write_ha_state` calls and redundant service calls to underlyings; send a command only when the target value changes or the protocol requires it.
- Register listeners and timers so that they are released on unload or removal (`async_on_remove` or the existing cleanup path).
- Respect the startup order: entities and underlyings may be unavailable at startup; follow the existing startup and retry paths (`runtime-flow.md`).
- Log at the right level: `debug` for traces, `info` for state changes a user would want, `warning`/`error` for actionable problems. Use the existing logger and message prefixes of the module.

## Before handing over

- Targeted tests pass; new behaviour has tests (happy path, edge cases, regression of the bug fixed).
- `git --no-pager diff` re-read: only intended hunks.
- Docs and translations updated for user-visible changes (`docs-i18n.md`).
- Memory checklist done (`memory-maintenance.md`).
