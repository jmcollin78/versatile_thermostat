---
name: Issue
about: Create a report to help us improve

---

> Please read carefuly this instructions and fill this form before writing an issue. It helps me to help you.

<!-- This template will allow the maintainer to be efficient and post the more accurante response as possible. There is many types / modes / configuration possible, so the analysis can be very tricky. If don't follow this template, your issue could be rejected without any message. Please help me to help you. -->

<!-- Before you open a new issue, search through the existing issues to see if others have had the same problem.

If you have a simple question or you are not sure this is an issue, don't open an issue but open a new discussion [here](https://github.com/jmcollin78/versatile_thermostat/discussions).

Check also in the [Troubleshooting](#troubleshooting) paragrah of the README if the aswer is not already given.

Issues not containing the minimum requirements will be closed:

- Issues without a description (using the header is not good enough) will be closed.
- Issues that don't follow this template could be closed

-->

## Version of the custom_component
<!-- If you are not using the newest version, download and try that before opening an issue
If you are unsure about the version check the manifest.json file.
-->

## Configuration

<!-- Copy / paste the attributes of the VTherm here. You can go to Development Tool / States, find and select your VTherm and the copy/paste the attributes. Surround these attributes by a yaml formatting ```yaml <put the attributes> .... ```
Without these attribute support is impossible due to the number of configuration attributes the VTherm have (more than 60). -->

My VTherm attributes are the following:
```yaml
hvac_modes:
  - heat
  - 'off'
min_temp: 7
max_temp: 35
preset_modes:
  - none
  - eco
  - comfort
  - boost
  - activity
current_temperature: 18.9
temperature: 22
hvac_action: 'off'
preset_mode: security
hvac_mode: 'off'
type: null
eco_temp: 17
boost_temp: 20
comfort_temp: 19
eco_away_temp: 16.1
boost_away_temp: 16.3
comfort_away_temp: 16.2
power_temp: 13
ext_current_temperature: 11.6
ac_mode: false
current_power: 450
current_power_max: 910
saved_preset_mode: none
saved_target_temp: 22
saved_hvac_mode: heat
window_state: 'on'
motion_state: 'off'
overpowering_state: false
presence_state: 'on'
window_auto_state: false
is_window_bypass: false
security_delay_min: 2
security_min_on_percent: 0.5
security_default_on_percent: 0.1
last_temperature_datetime: '2023-11-05T00:48:54.873157+01:00'
last_ext_temperature_datetime: '2023-11-05T00:48:53.240122+01:00'
security_state: true
minimal_activation_delay_sec: 1
device_power: 300
mean_cycle_power: 30
total_energy: 137.5
last_update_datetime: '2023-11-05T00:51:54.901140+01:00'
timezone: Europe/Paris
window_sensor_entity_id: input_boolean.fake_window_sensor1
window_delay_sec: 20
window_auto_open_threshold: null
window_auto_close_threshold: null
window_auto_max_duration: null
motion_sensor_entity_id: input_boolean.fake_motion_sensor1
presence_sensor_entity_id: input_boolean.fake_presence_sensor1
power_sensor_entity_id: input_number.fake_current_power
max_power_sensor_entity_id: input_number.fake_current_power_max
is_over_switch: true
underlying_switch_0: input_boolean.fake_heater_switch1
underlying_switch_1: null
underlying_switch_2: null
underlying_switch_3: null
on_percent: 0.1
on_time_sec: 6
off_time_sec: 54
cycle_min: 1
function: tpi
tpi_coef_int: 0.6
tpi_coef_ext: 0.01
friendly_name: Thermostat switch 1
supported_features: 17
```

<!-- Please do not send an image but a copy / paste of the attributes in yaml format. -->

## If it is releveant to regulation performance or optimisation some curves are needed
To have a great curves demonstrating what you think is a problem, please install and configure what is described here: [Even better with Plotly to tune your Thermostat](#even-better-with-plotly-to-tune-your-thermostat)

## Describe the bug
A clear and concise description of what the bug is.

I'm trying to:
<!-- compleete the description -->

And I expect:
<!-- complete the expectations -->

But I observe this ....
<!-- complete what you observe and why you think it is erroneous. -->

I read the documentation on the README.md file and I don't find any relevant information about this issue.


## Debug log

<!-- To enable debug logs check this https://www.home-assistant.io/components/logger/
Add the following configuration into your `configuration.yaml` (or `logger.yaml` if you have one) to enable logs:  -->

```yaml
logger:
    default: info
    logs:
        custom_components.versatile_thermostat: info
```

<!-- You can also switch to debug mode but be careful, in debug mode, the logs are verbose.
Please copy/paste the releveant logs (around the failure) below: -->

```text

Add your logs here.

```