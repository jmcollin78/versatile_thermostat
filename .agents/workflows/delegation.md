# Delegation: which agent for which task

Goal: spend strong models on thinking, cheaper models on execution. Profiles exist for Claude Code (`.claude/agents/*.md`), Codex (`.codex/agents/*.toml`) and GitHub Copilot (`.github/agents/vt-*.agent.md`) with the same names and the same instructions. They are generated from one source: edit the list in `.agents/scripts/gen_profiles.py`, run it, never edit the generated files by hand. Copilot profiles carry hand-off buttons along the typical flows below. The other Copilot profiles of `.github/agents/` belong to the maintainers; `.github/agents/vtherm.agent.md` routes to the `vt-*` agents.

| Profile | Claude model / effort | Codex model / effort | Use for |
| --- | --- | --- | --- |
| vt-explorer | haiku / low | gpt-6-luna / low | locate code, callers, tests, config keys; read-only |
| vt-developer | sonnet / medium | gpt-6.1-terra / medium | implement a well-specified change with its tests |
| vt-test-engineer | sonnet / medium | gpt-6.1-terra / medium | write, repair and run tests |
| vt-docs-writer | sonnet / medium | gpt-6.1-terra / medium | user docs, tech docs, release notes |
| vt-translator | haiku / low | gpt-6-luna / low | translation files and doc languages in sync |
| vt-senior-developer | opus / high | gpt-6.1-sol / high | changes needing judgement: thermostat state logic, underlyings, cycle scheduler, config migrations, `vtherm_api` contracts, feature extraction |
| vt-debugger | opus / high | gpt-6.1-sol / high | root cause of a bug or a user report; may run tests, does not edit product code |
| vt-architect | opus / high | gpt-6.1-sol / high | design and implementation plan, plugin-first analysis; read-only |
| vt-reviewer | opus / high | gpt-6.1-sol / high | independent review of a diff against its plan; read-only |

Copilot uses the Claude model of the same tier. Codex and Copilot model names may change; if a profile fails on an unknown model, adjust the name in the generator or remove it to inherit the chat's model. "Read-only" profiles keep a shell tool and are read-only by instruction. Sub-agents cannot spawn other agents: the orchestrating session chains them.

## Routing rules

1. Default to the cheapest adequate profile. Escalate when a cheaper agent reports it cannot decide, or when the change touches state calculation, underlyings, the cycle scheduler, config migrations or a `vtherm_api` contract.
2. Feature: architect (plan, plugin-first answer) -> user validation -> senior-developer or developer -> test-engineer -> reviewer -> docs-writer -> translator.
3. Bug or user report: debugger (root cause, failing test) -> developer or senior-developer (fix) -> reviewer for non-trivial fixes.
4. **Fresh agent per task** with a self-contained brief built from the task's `handoff.md`: goal, files to read, what was ruled out, rules, expected report. Resume an agent only for a short follow-up on the same task.
5. **Tight briefs**: point to files instead of restating them; ask for a short report (what was done, verified, unverified, open questions). Include the standing rules: no commit, no polling (long jobs in the background, wait for the notification), stay in scope.
6. Parallel agents only for independent, read-mostly work. Do not duplicate an agent's work while it runs; do not re-read a large report when its summary is enough.
7. The orchestrator validates each step before the next and re-reads delegated diffs.
