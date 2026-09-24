# Functional Specification — Joint resolution of issues #2069 and #2070

---

## Part 1 — French version

### 1. Title and metadata

| Field | Value |
| --- | --- |
| Name | Fixes for the `max_closing_degree` floor and valve activity detection (`over_valve` and `over_climate` valve regulation) |
| Identifier | SPEC-2069-2070 |
| Version | 1.1 |
| Status | Converged with the DESIGN-2069-2070 v1.0 design |
| Date | 2026-09-24 (v1.1: QC-001/QC-002 closure) |
| Owner | versatile_thermostat maintainer |
| Sources analyzed | `documentation/tech-docs/issue-2069-2070.md`, `documentation/tech-docs/issue-2069-2070-en.md`, `documentation/tech-docs/issue-2069-2070-design.md` (DESIGN-2069-2070 v1.0), `custom_components/versatile_thermostat/opening_degree_algorithm.py` (`OpeningClosingDegreeCalculation`), `custom_components/versatile_thermostat/underlyings.py` (`UnderlyingValve`, `UnderlyingValveRegulation`), `custom_components/versatile_thermostat/config_schema.py` (reviewed, not reread line by line), GitHub issues #2069 (PR) and #2070 |

### 2. Context and objectives

Two distinct defects, to be fixed together on the #2070 resolution branch:

1. **Issue #2069 (PR closed without merge, fixes to be reinstated)**: for an `over_valve` VTherm, the effective shutdown command is the `100 - max_closing_degree` floor. However, the `should_device_be_active` and `is_device_active` predicates of `UnderlyingValve` compare the effective command only with the minimum of the `number` entity (`self._min_open`). A valve held at the floor, and therefore with no heating demand, is consequently declared active. Likewise, during `check_initial_state`, a valve with no demand is closed to the entity minimum (`self._min_open`) rather than to the effective floor.
2. **Issue #2070**: in `OpeningClosingDegreeCalculation.calculate_opening_closing_degree`, the interpolation branch (raw demand `>= opening_threshold`) starts at `min_opening_degree`, without a guaranteed floor. If `min_opening_degree < 100 - max_closing_degree`, crossing the threshold causes the command to change from `100 - max_closing_degree` (below-threshold branch) to a value below the floor: a break in monotonicity and a command that may fall below `100 - max_closing_degree`.

**Expected value**: consistency between the state published by VTherm (`hvac_action`, list of active underlying devices, central boiler) and the actual heating demand; physically guaranteed behavior across the entire demand range.

**Functional scope**: `over_valve` VTherms, and `over_climate` VTherms with valve regulation for the parts governed by the shared `OpeningClosingDegreeCalculation` algorithm.

### 3. Actors and use cases

| Actor | Use case |
| --- | --- |
| End user | Configures an `over_valve` VTherm with `opening_threshold_degree`, `max_opening_degrees` (and optionally `min_opening_degrees`, `max_closing_degree`); observes `hvac_action` and the valve position |
| VTherm (`over_valve`) | Calculates the effective valve command from the raw TPI demand and determines its activity state |
| VTherm (`over_climate` + valve regulation) | Uses the same algorithm to send `opening_degree` / `closing_degree` to dedicated entities |
| Central boiler / state consumers | Consume `is_device_active` / `hvac_action` to decide activation |
| Physical valve / `number` entity | Receives the effective command and reports its state |

Nominal `over_valve` flow: the raw TPI demand is calculated → `set_valve_open_percent` converts the demand into a command through `_get_controlled_percent` → the command is sent and constrained to the entity limits → activity predicates and `hvac_action` are published consistently with the raw demand.

### 4. Functional requirements

