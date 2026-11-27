# 🧠 Auto TPI: In-Depth Technical Guide

> [!NOTE]
> This document is intended for advanced users who want to understand how Auto TPI works. For a simpler introduction, see the [Auto TPI User Guide](feature-autotpi.md).

---

## Table of Contents

1. [The TPI Algorithm](#the-tpi-algorithm)
2. [Room Model and Target Coefficients](#room-model-and-target-coefficients)
3. [Learning Cycle](#learning-cycle)
4. [Kint Learning](#kint-learning)
5. [Kext Learning](#kext-learning)
6. [Continuous Kext Learning](#continuous-kext-learning)
7. [Parameters and Constants](#parameters-and-constants)
8. [Services and API](#services-and-api)
9. [Diagnostics and Troubleshooting](#diagnostics-and-troubleshooting)

---

## The TPI Algorithm

### Fundamental Principle

The **TPI** (Time Proportional & Integral) algorithm calculates a **power percentage** at each cycle. This percentage determines how long the heater will be active during the cycle (e.g., 60% on a 10-minute cycle = 6 minutes of heating).

### Basic Formula

```
Power = (Kint × ΔT_indoor) + (Kext × ΔT_outdoor)
```

Where:
- **Kint** (`tpi_coef_int`): Indoor coefficient, reacts to the setpoint gap
- **Kext** (`tpi_coef_ext`): Outdoor coefficient, compensates for thermal losses
- **ΔT_indoor** = Setpoint − Indoor Temperature
- **ΔT_outdoor** = Setpoint − Outdoor Temperature

The power is limited to 0–100%. In cooling mode, the differences are reversed.

### Role of Coefficients

| Coefficient | Role | Learning Situation |
|-------------|------|-------------------|
| **Kint** | Sets the **reactivity**: the higher it is, the stronger the heating reacts to a gap | During a **temperature rise** (gap ≥ 0.3°C at the start of a window, power between 0 and 100%) |
| **Kext** | Compensates the **thermal losses**: it provides the power needed to hold the setpoint | When the room is **settled near the setpoint** |

---

## Room Model and Target Coefficients

Auto TPI relies on a simple room model (one thermal capacity, one loss to the outside):

```
dT/dt = a × P − b × (T − T_ext)
```

- `a` (°C/h): temperature rise rate at 100% power, without losses
- `b` (1/h): loss rate, inverse of the room time constant
- `P`: heating power (0–1)

**Kext**: at the setpoint, the power needed is `P = (b/a) × (Setpoint − T_ext)`. The ideal Kext is therefore `b/a`. With this value, the outdoor term alone holds the setpoint and no static gap remains.

**Kint**: once Kext compensates the losses, the room rises at `a × Kint × gap`. To close the gap with a time constant `T_cl`, Kint must be `1 / (a × T_cl)`. A weak emitter (small `a`) therefore needs a larger Kint.

`T_cl` is the target closed-loop time constant. It is derived from the **heating time** of the emitter:

```
T_cl = 2 × (heating_time + cycle / 2)     bounded to [30 min, 180 min]
```

A slow emitter (long heating time) gives a longer `T_cl`, hence a gentler regulation that does not overshoot.

Neither `a` nor `b` needs to be known: both coefficients are learned from observations, by small steps, toward these targets.

---

## Learning Cycle

At the end of each TPI cycle, the manager checks the cycle and updates the learning.

### Cycle Snapshot

At the start of each cycle, the system records the indoor and outdoor temperatures, the setpoint, the power and the HVAC mode. At the end of the cycle, the power actually applied (after timing constraints) is used.

### Cycle Validation Conditions

A cycle is ignored for learning if:

| Condition | Reason |
|-----------|--------|
| Power ≤ 0% or ≥ 100% | A saturated cycle says nothing about the power to apply |
| Cycle shorter or longer than expected | Interrupted cycle or gap in the data |
| Power shedding during the cycle | The heating was limited by another feature |
| Central boiler off | The emitter did not heat |
| Heating failure detected | The emitter did not heat as requested |
| First cycle after a stop | No previous state |
| Setpoint changed during the cycle | The cycle mixes two targets |
| \|Setpoint − T_ext\| < 1°C (Kext) | The outdoor term is too small to be learned |

### End of the Session

The session ends when Kint has been learned over **15 windows** and Kext over **50 cycles**. The coefficients are then written to the configuration and a notification is sent.

---

## Kint Learning

Kint is learned over **windows** of several consecutive cycles, never over a single cycle: on a 5-minute cycle, the temperature change is of the same order as the sensor resolution (often 0.1°C).

### Window Rules

- A window opens when the room is at least **0.3°C** from the setpoint, and only **T_cl / 2** after the last setpoint change, mode change, cycle at 0% or invalid cycle (the emitter needs this time to respond). A cycle at 100% closes the window without restarting this delay: the emitter is already running.
- Every cycle of the window must be valid with a power between 0 and 100%. Otherwise the window is closed without learning.
- The window duration is set when it opens, from the rise speed measured over the previous 20 minutes, so that the window sees about 0.3°C of change: between 10 minutes (and at least 2 cycles) for a fast rise and **max(30 min, T_cl)** for a slow one. It only uses data older than the window, so it never depends on the change the window measures. The next window starts where the previous one ends, under the same 0.3°C condition.
- A window is accepted on its duration and its starting gap only. It never depends on the measured temperature change: otherwise only the windows where noise increased the rise would be kept, which would bias Kint.

### Update Formula

```
mean_gap    = Setpoint − (T_start + T_end) / 2
target_rate = mean_gap / T_cl
rate        = (T_end − T_start) / duration
ratio       = target_rate / rate          (1.15 if rate ≤ 0)
Kint_new    = Kint × clamp(ratio, 1/1.15, 1.15)
```

Kint moves by at most ±15% per window and stays within [0.01, 3.0]. A bounded step converges toward the median of the ratio: an isolated window disturbed by noise or by the sun cannot move Kint much.

If the room crossed the setpoint during the window (`mean_gap ≤ 0`), the window is not used.

---

## Kext Learning

### Settling Condition

The rise after a setpoint change belongs to Kint. Kext is learned only:
- at least **3 × T_cl** after the last setpoint change,
- and once the room came back within **0.3°C** of the setpoint, or after **12 × T_cl** so that a very wrong Kext (large static gap) can still be corrected.

### Formula

When the room is settled and the gap is small (|gap| ≤ 1°C, or any gap above the setpoint while the power is at least 10%):

```
Kext_target = Kext + Kint × (ΔT_indoor / ΔT_outdoor)
```

The remaining indoor gap is converted into the outdoor power that would remove it. Kext_target is limited to 1.2.

Samples above the setpoint are ignored when the power is very low (the room is cooling down naturally, or an external source heats it).

### Smoothing

The samples are combined with a **weighted average**:

```
Kext_new = (Kext × n + Kext_target) / (n + 1)       n = number of samples, capped at 50
```

The configured Kext has no weight: the first sample replaces it, then each sample weighs 1/(n+1). For a fixed quantity, the average gives the least noisy estimate.

---

## Continuous Kext Learning

When **Continuous Kext Learning** is enabled, Kext keeps being adjusted after the session, to follow slow changes of the losses.

### Eligibility Conditions
- At least one Kext sample from a learning session.
- Same cycle and settling conditions as Kext learning.

### Formula

```
Kext_new = Kext × (1 − α) + Kext_target × α        α = 0.04
```

A fixed weight lets Kext follow a quantity that drifts slowly. The new value is written to the configuration when it changes by more than 0.001, and the regulation uses it right away.

---

## Parameters and Constants

### Configurable Parameters

| Parameter | Description |
|-----------|-------------|
| `heater_heating_time` | Heating time of the emitter (min). Sets `T_cl`. |
| `auto_tpi_continuous_kext` | Continuous Kext learning after the session. |

### Internal Constants

| Constant | Value | Role |
|----------|-------|------|
| Minimum gap for a Kint window | 0.3°C | Kint is learned only when the room has a gap to close |
| Window duration | 10 min to max(30 min, T_cl), set from the previous rise speed | About 0.3°C of change per window |
| Maximum Kint step | ×1.15 / ÷1.15 | Bounded step per window |
| Kint bounds | 0.01 – 3.0 | |
| Kint windows to end the session | 15 | |
| Kext cycles to end the session | 50 | |
| Kext settling | 3 × T_cl, then near setpoint (or 12 × T_cl) | Kext is not learned during a rise |
| Maximum gap for Kext | 1.0°C | |
| Maximum Kext | 1.2 | |
| Continuous Kext alpha | 0.04 | |

---

## Services and API

### `versatile_thermostat.set_auto_tpi_mode`

Starts or stops a learning session.

| Parameter | Type | Description |
|-----------|------|-------------|
| `auto_tpi_mode` | boolean | `true` to start, `false` to stop |
| `reinitialise` | boolean | `true` (default): start again from the configured coefficients. `false`: resume the previous session |

```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.living_room
data:
  auto_tpi_mode: true
  reinitialise: true
```

---

## Diagnostics and Troubleshooting

### Diagnostic Sensor

Entity: `sensor.<name>_auto_tpi_learning_state`

State: `active` during a session, `off` otherwise.

| Attribute | Description |
|-----------|-------------|
| `heating_cycles_count` | Total observed cycles |
| `coeff_int_cycles` | Kint windows learned |
| `coeff_ext_cycles` | Kext cycles learned |
| `model_confidence` | Session progress 0.0 – 1.0 |
| `calculated_coef_int` | Current Kint |
| `calculated_coef_ext` | Current Kext |
| `last_learning_status` | Result of the last cycle |
| `learning_start_dt` | Start of the session |

### Common Learning Statuses

| Status | Meaning |
|--------|---------|
| `learned_indoor_heat` / `learned_indoor_cool` | Kint updated at the end of a window |
| `learned_outdoor_heat` / `learned_outdoor_cool` | Kext updated |
| `kext_waiting_settling` | Kext waits for the room to settle after a setpoint change |
| `kint_window_crossed_setpoint` | The room crossed the setpoint during the window, window not used |
| `power_out_of_range(...)` | Power at 0% or 100%, cycle ignored |
| `cycle_gap_detected` / `cycle_too_short` | Abnormal cycle duration, cycle ignored |
| `setpoint_changed_during_cycle` | Setpoint modified during the cycle |
| `outdoor_delta_too_small(...)` | Outdoor temperature too close to the setpoint |
| `gap_too_large_for_outdoor(...)` | Gap above 1°C, Kext not learned |
| `cooling_down_naturally` / `warming_up_naturally` | Room returning to the setpoint by itself, Kext not changed |
| `continuous_kext_learned_heat` / `continuous_kext_learned_cool` | Kext updated by continuous learning |

### Troubleshooting

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Kint does not progress | No rise of at least 0.3°C with non-saturated power | Lower the setpoint by 1–2°C for a few hours, then set it back |
| Overshoot after each rise | Heating time too short for the emitter | Increase the heating time, then restart a session |
| Slow rise, no overshoot | Heating time too long | Decrease the heating time, then restart a session |
| Room always below or above the setpoint | Kext not learned yet, or losses changed | Let the session end, or enable continuous Kext learning |
| Learning makes no progress at all | Heating always at 100% (extreme cold) | Wait for milder weather |

### Persistence File

**Location**: `.storage/versatile_thermostat.auto_tpi.<unique_id>`

This file contains the learning state and is restored on Home Assistant restart. When no learning cycle has been recorded yet, the configured coefficients are used. Outside a learning session, the configuration is the reference: a coefficient changed in the configuration (options or `set_tpi_parameters` service) replaces the stored one.
