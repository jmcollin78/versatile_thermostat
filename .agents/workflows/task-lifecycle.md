# Task lifecycle

Every task follows the same five steps. The size of each step scales with the task.

## 1. Understand

- Restate the goal in one or two sentences. Ask when the goal, the scope or an acceptance criterion is unclear.
- Read only what the routing table of `AGENTS.md` names for this kind of task, then grep the code.
- For a bug: reproduce or locate the failing path before proposing anything (`debugging-user-reports.md`).

## 2. Plan

- Trivial task (one file, obvious fix, no behaviour or contract change): a three-line plan in the conversation (what, where, how verified).
- Otherwise create `.agents/local/tasks/<task-slug>/plan.md` from `.agents/templates/plan.md` and have the user validate it before writing code. The plan states:
  - verified facts (with `path::Symbol`), and what is still unverified;
  - the **plugin-first answer**: can this live behind a `vtherm_api` contract? If not, why not;
  - options considered and the chosen one, with the reason (simplicity, performance, fit with the architecture);
  - files touched, contracts or config changes, migration needs;
  - tests to add or change, docs and translations to update;
  - expected memory updates.
- A plan is revised, not bypassed: when the implementation reveals a different path, update the plan and tell the user.

## 3. Implement

- Follow `develop.md`. Work step by step; after each step re-read the diff and run the targeted tests.
- Record findings, dead ends and measurements in `notes.md` of the task folder as they happen, not in the long-term memory.
- Keep `handoff.md` current at each milestone: what is done, what is next, open questions. It is the brief for sub-agents and the resumption point after a context compaction.

## 4. Verify

- Targeted tests, then the related areas, then the full suite in the background when the change is not local (`testing.md`).
- Re-read the full diff: only intended hunks, no debug leftovers, no plan vocabulary, English comments, docstrings present.
- For a non-trivial change, an independent review (`vt-reviewer`) of the diff against the plan.

## 5. Close

- Run the end-of-task checklist of `memory-maintenance.md`, including the promotion step from the task folder.
- Give the user: what changed, how it was verified, what remains unverified, a brief English commit message.
- Delete the task folder once its durable facts are promoted and the user considers the task done.
