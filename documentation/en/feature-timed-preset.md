# Timed Preset

- [Timed Preset](#timed-preset)
  - [Purpose](#purpose)
  - [How it works](#how-it-works)
  - [Activate a timed preset](#activate-a-timed-preset)
  - [Cancel a timed preset](#cancel-a-timed-preset)
  - [Custom attributes](#custom-attributes)
  - [Events](#events)
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

| Attribute               | Meaning                                                              |
| ----------------------- | -------------------------------------------------------------------- |
| `timed_preset_active`   | `true` if a timed preset is active, `false` otherwise                |
| `timed_preset_preset`   | The name of the active timed preset (or `null` if none)              |
| `timed_preset_end_time` | The end date/time of the timed preset (ISO format)                   |
| `remaining_time_min`    | The remaining time in minutes before the timed preset ends (integer) |

Example attributes:
```yaml
timed_preset_manager:
  timed_preset_active: true
  timed_preset_preset: "boost"
  timed_preset_end_time: "2024-01-15T14:30:00+00:00"
  remaining_time_min: 25
```

## Events

The `versatile_thermostat_timed_preset_event` event is emitted when timed preset changes occur.

Event data:
- `entity_id`: The _VTherm_ identifier
- `name`: The _VTherm_ name
- `timed_preset_active`: `true` if a timed preset has just been activated, `false` if it has just been deactivated
- `timed_preset_preset`: The name of the timed preset
- `old_preset`: The previous preset (before timed preset activation)
- `new_preset`: The new active preset

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
        value_template: "{{ trigger.event.data.timed_preset_active == false }}"
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
