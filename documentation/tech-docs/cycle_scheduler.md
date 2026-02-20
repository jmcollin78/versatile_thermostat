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
|  |                                    |  |
|  | start_cycle(hvac_mode, on_percent) |  |
|  |   calculate_cycle_times()          |  |
|  |   compute_offsets()                |  |
|  |   schedule_actions()               |  |
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

---

## 3. Operating Modes

### 3.1 Switch Mode (PWM scheduling)

For `UnderlyingSwitch` entities, the scheduler uses a PWM approach:
- Computes staggered ON offsets to minimize simultaneous heater activation
- Schedules `turn_on()` and `turn_off()` calls via `async_call_later`
- Schedules `_on_master_cycle_end` at `t = cycle_duration_sec`
- At cycle end, increments energy, clears timers, and restarts with the same parameters

### 3.2 Valve Mode (passthrough)

For `UnderlyingValve` and `UnderlyingValveRegulation` entities, no timer scheduling is needed:
- `_start_cycle_valve()` directly calls `set_valve_open_percent()` on each underlying
- No master cycle repeat is scheduled — the thermostat's `async_track_time_interval` drives periodic re-evaluation
- This unifies valve cycle handling under the same `start_cycle()` API

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

## 5. Offset Computation Algorithm

### 5.1 Principle

For switch mode, the scheduler spreads ON start times evenly across the available window `[0, cycle_duration - on_time]`. This is the **uniform distribution** strategy.

```python
max_offset = cycle_duration_sec - on_time_sec
step = max_offset / (n - 1)
offsets = [i * step for i in range(n)]
```

Edge cases:
- `n <= 1`: returns `[0.0]`
- `on_time_sec <= 0`: returns `[0.0] * n` (nothing to schedule)
- `on_time_sec >= cycle_duration_sec` (100% power): returns `[0.0] * n` (all start together)

### 5.2 Examples — 2 heaters, 600s cycle

| on_percent | on_time | max_offset | step | Offsets  | ON periods             |
| ---------- | ------- | ---------- | ---- | -------- | ---------------------- |
| 20%        | 120s    | 480s       | 480s | [0, 480] | R1: 0-120, R2: 480-600 |
| 40%        | 240s    | 360s       | 360s | [0, 360] | R1: 0-240, R2: 360-600 |
| 50%        | 300s    | 300s       | 300s | [0, 300] | R1: 0-300, R2: 300-600 |
| 60%        | 360s    | 240s       | 240s | [0, 240] | R1: 0-360, R2: 240-600 |
| 100%       | 600s    | 0s         | —    | [0, 0]   | R1: 0-600, R2: 0-600   |

### 5.3 Examples — 3 heaters, 600s cycle

| on_percent | on_time | Offsets       | Max overlap   |
| ---------- | ------- | ------------- | ------------- |
| 20%        | 120s    | [0, 240, 480] | 0             |
| 33%        | 200s    | [0, 200, 400] | 0             |
| 40%        | 240s    | [0, 180, 360] | 60s per pair  |
| 50%        | 300s    | [0, 150, 300] | 150s per pair |
| 100%       | 600s    | [0, 0, 0]     | Total         |

At high `on_percent`, some overlap is unavoidable. The uniform distribution minimizes peak simultaneous load.

---

## 6. Master Cycle Lifecycle

### 6.1 Sequence Diagram

```
t=0          t=offset[1]  t=offset[2]  t=off[1]     t=off[2]    t=cycle_end
 |               |            |             |            |            |             |
 | start_cycle() |            |             |            |            |             |
 | R1.turn_on()  |            |             |            |            |             |
 |               | R2.turn_on |             |            |            |             |
 |               |            | R3.turn_on  |            |            |             |
 |               |            |             | R1.turn_off|            |             |
 |               |            |             |            | R2.turn_off|             |
 |               |            |             |            |            | R3.turn_off |
 |               |            |             |            |            |             |
 |               |            |             |            |            | _on_master_ |
 |               |            |             |            |            | cycle_end() |
 |               |            |             |            |            |  → energy   |
 |               |            |             |            |            | → restart  |
```

R1 (offset=0) is turned on immediately with `await under.turn_on()`.
All others are scheduled via `async_call_later`.

### 6.2 Timer count per cycle

```
Total timers = 2 * N + 1
  N  × turn_on  timers  (offset[1..N-1]; R1 at offset=0 is immediate)
  N  × turn_off timers  (unless the underlying spans until cycle end)
  1  × master cycle end timer
```

For typical configurations (N = 2–4), this is 5–9 timers per cycle — negligible for Home Assistant.

### 6.3 At `_on_master_cycle_end`

1. Turn off any underlying still ON (except when `on_time >= cycle_duration`)
2. Fire all registered `_on_cycle_end_callbacks`
3. Call `thermostat.incremente_energy()`
4. Call `start_cycle(hvac_mode, on_percent, force=True)` — `cancel_cycle()` is called atomically inside

---

## 7. `start_cycle()` Logic

```
start_cycle(hvac_mode, on_percent, force=False)
│
├── calculate_cycle_times(on_percent, cycle_min,
│       min_activation_delay, min_deactivation_delay)
│     → on_time_sec, off_time_sec
│
├── update thermostat._on_time_sec / _off_time_sec   ← always, even before early return
│
├── if _scheduled_actions is non-empty AND force=False
│   ├── if current on_time > 0  → update stored params, return (non-disruptive update)
│   └── if current on_time == 0 → cancel idle cycle, fall through
│
├── cancel_cycle()          ← always cancel before (re)starting
├── store current params
├── fire cycle_start callbacks
│
├── if valve mode → _start_cycle_valve()
└── if switch mode → _start_cycle_switch()
```

