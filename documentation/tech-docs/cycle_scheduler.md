# CycleScheduler — Technical Documentation

## 1. Problem Statement

### 1.1 Previous Architecture

Each `UnderlyingSwitch` independently managed its own ON/OFF cycle:

```
start_cycle() → _turn_on_later() → _turn_off_later() → _turn_on_later() → ...
```

A fixed initial delay (`initial_delay_sec = idx * delta_cycle`) was applied at startup to stagger the underlyings. After the first cycle, each underlying looped independently with no further coordination.

For valves, `UnderlyingValve` handled its own `set_valve_open_percent()` call directly inside a cycle method.

### 1.2 Problems

| #   | Problem                     | Description                                                                                                                        |
| --- | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Temporal drift**          | Cycles of multiple underlyings progressively desynchronized from the master thermostat cycle.                                      |
| 2   | **SmartPI incompatibility** | SmartPI computes a single `on_percent` for one global cycle. Independent sub-cycles per underlying made power feedback incoherent. |
| 3   | **False power feedback**    | `update_realized_power` did not match physical reality because underlyings were not synchronized to the master cycle.              |
| 4   | **Static initial delay**    | `initial_delay_sec` was computed once and never adapted to the actual `on_percent` at each cycle.                                  |
| 5   | **Scattered logic**         | Cycle management was duplicated across `UnderlyingSwitch`, `UnderlyingValve`, and `UnderlyingValveRegulation`.                     |

### 1.3 Illustration (2 heaters, 10-minute cycle)

**Before** — independent cycles with fixed initial delay:
```
R1: |==ON==|----OFF----|==ON==|----OFF----|==ON==|----OFF----|
R2:      |==ON==|----OFF----|==ON==|----OFF----|==ON==|----OFF----|
    ^                   ^                   ^
    Master cycle 1      Master cycle 2      Master cycle 3
    (R2 offset)         (R1 and R2 already  (drift increases)
                         desynchronized)
```

After a few cycles, R1 and R2 drift and no longer align with the master cycle.

---

## 2. Solution: Centralized CycleScheduler

### 2.1 Principle

A single `CycleScheduler` per thermostat orchestrates all underlyings within a shared master cycle window. It replaces the per-underlying cycle logic for both switches and valves.

```
BEFORE:
  Handler → for each underlying: underlying.start_cycle(on_time, off_time)
             (each underlying loops independently)

AFTER:
  Handler → cycle_scheduler.start_cycle(hvac_mode, on_percent, force)
             (scheduler computes timing internally and orchestrates all underlyings)
```

### 2.2 Architecture Diagram

```
+------------------------------------------+
|           ThermostatProp                  |
|                                           |
|  +--------------------+                  |
|  | AlgoHandler        |                  |
|  | (TPI / SmartPI)    |                  |
|  |                    |                  |
|  | control_heating()  |                  |
|  |   → on_percent     |                  |
|  +--------+-----------+                  |
|           |                               |
|           v                               |
|  +--------+---------------------------+  |
|  | CycleScheduler                     |  |
|  |   cycle_scheduler.py               |  |
|  |   + cycle_tick_logic.py            |  |
|  |                                    |  |
|  | start_cycle(hvac_mode, on_percent) |  |
|  |   _init_cycle() → tick → tick → … |  |
|  |   _on_master_cycle_end() → e_eff  |  |
|  |                                    |  |
|  +--+------+------+------------------+  |
|     |      |      |                      |
|     v      v      v                      |
|   R1.on  R2.on  R3.on                   |
|   R1.off R2.off R3.off                   |
|                                           |
|  Underlyings (turn_on/turn_off only)     |
+------------------------------------------+
```

### 2.3 Two-File Separation

| File                  | Role                                                                                         |
| --------------------- | -------------------------------------------------------------------------------------------- |
| `cycle_scheduler.py`  | Orchestration (HA timers, callbacks, master cycle management, thermostat integration)         |
| `cycle_tick_logic.py` | Pure logic (offset computation, target state, need_on/need_off, e_eff) — no HA dependency    |

---

## 3. Operating Modes

### 3.1 Switch Mode (Event-Driven Tick Scheduling)

