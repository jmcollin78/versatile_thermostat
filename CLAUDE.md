@AGENTS.md

## Claude Code specifics

- Project sub-agents are in `.claude/agents/` (`vt-*`); routing rules in `.agents/workflows/delegation.md`. Prefer `sonnet` agents for implementation, tests and docs, `haiku` for exploration and translation, `opus` for design, judgement-heavy implementation, debugging and review.
- Project permissions (`.claude/settings.json`) ask before `git commit`, `git push` and `git tag`.
- Before an automatic context compaction, the in-progress state is saved to the current task's `.agents/local/tasks/<task-slug>/handoff.md`, never to the long-term memory.
- Your personal auto-memory is per machine; durable project knowledge belongs in `.agents/context/`.
