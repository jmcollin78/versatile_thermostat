# Versatile Thermostat Documentation

Versatile Thermostat (_VTherm_) is a Home Assistant integration that turns your heat pump, air conditioner or any HVAC system controlled by a `climate` entity into a smart thermostat: presets, window detection, presence, automatic start/stop and self-regulation to reach the target temperature.

_VTherm_ also controls electric radiators and thermostatic radiator valves. All features are configured from the Home Assistant interface, without scripts or complex automations: nobody home, a window open, a room that does not reach its setpoint? The thermostat handles it natively.

- [Versatile Thermostat Documentation](#versatile-thermostat-documentation)
  - [Installation Example](#installation-example)
  - [Supported Equipment](#supported-equipment)
  - [Prerequisites](#prerequisites)
  - [Devices](#devices)
  - [Documentation Contents](#documentation-contents)
    - [Getting Started](#getting-started)
    - [VTherm Types](#vtherm-types)
    - [Features](#features)
    - [Regulation](#regulation)
    - [Help and Reference](#help-and-reference)
    - [Going Further](#going-further)
  - [Next Step](#next-step)

## Installation Example

For heat pumps and air conditioners:

1. Create a _VTherm_ of type [`over_climate`](over-climate.md) on top of the existing `climate` entity of your heat pump or air conditioner. The device keeps its own regulation and _VTherm_ adds its features on top of it.
2. The [heat pump quick start](https://www.versatile-thermostat.org/en/quick-start/heat-pump/) of the website details the configuration step by step.
3. If the device does not reach the target temperature, enable [self-regulation](self-regulation.md): _VTherm_ then adjusts the setpoint sent to the device.
4. Add the useful features: [automatic start/stop](feature-auto-start-stop.md) to stop the device when it is not needed, [window detection](feature-window.md), [presence management](feature-presence.md), and the [auto-fan](over-climate.md#auto-fan-auto-ventilation) to speed up the fan when the temperature gap is large.

## Supported Equipment

_VTherm_ controls the heating and cooling equipment available in Home Assistant:

- **Heat pumps, air conditioners and HVAC systems** exposed by a `climate` entity: [heat pump guide](https://www.versatile-thermostat.org/en/quick-start/heat-pump/),
- **Water radiators** fitted with thermostatic radiator valves (TRV), with or without direct valve control: [TRV guide](https://www.versatile-thermostat.org/en/quick-start/trv/),
- **Electric radiators**, controlled by a switch or by a pilot wire module: [pilot wire guide](https://www.versatile-thermostat.org/en/quick-start/pilot-wire/),
- **Valves** controlled by a `number` entity, without an associated thermostat,
- **Pellet stoves**, with the [VTherm Pellet stove](https://www.versatile-thermostat.org/en/plugins/#jmcollin78/vtherm_pellet_stove) plugin: [pellet stove guide](https://www.versatile-thermostat.org/en/quick-start/pellet-stove/),
- **Central boiler**: _VTherm_ turns it on as soon as a room needs heating (see [Controlling a Central Boiler](feature-central-boiler.md)).

The _VTherm_ type to create for each piece of equipment is explained in [Choosing a VTherm](creation.md#making-the-right-choice).

## Prerequisites

- Home Assistant and the Versatile Thermostat integration installed from HACS (see [Installation](installation.md)),
- the equipment to control, available in Home Assistant,
- a room temperature sensor: any sensor available in Home Assistant can be used, or an `input_number`,
- an outdoor temperature sensor: the Home Assistant weather integration is enough.

## Devices

The heat pumps, air conditioners and other devices exposed by a `climate` entity that have been tested with _VTherm_ are listed in the [device catalog](https://www.versatile-thermostat.org/en/devices/?type=climate) of the website, with their support level and configuration advice. The catalog also lists [thermometers](https://www.versatile-thermostat.org/en/devices/?type=sensor), [thermostatic valves](https://www.versatile-thermostat.org/en/devices/?type=trv) and [electric heating devices](https://www.versatile-thermostat.org/en/devices/?type=electric).

This catalog is not exhaustive: a device that is not listed is not necessarily incompatible. The [incompatible devices](https://www.versatile-thermostat.org/en/devices/?state=unsupported) and the [partially supported devices](https://www.versatile-thermostat.org/en/devices/?state=partially) are described there with their known limitations.

## Documentation Contents

### Getting Started

- [Installation](installation.md): install the integration with HACS.
- [Quick Start](quick-start.md): a working _VTherm_ in a few steps, depending on your equipment.
- [Choosing a VTherm](creation.md): centralized configuration or not, choice of the _VTherm_ type.
- [Choosing Basic Attributes](base-attributes.md): name, temperature sensors and features to enable.

### VTherm Types

- [`over_climate` Type Thermostat](over-climate.md): heat pumps, air conditioners and thermostatic valves exposed by a `climate` entity.
- [`over_switch` Type Thermostat](over-switch.md): electric radiators controlled by a switch or a pilot wire.
- [`over_valve` Type Thermostat](over-valve.md): valves controlled by a `number` entity.

### Features

- **Comfort and savings**
  - [Presets](feature-presets.md): preset temperatures (Comfort, Eco, Frost protection...).
  - [Timed Preset](feature-timed-preset.md): apply a preset for a given duration.
  - [Presence Management](feature-presence.md): lower the setpoint when nobody is home.
  - [Motion Detection](feature-motion.md): change the preset depending on the activity in the room.
  - [Door/Window Open Detection](feature-window.md): react when a door or a window is opened.
  - [External Humidity Sensor](feature-humidity.md): display the humidity measured by an external sensor.
- **Controlling the installation**
  - [Auto-start / Auto-stop](feature-auto-start-stop.md): stop an `over_climate` when it is not needed.
  - [Power Management (Load Shedding)](feature-power.md): do not exceed the available power.
  - [Centralized Control](feature-central-mode.md): control all the _VTherm_ at once.
  - [Central Boiler](feature-central-boiler.md): turn the boiler on when a _VTherm_ needs heating.
  - [Lock Feature](feature-lock.md): prevent changes from the interface or from automations.
- **Safety**
  - [Advanced Configuration and Safety Mode](feature-advanced.md): sensor that stops responding, incorrect equipment state.
  - [Heating Failure Detection](feature-heating-failure-detection.md): the temperature does not follow the command.

### Regulation

- [Self-regulation](self-regulation.md): adjust the setpoint sent to an `over_climate`, or control the valve directly.
- [Internal Device Temperature Synchronization](feature-sync_device_temp.md): align the internal thermometer of the device with the room temperature.
- [The Different Algorithms Used](algorithms.md): TPI, SmartPI and other algorithms available as plugins.
- [Auto TPI](feature-autotpi.md): automatic learning of the TPI coefficients.
  - [Auto TPI: In-Depth Technical Guide](feature-autotpi-technical.md)
- [Valve Recalibration](feature-recalibrate-valves.md): the `recalibrate_valves` service.
- [Tuning Examples](tuning-examples.md): commented settings for different types of installation.

### Help and Reference

- [Troubleshooting](troubleshooting.md): common problems and their solutions.
- [Download Past Logs](feature-logs-collector.md): collect targeted logs, then open them in the [log analyzer](https://www.versatile-thermostat.org/en/debugger/) of the website.
- [Reference Documentation](reference.md): parameters, sensors, actions, events and attributes.
- [Release Notes](releases.md)

### Going Further

- [Some Essential Add-Ons](additions.md): UI card, scheduler, curves, notifications.
- [Plugins catalog](https://www.versatile-thermostat.org/en/plugins/): algorithms, cards and device helpers.
- [Device catalog](https://www.versatile-thermostat.org/en/devices/): tested devices and their support level.
- [Comparisons](https://www.versatile-thermostat.org/en/versus/): _VTherm_ compared with the generic thermostat, Better Thermostat and other solutions.

## Next Step

[Installation](installation.md): install Versatile Thermostat in Home Assistant.

For common equipment, the [quick start](quick-start.md) sums up the whole configuration on a single page.
