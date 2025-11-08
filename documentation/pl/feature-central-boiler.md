# Le contrôle d'une chaudière centrale# Controlling a Central Boiler

- [Le contrôle d'une chaudière centrale# Controlling a Central Boiler](#le-contrôle-dune-chaudière-centrale-controlling-a-central-boiler)
  - [Principle](#principle)
  - [Configuration](#configuration)
    - [How to Find the Right Action?](#how-to-find-the-right-action)
  - [Events](#events)
  - [Warning](#warning)

You can control a centralized boiler. As long as it's possible to trigger or stop the boiler from Home Assistant, Versatile Thermostat will be able to control it directly.

## Principle
The basic principle is as follows:
1. A new entity of type `binary_sensor`, named by default `binary_sensor.central_boiler`, is added.
2. In the configuration of the _VTherms_, you specify whether the _VTherm_ should control the boiler. In a heterogeneous installation, some _VTherms_ should control the boiler, and others should not. Therefore, you need to indicate in each _VTherm_ configuration whether it controls the boiler.
3. The `binary_sensor.central_boiler` listens for state changes in the equipment of the _VTherms_ marked as controlling the boiler.
4. When the number of devices controlled by the _VTherm_ requesting heating (i.e., when its `hvac_action` changes to `Heating`) exceeds a configurable threshold, the `binary_sensor.central_boiler` turns `on`, and **if an activation service has been configured, that service is called**.
5. If the number of devices requesting heating drops below the threshold, the `binary_sensor.central_boiler` turns `off`, and **if a deactivation service has been configured, that service is called**.
6. You have access to two entities:
   - A `number` type entity, named by default `number.boiler_activation_threshold`, which gives the activation threshold. This threshold is the number of devices (radiators) requesting heating.
   - A `sensor` type entity, named by default `sensor.nb_device_active_for_boiler`, which shows the number of devices requesting heating. For example, a _VTherm_ with 4 valves, 3 of which request heating, will make this sensor show 3. Only the devices from _VTherms_ marked to control the central boiler are counted.

You therefore always have the information to manage and adjust the triggering of the boiler.

All these entities are linked to the central configuration service:

![Boiler Control Entities](images/entitites-central-boiler.png)

## Configuration
To configure this feature, you need a centralized configuration (see [Configuration](#configuration)) and check the 'Add Central Boiler' box:

![Add a Central Boiler](images/config-central-boiler-1.png)

On the next page, you can provide the configuration for the actions (e.g., services) to be called when the boiler is turned on/off:

![Add a Central Boiler](images/config-central-boiler-2.png)

The actions (e.g., services) are configured as described on the page:
1. The general format is `entity_id/service_id[/attribute:value]` (where `/attribute:value` is optional).
2. `entity_id` is the name of the entity controlling the boiler in the form `domain.entity_name`. For example: `switch.chaudiere` for a boiler controlled by a switch, or `climate.chaudière` for a boiler controlled by a thermostat, or any other entity that allows boiler control (there is no limitation). You can also toggle inputs (`helpers`) such as `input_boolean` or `input_number`.
3. `service_id` is the name of the service to be called in the form `domain.service_name`. For example: `switch.turn_on`, `switch.turn_off`, `climate.set_temperature`, `climate.set_hvac_mode` are valid examples.
4. Some services require a parameter. This could be the 'HVAC Mode' for `climate.set_hvac_mode` or the target temperature for `climate.set_temperature`. This parameter should be configured in the format `attribute:value` at the end of the string.

Examples (to adjust to your case):
- `climate.chaudiere/climate.set_hvac_mode/hvac_mode:heat`: to turn the boiler thermostat on in heating mode.
- `climate.chaudiere/climate.set_hvac_mode/hvac_mode:off`: to turn off the boiler thermostat.
- `switch.pompe_chaudiere/switch.turn_on`: to turn on the switch powering the boiler pump.
- `switch.pompe_chaudiere/switch.turn_off`: to turn off the switch powering the boiler pump.
- ...

### How to Find the Right Action?
To find the correct action to use, it's best to go to "Developer Tools / Services", search for the action to call, the entity to control, and any required parameters.
Click 'Call Service'. If your boiler turns on, you have the correct configuration. Then switch to YAML mode and copy the parameters.

Example:

In "Developer Tools / Actions":

![Service Configuration](images/dev-tools-turnon-boiler-1.png)

In YAML mode:

![Service Configuration](images/dev-tools-turnon-boiler-2.png)

The service to configure will then be: `climate.sonoff/climate.set_hvac_mode/hvac_mode:heat` (note the removal of spaces in `hvac_mode:heat`).

Do the same for the off service, and you’re ready to go.

## Events

Each successful boiler activation or deactivation sends an event from Versatile Thermostat. This can be captured by an automation, for example, to notify you of the change.
The events look like this:

An activation event:
```yaml
event_type: versatile_thermostat_central_boiler_event
data:
  central_boiler: true
  entity_id: binary_sensor.central_boiler
  name: Central boiler
  state_attributes: null
origin: LOCAL
time_fired: "2024-01-14T11:33:52.342026+00:00"
context:
  id: 01HM3VZRJP3WYYWPNSDAFARW1T
  parent_id: null
  user_id: null
```yaml
event_type: versatile_thermostat_central_boiler_event
data:
  central_boiler: true
  entity_id: binary_sensor.central_boiler
  name: Central boiler
  state_attributes: null
origin: LOCAL
time_fired: "2024-01-14T11:33:52.342026+00:00"
context:
  id: 01HM3VZRJP3WYYWPNSDAFARW1T
  parent_id: null
  user_id: null
```

Un évènement d'extinction :
```yaml
event_type: versatile_thermostat_central_boiler_event
data:
  central_boiler: false
  entity_id: binary_sensor.central_boiler
  name: Central boiler
  state_attributes: null
origin: LOCAL
time_fired: "2024-01-14T11:43:52.342026+00:00"
context:
  id: 01HM3VZRJP3WYYWPNSDAFBRW1T
  parent_id: null
  user_id: null
```

## Warning

> ![Astuce](images/tips.png) _*Notes*_
>
> Software or home automation control of a central boiler may pose risks to its proper operation. Before using these functions, ensure that your boiler has proper safety features and that they are functioning correctly. For example, turning on a boiler with all valves closed can create excessive pressure.
