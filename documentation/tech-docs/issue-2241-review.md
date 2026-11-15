# Issue #2241: switch repair timing

## Reference and scope

https://github.com/jmcollin78/versatile_thermostat/issues/2241

Updated on 2026-11-15: centralized architecture explicitly approved by the user.
Authorization is documentation only; development requires renewed user validation.
Historical report: VTherm 10.6.5, SmartPI 0.6.5, HA Core 2026.11.1, Shelly
relays, 30-minute cycle, 300-second keep-alive; repair warnings reportedly precede
HA state feedback by 0.08-0.3 s. No debug trace; introducing change unverified.

## Verified sources and facts

- Re-read locally: [underlyings.py](../../custom_components/versatile_thermostat/underlyings.py)
  and [feature_repair_incorrect_state_manager.py](../../custom_components/versatile_thermostat/feature_repair_incorrect_state_manager.py).
- Previous assessment recorded issue/owner comments, published 10.6.5 sources,
  heating-control call site, keep-alive documentation and targeted tests;
  these historical inputs were not re-fetched or re-executed for this update.
- Switch ON/OFF call HA directly, then update expected cycle state and rearm
  keep-alive; no command timestamp or temporal repair guard on that path.
- Climate/valve checks currently have 2 s guards; valve regulation inherits
  the valve check. The wrapper timestamps successful calls with `_thermostat.now`;
  blocked/failed wrapper calls do not timestamp, irrespective of their response.
- Opening then optional closing use the same valve-regulation object/wrapper;
  each accepted send updates its timestamp, independently of the associated climate.
- The manager iterates `all_underlying_entities`, warns on truthy check results
  and increments once per repaired cycle; otherwise it resets the global counter.
  Initial readiness uses a separate UTC clock and 30 s delay; pauses remain global.

## Assessment and approved architecture

Retain the issue. The reported race is supported by the code and observations.
Exact callbacks and physical application remain unproven; warnings are not acknowledgments.
The approved variant replaces the previous three-check temporal design only:
- Add dedicated `REPAIR_COMMAND_GRACE_SEC = 10` in `const.py`, imported by the manager.
- Add read-only `UnderlyingEntity.last_command_sent_datetime -> datetime`, exposing
  the existing private timestamp, initially UTC epoch, without persistence/migration.
- Before EVERY `await underlying.check_and_repair()`, the manager reads `_vtherm.now`
  and that object's public timestamp. If `now < last_sent + timedelta(seconds=10)`,
  `continue` without invoking the check or an attributable warning/attempt/increment.
  At `>= 10 s`, the existing check is eligible at the next control, not on a timer/SLA.
- Use `_vtherm.now` consistently with send timestamps from `_thermostat.now`;
  do not refactor the existing UTC ready-delay clock, 30 s initialization or pauses.
  Preserve accounting: skips alone reset outside pauses; skip+repair increments once.
- Remove climate/valve temporal repair guards; add none to switch checks. Direct checks
  retain type-specific comparisons/corrections and protections, including OFF,
  inversion/custom commands, SLEEP mapping, opening tolerance/thresholds; no setpoint repair.
- Timestamp direct switch ON/OFF immediately after successful `async_call`, before cycle
  update/rearming; preserve power-operation order, cancellation, logged `ServiceNotFound`
  and propagation of other errors. No wrapper substitution or error-handling redesign.
- Retain wrapper/`send_value_to_number` timestamping at successful sends, not high-level
  return values or scheduled callbacks. Blocking, failure and no send leave it unchanged;
  later hook/rearming errors do not erase success. For pairs, success/failure retains
  the first date, failure/success the second, two failures neither; no transaction/rollback.

## Related assessment: issue #1900 temperature resend

https://github.com/jmcollin78/versatile_thermostat/issues/1900 and its referenced
commit `6414480db9b84f7387ed5657141c8763ffeff5cf` were reviewed previously:
the reporter confirmed the delayed resend fixed the TRVZB/ZHA issue in 9.3.2.beta1.
Keep unconditional HEAT/COOL resend after 2 s, even after repair and with matching
setpoint, independent of repair eligibility/option; OFF cancels the pending callback.
Keep last-sent/regulation/target selection and existing initialization/inhibition protections.
Repair at t followed by accepted resend at t+2 s moves eligibility to t+12 s earliest;
a delayed callback restarts grace at the actual send. Fan spacing/reprogramming stays
`resend_delay_sec = 2`, with immediate send only when `now > last_sent + 2 s`.

## Tests, risks and next gate

The [bilingual specification](../specs/issue-2241-repair-delay.md) retains FR-001..005,
BR-001..005 and AC-001..010: same functional scope and acceptance coverage.
Adapt existing tests only after renewed user validation authorizing development:
- Manager boundaries `< 10`, `== 10`, `> 10 s`, four types, public-property mocks,
  mixed objects/dates and independent pair/climate clocks; assert skipped checks not called.
- Migrate old direct climate/valve 2 s guard tests to the manager; test all direct
  underlying checks without temporal protection, retaining consistency/OFF protections.
- Service success timestamps, failures without successful sends/blocking/non-sends unchanged,
  post-success errors retain the successful send's timestamp; all pair outcomes,
  repeated keep-alive renewed timestamps and accepted indefinite postponement.
- Climate repair plus #1900 callback, HEAT/COOL/matching setpoint, OFF cancellation,
  unchanged fan 2 s behavior; ready-delay UTC separate from mocked thermostat/send clocks.
- Preserve disabled/unknown/unavailable handling, pauses and counter reset/increment semantics.
  Manager repair warnings require a check reporting repair; other error logs remain unchanged.

Feasible and testable from the verified extension points; no identified blocker.
Accepted risks: feedback beyond 10 s, indefinite postponement by frequent accepted commands,
wall-clock adjustments and dependency on existing control/protections; no physical/SLA guarantee.
No algorithm, setpoint repair, scheduling, configuration, dependency or environment expansion.
Only these two documents were updated; no implementation, application tests or HA inspection.
Sources are targeted static reads and prior assessment; hardware trace/introducing commit remain
unverified. A subsequent editorial reread may flag divergences; development still needs new approval.