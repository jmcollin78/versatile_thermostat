# Heating Failure Detection

- [Heating Failure Detection](#heating-failure-detection)
  - [Why this feature?](#why-this-feature)
  - [How it works](#how-it-works)
    - [Heating failure detection](#heating-failure-detection-1)
    - [Cooling failure detection](#cooling-failure-detection)
  - [Configuration](#configuration)
  - [Parameters](#parameters)
  - [Exposed attributes](#exposed-attributes)
  - [Events](#events)
  - [Automation examples](#automation-examples)
    - [Persistent notification for heating failure](#persistent-notification-for-heating-failure)
    - [Persistent notification for all failure types](#persistent-notification-for-all-failure-types)
    - [Automatically dismiss notification when failure is resolved](#automatically-dismiss-notification-when-failure-is-resolved)

## Why this feature?

Heating failure detection allows you to monitor the proper operation of your heating system. It detects two types of abnormal situations:

1. **Heating failure**: the thermostat is requesting a lot of power (high `on_percent`) but the temperature is not increasing. This may indicate:
   - a faulty or turned off radiator,
   - a stuck thermostatic valve,
   - an undetected open window,
   - a hot water circulation problem (central heating).

2. **Cooling failure**: the thermostat is not requesting power (`on_percent` at 0) but the temperature keeps rising. This may indicate:
   - a radiator that stays on despite the stop command,
   - a relay stuck in the "on" position,
   - an underlying device that is no longer responding.

> ![Tip](images/tips.png) _*Important*_
>
> This feature **does not change the thermostat's behavior**. It only sends events to alert you of an abnormal situation. It is up to you to create the necessary automations to react to these events (notifications, alerts, etc.).

## How it works

This feature only applies to _VTherm_ using the TPI algorithm (over_switch, over_valve, or over_climate with valve regulation). Therefore, `over_climate` _VTherms_ that control a heat pump, for example, are not affected. Indeed, in this case, the heating decision is made by the underlying device itself, which prevents access to reliable information.

This function only applies to Heating mode (`hvac_mode=heat`). In cooling mode (`hvac_mode=cool`) no detection is performed to avoid false positives.

### Heating failure detection

1. The _VTherm_ is in heating mode,
2. The `on_percent` is greater than or equal to the configured threshold (default 90%),
3. This situation has lasted longer than the detection delay (default 15 minutes),
4. The temperature has not increased during this period.

➡️ A `versatile_thermostat_heating_failure_event` event is emitted with `failure_type: heating` and `type: heating_failure_start`.

When the situation returns to normal (temperature rising or `on_percent` dropping), an event with `type: heating_failure_end` is emitted.

### Cooling failure detection

1. The _VTherm_ is in heating mode,
2. The `on_percent` is less than or equal to the configured threshold (default 0%),
3. This situation has lasted longer than the detection delay (default 15 minutes),
4. The temperature continues to rise.

➡️ A `versatile_thermostat_heating_failure_event` event is emitted with `failure_type: cooling` and `type: cooling_failure_start`.

When the situation returns to normal, an event with `type: cooling_failure_end` is emitted.

## Configuration

Like many _VTherm_ features, this functionality can be configured **in the central configuration** to share parameters. To apply it to the chosen _VTherms_, the user must add the feature (see "Features" menu) and choose to use the common parameters from the central configuration or specify new ones that will only be applied to this _VTherm_.

To access it:
1. Go to the configuration of your "Central Configuration" type _VTherm_
2. In the menu, select "Heating failure detection"
3. Then go to the configuration of the relevant _VTherms_,
4. Select the "Features" menu,
5. Check the "Heating failure detection" feature,
6. Choose to use the central configuration parameters or specify new ones.

![Configuration](images/config-heating-failure-detection.png)

## Parameters

| Parameter                            | Description                                                                                                         | Default value |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------- | ------------- |
| **Enable heating failure detection** | Enables or disables the feature                                                                                     | Disabled      |
| **Heating failure threshold**        | `on_percent` percentage above which heating should cause temperature to increase. Value between 0 and 1 (0.9 = 90%) | 0.9 (90%)     |
| **Cooling failure threshold**        | `on_percent` percentage below which temperature should not increase. Value between 0 and 1 (0 = 0%)                 | 0.0 (0%)      |
| **Detection delay (minutes)**        | Waiting time before declaring a failure. Helps avoid false positives due to normal fluctuations                     | 15 minutes    |

> ![Tip](images/tips.png) _*Tuning tips*_
>
> - **Heating threshold**: If you have false positives (failure detection when everything is working), increase this threshold to 0.95 or 1.0.
> - **Cooling threshold**: If you want to detect a radiator that stays on even with a low `on_percent`, increase this threshold to 0.05 or 0.1.
> - **Detection delay**: Increase this delay if you have rooms with high thermal inertia (large rooms, underfloor heating, etc.). You can look at the heating curves (see [additions](additions.md#regulation-curves-with-plotly)) and see how long it takes for your thermometer to increase after heating is triggered. This duration should be the minimum for this parameter.

## Exposed attributes

_VTherms_ with TPI expose the following attributes:

```yaml
is_heating_failure_detection_configured: true
heating_failure_detection_manager:
  heating_failure_state: "off"      # "on", "off", "unknown", "unavailable"
  cooling_failure_state: "off"      # "on", "off", "unknown", "unavailable"
  heating_failure_threshold: 0.9
  cooling_failure_threshold: 0.0
  detection_delay_min: 15
```

## Events

The `versatile_thermostat_heating_failure_event` event is emitted when a failure is detected or ends.

Event data:
| Field                    | Description                                                                                                |
| ------------------------ | ---------------------------------------------------------------------------------------------------------- |
| `entity_id`              | The _VTherm_ identifier                                                                                    |
| `name`                   | The _VTherm_ name                                                                                          |
| `type`                   | Event type: `heating_failure_start`, `heating_failure_end`, `cooling_failure_start`, `cooling_failure_end` |
| `failure_type`           | Failure type: `heating` or `cooling`                                                                       |
| `on_percent`             | The power percentage requested at the time of detection                                                    |
| `temperature_difference` | The temperature difference observed during the detection period                                            |
| `current_temp`           | The current temperature                                                                                    |
| `target_temp`            | The target temperature                                                                                     |
| `threshold`              | The configured threshold that triggered the detection                                                      |
| `detection_delay_min`    | The configured detection delay                                                                             |
| `state_attributes`       | All entity attributes at the time of the event                                                             |

## Automation examples

### Persistent notification for heating failure

This automation creates a persistent notification when a heating failure is detected:

```yaml
- alias: "Heating failure alert"
  description: "Creates a persistent notification when heating failure is detected"
  trigger:
    - platform: event
      event_type: versatile_thermostat_heating_failure_event
  condition:
    - condition: template
      value_template: "{{ trigger.event.data.type == 'heating_failure_start' }}"
  action:
    - service: persistent_notification.create
      data:
        title: "🔥 Heating failure detected"
        message: >
          The thermostat **{{ trigger.event.data.name }}** has detected a heating failure.

          📊 **Details:**
          - Power requested: {{ (trigger.event.data.on_percent * 100) | round(0) }}%
          - Current temperature: {{ trigger.event.data.current_temp }}°C
          - Target temperature: {{ trigger.event.data.target_temp }}°C
          - Temperature change: {{ trigger.event.data.temperature_difference | round(2) }}°C

          ⚠️ The heating is running at full power but the temperature is not increasing.
          Check that the radiator is working properly.
        notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
```

### Persistent notification for all failure types

This automation handles both failure types (heating and cooling):

```yaml
- alias: "Heating anomaly alert"
  description: "Notification for all types of heating failures"
  trigger:
    - platform: event
      event_type: versatile_thermostat_heating_failure_event
  condition:
    - condition: template
      value_template: "{{ trigger.event.data.type in ['heating_failure_start', 'cooling_failure_start'] }}"
  action:
    - service: persistent_notification.create
      data:
        title: >
          {% if trigger.event.data.failure_type == 'heating' %}
            🔥 Heating failure detected
          {% else %}
            ❄️ Cooling failure detected
          {% endif %}
        message: >
          The thermostat **{{ trigger.event.data.name }}** has detected an anomaly.

          📊 **Details:**
          - Failure type: {{ trigger.event.data.failure_type }}
          - Power requested: {{ (trigger.event.data.on_percent * 100) | round(0) }}%
          - Current temperature: {{ trigger.event.data.current_temp }}°C
          - Target temperature: {{ trigger.event.data.target_temp }}°C
          - Temperature change: {{ trigger.event.data.temperature_difference | round(2) }}°C

          {% if trigger.event.data.failure_type == 'heating' %}
          ⚠️ The heating is running at {{ (trigger.event.data.on_percent * 100) | round(0) }}% but the temperature is not increasing.
          Check that the radiator is working properly.
          {% else %}
          ⚠️ The heating is off but the temperature keeps rising.
          Check that the radiator turns off properly.
          {% endif %}
        notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
```

### Automatically dismiss notification when failure is resolved

This automation dismisses the persistent notification when the failure is resolved:

```yaml
- alias: "Heating anomaly resolved"
  description: "Dismisses the notification when the failure is resolved"
  trigger:
    - platform: event
      event_type: versatile_thermostat_heating_failure_event
  condition:
    - condition: template
      value_template: "{{ trigger.event.data.type in ['heating_failure_end', 'cooling_failure_end'] }}"
  action:
    - service: persistent_notification.dismiss
      data:
        notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
    - service: persistent_notification.create
      data:
        title: "✅ Anomaly resolved"
        message: >
          The thermostat **{{ trigger.event.data.name }}** is working normally again.
        notification_id: "heating_failure_resolved_{{ trigger.event.data.entity_id }}"
    # Automatically dismiss the resolution notification after 1 hour
    - delay:
        hours: 1
    - service: persistent_notification.dismiss
      data:
        notification_id: "heating_failure_resolved_{{ trigger.event.data.entity_id }}"
```

> ![Tip](images/tips.png) _*Notes*_
>
> 1. Persistent notifications remain displayed until the user closes them or they are dismissed by an automation.
> 2. Using `notification_id` allows you to update or dismiss a specific notification.
> 3. You can adapt these automations to send notifications on mobile, Telegram, or any other notification service.
> 4. This feature only works with _VTherms_ using the TPI algorithm (over_switch, over_valve, or over_climate with valve regulation).
