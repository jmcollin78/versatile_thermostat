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
  Handler → cycle_scheduler.start_cycle(hvac_mode, on_time, off_time, on_percent, force)
             (scheduler orchestrates all underlyings in one master cycle)
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
|  +--------+-----------+                  |
|  | CycleScheduler     |                  |
|  |                    |                  |
|  | start_cycle()      |                  |
|  |   compute_offsets()|                  |
|  |   schedule_actions()|                 |
|  |                    |                  |
|  +--+------+------+--+                  |
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

## 4. Offset Computation Algorithm

### 4.1 Principle

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

### 4.2 Examples — 2 heaters, 600s cycle

| on_percent | on_time | max_offset | step | Offsets  | ON periods             |
| ---------- | ------- | ---------- | ---- | -------- | ---------------------- |
| 20%        | 120s    | 480s       | 480s | [0, 480] | R1: 0-120, R2: 480-600 |
| 40%        | 240s    | 360s       | 360s | [0, 360] | R1: 0-240, R2: 360-600 |
| 50%        | 300s    | 300s       | 300s | [0, 300] | R1: 0-300, R2: 300-600 |
| 60%        | 360s    | 240s       | 240s | [0, 240] | R1: 0-360, R2: 240-600 |
| 100%       | 600s    | 0s         | —    | [0, 0]   | R1: 0-600, R2: 0-600   |

### 4.3 Examples — 3 heaters, 600s cycle

| on_percent | on_time | Offsets       | Max overlap   |
| ---------- | ------- | ------------- | ------------- |
| 20%        | 120s    | [0, 240, 480] | 0             |
| 33%        | 200s    | [0, 200, 400] | 0             |
| 40%        | 240s    | [0, 180, 360] | 60s per pair  |
| 50%        | 300s    | [0, 150, 300] | 150s per pair |
| 100%       | 600s    | [0, 0, 0]     | Total         |

At high `on_percent`, some overlap is unavoidable. The uniform distribution minimizes peak simultaneous load.

---

## 5. Master Cycle Lifecycle

### 5.1 Sequence Diagram

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

### 5.2 Timer count per cycle

```
Total timers = 2 * N + 1
  N  × turn_on  timers  (offset[1..N-1]; R1 at offset=0 is immediate)
  N  × turn_off timers  (unless the underlying spans until cycle end)
  1  × master cycle end timer
```

For typical configurations (N = 2–4), this is 5–9 timers per cycle — negligible for Home Assistant.

### 5.3 At `_on_master_cycle_end`

1. Turn off any underlying still ON (except when `on_time >= cycle_duration`)
2. Fire all registered `_on_cycle_end_callbacks`
3. Call `thermostat.incremente_energy()`
4. Clear `_scheduled_actions`
5. Call `start_cycle(..., force=True)` to restart with the same parameters

---

## 6. `start_cycle()` Logic

```
start_cycle(hvac_mode, on_time, off_time, on_percent, force=False)
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

The non-disruptive update (when `force=False` and a real cycle is running) allows the handler to submit new `on_percent` values without breaking the current cycle's timing. The new parameters take effect at the next auto-repeat.

---

## 7. Callbacks

### 7.1 Registration

```python
cycle_scheduler.register_cycle_start_callback(callback)
cycle_scheduler.register_cycle_end_callback(callback)
```

### 7.2 Cycle start callback signature

```python
async def callback(
    on_time_sec: float,
    off_time_sec: float,
    on_percent: float,
    hvac_mode: VThermHvacMode,
) -> None: ...
```

Called once at the beginning of each master cycle (before any `turn_on`).
Used by SmartPI for learning and power feedback computation.

### 7.3 Cycle end callback signature

```python
async def callback() -> None: ...
```

Called once at `_on_master_cycle_end`, before `incremente_energy()` and before the cycle restarts.

---

## 8. Special Cases

| Case                  | Behavior                                                                                                                                 |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `on_percent = 0`      | All underlyings turned off. Idle cycle scheduled for `cycle_duration_sec` (keeps master rhythm).                                         |
| `on_percent = 100`    | All underlyings turned on at offset=0. No `turn_off` scheduled. All turned off at `_on_master_cycle_end` then immediately re-enabled.    |
| Force restart         | `force=True` cancels all current timers via `cancel_cycle()` then restarts immediately.                                                  |
| HVAC_MODE_OFF         | Handler calls `async_underlying_entity_turn_off()` which calls `cancel_cycle()` + `turn_off()` on each underlying.                       |
| Single underlying     | `compute_offsets` returns `[0.0]`. Behavior identical to the previous implementation.                                                    |
| Keep-alive            | Remains in `UnderlyingSwitch`. Reads `_should_be_on` (updated by the scheduler) to resend the current state periodically.                |
| Pre-cycle constraints | `calculate_cycle_times()` in `timing_utils.py` clamps `on_time_sec`/`off_time_sec` before the scheduler receives them. No change needed. |

---

## 9. Impact on Existing Code

### 9.1 Removed from `underlyings.py`

| Class                       | Removed                                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| `UnderlyingEntity`          | `start_cycle()`, `_cancel_cycle()`, `turn_off_and_cancel_cycle()`                                |
| `UnderlyingSwitch`          | `start_cycle()`, `_turn_on_later()`, `_turn_off_later()`, `_cancel_cycle()`, `initial_delay_sec` |
| `UnderlyingValve`           | `start_cycle()`, `_async_cancel_cycle`, `_cancel_cycle()` call in `remove_entity()`              |
| `UnderlyingValveRegulation` | `start_cycle()`                                                                                  |

`UnderlyingSwitch` retains: `turn_on()`, `turn_off()`, `_should_be_on`, `_on_time_sec`, `_off_time_sec`, keep-alive logic.

### 9.2 Modified files

| File                      | Change                                                                                                                                                                                                                    |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `thermostat_switch.py`    | Creates `CycleScheduler` in `post_init()` after building underlyings list                                                                                                                                                 |
| `thermostat_valve.py`     | Creates `CycleScheduler` in `post_init()` after building underlyings list                                                                                                                                                 |
| `base_thermostat.py`      | `_cycle_scheduler = None` in `__init__`; `cycle_scheduler` property; `async_underlying_entity_turn_off()` calls `cancel_cycle()`; `register_cycle_callback()` routes to `cycle_scheduler.register_cycle_start_callback()` |
| `prop_handler_tpi.py`     | Calls `t.cycle_scheduler.start_cycle(...)` directly                                                                                                                                                                       |
| `prop_handler_smartpi.py` | Calls `t.cycle_scheduler.start_cycle(...)` directly                                                                                                                                                                       |

### 9.3 Unaffected files

- `prop_algo_tpi.py`, `prop_algo_smartpi.py` (pure algorithms)
- Config flow, services, feature managers
- `timing_utils.py`

---

## 10. Properties

| Property           | Type   | Description                               |
| ------------------ | ------ | ----------------------------------------- |
| `is_cycle_running` | `bool` | True if `_scheduled_actions` is non-empty |
| `is_valve_mode`    | `bool` | True if managing valve underlyings        |