For `UnderlyingSwitch` entities, the scheduler uses an **event-driven tick** approach:
- Computes circular offsets to distribute underlying activations evenly across the cycle.
- At each tick, evaluates the theoretical state of each underlying and applies minimum duration constraints.
- Schedules the next tick via `async_call_later` at the time of the next expected state change.
- Schedules `_on_master_cycle_end` at `t = cycle_duration_sec`.
- At cycle end, computes `e_eff`, increments energy, and restarts with the same parameters.

### 3.2 Valve Mode (Passthrough)

For `UnderlyingValve` and `UnderlyingValveRegulation` entities, no timer scheduling is needed:
- `_start_cycle_valve()` directly calls `set_valve_open_percent()` on each underlying.
- No master cycle repeat is scheduled — the thermostat's `async_track_time_interval` drives periodic re-evaluation.
- This unifies valve cycle handling under the same `start_cycle()` API.

Mode detection is automatic at construction time via `_detect_valve_mode()`, which inspects the `entity_type` of the first underlying.

---

## 4. `calculate_cycle_times()` — Timing Constraint Function

This module-level function (defined in `cycle_scheduler.py`) converts `on_percent` to `on_time_sec` / `off_time_sec` while enforcing equipment-protection constraints.

```python
def calculate_cycle_times(
    on_percent: float,           # fraction 0.0–1.0
    cycle_min: int,              # cycle duration in minutes
    minimal_activation_delay: int = 0,    # minimum ON time (seconds)
    minimal_deactivation_delay: int = 0,  # minimum OFF time (seconds)
) -> tuple[int, int, bool]:
    # returns (on_time_sec, off_time_sec, forced_by_timing)
```

**Constraint rules:**

| Condition                              | Effect                                          |
| -------------------------------------- | ----------------------------------------------- |
| `0 < on_time < min_activation_delay`  | `on_time` forced to 0 (too short to be useful)  |
| `off_time < min_deactivation_delay`   | `on_time` forced to `cycle_sec` (stays full ON) |
| `forced_by_timing = True`             | Handlers use this to update `realized_power`    |

This function is also called directly by handlers (TPI, SmartPI) to compute `realized_percent` for algorithm feedback — independently of the scheduler's internal computation.

---

## 5. Circular Offset Computation Algorithm

### 5.1 Principle

For switch mode, the scheduler distributes cycle start times of each underlying evenly across the cycle duration using **circular offsets**. The offset determines the cycle start shift for each underlying.

```python
offset = (cycle_duration / n) * index
```

Edge case:
- `n <= 1`: returns `[0.0]`

### 5.2 Examples

**5 underlyings, 5-minute cycle (300s):**

| Underlying | Index | Offset                |
| ---------- | ----- | --------------------- |
| R1         | 0     | (300 / 5) × 0 = 0s   |
| R2         | 1     | (300 / 5) × 1 = 60s  |
| R3         | 2     | (300 / 5) × 2 = 120s |
| R4         | 3     | (300 / 5) × 3 = 180s |
| R5         | 4     | (300 / 5) × 4 = 240s |

**2 underlyings, 600s cycle:**

| Underlying | Index | Offset                 |
| ---------- | ----- | ---------------------- |
| R1         | 0     | (600 / 2) × 0 = 0s    |
| R2         | 1     | (600 / 2) × 1 = 300s  |

Offsets are independent of `on_percent`. The distribution is fixed and circular — each underlying starts its activation at a regularly spaced point in the cycle, with wrap-around to the beginning of the cycle if `on_t + on_time` exceeds the cycle duration.

---

## 6. Cycle Initialization (`_init_cycle`)

### 6.1 Principle

This step occurs once per cycle, at startup. It resets the states of each underlying and the global penalty.

### 6.2 Initialized Variables

**Global:**
- `penalty = 0.0` — counter of heating time added or removed for the `e_eff` computation at cycle end.

**Per underlying (`UnderlyingCycleState`):**

| Variable  | Formula                                        | Description                                        |
| --------- | ---------------------------------------------- | -------------------------------------------------- |
| `on_t`    | `offset`                                       | Time at which the underlying should turn on        |
| `on_time` | `cycle_duration × on_percent`                  | Operating duration of the underlying               |
| `off_t`   | `(on_t + on_time) % cycle_duration`            | Time at which the underlying should turn off       |

