# Review of Issue #2111 and PR #2113

**Status:** retain the proposed approach; defer merging. Revalidation after conflict resolution is required.
**Issue:** [#2111](https://github.com/jmcollin78/versatile_thermostat/issues/2111)
**PR:** [#2113](https://github.com/jmcollin78/versatile_thermostat/pull/2113)
**Review updated:** 2026-10-18; supersedes the less conditional conclusion of 2026-10-13.
**PR commit reviewed:** `f19d5aa8e6ec2c0dee45af71f632748b8aa4c1fd`.
**Reported GitHub base:** `d61ba711d0d1564a33d97131e50517f90e88ad7e` (`main`).
**Method:** static review of the remote diff, the file at the PR commit, and relevant local code paths. No checkout, test execution, or changes to code, configuration, or Home Assistant state. The exact workspace revision was not verified through Git.

## Conclusion for the Maintainer

No definite regression introduced by the diff has been established in the code paths reviewed. This is not proof that regressions are absent. The fix is localized and consistent for normal transitions with temperature data available; it does not justify unconditional approval.

Do not merge as it stands: GitHub reports `mergeable: false`, `mergeable_state: dirty`. Require a fresh review of the conflict resolution, tests on that revision, and a targeted beta. The main risks involve concurrent commands, resuming operation with missing data, and interactions with existing protections. These are not all new defects introduced by this PR.

## Verified Summary and Discussion

The issue concerns VTherm 10.5.1, HA 2026.10.1, and Sonoff TRVZB devices through Zigbee2MQTT, using `over_climate` with direct valve regulation and a five-minute minimum regulation period. Transitions to or from `sleep` can retain a stale 100% opening, an unjustified `hvac_action: heating`, and an incorrect active-device count. According to the reporter, a heat pump automation actually reacted to this state.

The PR adds two stored modes, one for the last calculation and one for the last pass through the sending method. A mode change bypasses the regulation-period and opening-change filters. It changes two files: +13/-3 production lines and +211 test lines (five tests).

- @jmcollin78, October 13: highlights the sensitivity of the control loop, requests a separate beta and real-world observation, and references the first version of this report.
- @JMBO1701, October 14: offers to test with 13 Sonoff TRVZB devices, several daily transitions, and feedback after one to two weeks. This is an offer to test, not a beta result.
- @jmcollin78, October 18: announces 10.6.1 and requests conflict resolution before publishing a beta.
- The review and inline-comment APIs returned empty lists when consulted. No additional hardware feedback was found in the three accessible comments.

## Prioritized Findings

### 1. High Priority: the Revision to Be Merged Cannot Yet Be Validated

**Confirmed fact and merge blocker, not a demonstrated regulation bug.** The conflict is confirmed by the API, not just the maintainer's comment. CI for the October 13 commit does not cover the not-yet-existing result of resolving that conflict against the current base.

This code path has since evolved with inhibition support in [#2101](https://github.com/jmcollin78/versatile_thermostat/pull/2101), commit `be64352685510dbca9f88252ca2a50aea3bf7077`. Valve bootstrap support in [#2096](https://github.com/jmcollin78/versatile_thermostat/pull/2096), fixing #2049, is another functional dependency that must be preserved, although it predates this PR.

**Requested action:** do not resolve the conflict by replacing the current file with the version from the PR branch. Preserve the protections and inspect the resulting diff. The exact conflict locations were not determined in this review.

### 2. Medium Priority: the Guarantee When Leaving Sleep Requires an Available Calculation

**Limitation established by code inspection; pre-existing behavior, not a proven new regression.** In [recalculate](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L234), if `safe_on_percent` is `None`, the code preserves `_valve_open_percent` and returns without recording the new calculation mode. In [TPI](../../custom_components/versatile_thermostat/prop_algo_tpi.py#L83), a missing target or current temperature makes the result unavailable.

Consequently, an unavailable calculation after `sleep` can leave 100% cached. If the target temperature exists, the next send may use that cache; if the target is also missing, the sending method returns before issuing any command, including in OFF mode within this method. Other paths may still stop the device: this does not establish that OFF is ineffective overall.

A Home Assistant state of `unavailable` does not necessarily imply `_cur_temp = None`: sensor handling may retain an older measurement. The exact occurrence of this scenario in production has not been demonstrated.

**Requested action:** test leaving sleep with `on_percent is None`, followed by sensor recovery, and explicitly decide the expected behavior. Do not promise a freshly calculated opening in every case. Do not introduce unconditional closure here without considering that it would change the existing policy.

### 3. Medium Priority: the dpercent Filter Is Not Tested Independently

**Verified coverage gap.** The new tests use `dpercent = 0.5` and integer openings of 0/40/100. The unchanged-mode test stays within the regulation period: the first filter alone makes it pass, even if the dpercent filter were broken. It therefore does not establish that both filters mentioned in the description are preserved.

**Requested action:** add a check with a meaningful threshold, for example five percentage points: after the period expires, a small nonzero change in a positive opening should be filtered while the mode stays unchanged. Then test `heat 98% -> sleep 100% -> heat 98%`, which should bypass that filter and return to 98%. Also verify closure to 0% independently of the filter, and that filtering resumes after a transition.

### 4. Potentially High-Impact Risk: a Stored Mode Is Not a Hardware Acknowledgement

**Structural fact and unreproduced risk.** `_last_sent_hvac_mode` is assigned after several `await` calls and reads the current mode again, without capturing a request revision. Another call chain can change that mode during sending. The new tests wait for tasks to complete between transitions: they do not exercise this interleaving.

The service wrapper in [UnderlyingEntity](../../custom_components/versatile_thermostat/underlyings.py#L225) can absorb an error or drop a command through the inhibition gate. [set_valve_open_percent](../../custom_components/versatile_thermostat/underlyings.py#L1435) deduplicates using a cache updated before sending. The stored mode therefore guarantees neither service success nor physical position. These mechanisms predate the PR; the new stored mode adds a filtering condition to verify, not proof of a failure.

**Requested action:** add a deterministic interleaving test with a paused service call, a concurrent mode change, and at least two valves; verify convergence to the latest request. Cover a service failure and a blocked command without assuming that a coroutine returning constitutes an acknowledgement.

## What the Fix Preserves or Changes

| Area                              | Static analysis                                                                 | Caveat                                                                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `heat -> sleep`                   | The calculation immediately switches to 100%, even within the period.           | Logical 100% remains subject to valve min/max conversion.                                                                  |
| `sleep -> heat`, warm room        | TPI can calculate 0 and sending no longer waits.                                | Requires calculation data; hardware feedback is not instantaneous.                                                         |
| `sleep -> off -> heat`            | Each mode is distinguished; the sleep value can be replaced before resuming.    | Also test a cold room and an unavailable result.                                                                           |
| `off -> heat` without sleep       | Calculation also becomes immediate.                                             | An intentional behavioral extension beyond the sleep symptom alone.                                                        |
| Automatic HVAC changes            | The effective mode is used, not just the user service call.                     | Window, central control, safety, and inhibition need coverage.                                                             |
| Steady operation in the same mode | Regulation-period and dpercent conditions remain present.                       | The five tests do not establish all boundaries or behavior after a transition.                                             |
| Repeated identical request        | The comparison does not force another calculation for an already recorded mode. | Other pre-existing `force=True` calls remain possible.                                                                     |
| Same opening after a mode change  | The calculation mode is recorded even if the percentage does not change.        | Positive point: avoids detecting the same transition indefinitely. The calculation timestamp is not advanced in this case. |
| Physical sending                  | Underlying caches still deduplicate an identical opening.                       | It is inaccurate to say that every transition always produces a physical command.                                          |
| TPI, closure threshold, min/max   | No formula or conversion changes in the diff.                                   | Earlier recalculation; tests with multiple valves and nontrivial limits are required.                                      |
| Other thermostat types            | No direct changes to their code.                                                | Run the full suite after rebasing to cover shared interactions.                                                            |

### Two Command Paths Must Be Distinguished

`ThermostatOverClimate.async_control_heating()` calls the regulated sending method and then the base control chain. The proportional handler can subsequently call [CycleScheduler._apply_valve_command](../../custom_components/versatile_thermostat/cycle_scheduler.py#L409), which also calls `set_valve_open_percent()`.

It would therefore be incorrect to infer a stuck valve solely from an early return in `_send_regulated_temperature()`. Tests must observe the services actually issued through the complete flow, rather than just mocking this method. Underlying deduplication normally limits duplicate commands.

Calculation and sending timestamps are not transactional: a calculation that leaves the value unchanged retains its old timestamp, whereas a pass through sending outside OFF mode advances its timestamp even without a new command. A transition with an unchanged opening can therefore put these delays out of sync. Verify the first subsequent update; no new blockage has been proven here, particularly because of the second path described above.

## Risk and Impact Assessment

Likelihood cannot be quantified without execution and field observations. The levels below describe potential consequences, not predictions of failure.

| Risk                                                     | Potential severity | Likelihood / evidence                                                                           | Mitigation                                                   |
| -------------------------------------------------------- | ------------------ | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Persistent heating or boiler demand after resuming       | High               | Original bug reported; missing-data variant not reproduced                                      | Transition matrix, sensors, and boiler feedback.             |
| Concurrent commands or inconsistent opening/closing pair | High               | Hypothesis; interleaving not tested in the diff                                                 | Tests with paused services and a multi-valve beta.           |
| Inhibition or post-inhibition recovery regression        | High               | Integration not validated after conflict resolution; central gate remains in the code inspected | Rerun inhibition tests on the final revision.                |
| More commands during rapid mode changes                  | Medium             | Explicit bypass of delays; actual volume depends on caches                                      | Count service calls and Zigbee2MQTT messages.                |
| Loss of filtering or delay after a transition            | Medium             | Conditions inspected; partial coverage                                                          | Regulation-period/dpercent tests and out-of-sync timestamps. |
| Initialization, sleep restoration, recalibration         | Medium to high     | No new execution results                                                                        | Rerun corresponding tests and restart during the beta.       |

**Security/privacy:** no new access, storage, network use, or secrets in the diff. The relevant risk is operational (heating, flow, and physical commands), not a new data exposure.

**Compatibility/migration:** two internal volatile attributes, with no schema or configuration migration. COOL mode is exposed for AC configurations, but the new tests use `AC_MODE=False`: do not claim COOL has been validated.

**Operations/documentation:** an isolated beta makes it easier to attribute anomalies and roll back to 10.6.1. Document the mode-change exception to command timing and the conditions required for a valid calculation; no user documentation or release changes were made during this review.

## Tests: Evidence and Gaps

The checks API for the reviewed commit reports `testu: success`, successful style/HACS/Validate jobs, and `Run tests: skipped`. There is therefore a successful test job; the skipped job does not mean that all tests were skipped. The executed test count was not extracted from logs. **767 passed / 2 skipped**, and the statement that the first three tests fail without the fix, remain contributor-reported results that were not reproduced in this review.

The five tests provide real value: they inspect opening/closing number entities and, for some transitions out of sleep, heating and activity states. They do not exercise an actual central boiler or delayed Zigbee2MQTT feedback. Their helper directly sets both timestamps, reproducing the timing restriction but not how those timestamps are naturally established in real operation.

### Priority Checks Before a Beta

1. Resolve the conflict without losing current changes, then rerun the five tests and the existing regulation suite, particularly the minimum-period test.
2. Add independent dpercent and post-transition timing tests; cover a small change, zero, 100%, and an unchanged opening across a mode change.
3. Test that the latest request wins with paused services and multiple valves; distinguish rapid sequential calls from genuinely concurrent calls.
4. Test missing temperature data followed by recovery, and verify that OFF retains its guarantees through the complete flow.
5. Rerun inhibition, recalibration, restart with unknown degree entities (#2049), window, safety, central-control tests, and the full suite on the final commit. Add a sleep transition to these matrices where not already covered.
6. Test `cool -> sleep -> cool` if this configuration is declared supported in the release.

### Proposed Beta Protocol

- Use an immutable revision rebased onto the current stable version, identified in the test feedback; do not mix in other functional fixes.
- Run for one to two weeks on the 13 proposed TRVs, with daily transitions, weekly valve exercise, and a controlled restart.
- Record requested/effective mode, temperatures, `on_percent`, logical opening, both physical degree entities, `hvac_action`, active devices, boiler state, and the Zigbee2MQTT command timeline.
- Require closure consistent with the configured conversion when returning to a warm room, followed by attribute convergence after physical state feedback arrives. Do not require radio feedback synchronous with the HA service call.
- No unintended valve commands at constant mode, no commands during inhibition outside an authorized transaction, and correct recovery when inhibition ends.
- Stop the beta if unjustified heating persists, the final position contradicts the latest request, or inhibition is violated; preserve traces and roll back to stable.

## Alternatives Considered

| Option                                         | Advantage                                                                   | Drawback / recommendation                                                                                                                  |
| ---------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Keep the two stored modes                      | Local exception in the owning class; distinguishes calculation from sending | Reasonable option; revalidate concurrency, filters, and limitations before merging.                                                        |
| Force `update_states(force=True)` around sleep | Short, centralized expression of intent                                     | Force propagates into control/scheduler; the current dpercent filter does not check force. Not automatically an equivalent simplification. |
| Reset the cache to zero in OFF                 | Avoids a stale reopening after OFF in some cases                            | Does not fix all direct sleep transitions; insufficient on its own.                                                                        |
| Limit bypassing to sleep                       | Reduces timing changes outside sleep                                        | Must still handle sleep -> off -> heat and any resumption with a stale cache; requires a validated design, not an ad hoc adjustment.       |
| Have automations also check `on_percent > 0`   | Heat pump workaround already used by the reporter                           | Does not fix the valve; should not become a general solution for the project's boiler control.                                             |

## Scope and Decision Questions

**Proposed scope:** direct valve regulation, effective HVAC transitions, immediate recalculation and application when data is available, preservation of filtering outside transitions and of existing protections.

**Out of scope:** redesigning concurrency across the whole thermostat, changing TPI, introducing a new missing-temperature safety policy, other thermostat types, and changes to the HA environment. Any reproducible defect discovered in these areas must be assessed before expanding the scope.

Decisions needed:

1. Does the maintainer confirm the timing exception for all effective transitions, including automatic resumption outside sleep?
2. What behavior is acceptable when leaving sleep if a calculation is unavailable: preserve and document the existing policy, or address it in a separate change?
3. Who will supply beta traces and validate the boiler and recovery after restart/inhibition?

## Next Steps and Acceptance Gates

**Recommendation: retain the fix, defer merging.** The conflict and validation of its resolution are factual blockers. The limitations above are requests for evidence or clarification, not newly introduced regressions presented as demonstrated facts.

After explicit approval of this report, align the specification and technical design on scope and edge cases. Present the results and obtain a second explicit approval before development. No development agent has been launched.

Merge only after review of the final commit, successful priority checks and full suite, explicit behavioral decisions, and documented beta feedback meeting the criteria above.

## Sources

- [Issue #2111](https://github.com/jmcollin78/versatile_thermostat/issues/2111), [PR #2113](https://github.com/jmcollin78/versatile_thermostat/pull/2113), their descriptions, and accessible comments.
- [PR metadata](https://api.github.com/repos/jmcollin78/versatile_thermostat/pulls/2113), [diff](https://patch-diff.githubusercontent.com/raw/jmcollin78/versatile_thermostat/pull/2113.diff), [commit checks](https://api.github.com/repos/jmcollin78/versatile_thermostat/commits/f19d5aa8e6ec2c0dee45af71f632748b8aa4c1fd/check-runs).
- [Exact regulator version in the PR](https://github.com/jmcollin78/versatile_thermostat/blob/f19d5aa8e6ec2c0dee45af71f632748b8aa4c1fd/custom_components/versatile_thermostat/thermostat_climate_valve.py#L244).
- Local code: [update_states](../../custom_components/versatile_thermostat/base_thermostat.py#L1768), [over_climate control](../../custom_components/versatile_thermostat/thermostat_climate.py#L856), [proportional recalculation](../../custom_components/versatile_thermostat/thermostat_prop.py#L223), [TPI handler](../../custom_components/versatile_thermostat/prop_handler_tpi.py#L355).
- Local tests inspected: [minimum period](../../tests/test_overclimate_valve.py#L782), [inhibition with regulation](../../tests/test_inhibition.py#L942), [concurrency during inhibition exit](../../tests/test_inhibition.py#L1426).

**Verification limitations:** terminal/Python execution tools were unavailable during the review; no pytest run, dynamic reproducer, or hardware test was executed. Local links document the code inspected, not the guaranteed outcome of a future conflict resolution.