- **FR-001** — The system shall guarantee that, for any raw TPI demand from 0 to 100%, the effective opening command sent to the valve remains greater than or equal to the `100 - max_closing_degree` floor, after applying the limits of the underlying entity, for `over_valve`.
- **FR-002** — The system shall guarantee that the raw demand → effective command conversion function is monotonically non-decreasing over [0; 100], including when crossing `opening_threshold_degree`.
- **FR-003** — The system shall determine `over_valve` valve activity using a single scale **for each predicate**: (a) *desired* activity (`should_device_be_active`) shall be evaluated by comparing the raw TPI demand to `opening_threshold_degree`; (b) *observed* activity (`is_device_active`) shall be evaluated by comparing the actual physical valve opening to the effective physical floor `max(100 - max_closing_degree, entity minimum)`. The system shall never compare `opening_threshold_degree` (raw demand scale) to the effective command or to the valve state (physical scale). *(QC-001 decision ratified, option 1 — see DESIGN-2069-2070 §5.3, decision D1.)*
- **FR-004** — The system shall declare an `over_valve` valve with no heating demand (zero raw demand) inactive even if its effective command (at the floor) is greater than the minimum of the `number` entity. The stored raw demand value shall be reset to zero when stopped (`turn_off`) and when closed at startup, so that the activity predicates remain consistent with the absence of demand. The corresponding published state (`hvac_action`) shall be consistent with this inactivity.
- **FR-005** — The system shall declare an `over_valve` valve receiving raw demand greater than or equal to `opening_threshold_degree` (and strictly positive) active, including in the valid case `opening_threshold_degree > max_opening_degrees` with raw demand of 100%.
- **FR-006** — During `check_initial_state` (startup or reload) of an `over_valve` VTherm, the system shall return a valve with no demand to the effective `100 - max_closing_degree` floor (constrained to the entity limits), rather than systematically to the minimum of the `number` entity.
- **FR-007** — Requirements FR-001, FR-002 and FR-003 shall also apply to the `over_climate` VTherm with valve regulation for the part governed by the shared `OpeningClosingDegreeCalculation` algorithm (`opening_degree` and `closing_degree` commands).
- **FR-008** — The system shall preserve compatibility with default and existing configurations: no combination currently accepted by the configuration flow and schema (notably `max_opening_degrees < opening_threshold_degree`, `max_closing_degree = 100`) shall be rejected or experience degraded behavior outside the targeted fixes.
- **FR-009** — User documentation of the behavior (floor, activity detection, monotonicity) shall be published equivalently in the five localized guides (`en`, `fr`, `cs`, `de`, `pl` — `documentation/*/over-valve.md`) **in the same release as the fix**. *(QC-002 decision ratified — see DESIGN-2069-2070 §5.5, decision D2.)*

### 5. Business rules

- **BR-001** — For `over_valve`: a valve is considered active if and only if the raw TPI demand is `> 0` and `>= opening_threshold_degree` (current algorithm semantics). Exceptions: zero raw demand → always inactive; unknown raw demand (before the first cycle) → inactive; configurations with neither `opening_threshold_degree` nor `min/max_opening_degrees` configured (default configurations) → existing behavior (comparison of the effective command with the entity minimum) is preserved. Priority: high.
- **BR-002** — Effective floor: for any demand, the effective command `>= max(100 - max_closing_degree, entity minimum)` — the algorithmic floor and the entity lower limit are applied together, without either cancelling the other. Priority: high.
- **BR-003** — Valid case `opening_threshold_degree > max_opening_degrees` with raw demand of 100%: the effective command is `max_opening_degrees` (the configured maximum, constrained to the entity maximum); the state shall be `heating` / underlying device active. Priority: high.
- **BR-004** — On shutdown or with no demand (`turn_off`, `check_initial_state`), the command of an `over_valve` valve is the image of the floor: conversion of demand 0 through the same algorithm as the normal command (consistent with `turn_off` calling `_get_controlled_percent(0)`), and the stored raw demand is reset to zero in the same operation. Priority: medium.
- **BR-005** — For `UnderlyingValveRegulation` (`over_climate` valve regulation): its already overridden activity predicates (comparison of the actual state with the `100 - max_closing_degree` floor for `is_device_active`, comparison of demand with `opening_threshold` for `should_device_be_active`) shall not be changed as part of #2069; only the shared #2070 algorithmic fix applies to it. Priority: medium.

### 6. Functional constraints