```python
on_t = offset
on_time = cycle_duration_sec * on_percent
off_t = (on_t + on_time) % cycle_duration_sec
```

### 6.3 Circular Wrap-Around

When `on_t + on_time > cycle_duration`, `off_t` wraps back to the beginning of the cycle thanks to the modulo. This creates an activation that "wraps" around the end and beginning of the cycle.

**Example** — 2 underlyings, 600s cycle, on_percent = 60% (on_time = 360s):

| Underlying | offset | on_t | on_time | off_t              | ON period            |
| ---------- | ------ | ---- | ------- | ------------------ | -------------------- |
| R1         | 0s     | 0s   | 360s    | 360s               | 0–360s               |
| R2         | 300s   | 300s | 360s    | (300+360)%600=60s  | 300–600s then 0–60s  |

### 6.4 Sequencing

After initialization, the first tick is executed immediately (`_is_initial=True`). Initialization is re-executed after `cycle_duration` seconds or after a power change with `force=True`.

---

## 7. The Tick — Main State Computation Method

### 7.1 Principle

The tick is the method that determines what state each underlying should be in. It executes:
- At `t = 0` of the cycle (first tick, `_is_initial=True`).
- At each `on_t` or `off_t` of an underlying.
- At other times if the reattachment algorithm defers a state change.

The tick does not need to execute at regular intervals: the next state changes of underlyings can be determined and the next tick scheduled exactly at that time.

`current_t` refers to the time elapsed since the start of the cycle when the tick executes.

### 7.2 Theoretical State Determination (`compute_target_state`)

For each underlying, the function `compute_target_state(on_t, off_t, current_t, cycle_duration)` determines the desired state (ON or OFF), the next tick, and the duration in the current state.

Conditions are evaluated in cascade (if / elif). Once a state is determined, subsequent tests are skipped.

#### Case 1: `off_t > on_t` — ON confined to `[on_t, off_t)`

```
|----OFF----|====ON====|----OFF----|
0          on_t       off_t       cycle_end
```

| Condition            | State | Next tick    | State duration         |
| -------------------- | ----- | ------------ | ---------------------- |
| `current_t < on_t`   | OFF   | `on_t`       | `on_t - current_t`    |
| `current_t < off_t`  | ON    | `off_t`      | `off_t - current_t`   |
| `current_t >= off_t` | OFF   | `cycle_end`  | `cycle_end - current_t`|

#### Case 2: `off_t <= on_t` — ON wraps around `[0, off_t) ∪ [on_t, cycle_end)`

```
|====ON====|----OFF----|====ON====|
0          off_t       on_t       cycle_end
```

| Condition            | State | Next tick    | State duration         |
| -------------------- | ----- | ------------ | ---------------------- |
| `current_t < off_t`  | ON    | `off_t`      | `off_t - current_t`   |
| `current_t < on_t`   | OFF   | `on_t`       | `on_t - current_t`    |
| `current_t >= on_t`  | ON    | `cycle_end`  | `cycle_end - current_t`|

### 7.3 State Application — Need ON / Need OFF

Once the theoretical state is determined, the tick checks whether the underlying's state actually needs to change, taking into account minimum activation and deactivation duration constraints.

---

## 8. Need ON — Activation Logic

### 8.1 Nominal Case

If the underlying is already ON, no action is needed.

`under_dt` is determined: the time elapsed since the underlying's last state change.

`state_duration` is known: the time between `current_t` and the next expected state change (computed by `compute_target_state`).

If both conditions are met:
- `under_dt >= minimal_deactivation_delay` (the underlying has been OFF long enough)
- `state_duration > minimal_activation_delay` (the planned activation duration is sufficient)

Then the action is `turn_on`.

### 8.2 Reattachment Case (skip + `on_t` shift)

If activation cannot occur (conditions not met), a **reattachment** is performed: the missed activation time is carried over to the next activation window.

1. A new `on_t = on_t - state_duration` is computed to incorporate the missed activation time ahead of the next activation.

2. This new `on_t` is checked against the remaining minimum deactivation time:
   - Time before the next activation: `on_t - current_t`
   - Time needed to respect minimum deactivation: `minimal_deactivation_delay - under_dt`
   - If `on_t - current_t < minimal_deactivation_delay - under_dt`, then `on_t` is forced to `current_t + (minimal_deactivation_delay - under_dt)`.

