# Functional Specification — Issue #2109, item 1.1

## 1. Title and metadata

- **Name:** Under-counting of the `over_switch` energy sensor with multiple relays
- **Issue:** [#2109 — Energy sensor and power manager](https://github.com/jmcollin78/versatile_thermostat/issues/2109)
- **Covered item:** 1.1 only
- **Version:** 1.0
- **Status:** Proposed for approval before development
- **Date:** 2026-10-13
- **Owner:** Versatile Thermostat project
- **Validated review:** [issue-2109-review.md](../tech-docs/issue-2109-review.md)
- **Verified sources:** [thermostat_switch.py](../../custom_components/versatile_thermostat/thermostat_switch.py), [cycle_scheduler.py](../../custom_components/versatile_thermostat/cycle_scheduler.py), [feature_power_manager.py](../../custom_components/versatile_thermostat/feature_power_manager.py), [base-attributes.md](../fr/base-attributes.md), [test_power.py](../../tests/test_power.py)

## 2. Purpose and context

For an `over_switch` thermostat controlling multiple relays, the energy sensor currently under-counts the energy added per cycle by a factor equal to the number of relays. The validated review attributes this under-counting to division by `nb_underlying_entities`, although the cycle end invokes `incremente_energy()` only once and `mean_cycle_power` already represents the thermostat's total average power.

The purpose is to define the expected behavior so that each cycle increment reflects the configured total power, while preserving single-relay behavior and existing unit contracts.

## 3. Included scope and exclusions

### Included

- The energy increment calculation per cycle for `over_switch` when the thermostat has two or more relays.
- Removing division by the number of relays from that calculation.
- Updating the expectations of the existing energy test.
- Adding an integration test through the scheduler cycle end, covering multiple relays and one call per cycle.
- Preserving `device_power` as the total power when multiple devices are controlled.

### Excluded

- Issue #2109 item 1.2, concerning a possible burst of increments.
- Item 2, concerning power-manager reservations.
- Any retrospective correction of Home Assistant statistics or histories already recorded.
- The alternative of invoking the increment once per relay.
- Adding a compatibility option that preserves the under-counted calculation.
- Any code, configuration, dependency, or Home Assistant state change as part of this specification.

## 4. Actors and use cases

### Actors

- **User or administrator:** configures total equipment power and views the energy sensor.
- **`over_switch` thermostat:** maintains the energy counter from its cycle average power.
- **Cycle scheduler:** triggers the increment at the end of the master cycle.
- **Home Assistant:** exposes energy and its units to users and statistics.
- **Maintainer:** approves the specification and tests before development.

### Nominal use case — Multi-relay cycle increment

1. The user has configured `device_power` as the total power of the controlled relays.
2. The thermostat calculates `mean_cycle_power` from that total power and the cycle on percentage.
3. The scheduler reaches the master-cycle end and triggers one increment.
4. The thermostat adds the energy corresponding to total average power over the cycle duration.
5. The counter exposes a value in the energy unit corresponding to the configured power unit.

## 5. Terminology and units

- **Relay / underlying entity:** device controlled by the `over_switch` thermostat.
- **`nb_underlying_entities`:** number of controlled underlying entities.
- **`device_power`:** total configured power for all controlled devices when there is more than one.
- **`mean_cycle_power`:** thermostat average power during the cycle; it is calculated from `device_power` and the on percentage.
- **Cycle duration (`cycle_min`):** cycle duration in minutes.
- **Power:** W or kW according to the configured unit; the verified code normalizes the internal calculation to W.
- **Added energy:** Wh when power is expressed in W, or kWh when the configured/displayed power is expressed in kW.

The expected formula is:

`added_energy = mean_cycle_power × cycle_min / 60`

The formula shall not contain an additional division by `nb_underlying_entities`. Example from the review: for 4,300 W, five minutes, and three relays, the expected increment is approximately 358.3 Wh, versus 119.4 Wh with the erroneous division.

## 6. Functional requirements

- **FR-001 — Total power:** The system shall interpret `device_power` as the total power of all relays when multiple devices are controlled.
- **FR-002 — Multi-relay calculation:** For an `over_switch` with at least two relays, the system shall calculate each increment as `mean_cycle_power × cycle_min / 60`, without division by `nb_underlying_entities`.
- **FR-003 — One call per cycle:** The system shall produce one energy increment at the end of each scheduler master cycle.
- **FR-004 — Average power:** The system shall use `mean_cycle_power` as the thermostat's total average power, not as the power of a single relay.
- **FR-005 — Single relay:** With one relay, the expected functional behavior shall remain unchanged.
- **FR-006 — Units:** The system shall preserve consistency between W and Wh, and between kW and kWh, when exposing the calculation.
- **FR-007 — History:** The system shall not recalculate or change energy values already recorded by Home Assistant.
- **FR-008 — Scope non-regression:** The change shall not modify power-manager reservations or address issue items 1.2 and 2.

## 7. Business rules and calculation rules

- **BR-001 — Configured total:** When multiple relays are controlled, `device_power` is the total power and shall not be divided again during energy counting.
- **BR-002 — Cycle formula:** For an active cycle, added energy is total average power multiplied by the cycle duration expressed in hours.
- **BR-003 — Single call:** The master-cycle end is the increment trigger; a cycle shall not be counted once per relay.
- **BR-004 — Consistent units:** Power and energy shall remain in corresponding units; the duration in minutes is divided by 60 to obtain hours.
- **BR-005 — Off state:** If the thermostat is off or no cycle average power is available, this specification shall not infer a new positive increment.
- **BR-006 — History:** Past values remain unchanged; the correction applies only to new increments.

## 8. Compatibility, non-regression, and data

- A single-relay `over_switch` shall remain compatible with the behavior expected before this correction.
- Existing attributes and units shall remain usable by Home Assistant.
- The existing direct test that encodes division by two shall be aligned with the corrected formula; by itself it does not prove one call per cycle.
- An integration test shall pass through `_on_master_cycle_end()` and verify one increment for multiple relays.
- No data, configuration, or history migration is required.
- Already recorded Home Assistant statistics shall not be corrected retrospectively.

## 9. Acceptance criteria

- **AC-001:** With two or more relays and configured total power, one cycle adds `mean_cycle_power × cycle_min / 60` in the corresponding energy unit.
- **AC-002:** With 4,300 W, three relays, and a five-minute cycle, the increment is approximately 358.3 Wh and not 119.4 Wh.
- **AC-003:** A scenario through the scheduler cycle end confirms that one increment call is made per master cycle.
- **AC-004:** The calculation never divides cycle energy by `nb_underlying_entities`.
- **AC-005:** With one relay, functional results and units remain unchanged.
- **AC-006:** W values produce Wh values and kW values produce kWh values, without an incorrect factor of 1,000.
- **AC-007:** A cycle with no available average power or with the thermostat off does not add positive energy to the counter.
- **AC-008:** Existing Home Assistant history values are neither recalculated nor changed.
- **AC-009:** Power-manager reservation tests and behavior outside item 1.1 are not changed by this correction.

## 10. Explicitly out-of-scope behavior

- Handling a burst or multiple increment calls under item 1.2.
- Correcting reservations or load-shedding logic under item 2.
- Changing the call model to trigger one increment per relay.
- Rebuilding Home Assistant history and statistics.
- Changing the user's configured power or reinterpreting it as per-relay power.
- Modifying `over_climate` thermostats or other modes not concerned by item 1.1.

## 11. Risks and mitigation

| Risk                                                 | Severity / likelihood               | Planned treatment                                                               |
| ---------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------- |
| Higher new energy values for multi-relay thermostats | Medium / certain                    | Accept it as the expected correction and do not migrate history.                |
| Regression to one increment per relay                | Medium / low                        | Add the integration test asserting one call per cycle.                          |
| Confusion about configured total power               | Medium / medium                     | Preserve and verify the documentation stating that `device_power` is the total. |
| W/Wh or kW/kWh inconsistency                         | Medium / low                        | Verify units in tests and acceptance criteria.                                  |
| Security or privacy                                  | None / none according to the review | No impact identified; no additional treatment.                                  |

## 12. Proposed future enhancements

- Address item 1.2 separately after a dedicated decision and specification.
- Address item 2 on power-manager reservations separately.
- Strengthen cycle tests if other increment call paths appear.

## 13. Assumptions, open questions, and traceability

### Assumptions

- No other active path invokes `incremente_energy()` once per relay for `over_switch`; the integration test must confirm this assumption.
- `mean_cycle_power` remains the thermostat's total average power in the affected path.

### Open questions

- Must the specification and design be explicitly approved by the maintainer before any development, as required by the review?
- Should the integration test cover heating only, or also other already-supported `over_switch` states?

### Traceability

This specification is strictly aligned with the validated review [issue-2109-review.md](../tech-docs/issue-2109-review.md) and covers only item 1.1. The review is the source for the decision to remove the division, the formula, the numeric example, the exclusions, and the risks. The code and documentation files listed in the metadata were consulted to verify existing symbols and contracts. No development is included in this document.