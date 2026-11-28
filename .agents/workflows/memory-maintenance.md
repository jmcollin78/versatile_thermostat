# Maintaining the memory

The long-term memory (`.agents/context/`) is the current truth about the project, shared with every developer. It is not a log and not a dump of a development session. Git history is the archive: delete, do not keep tombstones.

## The two tiers

- **Short-term**: `.agents/local/tasks/<task-slug>/` (gitignored, local to one checkout).
  - `plan.md`: the validated plan (template `templates/plan.md`).
  - `notes.md`: findings, dead ends, measurements, log excerpts, test results, anything useful to this task only.
  - `handoff.md`: state for resumption and for sub-agent briefs (template `templates/handoff.md`).
  - Created at planning, updated during the task (before an automatic context compaction too), deleted at close after promotion.
- **Long-term**: `.agents/context/` (versioned). Written only through the admission test below.

## Admission test (all four must hold)

1. A future session working on a **different** task will need it.
2. It stays true beyond this task and this release.
3. It cannot be found with two greps in the code (a non-obvious coupling, a trap, a reason, a decision).
4. It is current state: no history, dates, issue or plan identifiers, logs, raw numbers that do not justify a decision.

Everything else stays in the task folder or goes into the commit message.

## End-of-task checklist

1. **Promote**: read the task's `notes.md`; keep 0 to 3 facts that pass the admission test and write each in the file the trigger table names (rewrite the existing paragraph rather than appending).
2. **Update** the files the code change touched (trigger table), in the same change set as the code.
3. **Prune** what the change made wrong or obsolete.
4. Run `python3 .agents/scripts/check_memory.py`; fix every ERROR, treat WARN as a prune request.
5. Report "memory: updated X, Y" or "memory: nothing to update because ...".
6. Delete the task folder when the user considers the task done.

Who writes: the agent that implemented the change (it knows the facts). Read-only profiles (architect, reviewer, debugger, explorer) do not edit `.agents/context/`; they list in their report what should be recorded, and the orchestrating session applies it.

## Trigger table

| Event | Update |
| --- | --- |
| Module added, moved, renamed, deleted; role change | `context/architecture.md` |
| Startup, listeners, control cycle, services, events changed | `context/runtime-flow.md` |
| `vtherm_api` contract or runtime surface changed; feature externalized | `context/plugin-api.md`, `context/status.md` |
| Config option, step, central inheritance, migration changed | `context/config-flow.md` |
| Attribute, event, log or diagnostic tool changed; new symptom pattern | `context/diagnostics.md` |
| Durable trap discovered (cost hours, will bite again) | `context/pitfalls.md` |
| Approach adopted or rejected, with the reason | `context/decisions.md` |
| Maintainer states a rule | `context/principles.md` |
| Long-running workstream started, advanced or finished | `context/status.md` |
| Version, dependency, language or repository facts changed | `context/project.md` |
| Test, docs, release or delegation procedure changed | the matching `workflows/*.md` |
| Agent profile added, removed or retuned | the list in `.agents/scripts/gen_profiles.py` (then run it), `workflows/delegation.md` |

## `context/status.md`

An index of long-running workstreams only (externalization roadmap, multi-PR refactors), at most 60 lines. One to three lines per item: goal, state, next step. No task details, no test results, no dates. When an item finishes, move its outcome to `decisions.md` (one row) and delete it.

## Pruning rules

Delete or rewrite when:
- the code it describes no longer exists or changed (verify with grep, never from memory);
- it is history ("was", "used to", "new", "now"), a dated entry, a session log, or a conclusion superseded by a later one;
- it duplicates another file (keep the more specific one, link from the other);
- it is task-local context no future session needs;
- it cites a plan, an issue or review identifier, a person, or a machine path.

Prefer a short rewrite over appending. When a file passes its budget (`.agents/README.md`), cut the least useful content or split by theme.

## Periodic audit

Before a release, or when `check_memory.py` warns repeatedly:
1. Run `check_memory.py` and fix everything.
2. Per context file, have a cheap read-only explorer verify every module, symbol and path claimed; delete or rewrite what cannot be verified.
3. Re-read `status.md`, `decisions.md` and `pitfalls.md` against the code for items that completed or became obsolete.
4. Check `AGENTS.md` stays short and that every file it names exists; check agent profiles match `workflows/delegation.md`.

## Merges

Memory files merge like code: on a conflict, take the version that matches the merged code, then re-run the checker. Never keep both versions.