3. The unrealized heating time is added to `penalty` (positive value = lost heating time).

A new tick is scheduled at the time of the new `on_t`.

---

## 9. Need OFF — Deactivation Logic

The logic is symmetric to Need ON, with inverted roles:

### 9.1 Nominal Case

If the underlying is already OFF, no action is needed.

If both conditions are met:
- `under_dt >= minimal_activation_delay` (the underlying has been ON long enough)
- `state_duration > minimal_deactivation_delay` (the planned deactivation duration is sufficient)

Then the action is `turn_off`.

### 9.2 Reattachment Case (skip + `off_t` shift)

1. A new `off_t = off_t - state_duration` is computed.
2. This new `off_t` is checked against the remaining minimum activation time.
3. The extra heating time (the underlying stays ON longer than planned) is **subtracted** from `penalty` (negative value = excess heating time).

---

## 10. Effective Power Computation (`e_eff`)

### 10.1 Principle

Effective power is computed and notified by `CycleScheduler` via the internal `_calculate_realized_e_eff(elapsed_sec)` method.
It represents the power actually produced by exactly integrating the underlyings' heating time over the elapsed time, accounting for reattachment adjustments.

### 10.2 Exact Integration Formula

Rather than estimating at cycle end, the algorithm computes the exact physical projected activation time `t_on_actual` of each underlying over an absolute `elapsed_sec` window:

```python
e_eff = max(0.0, t_on_actual - penalty) / (elapsed_sec * n_underlyings)
```

