# Timed Preset

- [Timed Preset](#timed-preset)
  - [Purpose](#purpose)
  - [How it works](#how-it-works)
  - [Activate a timed preset](#activate-a-timed-preset)
  - [Cancel a timed preset](#cancel-a-timed-preset)
  - [Custom attributes](#custom-attributes)
  - [Events](#events)
  - [Manual override with automatic revert](#manual-override-with-automatic-revert)
  - [Automation examples](#automation-examples)
    - [30-minute boost when arriving home](#30-minute-boost-when-arriving-home)
    - [Notification at boost end](#notification-at-boost-end)
    - [Dashboard boost button](#dashboard-boost-button)

## Purpose

The timed preset feature allows you to force a preset on a _VTherm_ for a specified duration. At the end of this duration, the original preset (the one defined in `requested_state`) is automatically restored.

This feature is useful in several scenarios:
- **Heating boost**: Temporarily increase the temperature (e.g., Comfort preset) for 30 minutes when you come home
- **Guest mode**: Activate a warmer preset for a few hours when hosting guests
- **Drying**: Force a high preset for a limited time to speed up room drying
- **Occasional savings**: Temporarily force an Eco preset during a short absence

## How it works

1. You call the `versatile_thermostat.set_timed_preset` service with a preset and duration
2. The _VTherm_ immediately switches to the specified preset
3. A timer is started for the indicated duration
4. At the end of the timer, the _VTherm_ automatically restores the original preset
5. A `versatile_thermostat_timed_preset_event` event is emitted on each change

> ![Tip](images/tips.png) _*Notes*_
> - The timed preset has an intermediate priority: it is applied after safety and power (load shedding) checks, but before other features (presence, motion, etc.)
> - If you manually change the preset while a timed preset is active, the timer is cancelled
> - The maximum duration is 1440 minutes (24 hours)

## Activate a timed preset

To activate a timed preset, use the `versatile_thermostat.set_timed_preset` service:

```yaml
service: versatile_thermostat.set_timed_preset
data:
  preset: "boost"
  duration_minutes: 30
target:
  entity_id: climate.my_thermostat
```

Parameters:
- `preset`: The name of the preset to activate. Must be a valid preset configured on the _VTherm_ (e.g., `eco`, `comfort`, `boost`, `frost`, etc.)
- `duration_minutes`: The duration in minutes (between 1 and 1440)

## Cancel a timed preset

To cancel a timed preset before its duration ends, use the `versatile_thermostat.cancel_timed_preset` service:

```yaml
service: versatile_thermostat.cancel_timed_preset
target:
  entity_id: climate.my_thermostat
```

When you cancel a timed preset, the original preset is immediately restored.

## Custom attributes

When a timed preset is active, the following attributes are available in the `timed_preset_manager` section of the _VTherm_ attributes:

| Attribute            | Meaning                                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------------------------ |
| `is_active`          | `true` if a timed preset is active, `false` otherwise                                                        |
| `preset`             | The name of the active timed preset (or `null` if none)                                                      |
| `original_preset`    | The preset restored at the end of the timed preset (or `null` if none)                                       |
| `end_time`           | The end date/time of the timed preset (ISO format, or `null` if none)                                        |
| `remaining_time_min` | The remaining time in minutes before the timed preset ends (integer)                                         |
| `is_manual_override` | `true` if the active timed preset is a manual override (see [below](#manual-override-with-automatic-revert)) |
| `resume_preset`      | The timed preset interrupted by the manual override, resumed at its end (or `null`)                          |
| `resume_end_time`    | The end date/time of the interrupted timed preset (ISO format, or `null`)                                    |

Example attributes:
```yaml
timed_preset_manager:
  is_active: true
  preset: "boost"
  original_preset: "comfort"
  end_time: "2024-01-15T14:30:00+00:00"
  remaining_time_min: 25
  is_manual_override: false
  resume_preset: null
  resume_end_time: null
```

## Events

The `versatile_thermostat_timed_preset_event` event is emitted when timed preset changes occur.

Event data:
- `entity_id`: The _VTherm_ identifier
- `name`: The _VTherm_ name
- `state_attributes`: The state attributes of the _VTherm_ at the time of the event
- `type`: `start` when a timed preset (or a manual override) starts, `end` when it ends
- `preset`: The timed preset concerned (the one that starts, or the one that has just ended)

Additional data for a `start` event:
- `duration_minutes`: The duration of the timed preset in minutes
- `end_time`: The end date/time of the timed preset (ISO format)
- `original_preset`: The preset that will be restored at the end
- `manual_override`: `true` if the event concerns a manual override

Additional data for an `end` event:
- `cause`: Why the timed preset ended: `expired` (the duration elapsed), `cancelled` (the `cancel_timed_preset` service was called) or `preset_selected` (a preset was selected manually)
- `restored_preset`: The preset restored after the end (can be `null` when a preset was selected manually)
- `manual_override`: `true` if the event concerns a manual override

## Manual override with automatic revert

When you change the target temperature manually, _VTherm_ normally switches to the `none` preset and stays there until you select a preset again. If a **manual override duration** is configured, _VTherm_ reverts automatically after this duration instead.

The duration is set in the advanced configuration (`manual_override_duration_min`, in minutes). It can be defined in the central configuration and overridden per _VTherm_. See [advanced configuration](feature-advanced.md#manual-override-duration). The default value `0` disables the feature, and the behaviour is then unchanged.

How it works:
1. A manual change of the target temperature (from the UI, from an automation calling `climate.set_temperature`, or from the underlying device when `Follow underlying temperature change` is enabled) starts a manual override. The manual temperature applies immediately.
2. Another manual change during the override restarts the timer with the full duration.
3. When the timer expires, the preset that was active before the manual change is restored.
4. If a timed preset was active when the manual change happened, it is resumed at the end of the override, until its own end time. If that end time has already passed, the preset that was active before the timed preset is restored.
5. If no preset was active (`none`) before the manual change, no override is started.

The manual override reuses the timed preset mechanism: it appears as a timed preset of `none` and survives a Home Assistant restart.

> ![Tip](images/tips.png) _*Notes*_
> - Selecting a preset during the manual override cancels it: the selected preset applies and nothing is reverted later.
> - Setting a timed preset during the manual override replaces it.
> - Cancelling the timed preset during the manual override restores the preset that was active before the manual change.
> - Window, safety, power and central mode keep their priority while the manual override is running.

The `timed_preset_manager` attributes `is_manual_override`, `resume_preset` and `resume_end_time` are described in the [Custom attributes](#custom-attributes) table. The `manual_override` field of the `versatile_thermostat_timed_preset_event` event is `true` when the event concerns a manual override.

## Automation examples

### 30-minute boost when arriving home

```yaml
automation:
  - alias: "Heating boost on arrival"
    trigger:
      - platform: state
        entity_id: binary_sensor.home_presence
        to: "on"
    condition:
      - condition: numeric_state
        entity_id: climate.living_room
        attribute: current_temperature
        below: 19
    action:
      - service: versatile_thermostat.set_timed_preset
        data:
          preset: "boost"
          duration_minutes: 30
        target:
          entity_id: climate.living_room
```

### Notification at boost end

```yaml
automation:
  - alias: "Boost end notification"
    trigger:
      - platform: event
        event_type: versatile_thermostat_timed_preset_event
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.type == 'end' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Thermostat"
          message: "The boost for {{ trigger.event.data.name }} has ended"
```

### Dashboard boost button

Create a button with a `button` card type:

```yaml
type: button
tap_action:
  action: call-service
  service: versatile_thermostat.set_timed_preset
  data:
    preset: boost
    duration_minutes: 30
  target:
    entity_id: climate.living_room
name: Boost 30 min
icon: mdi:fire
```
