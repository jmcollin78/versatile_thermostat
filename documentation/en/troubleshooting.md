
# Troubleshooting

- [Troubleshooting](#troubleshooting)
  - [Using a Heatzy](#using-a-heatzy)
  - [Using a radiator with a pilot wire (Nodon SIN-4-FP-21)](#using-a-radiator-with-a-pilot-wire-nodon-sin-4-fp-21)
  - [Only the first radiator heats](#only-the-first-radiator-heats)
  - [The radiator heats even though the setpoint temperature is exceeded, or it does not heat when the room temperature is well below the setpoint](#the-radiator-heats-even-though-the-setpoint-temperature-is-exceeded-or-it-does-not-heat-when-the-room-temperature-is-well-below-the-setpoint)
    - [Type `over_switch` or `over_valve`](#type-over_switch-or-over_valve)
    - [Type `over_climate`](#type-over_climate)
  - [Adjust the window open detection parameters in auto mode](#adjust-the-window-open-detection-parameters-in-auto-mode)
  - [Why is my Versatile Thermostat going into Safety Mode?](#why-is-my-versatile-thermostat-going-into-safety-mode)
    - [How to detect Safety Mode?](#how-to-detect-safety-mode)
    - [How to Be Notified When This Happens?](#how-to-be-notified-when-this-happens)
    - [How to Fix It?](#how-to-fix-it)
  - [Using a Group of People as a Presence Sensor](#using-a-group-of-people-as-a-presence-sensor)
  - [Enable Logs for the Versatile Thermostat](#enable-logs-for-the-versatile-thermostat)
  - [VTherm does not track setpoint changes made directly on the underlying device (`over_climate`)](#vtherm-does-not-track-setpoint-changes-made-directly-on-the-underlying-device-over_climate)


## Using a Heatzy

Using a Heatzy or Nodon is possible provided you use a virtual switch with this model:

```yaml
- platform: template
  switches:
    chauffage_sdb:
      unique_id: chauffage_sdb
      friendly_name: Bathroom heating
      value_template: "{{ is_state_attr('climate.bathroom', 'preset_mode', 'comfort') }}"
      icon_template: >-
        {% if is_state_attr('climate.bathroom', 'preset_mode', 'comfort') %}
          mdi:radiator
        {% elif is_state_attr('climate.bathroom', 'preset_mode', 'away') %}
          mdi:snowflake
        {% else %}
          mdi:radiator-disabled
        {% endif %}
      turn_on:
        service: climate.set_preset_mode
        entity_id: climate.bathroom
        data:
          preset_mode: "comfort"
      turn_off:
        service: climate.set_preset_mode
        entity_id: climate.bathroom
        data:
          preset_mode: "eco"
```
Thanks to @gael for this example.

## Using a radiator with a pilot wire (Nodon SIN-4-FP-21)
As with the Heatzy above, you can use a virtual switch that will change the preset of your radiator based on the VTherm’s on/off state.
Example:

```yaml
- platform: template
  switches:
    chauffage_chb_parents:
      unique_id: chauffage_chb_parents
      friendly_name: Chauffage chambre parents
      value_template: "{{ is_state('select.fp_chb_parents_pilot_wire_mode', 'comfort') }}"
      icon_template: >-
        {% if is_state('select.fp_chb_parents_pilot_wire_mode', 'comfort') %}
          mdi:radiator
        {% elif is_state('select.fp_chb_parents_pilot_wire_mode', 'frost_protection') %}
          mdi:snowflake
        {% else %}
          mdi:radiator-disabled
        {% endif %}
      turn_on:
        service: select.select_option
        target:
          entity_id: select.fp_chb_parents_pilot_wire_mode
        data:
          option: comfort
      turn_off:
        service: select.select_option
        target:
          entity_id: select.fp_chb_parents_pilot_wire_mode
        data:
          option: eco
```

Another more complex example is [here](https://github.com/jmcollin78/versatile_thermostat/discussions/431#discussioncomment-11393065)

## Only the first radiator heats

In `over_switch` mode, if multiple radiators are configured for the same VTherm, the heating will be triggered sequentially to smooth out the consumption peaks as much as possible.
This is completely normal and intentional. It is described here: [For a thermostat of type ```thermostat_over_switch```](#for-a-thermostat-of-type-thermostat_over_switch)

## The radiator heats even though the setpoint temperature is exceeded, or it does not heat when the room temperature is well below the setpoint

### Type `over_switch` or `over_valve`
With a VTherm of type `over_switch` or `over_valve`, this issue simply indicates that the TPI algorithm parameters are not properly configured. See [TPI Algorithm](#tpi-algorithm) to optimize the settings.

### Type `over_climate`
With a VTherm of type `over_climate`, the regulation is handled directly by the underlying `climate`, and VTherm simply transmits the setpoints to it. So if the radiator is heating even though the setpoint temperature is exceeded, it is likely that its internal temperature measurement is biased. This often happens with TRVs and reversible air conditioners that have an internal temperature sensor, either too close to the heating element (so it's too cold in winter).

Examples of discussions on these topics: [#348](https://github.com/jmcollin78/versatile_thermostat/issues/348), [#316](https://github.com/jmcollin78/versatile_thermostat/issues/316), [#312](https://github.com/jmcollin78/versatile_thermostat/discussions/312), [#278](https://github.com/jmcollin78/versatile_thermostat/discussions/278)

To resolve this, VTherm is equipped with a feature called self-regulation, which allows it to adjust the setpoint sent to the underlying device until the setpoint is met. This function compensates for the bias of internal temperature sensors. If the bias is significant, the regulation should also be significant. See [Self-regulation](self-regulation.md) for configuring self-regulation.

## Adjust the window open detection parameters in auto mode

If you are unable to configure the automatic window open detection function (see [auto](feature-window.md#auto-mode)), you can try modifying the temperature smoothing algorithm parameters.
Indeed, the automatic window open detection is based on calculating the temperature slope. To avoid artifacts caused by an imprecise temperature sensor, this slope is calculated using a temperature smoothed with an algorithm called Exponential Moving Average (EMA).
This algorithm has 3 parameters:
1. `lifecycle_sec`: the duration in seconds considered for smoothing. The higher it is, the smoother the temperature will be, but the detection delay will also increase.
2. `max_alpha`: if two temperature readings are far apart in time, the second one will carry much more weight. This parameter limits the weight of a reading that comes well after the previous one. This value must be between 0 and 1. The lower it is, the less distant readings are taken into account. The default value is 0.5, meaning that a new temperature reading will never weigh more than half of the moving average.
3. `precision`: the number of digits after the decimal point retained for calculating the moving average.

To change these parameters, you need to modify the `configuration.yaml` file and add the following section (the values below are the default values):

```yaml
versatile_thermostat:
  short_ema_params:
    max_alpha: 0.5
    halflife_sec: 300
    precision: 2
```

These parameters are sensitive and quite difficult to adjust. Please only use them if you know what you’re doing and if your temperature readings are not already smoothed.

## Why is my Versatile Thermostat going into Safety Mode?

Safety mode is only available for VTherm types `over_switch` and `over_valve`. It occurs when one of the two thermometers (providing either the room temperature or the external temperature) has not sent a value for more than `safety_delay_min` minutes, and the radiator had been heating at least `safety_min_on_percent`. See [safety mode](feature-advanced.md#safety-mode)

Since the algorithm relies on temperature measurements, if they are no longer received by the VTherm, there is a risk of overheating and fire. To prevent this, when the above conditions are detected, heating is limited to the `safety_default_on_percent` parameter. This value should therefore be reasonably low (10% is a good value). It helps avoid a fire while preventing the radiator from being completely turned off (risk of freezing).

All these parameters are configured on the last page of the VTherm configuration: "Advanced Settings".

### How to detect Safety Mode?
The first symptom is an unusually low temperature with a short and consistent heating time during each cycle.
Example:

[security mode](images/security-mode-symptome1.png)

If you have installed the [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card), the affected VTherm will appear like this:

[security mode UI Card](images/security-mode-symptome2.png)

You can also check the VTherm's attributes for the dates of the last received values. **The attributes are available in the Developer Tools / States**.

Example:

```yaml
security_state: true
last_temperature_datetime: "2023-12-06T18:43:28.346010+01:00"
last_ext_temperature_datetime: "2023-12-06T13:04:35.164367+01:00"
last_update_datetime: "2023-12-06T18:43:28.351103+01:00"
...
safety_delay_min: 60
```

We can see that:
1. The VTherm is indeed in safety mode (`security_state: true`),
2. The current time is 06/12/2023 at 18:43:28 (`last_update_datetime: "2023-12-06T18:43:28.351103+01:00"`),
3. The last reception time of the room temperature is 06/12/2023 at 18:43:28 (`last_temperature_datetime: "2023-12-06T18:43:28.346010+01:00"`), so it's recent,
4. The last reception time of the external temperature is 06/12/2023 at 13:04:35 (`last_ext_temperature_datetime: "2023-12-06T13:04:35.164367+01:00"`). The external temperature is over 5 hours late, which triggered the safety mode, as the threshold is set to 60 minutes (`safety_delay_min: 60`).

### How to Be Notified When This Happens?
The VTherm sends an event as soon as this happens and again at the end of the safety alert. You can capture these events in an automation and send a notification, blink a light, trigger a siren, etc. It's up to you.

For handling events generated by VTherm, see [Events](#events).

### How to Fix It?
It depends on the cause of the problem:
1. If a sensor is faulty, it should be repaired (replace batteries, change it, check the weather integration that provides the external temperature, etc.),
2. If the `safety_delay_min` parameter is too small, it may generate many false alerts. A correct value is around 60 minutes, especially if you have battery-powered temperature sensors. See [my settings](tuning-examples.md#battery-powered-temperature-sensor),
3. Some temperature sensors don't send measurements if the temperature hasn't changed. So if the temperature stays very stable for a long time, safety mode can trigger. This is not a big issue since it will deactivate once the VTherm receives a new temperature. On some thermometers (e.g., TuYA or Zigbee), you can force a max delay between two measurements. The max delay should be set to a value lower than `safety_delay_min`,
4. As soon as the temperature is received again, safety mode will turn off, and the previous preset, target temperature, and mode values will be restored.
5. If the external temperature sensor is faulty, you can disable safety mode triggering as it has a minimal impact on the results. To do so, see [here](feature-advanced.md#safety-mode).

## Using a Group of People as a Presence Sensor

Unfortunately, groups of people are not recognized as presence sensors. Therefore, you cannot use them directly in VTherm.
A workaround is to create a binary sensor template with the following code:

File `template.yaml`:

```yaml
- binary_sensor:
    - name: maison_occupee
      unique_id: maison_occupee
      state: "{{is_state('person.person1', 'home') or is_state('person.person2', 'home') or is_state('input_boolean.force_presence', 'on')}}"
      device_class: occupancy
```

In this example, note the use of an `input_boolean` called `force_presence`, which forces the sensor to `True`, thereby forcing any VTherm that uses it to have active presence. This can be used, for example, to trigger a pre-heating of the house when leaving work or when an unrecognized person is present in HA.

File `configuration.yaml`:

```yaml
...
template: !include templates.yaml
...
```

## Enable Logs for the Versatile Thermostat

Sometimes, you will need to enable logs to fine-tune your analysis. To do this, edit the `logger.yaml` file in your configuration and configure the logs as follows:

```yaml
default: xxxx
logs:
  custom_components.versatile_thermostat: info
```
You must reload the YAML configuration (Developer Tools / YAML / Reload all YAML configuration) or restart Home Assistant for this change to take effect.

Be careful, in debug mode, Versatile Thermostat is very verbose and can quickly slow down Home Assistant or saturate your hard drive. If you switch to debug mode for anomaly analysis, do so only for the time needed to reproduce the bug and disable debug mode immediately afterward.

## VTherm does not track setpoint changes made directly on the underlying device (`over_climate`)

See the details of this feature [here](over-climate.md#track-underlying-temperature-changes).