**Key behavior:** `thermostat._on_time_sec` and `thermostat._off_time_sec` are updated **before** the early-return check. This ensures sensor display values always reflect the latest computed values, even when the running cycle is not interrupted — preserving backward compatibility with the previous handler-side assignment.

The non-disruptive update (when `force=False` and a real cycle is running) allows the handler to submit new `on_percent` values without breaking the current cycle's timing. The new parameters take effect at the next auto-repeat.

---

## 8. Callbacks and Handler Integration

### 8.1 Registration

```python
cycle_scheduler.register_cycle_start_callback(callback)
cycle_scheduler.register_cycle_end_callback(callback)
```

### 8.2 Cycle start callback signature

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

### 8.3 Cycle end callback signature

```python
async def callback() -> None: ...
```

Called once at `_on_master_cycle_end`, before `incremente_energy()` and before the cycle restarts.

### 8.4 Handler Integration via `on_scheduler_ready()`

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
- `on_cycle_completed()` fires → algo reads stored params, runs learning

### 8.5 Removal of `CycleManager`

`CycleManager` — a polling-based abstract class with `process_cycle(timestamp, data_provider, event_sender, force)` — has been deleted. Algorithm classes that previously inherited from it (`AutoTpiManager`, `SmartPI`) now:

- Implement `on_cycle_started()` / `on_cycle_completed()` callbacks directly
- Do not inherit from `CycleManager`
- Are no longer driven by `process_cycle()` calls from handlers

Handlers no longer contain a `_data_provider` / `process_cycle()` block in `control_heating()`.

### 8.6 `update_realized_power()` — Heartbeat Requirement

`AutoTpiManager.update_realized_power(realized_percent)` must be called **on every `control_heating()` invocation**, not only at cycle boundaries. This ensures `last_power` stays current when `max_on_percent` or other limiting factors change mid-cycle.

The TPI handler calls this unconditionally:

```python
if self._auto_tpi_manager:
    self._auto_tpi_manager.update_realized_power(realized_percent)
```

This call is independent of the `on_cycle_started` callback (which fires only at cycle boundaries via the scheduler timer).

---

## 9. Special Cases

| Case                      | Behavior                                                                                                                              |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `on_percent = 0`          | All underlyings turned off. Idle cycle scheduled for `cycle_duration_sec` (keeps master rhythm).                                      |
| `on_percent = 1.0` (100%) | All underlyings turned on at offset=0. No `turn_off` scheduled. All turned off at `_on_master_cycle_end` then immediately re-enabled. |
| Force restart             | `force=True` cancels all current timers via `cancel_cycle()` then restarts immediately.                                               |
| HVAC_MODE_OFF             | Handler sets `t._on_time_sec=0`, `t._off_time_sec=cycle_sec` directly, then calls `async_underlying_entity_turn_off()` (→ `cancel_cycle()` + `turn_off()`). `start_cycle()` is not called. |
| Single underlying         | `compute_offsets` returns `[0.0]`. Behavior identical to the previous implementation.                                                 |
| Keep-alive                | Remains in `UnderlyingSwitch`. Reads `_should_be_on` (updated by the scheduler) to resend the current state periodically.            |
| Timing constraints        | `calculate_cycle_times()` is called **internally** by `start_cycle()`. Handlers also call it directly for `realized_percent` feedback only. |

---

## 10. Impact on Existing Code

### 10.1 Removed from `underlyings.py`

| Class                       | Removed                                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| `UnderlyingEntity`          | `start_cycle()`, `_cancel_cycle()`, `turn_off_and_cancel_cycle()`                                |
| `UnderlyingSwitch`          | `start_cycle()`, `_turn_on_later()`, `_turn_off_later()`, `_cancel_cycle()`, `initial_delay_sec` |
| `UnderlyingValve`           | `start_cycle()`, `_async_cancel_cycle`, `_cancel_cycle()` call in `remove_entity()`              |
| `UnderlyingValveRegulation` | `start_cycle()`                                                                                  |

`UnderlyingSwitch` retains: `turn_on()`, `turn_off()`, `_should_be_on`, `_on_time_sec`, `_off_time_sec`, keep-alive logic.

### 10.2 Deleted files

| File               | Reason                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------- |
| `timing_utils.py`  | `calculate_cycle_times()` moved to module level of `cycle_scheduler.py`                     |
| `cycle_manager.py` | Abstract polling-based cycle detection; replaced by timer callbacks in `CycleScheduler`     |

### 10.3 Modified files

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

### 10.4 Unaffected files

- `prop_algo_tpi.py` (pure TPI algorithm)
- Config flow, services, feature managers

---

## 11. Properties and Constructor

### 11.1 Constructor

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

### 11.2 Properties

| Property               | Type   | Description                                  |
| ---------------------- | ------ | -------------------------------------------- |
| `is_cycle_running`     | `bool` | True if `_scheduled_actions` is non-empty    |
| `is_valve_mode`        | `bool` | True if managing valve underlyings           |
| `min_activation_delay` | `int`  | Minimum ON time in seconds (equipment guard) |
| `min_deactivation_delay` | `int` | Minimum OFF time in seconds (equipment guard)|