- No change to `UnderlyingValveRegulation` is imposed by this specification, unless the implementation of FR-007 requires it to preserve the floor of `opening_degree` / `closing_degree` commands.
- No new configuration validation is required; adding validation `max_opening_degrees >= opening_threshold_degree` is explicitly excluded (alternative rejected by the review) as long as the algorithmic fix preserves existing configurations.
- The fix shall remain compatible with the physical limits of the `number` entity (`min`/`max` of the entity state, applied by `clamp_sent_value`).
- Localized documentation: the repository publishes guides in 5 languages; any documented behavior change shall be propagated to them (constraint inherited from specification #1348).

### 7. Acceptance criteria

#### CA-A — Guaranteed floor (#2070, FR-001, FR-002, BR-002)

| # | Raw demand | Parameters | Expected effective command (`over_valve`) |
| --- | --- | --- |
| A1 | 0 | defaults (`max_closing_degree=100`) floor 0 | 0 |
| A2 | 50 | `max_closing_degree=60` (floor 40), `min_opening_degree=10`, `max_opening_degree=100`, `opening_threshold=30` | ≥ 40 |
| A3 | 35 | same parameters as A2 (above threshold): interpolation starts from `min_opening_degree=10` | ≥ 40 (fixed: interpolation shall be constrained to the floor) |
| A4 | 100 | same parameters as A2 | 100 |
| A5 | 100 | `opening_threshold_degree=60`, `max_opening_degrees=50`, `max_closing_degree=100` | 50, `heating` state, underlying device active (BR-003) |

Moving from demand 29 to 31 (threshold 30) in A2 shall never decrease the effective command (FR-002 monotonicity).

#### CA-B — Activity detection (`over_valve`, #2069, FR-003, FR-004, FR-005, BR-001)

| # | Situation | Expected `hvac_action` | Valve listed as active |
| --- | --- | --- | --- |
| B1 | Raw demand 0, valve at floor 40 (greater than entity min 0) | `idle` or `off` (consistent with no demand) | No |
| B2 | Raw demand 100, `opening_threshold_degree=60 > max_opening_degrees=50`, valve at 50 | `heating` | Yes |
| B3 | Raw demand 25, `opening_threshold_degree=30`, valve at the floor | `idle` / inactive | No |
| B4 | Raw demand 30 (threshold equality, > 0) | active | Yes |

#### CA-C — `check_initial_state` (`over_valve`, FR-006, BR-004)

- C1: `over_valve` VTherm with no demand, valve open at 60, effective floor 40, entity min 0 → after `check_initial_state`, the valve is at 40 (floor), not 0.
- C2: VTherm with actual demand, valve closed to the floor → `check_initial_state` shall return the command corresponding to the demand (existing catch-up).

#### CA-D — `over_climate` valve regulation (FR-007)

- D1: with A2 parameters, any demand sent through `UnderlyingValveRegulation.send_percent_open` produces an `opening_degree >= 40`; `closing_degree` is the expected complement to 100.
- D2: no behavior change to `UnderlyingValveRegulation` predicates for configurations and demands not covered by #2070 (existing tests unchanged).

#### CA-E — Compatibility and documentation (FR-008, FR-009)

- E1: existing tests in `tests/test_valve.py`, `tests/test_check_initial_state.py`, `tests/test_overclimate_valve.py` unrelated to the fixed defects remain valid apart from explicitly corrected expectations.
- E2: the five `over-valve.md` guides (`en`, `fr`, `cs`, `de`, `pl`) contain the same translated behavior paragraph, delivered in the same PR as the fix (QC-002 decision ratified).
- E3 (new, tracking compatibility guard D3): for an `over_valve` configuration with neither `opening_threshold_degree` nor `min/max_opening_degrees` configured, activity predicates retain prior behavior (no regression of default configurations).

### 8. Out-of-scope functions

- Any change to `UnderlyingValveRegulation` beyond what FR-007 requires (predicates, `turn_off`), justified by the exclusion established during the review of PR #2069.
- New configuration validation prohibiting `max_opening_degrees < opening_threshold_degree` (alternative rejected on its own).
- General overhaul of the TPI algorithm or other VTherm types (`over_switch`, `over_climate` without a valve).
- API or user configuration changes.

### 9. Proposed future enhancements

- Addition of a non-blocking warning in the configuration flow when `max_opening_degrees < opening_threshold_degree` or `max_opening_degrees < 100 - max_closing_degree` — depends on QC-003 and validation policy.
- Exposure of raw TPI demand as an attribute/diagnostic to facilitate observation of the reference scale.

### 10. Assumptions, open questions, and traceability

**Established facts (verified in the code):**
- `OpeningClosingDegreeCalculation.calculate_opening_closing_degree` (`opening_degree_algorithm.py`, lines ~44-74): below the threshold, output `100 - max_closing_degree`; above the threshold, interpolation from `min_opening_degree` to `max_opening_degree` — without a floor in the interpolation branch (cause of defect #2070).
- `UnderlyingValve.should_device_be_active` / `is_device_active` (`underlyings.py`, lines ~1285-1299): comparison with `self._min_open` only, without accounting for the floor.
- `UnderlyingValve.check_initial_state`: closure through `send_percent_open(fixed_value=self._min_open)`.
- `UnderlyingValve.turn_off`: `self._percent_open = self._get_controlled_percent(0)` — consistency reference for FR-006.
- `UnderlyingValveRegulation` overrides `_get_controlled_percent` (raw identity) and `send_percent_open` (conversion at sending time); its `is_device_active` (comparison with the `100 - max_closing_degree` floor) and `should_device_be_active` (comparison of `_percent_open`, raw value, with `opening_threshold`) predicates already each use a consistent scale.
- `config_schema.py`: `opening_threshold_degree` and `max_opening_degrees` are validated independently (issue-2069-2070 review; not reread line by line as part of this specification).

**Assumptions (confirmed by review):**
- `opening_threshold_degree` is interpreted on the raw TPI demand (algorithm semantics).
- The A5 counterexample combination is accepted by the UI; YAML handling remains to be verified during development if a fix touches validations.

**Decisions made:**
- #2069 and #2070 are fixed together on the #2070 resolution branch; PR #2069 is closed without merge and its fixes are reinstated.
- **QC-001 (resolved — DESIGN-2069-2070 v1.0, decision D1)**: a single scale *per predicate*. Desired activity (`should_device_be_active`) is evaluated on raw TPI demand compared to `opening_threshold_degree`; observed activity (`is_device_active`) is evaluated on actual physical opening compared to the effective physical floor `max(100 - max_closing_degree, entity minimum)`. Alternative 2 (converting the threshold to a physical threshold per valve) is discarded: it would require duplicating the conversion formula (including entity clamping) for a threshold that is never sent, with a risk of divergence between sending and comparison. FR-003, FR-004 and BR-001 reflect this decision; BR-001 incorporates the compatibility guard exceptions (default configurations, unknown demand).
- **QC-002 (resolved — DESIGN-2069-2070 v1.0, decision D2)**: the five localized documentations (`en`, `fr`, `cs`, `de`, `pl`) are delivered in the same PR as the fix, in order to avoid a documentation inconsistency window between published versions. FR-009 and CA-E2 reflect this decision.

**Open questions (non-blocking for development):**
- **QC-003 (new, inherited from the design — DESIGN-2069-2070 QO-1)**: in the degenerate case where `max_opening_degrees < 100 - max_closing_degree` (the algorithmic floor exceeds the configured maximum), clamping to the floor may produce a command greater than `max_opening_degree`; clamping to the limits of the `number` entity remains the physical arbiter. This case, accepted by the current configuration flow, shall be observed during implementation; the possible addition of a non-blocking warning in the configuration flow remains a future enhancement (section 9).

**Convergence traceability (v1.1):** this v1.1 specification and DESIGN-2069-2070 v1.0 cover the same scope (`over_valve` + shared `OpeningClosingDegreeCalculation` algorithm for `over_climate` valve regulation); all requirements FR-001 to FR-009, rules BR-001 to BR-005 and criteria CA-A to CA-E are covered by the design (DESIGN §11 traceability matrix); no contradiction between the two documents was identified during the convergence cycle; the two initial questions (QC-001, QC-002) are closed and the remaining questions (QC-003/QO) are declared non-blocking.

### 11. Version history

- Version 1.1 (2026-09-24) — convergence cycle with the design: QC-001 closed (option 1, decision D1) and reflected in FR-003/FR-004/BR-001/BR-004; QC-002 closed (decision D2) and reflected in FR-009/CA-E2; FR-003 clarified as a single scale *per predicate*; compatibility guard for default configurations tracked by BR-001 and the new CA-E3 criterion; QC-003 question created (degenerate case `max_opening_degrees < 100 - max_closing_degree`, non-blocking). No requirement removed or weakened.
- Version 1.0 (2026-09-24) — initial creation.