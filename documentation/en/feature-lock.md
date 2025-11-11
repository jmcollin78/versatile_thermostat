# Lock Feature

## Overview

The Lock feature prevents changes to a thermostat's configuration from the UI or automations while keeping the thermostat operational.

## Usage

Use these services to control the lock state:

- `versatile_thermostat.lock` - Locks the thermostat
- `versatile_thermostat.unlock` - Unlocks the thermostat

Example automation:

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

## Lock State

The lock state is:

- Visible in the `is_locked` attribute of the climate entity
- Preserved across Home Assistant restarts
- Per-thermostat (each thermostat has its own lock)

## When Locked

**Blocked (from UI / automations / external calls):**

- HVAC mode changes (including on/off)
- Target temperature changes
- Preset changes and VTherm preset configuration services
- Presence state changes via VTherm services
- Safety configuration changes via VTherm services
- Window bypass changes via VTherm services
- Fan/swing/ventilation modes when exposed by VTherm

**Allowed (internal VTherm logic, always active):**

- Window detection and actions (turn-off or eco/frost on open, fan-only if applicable, restore behavior on close)
- Safety protections (e.g. overheat / frost safety presets, safety off/on handling)
- Power and overpowering management (including `PRESET_POWER` behavior)
- Automatic regulation algorithms (TPI / PI / PROP) and control loop
- Central/parent/child coordination and other VTherm internal automation

**Behavior guarantee:**

- Window actions (for example: turn-off on open, restore on close) operate even when the thermostat is locked.

**Implementation note:**

- The lock is enforced on external calls, while VTherm uses Home Assistant's context internally so that its own features can still adjust the thermostat when locked.

## Use Cases

- Prevent accidental changes during critical periods
- Child lock functionality