Where:
- `t_on_actual` is the sum of the absolute activation time fractions cut over `elapsed_sec` (handling the scheduler's *wrap-around*).
- `penalty` is the cumulative heating time added (+) or removed (−) by reattachments during the cycle.
- `e_eff` is clamped between 0.0 and 1.0.

### 10.3 Cycle End and Interruptions

The method applies in two crucial contexts:
1. **Normal end (`_on_master_cycle_end`)**: Called with `nominal_cycle_duration`.
2. **Interruption (`cancel_cycle`)**: If a running cycle (> 1.0s) is canceled (e.g., the setpoint is changed mid-cycle), a partial `e_eff` is computed over the actual elapsed time (`elapsed_sec`). The scheduler then triggers a notification (`on_cycle_completed(partial_e_eff)` callback), ensuring the regulation algorithms (like Smart-PI) properly integrate this slice of thermal history.

---

## 11. Tick Scheduling

### 11.1 Scheduling Algorithm

At each tick, the scheduler determines the next global tick as the minimum among:
- The time remaining before cycle end.
- The next `on_t` or `off_t` of each underlying.
- Any new `on_t` or `off_t` resulting from reattachment.

A minimum delay of 0.1s is enforced to prevent overly fast loops.

### 11.2 Timer Count

At any given time, there are at most **2 active timers**:
- 1 timer for the next tick (`_tick_unsub`)
- 1 timer for the master cycle end (`_cycle_end_unsub`)

This is significantly fewer than the previous approach (2 × N + 1 timers).

### 11.3 Sequence Diagram

```
t=0                t=off_t[R1]    t=on_t[R2]    t=off_t[R2]         t=cycle_end
 |                      |              |              |                    |
 | _init_cycle()        |              |              |                    |
 | _tick(initial=True)  |              |              |                    |
 |   R1 → ON            |              |              |                    |
 |   R2 → OFF           |              |              |                    |
 |   next_tick=off_t[1] |              |              |                    |
 |                      |              |              |                    |
 |                      | _tick()      |              |                    |
 |                      |  R1 → OFF    |              |                    |
 |                      |  next=on_t[2]|              |                    |
 |                      |              |              |                    |
 |                      |              | _tick()      |                    |
 |                      |              |  R2 → ON     |                    |
 |                      |              |  next=off[2] |                    |
 |                      |              |              |                    |
 |                      |              |              | _tick()            |
 |                      |              |              |  R2 → OFF          |
 |                      |              |              |  next=cycle_end    |
 |                      |              |              |                    |
 |                      |              |              |     _on_master_    |
 |                      |              |              |     cycle_end()    |
 |                      |              |              |      → e_eff       |
 |                      |              |              |      → energy      |
 |                      |              |              |      → restart     |
```

---

## 12. `start_cycle()` Logic

```
start_cycle(hvac_mode, on_percent, force=False)
│
├── calculate_cycle_times(on_percent, cycle_min,
│       min_activation_delay, min_deactivation_delay)
│     → on_time_sec, off_time_sec
│
├── update thermostat._on_time_sec / _off_time_sec   ← always, even before early return
│
├── if cycle running AND force=False
│   ├── if current on_time > 0  → update stored params, return (non-disruptive update)
│   └── if current on_time == 0 → cancel idle cycle, fall through
│
├── cancel_cycle()          ← always cancel before (re)starting
├── store current params
├── fire cycle_start callbacks
│
├── if valve mode → _start_cycle_valve()
└── if switch mode → _start_cycle_switch()
      ├── if HVAC_OFF or on_time=0 → turn off all, schedule cycle end
      ├── if on_time >= cycle_duration → turn on all, schedule cycle end
      └── else → _init_cycle() → _tick(initial=True) + schedule cycle end
```

**Key behavior:** `thermostat._on_time_sec` and `thermostat._off_time_sec` are updated **before** the early-return check. This ensures sensor display values always reflect the latest computed values.

The non-disruptive update (when `force=False` and a real cycle is running) allows the handler to submit new `on_percent` values without breaking the current cycle's timing. The new parameters take effect at the next auto-repeat.

---

## 13. Callbacks and Handler Integration

### 13.1 Registration

```python
cycle_scheduler.register_cycle_start_callback(callback)
cycle_scheduler.register_cycle_end_callback(callback)
```

### 13.2 Cycle Start Callback Signature

```python
async def callback(
    on_time_sec: float,
    off_time_sec: float,
    on_percent: float,   # realized fraction 0.0–1.0 (timing-constrained)
    hvac_mode: VThermHvacMode,
) -> None: ...
```

Called once at the beginning of each master cycle (before any `turn_on`).

> **Note:** `on_percent` is the **realized** fraction after applying `min_activation_delay` / `min_deactivation_delay` constraints — not the raw value passed to `start_cycle()`. Use this value for power feedback (e.g. `update_realized_power()`), not the raw algorithm output.

### 13.3 Cycle End Callback Signature

```python
async def callback(e_eff: float) -> None: ...
```

Called once at `_on_master_cycle_end`, before `incremente_energy()` and before the cycle restarts. `e_eff` is the effective power computed over the cycle that just completed.

### 13.4 Handler Integration via `on_scheduler_ready()`

Instead of assigning `self._cycle_scheduler = CycleScheduler(...)` directly, thermostat subclasses call `_bind_scheduler()`:

```python
# In thermostat_switch.py / thermostat_valve.py / thermostat_climate_valve.py:
self._bind_scheduler(CycleScheduler(
    hass=self._hass,
    thermostat=self,
    underlyings=self._underlyings,
    cycle_duration_sec=self._cycle_min * 60,
    min_activation_delay=self.minimal_activation_delay,
    min_deactivation_delay=self.minimal_deactivation_delay,
))
```

`ThermostatProp._bind_scheduler()` stores the scheduler and notifies the active handler:

```python
def _bind_scheduler(self, scheduler) -> None:
    self._cycle_scheduler = scheduler
    if self._algo_handler and hasattr(self._algo_handler, "on_scheduler_ready"):
        self._algo_handler.on_scheduler_ready(scheduler)
```

Each handler implements `on_scheduler_ready(scheduler)` to self-register callbacks:

**TPI handler:**
```python
def on_scheduler_ready(self, scheduler) -> None:
    if self._auto_tpi_manager:
        scheduler.register_cycle_start_callback(self._auto_tpi_manager.on_cycle_started)
        scheduler.register_cycle_end_callback(self._auto_tpi_manager.on_cycle_completed)
```

**SmartPI handler:**
```python
def on_scheduler_ready(self, scheduler) -> None:
    algo = self._thermostat.prop_algorithm
    if algo:
        scheduler.register_cycle_start_callback(algo.on_cycle_started)
        scheduler.register_cycle_end_callback(algo.on_cycle_completed)
```

Lifecycle:
```
ThermostatProp.post_init()
  └─ _bind_scheduler(CycleScheduler(...))
       ├─ self._cycle_scheduler = scheduler
       └─ algo_handler.on_scheduler_ready(scheduler)
            ├─ scheduler.register_cycle_start_callback(algo.on_cycle_started)
            └─ scheduler.register_cycle_end_callback(algo.on_cycle_completed)
```

At each master cycle boundary:
- `on_cycle_started(on_time_sec, off_time_sec, realized_on_percent, hvac_mode)` fires → algo stores params, updates power feedback
- `on_cycle_completed(e_eff)` fires → algo reads stored params, runs learning

### 13.5 Removal of `CycleManager`

`CycleManager` — a polling-based abstract class with `process_cycle(timestamp, data_provider, event_sender, force)` — has been deleted. Algorithm classes that previously inherited from it (`AutoTpiManager`, `SmartPI`) now:

- Implement `on_cycle_started()` / `on_cycle_completed()` callbacks directly
- Do not inherit from `CycleManager`
- Are no longer driven by `process_cycle()` calls from handlers

Handlers no longer contain a `_data_provider` / `process_cycle()` block in `control_heating()`.

### 13.6 `update_realized_power()` — Heartbeat Requirement

`AutoTpiManager.update_realized_power(realized_percent)` must be called **on every `control_heating()` invocation**, not only at cycle boundaries. This ensures `last_power` stays current when `max_on_percent` or other limiting factors change mid-cycle.

The TPI handler calls this unconditionally:

```python
if self._auto_tpi_manager:
    self._auto_tpi_manager.update_realized_power(realized_percent)
```

This call is independent of the `on_cycle_started` callback (which fires only at cycle boundaries via the scheduler timer).

---

## 14. Special Cases

| Case                      | Behavior                                                                                                                              |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `on_percent = 0`          | All underlyings turned off. Idle cycle scheduled for `cycle_duration_sec` (keeps master rhythm). No `_init_cycle` call.               |
| `on_percent = 1.0` (100%) | All underlyings turned on unconditionally. No tick scheduling. Cycle end scheduled for next iteration.                                |
| Force restart             | `force=True` cancels all current timers via `cancel_cycle()` then restarts immediately.                                               |
| HVAC_MODE_OFF             | Handler sets `t._on_time_sec=0`, `t._off_time_sec=cycle_sec` directly, then calls `async_underlying_entity_turn_off()` (→ `cancel_cycle()` + `turn_off()`). |
| Single underlying         | `compute_circular_offsets` returns `[0.0]`. Identical behavior: single underlying with offset 0.                                      |
| Keep-alive                | Remains in `UnderlyingSwitch`. Reads `_should_be_on` (updated by the scheduler) to resend the current state periodically.            |
| Timing constraints        | `calculate_cycle_times()` is called **internally** by `start_cycle()`. Handlers also call it directly for `realized_percent` feedback only. |

---

## 15. Impact on Existing Code

### 15.1 Removed from `underlyings.py`

| Class                       | Removed                                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| `UnderlyingEntity`          | `start_cycle()`, `_cancel_cycle()`, `turn_off_and_cancel_cycle()`                                |
| `UnderlyingSwitch`          | `start_cycle()`, `_turn_on_later()`, `_turn_off_later()`, `_cancel_cycle()`, `initial_delay_sec` |
| `UnderlyingValve`           | `start_cycle()`, `_async_cancel_cycle`, `_cancel_cycle()` call in `remove_entity()`              |
| `UnderlyingValveRegulation` | `start_cycle()`                                                                                  |

`UnderlyingSwitch` retains: `turn_on()`, `turn_off()`, `_should_be_on`, `_on_time_sec`, `_off_time_sec`, keep-alive logic.

### 15.2 Deleted Files

| File               | Reason                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------- |
| `timing_utils.py`  | `calculate_cycle_times()` moved to module level of `cycle_scheduler.py`                     |
| `cycle_manager.py` | Abstract polling-based cycle detection; replaced by timer callbacks in `CycleScheduler`     |

### 15.3 Added Files

| File                  | Role                                                                                         |
| --------------------- | -------------------------------------------------------------------------------------------- |
| `cycle_tick_logic.py` | Pure tick scheduler logic: `UnderlyingCycleState`, `compute_circular_offsets`, `compute_target_state`, `evaluate_need_on`, `evaluate_need_off` |

### 15.4 Modified Files

| File                          | Change                                                                                                                                                                                                                                  |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `thermostat_switch.py`        | Calls `_bind_scheduler(CycleScheduler(...))` in `post_init()` passing delay attributes (set by `init_algorithm()` earlier in the call chain)                                                                                           |
| `thermostat_valve.py`         | Same as above                                                                                                                                                                                                                           |
| `thermostat_climate_valve.py` | Same as above                                                                                                                                                                                                                           |
| `thermostat_prop.py`          | Added `_bind_scheduler()` to store scheduler and notify handler via `on_scheduler_ready()`; removed `_on_prop_cycle_start()` (dead code)                                                                                                |
| `base_thermostat.py`          | `_cycle_scheduler = None` in `__init__`; `cycle_scheduler` property; `async_underlying_entity_turn_off()` calls `cancel_cycle()`; removed `_fire_cycle_start_callbacks()` (dead code); removed unused `asyncio` import                 |
| `prop_handler_tpi.py`         | Imports `calculate_cycle_times` from `cycle_scheduler`; calls `start_cycle(hvac_mode, on_percent, force)`; implements `on_scheduler_ready()` to register `AutoTpiManager` callbacks; calls `update_realized_power()` on every heartbeat |
| `prop_handler_smartpi.py`     | Same pattern as TPI handler; implements `on_scheduler_ready()` to register `SmartPI` algo callbacks                                                                                                                                     |
| `auto_tpi_manager.py`         | Removed `CycleManager` inheritance; implements `on_cycle_started()` / `on_cycle_completed()` callbacks; stores cycle params in `state.current_cycle_params`                                                                             |
| `prop_algo_smartpi.py`        | Removed `CycleManager` inheritance; added `cycle_min` property; simplified `on_cycle_completed()`; added `reset_cycle_state()` method                                                                                                   |

### 15.5 Unaffected Files

- `prop_algo_tpi.py` (pure TPI algorithm)
- Config flow, services, feature managers

---

## 16. Constructor and Properties

### 16.1 Constructor

```python
CycleScheduler(
    hass: HomeAssistant,
    thermostat: Any,
    underlyings: list,
    cycle_duration_sec: float,
    min_activation_delay: int = 0,    # minimum ON time in seconds
    min_deactivation_delay: int = 0,  # minimum OFF time in seconds
)
```

`min_activation_delay` and `min_deactivation_delay` are permanent attributes accessible as `scheduler.min_activation_delay` and `scheduler.min_deactivation_delay`. They are updated by service calls (e.g. `service_set_tpi_parameters`) when the user changes these values at runtime.

### 16.2 Properties

| Property               | Type   | Description                                  |
| ---------------------- | ------ | -------------------------------------------- |
| `is_cycle_running`     | `bool` | True if a tick or cycle end is scheduled     |
| `is_valve_mode`        | `bool` | True if managing valve underlyings           |
| `min_activation_delay` | `int`  | Minimum ON time in seconds (equipment guard) |
| `min_deactivation_delay` | `int` | Minimum OFF time in seconds (equipment guard)|

### 16.3 Internal Cycle State

| Attribute             | Type                         | Description                                                    |
| --------------------- | ---------------------------- | -------------------------------------------------------------- |
| `_states`             | `list[UnderlyingCycleState]` | Per-underlying state (on_t, off_t, on_time, offset)            |
| `_penalty`            | `float`                      | Cumulative reattachment adjustments (seconds)                  |
| `_cycle_start_time`   | `float`                      | Cycle start timestamp (for real duration computation)          |
| `_tick_unsub`         | `CALLBACK_TYPE | None`       | Cancellation handle for the next scheduled tick                |
| `_cycle_end_unsub`    | `CALLBACK_TYPE | None`       | Cancellation handle for the master cycle end                   |

### 16.4 `UnderlyingCycleState`

Defined in `cycle_tick_logic.py`:

```python
class UnderlyingCycleState:
    underlying     # reference to the underlying entity
    offset: float  # fixed circular offset (seconds)
    on_t: float    # activation time in the cycle (may be modified by reattachment)
    off_t: float   # deactivation time in the cycle (may be modified by reattachment)
    on_time: float # planned operating duration (seconds)
```
