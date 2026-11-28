# Review

## Scope
Diff reviewed (base..head), plan it implements.

## Findings
Ordered by severity. For each: file and line, the defect, the concrete failure scenario, the suggested fix.
- Correctness and regressions
- Architecture: plugin-first, lean core, large files not grown, contracts generic and backward compatible
- Quality: readability, English docstrings, no shortcuts (swallowed exceptions, special-case flags, test-only branches, duplication)
- Performance in the event loop: blocking calls, per-tick work, redundant state writes or service calls, released listeners
- Tests: coverage of the change and of edge cases, config flow and managers
- Docs and translations: all languages, current-state wording, no private references
- Memory: `.agents/context` diff matches the code diff

## Verdict
Ready / ready after the listed fixes / needs redesign.
