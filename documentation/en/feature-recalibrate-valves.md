````markdown
# Valve recalibration (service recalibrate_valves)

- [Valve recalibration (service recalibrate_valves)](#valve-recalibration-service-recalibrate_valves)
  - [Why this feature?](#why-this-feature)
  - [How it works](#how-it-works)
  - [Restrictions and prerequisites](#restrictions-and-prerequisites)
  - [Configuration / accessing the service](#configuration--accessing-the-service)
  - [Service parameters](#service-parameters)
  - [Detailed behaviour](#detailed-behaviour)
  - [Automation examples](#automation-examples)

## Why this feature?

The `recalibrate_valves` service executes a simple valve recalibration procedure for thermostatic radiator valves (TRVs) controlled by a VTherm in valve regulation mode. It temporarily forces the underlying valve actuators to their extreme positions (fully open then fully closed) to help calibrate the thermostat's valve settings.

This service is useful when you suspect incorrect open/close values, miscalibrated valves, or after installation/maintenance of the underlying equipment. For example, if a radiator heats even when its valve is reported closed, recalibration may help.

⚠️ The actual recalibration depends on the underlying valve device. VTherm only forces open/close commands. If the device does not react correctly, contact your TRV vendor or use the device manufacturer's calibration procedure if available.

⚠️ Recalibrating may reduce battery life on battery-powered TRVs. Use it only when necessary.

## How it works

The service performs these steps for the targeted entity:

1. Verify the target entity is a `ThermostatClimateValve` (valve regulation). Otherwise the service returns an error.
2. Verify each underlying valve has two `number` entities configured for opening and closing (attributes `opening_degree` and `closing_degree`). If any valve lacks these entities the service refuses the operation.
3. Memorize the thermostat's requested state (`requested_state`).
4. Set VTherm HVAC mode to OFF.
5. Wait `delay_seconds`.
6. For each valve: force opening to 100% (send mapped value to the `number` entity). Wait `delay_seconds`.
7. For each valve: force closing to 100% (send mapped value to the `number` entity). Wait `delay_seconds`.
8. Restore the original requested state and update states/attributes.

During the procedure VTherm sends direct values to the valve `number` entities, bypassing normal algorithm thresholds and protections. The service runs in background and returns immediately: `{"message": "calibrage en cours"}`.

The delay between steps is specified by the caller. The service accepts a value between `0` and `300` seconds (0–5 minutes). In practice 10–60 seconds is usually appropriate depending on valve speed; 10 s is a good starting point for most electric actuators.

## Restrictions and prerequisites

- The service is available only for `ThermostatClimateValve` thermostats (valve regulation).
- Each underlying valve must have two `number` entities configured:
  - `opening_degree_entity_id` (open command)
  - `closing_degree_entity_id` (close command)
- `number` entities may define `min` and `max` attributes; the service maps 0–100% linearly to that range. If `min`/`max` are missing, the default range is 0–100.
- The service guards against concurrent executions for the same entity: if a recalibration is already running for this thermostat, a new request is refused immediately.

## Configuration / accessing the service

The service is registered as an entity service. Call it by targeting the climate entity in Home Assistant.

Service name: `versatile_thermostat.recalibrate_valves`

Example via Developer Tools / Services:

```yaml
service: versatile_thermostat.recalibrate_valves
target:
  entity_id: climate.my_thermostat
data:
  delay_seconds: 30
```

The service returns immediately:

```json
{"message": "calibrage en cours"}
```

## Service parameters

| Parameter       | Type    | Description                                                                                              |
| --------------- | ------- | -------------------------------------------------------------------------------------------------------- |
| `delay_seconds` | integer | Delay (seconds) to wait after full opening and after full closing. Valid range: 0–300 (recommended: 10). |

The service schema limits the value to `0`–`300` seconds.

## Detailed behaviour

- The operation runs as a background task. The caller receives an immediate acknowledgement and can follow progress in Home Assistant logs.
- At the end of the operation the requested state (`requested_state`) is restored (HVAC mode, target temperature and preset if present) and states are updated. The VTherm should return to its original state assuming sensors remain stable.

## Automation examples

1) Run the recalibration once a month (example):

The YAML below triggers recalibration at 03:00 on the first day of each month:

```yaml
alias: Monthly valve recalibration
trigger:
  - platform: time
    at: '03:00:00'
condition:
  - condition: template
    value_template: "{{ now().day == 1 }}"
  - condition: state
    entity_id: climate.my_thermostat
    state: 'off'
action:
  - service: versatile_thermostat.recalibrate_valves
    target:
      entity_id: climate.my_thermostat
    data:
      delay_seconds: 60
  - service: persistent_notification.create
    data:
      title: "🔧 Monthly recalibration started"
      message: "🔧 A valve recalibration was started for climate.my_thermostat"
```

> ![Tip](images/tips.png) _*Advice*_
>
> - Test recalibration on a single VTherm first and check logs and `number` values before running it on multiple devices.
> - Set `delay_seconds` long enough for the physical valve to reach the position (60 s is a reasonable start for most valves).

````
