# Issue #2111 - Immediate Recalculation on HVAC Mode Changes

**Date:** 2026-10-18.
**Status:** documentary convergence reached; human approval required before development.
**Reference:** [issue #2111](https://github.com/jmcollin78/versatile_thermostat/issues/2111).

**Related documents:** [bilingual specification](issue-2111-specification.md), [bilingual design](issue-2111-design.md), [French report](issue-2111-review.md).

## Decision and Context

Address issue #2111 directly: force recalculation on an actual change of the effective HVAC mode while fully preserving the `dpercent` filter. Reuse the existing transition signal and force mechanisms, without adding stored last-calculated or last-sent modes.

This report replaces the earlier analysis and recommendations that conflict with this decision. In particular, the recommendation to bypass `dpercent` during a transition is withdrawn.

The maintainer states that small movements can cause Sonoff TRVZB devices to lose calibration. This hardware rationale is a maintainer-supplied constraint, not a measurement reproduced in this session. The filter is a protection, not merely a battery optimization.

## Verified Facts and Sources

- The issue reports a stale 100% opening during sleep transitions, with unjustified heating states and heat pump demand. Reported setup: VTherm 10.5.1, HA 2026.10.1, Sonoff TRVZB through Zigbee2MQTT, five-minute minimum period.
- The [maintainer's October 18 comment](https://github.com/jmcollin78/versatile_thermostat/issues/2111#issuecomment-6254039750) announces forced recalculation on HVAC mode changes.
- [update_states](../../custom_components/versatile_thermostat/base_thermostat.py#L1768) knows when the effective mode changes and calls recalculation followed by control. Forcing only the user service would miss automatic transitions and could force requests that cause no effective change.
- [recalculate](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L234) bypasses the period with `force=True`, but its `dpercent` filter does not depend on `force`: this separation must remain unchanged.
- [Regulated sending](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L308) has a separate timing gate. Control and the scheduler can also apply the position: inspect commands from the complete flow, not just a calculation call.
- No local execution or hardware validation was performed. Code findings are static; no test result from another implementation validates this new approach.

## Agreed Scope

Include only `over_climate` thermostats with direct valve regulation, and all their actual effective-mode changes, whether manual or automatic. Force recalculation while processing the transition, then allow application without waiting for the minimum period of the value actually retained by existing protections.

Outside transitions, preserve timing gates, filters, min/max conversions, deduplication, and pre-existing forced calls. Do not introduce a general new force behavior for other thermostat types.

Exclude any new missing-sensor policy, concurrency redesign, TPI formula or hardware-setting changes, new configuration, and HA environment changes.

## Mandatory Rules

1. Do not introduce any bypass of `dpercent`, even with `force=True` or when leaving sleep. Preserve the current comparisons, including their asymmetric boundaries: with a threshold of 5, a -5 change remains filtered whereas a +5 change does not, subject to the other filter conditions.
2. Preserve the existing exception for closing to 0% and the existing treatment of small openings. Do not replace the filter with rounding or a new comparison.
3. Preserve existing sleep semantics: logical opening of 100%, subject to hardware conversion. The current sleep path does not pass through the change filter in the TPI branch; this fix introduces no new exception.
4. Discriminating example: when leaving `sleep 100%`, if the calculation proposes 98% with a threshold of 5, retain 100% and do not command 98%. This intentional difference is not the timing-delay symptom being fixed.
5. Never send the raw TPI result if the regulator filtered it. Inhibition and other protections retain priority; forcing must not bypass them.
6. When calculation data is missing, preserve the current policy without promising a fresh opening or inventing automatic closure. Physical states are not synchronous acknowledgements of HA services.

## Relevance and Recommendation

**Retain this localized approach.** It uses an already-known transition, limits new internal state, and removes the timing wait without removing hardware protection. Simplicity is not proof of regression safety.

The design must explain immediate application of the retained value: forcing calculation alone does not prove that sending will not be delayed. Conversely, a forced control call must neither use a raw opening nor generalize cycle effects to other thermostats.

## Impacts and Risks

| Risk                                               | Potential severity | Likelihood / evidence                        | Mitigation                                                          |
| -------------------------------------------------- | ------------------ | -------------------------------------------- | ------------------------------------------------------------------- |
| Calibration loss if small movements are introduced | High               | Maintainer-supplied hardware constraint      | Unchanged filter and discriminating sleep-exit tests.               |
| Stale opening despite recalculation                | High               | Two separate timing gates in the code        | Verify application of the retained value through the complete flow. |
| Forced behavior extended to other thermostats      | High               | Shared transition method                     | Strict scope condition for direct over_climate valve regulation.    |
| Inhibition / safety violation                      | High               | Integration risk, not a demonstrated failure | Command-gate and automatic-transition tests.                        |
| Additional commands and battery consumption        | Medium             | Plausible, not quantified                    | Force only actual transitions; retain deduplication and dpercent.   |
| Concurrency, missing sensor, recovery              | Medium to high     | Pre-existing limitations, not reproduced     | Focused tests without redesign or a new policy.                     |

No new data exposure, migration, or dependency is expected. Document the timing exception and preservation of calibration protection. Battery cost depends on actual commands and movements, not software recalculation itself.

## Alternatives

- Force calculation only: a short change, but immediate application must be demonstrated through the complete flow.
- Force transition processing within the target scope: recommended, provided filters and protections remain intact; do not force all thermostats globally.
- Reset only the cache in OFF: insufficient for direct sleep transitions.
- Add stored calculation/sending modes or bypass dpercent: outside the selected approach.

## Validation and Next Steps

Before any release, verify sleep entry/exit, `sleep -> off -> heat`, cold-room restart, protected small changes, closure to 0%, exact dpercent boundaries, no new force for unchanged mode, return to normal timing, unchanged opening, multiple valves, and min/max settings. Include automatic transitions, COOL if supported, inhibition, recalibration, and missing sensors followed by recovery. Check excluded thermostat types and run the regression suite against the final implementation.

A targeted beta remains recommended, with Zigbee2MQTT commands, openings, heating and boiler states, calibration observations, and command timing. Distinguish an opening intentionally retained by dpercent from an opening made stale by a timing gate.

The maintainer authorized report corrections, specification, and design in the current conversation turn. Cross-review by both specialists confirms the same scope, coverage of requirements and acceptance criteria, no blocking documentary contradiction, and a technically feasible and testable solution. Existing force effects on the scheduler, callbacks, and learning still require the planned tests; documentary convergence does not validate an implementation.

New explicit approval is required before development. This report authorizes neither implementation nor publication.