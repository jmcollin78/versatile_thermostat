# Functional Specification — Issue #2084

## 1. Title and metadata

- **Name:** Preserve the user preset during restoration and central reload
- **Version:** 1.1
- **Status:** converged with the technical design — cycle 1
- **Date:** 2026-10-10
- **Owner:** Versatile Thermostat project
- **Issue:** [#2084 — Hidden Safety preset becomes the requested choice after restart](https://github.com/jmcollin78/versatile_thermostat/issues/2084)
- **Approved report:** [issue-2084-review.md](../tech-docs/issue-2084-review.md)
- **Scope:** separation between the user `requested_state.preset` and the hidden (`safety`/`power`) `current_state.preset` during startup and central reload, including the associated regression tests.
- **Analyzed sources:** [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py), [vtherm_preset.py](../../custom_components/versatile_thermostat/vtherm_preset.py), [state_manager.py](../../custom_components/versatile_thermostat/state_manager.py), [feature_safety_manager.py](../../custom_components/versatile_thermostat/feature_safety_manager.py), [vtherm_central_api.py](../../custom_components/versatile_thermostat/vtherm_central_api.py), [test_safety.py](../../tests/test_safety.py), [test_last_seen.py](../../tests/test_last_seen.py), and [test_state_manager.py](../../tests/test_state_manager.py).

## 2. Context and objectives

The `safety` and `power` presets are hidden presets used as temporary overrides of the current state. The requested preset represents the user's choice and must remain available as the fallback when the override disappears.

The approved report establishes that, after restoring a state in which safety was active, preset reapplication can copy `current_state.preset: safety` into `requested_state.preset`, although the user's choice was, for example, `comfort`. When safety is no longer active after startup, the thermostat may then remain indefinitely on the wrong preset. The same path is reachable during a central configuration reload.

The objective is to preserve this separation without changing TPI algorithms, thresholds, or persistence of the active safety state.

## 3. Actors and use cases

### Actors

- **User or automation:** selects a visible preset such as `comfort`.
- **VTherm:** restores states, initializes presets, and calculates the current state.
- **Safety or power manager:** applies a hidden override to the current state when its condition is active.
- **Central configuration:** triggers preset reinitialization for affected thermostats.
- **Test suite:** verifies restoration, startup, and reload invariants.

### Nominal use case — startup after active safety

1. Before restart, `requested_state.preset` is the user preset, for example `comfort`.
2. Active safety produces `current_state.preset: safety`.
3. The persisted state is restored.
4. After startup, safety is no longer active.
5. The system keeps `requested_state.preset: comfort` and recalculates `current_state.preset: comfort`.

### Nominal use case — central reload

1. A VTherm uses the central preset configuration.
2. A hidden override may be present in `current_state` without representing the user's choice.
3. Reload reinitializes presets.
4. The user's requested choice remains unchanged; the current state returns to that choice when the override is no longer active.

## 4. Functional requirements

- **FR-001 — State separation:** The system shall preserve `requested_state.preset` and `current_state.preset` independently during restoration and preset initialization.
- **FR-002 — User source:** The system shall treat a valid, currently configured visible preset in `requested_state.preset` as the user choice to preserve and reapply.
- **FR-003 — Hidden override:** The system shall not turn `current_state.preset` equal to `safety` or `power` into a durable requested choice.
- **FR-004 — Startup:** After restoring a state where `current_state.preset` is hidden and `requested_state.preset` is visible, the system shall retain the visible requested preset.
- **FR-005 — Post-startup recalculation:** When safety or power is no longer active, the system shall allow `current_state.preset` to return to the retained requested preset.
- **FR-006 — Central reload:** Preset initialization caused by central configuration shall obey the same invariants as startup.
- **FR-007 — Generic coverage:** The protection shall cover `HIDDEN_PRESETS`, including `safety` and `power`, rather than being an ad hoc `safety`-only correction.
- **FR-008 — Existing transitions:** An actually active override shall still be allowed to appear in `current_state.preset` without overwriting the user preset in `requested_state.preset`.
- **FR-009 — Regression tests:** The test suite shall cover restoration after active safety, return to the user preset, central reload, and `power` when the common hidden-preset path is used.

## 5. Business rules and invariants

- **BR-001 — Role of `requested_state`:** `requested_state.preset` represents the last valid, visible user preset choice.
- **BR-002 — Role of `current_state`:** `current_state.preset` represents the currently effective preset, including a temporary hidden override.
- **BR-003 — No contamination:** A hidden `current_state.preset` shall never contaminate `requested_state.preset` during startup or reload.
- **BR-004 — Override priority:** While the safety or power condition is active, the override may remain visible in `current_state.preset`, while `requested_state.preset` remains the user choice.
- **BR-005 — Return:** When the override is no longer active, `current_state.preset` shall be calculated from the retained requested preset.
- **BR-006 — Generalization:** The same invariants shall apply to all `HIDDEN_PRESETS` values handled by the common path.
- **BR-007 — Already contaminated history:** If no reliable user preset is available because both persisted states are hidden, the system shall neither automatically repair nor silently invent a user choice; it shall preserve the available history and require an explicit command to restore a visible preset.

## 6. Functional constraints and risks

### Constraints

- The scope shall remain limited to startup, restoration, central reload, and the associated regression tests.
- This specification shall not redefine TPI algorithms, thresholds, safety delays, public preset commands, or persistence of the active safety state.
- Existing safety-entry and safety-exit behavior during one runtime shall be preserved.
- No new access, secret, network call, personal-data processing, or user setting shall be introduced.

### Risks

| Risk                                                             | Severity | Mitigation                                                                        |
| ---------------------------------------------------------------- | -------: | --------------------------------------------------------------------------------- |
| The user preset remains replaced by `safety` after restart.      |     High | Restoration test with safety inactive after resume and assertions on both states. |
| A `safety` fix leaves the same defect for `power`.               |   Medium | Cover `HIDDEN_PRESETS` and add a `power` scenario.                                |
| Reapplying the visible preset changes a legitimate startup case. |   Medium | Test a restored visible preset and central reload.                                |
| Central reload diverges from startup behavior.                   |   Medium | Separate scenario and test for central initialization.                            |
| Already contaminated history cannot recover the user choice.     |   Medium | Document a recovery policy; do not present an invented value as the user choice.  |

## 7. Acceptance criteria

- **AC-001 — Preservation before restart:** Given active safety, `current_state.preset` may be `safety`, but `requested_state.preset` retains the user preset `comfort`.
- **AC-002 — Restore with safety inactive:** Given persisted `current_state.preset: safety` and `requested_state.preset: comfort`, after startup and safety deactivation, `requested_state.preset` is still `comfort` and `current_state.preset` returns to `comfort` at the first applicable calculation.
- **AC-003 — No durable hidden effect:** No startup or preset-initialization call shall write `safety` or `power` into `requested_state.preset` solely because that value was in `current_state.preset`.
- **AC-004 — Central reload:** With the same state separation, reloading central configuration retains the user preset and allows the current state to return to it when the override is inactive.
- **AC-005 — Safety still active:** If safety is genuinely active after initialization, `current_state.preset` may remain `safety` while `requested_state.preset` remains the requested visible preset.
- **AC-006 — `power` regression:** The equivalent scenario with `power` observes the same separation when `power` belongs to `HIDDEN_PRESETS`.
- **AC-007 — Existing transitions:** Existing tests for safety activation and exit during one runtime continue to pass without a contract change.
- **AC-008 — Automated tests:** Regression tests cover AC-002, AC-004, and AC-006 and fail if a hidden preset is copied into `requested_state`.
- **AC-009 — Preserved out-of-scope behavior:** No criterion requires a change to TPI algorithms, user configuration, or the Home Assistant environment.
- **AC-010 — Irrecoverable history:** When both `current_state.preset` and `requested_state.preset` are hidden, initialization shall neither automatically select or invent a visible preset nor reapply a hidden preset; a later explicit command shall remain the recovery mechanism.

## 8. Functions not covered

- Changes to TPI algorithms, thresholds, timers, or safety strategy.
- Restoration of the active safety state itself in `feature_safety_manager`.
- Adding a preset, user setting, migration, or workaround automation.
- General changes to public preset commands beyond protection against contamination by a hidden preset.
- Fixing unrelated startup or reload issues.
- Changing product code, configuration, dependencies, or Home Assistant state as part of this specification.

## 9. Proposed future enhancements

- Add an explicit diagnostic when persisted history contains only hidden presets and no reliable user choice can be recovered.
- Document recovery rules for already contaminated historical states.
- Extend tests to future values added to `HIDDEN_PRESETS`.
- Add controlled logging or telemetry to ease restoration diagnosis if an operational need is confirmed.

## 10. Assumptions, open questions, and traceability

### Established facts

- `safety` and `power` are values in `HIDDEN_PRESETS`.
- Safety affects the current state, and normal calculation uses the requested preset when the override is absent.
- Restoration reads `current_state` and `requested_state` separately.
- The current initialization path reapplies a preset from the current state and can therefore contaminate the requested state.
- `init_presets()` is also called when central presets are reinitialized.
- Existing tests cover transitions during one runtime, but not the persisted-state scenario followed by restart or the central reload described here.

### Retained assumptions

- A valid, currently configured visible `requested_state.preset` is the source of truth to preserve and reapply.
- A hidden override is never a durable user choice.
- Existing test utilities can simulate a sufficiently complete restoration without changing the Home Assistant environment.

### Open questions

- **Q-001 — Resolved in cycle 1:** If both `current_state.preset` and `requested_state.preset` are `safety` or `power`, no automatic repair or inference shall be performed; an explicit command is required.
- **Q-002 — Non-blocking:** Should a log be produced when restoration ignores a hidden preset?
- **Q-003 — Non-blocking:** Can central reload occur during a `power` override in supported scenarios?

### Traceability

The [approved issue #2084 report](../tech-docs/issue-2084-review.md) is the normative source for scope. Verified facts and symbols are `BaseThermostat.async_startup`, `BaseThermostat.get_my_previous_state`, `BaseThermostat.init_presets`, `BaseThermostat.async_set_preset_mode_internal`, `StateManager.calculate_current_preset`, `FeatureSafetyManager`, `HIDDEN_PRESETS`, and `init_vtherm_preset_with_central`. Related tests are in [test_safety.py](../../tests/test_safety.py), [test_last_seen.py](../../tests/test_last_seen.py), and [test_state_manager.py](../../tests/test_state_manager.py).
