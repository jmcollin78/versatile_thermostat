# Lock Feature

## Overview

The Lock feature prevents changes to a thermostat from the UI or automations while keeping the thermostat operational.

## Configuration

The Lock feature is configured in the thermostat's settings, under the "Lock" section. You can choose to lock out:

- **Users**: Prevents changes from the Home Assistant UI.
- **Automations & integrations**: Prevents changes from automations, scripts, and other integrations  like scheduler.

You can also configure an optional **Lock Code**:

- **Lock Code**: A 4-digit numeric pincode (e.g., "1234"). If set, this code is required to lock/unlock the thermostat. This is optional and if not configured, no code is required.

You can also choose to use a central configuration for the lock settings.

## Usage

Use these services to control the lock state:

- `versatile_thermostat.lock` - Locks the thermostat
- `versatile_thermostat.unlock` - Unlocks the thermostat (requires `code` if configured)

Example locking automation:

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

Example unlocking automation with code:

```yaml
service: versatile_thermostat.unlock
target:
  entity_id: climate.my_thermostat
data:
  code: "1234"
```

## Lock State

The lock state is:

- Visible in the `is_locked`, `lock_users`, and `lock_automations` attributes of the climate entity
- Preserved across Home Assistant restarts (including the pincode if set)
- Per-thermostat (each thermostat has its own lock and optional pincode)

## When Locked

**Blocked (from UI / automations / external calls depending of lock type in the configuration):**

- HVAC mode changes (including on/off)
- Target temperature changes
- Preset changes and VTherm preset configuration services
- HA action service call

**Allowed (internal VTherm logic, always active):**

- Window detection and actions (turn-off or eco/frost on open, fan-only if applicable, restore behavior on close)
- Safety protections (e.g. overheat / frost safety presets, safety off/on handling)
- Power and overpowering management (including `PRESET_POWER` behavior)
- Automatic regulation algorithms (TPI / PI / PROP) and control loop
- Central/parent/child coordination and other VTherm internal automation

**Behavior guarantee:**

- Window actions (for example: turn-off on open, restore on close) operate even when the thermostat is locked.

**Implementation note:**

- The lock is enforced on external calls, which are the only ones that modify the `requested_state`. Internal operations (like those from `SafetyManager` or `PowerManager`) bypass the lock by design because the `StateManager` prioritizes their output over external requests. The lock only prevents external calls from modifying the `requested_state`.

## Use Cases

- Prevent accidental changes during critical periods
- Child lock functionality
- Temporary prevent scheduler to change current settings
- Security against unauthorized unlocking (using pincode)
