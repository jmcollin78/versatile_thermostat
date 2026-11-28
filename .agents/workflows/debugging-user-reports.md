# Debugging a user report

Goal: find the root cause with evidence, then propose the smallest correct fix. Never guess.

## Collect

- Versions: VT, Home Assistant, `vtherm_api`, installed plugins.
- Thermostat type (`over_switch`, `over_valve`, `over_climate`), proportional algorithm, enabled features, central configuration use.
- The thermostat attributes at the time of the problem, the relevant events, and debug logs covering the period (how to obtain them: `context/diagnostics.md`).
- What the user expected, what happened, when, and whether it is reproducible.
Ask the user to redact names, addresses, tokens and entity ids they do not want to share. Never store their data in the repository.

## Triage

1. Use the symptom table of `context/diagnostics.md` to pick the subsystem.
2. Check configuration first (inheritance from the central configuration, cycle length, activation delays, sensors), then the state calculation (preset, hvac mode, features overriding the target), then the command path to the underlyings.
3. Locate the code path with grep and partial reads; confirm with the logs which branch ran.
4. Reproduce in a test when possible: a failing test is the best evidence and becomes the regression test.
5. Distinguish a VT bug, a plugin bug, an underlying device or integration behaviour, and a configuration problem.

## Report

Use `templates/issue-report.md`: symptom, evidence, root cause (or ranked hypotheses with the next measurement that separates them), proposed fix (file, symbol, behaviour), risk, tests. Stay read-only on the user's system; do not call services that change their configuration or state without consent.

Keep the investigation notes in `.agents/local/tasks/<task-slug>/notes.md`. Only a durable trap (one that will bite again) goes to `context/pitfalls.md`, and a new symptom pattern to the table of `context/diagnostics.md`.
