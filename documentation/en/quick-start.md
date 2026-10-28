# Quick Start

This page sums up the steps to get a working _VTherm_, whatever the controlled equipment. Each step links to the page that details it. For a tutorial by heating type (pilot wire, thermostatic valve, heat pump, pellet stove), see the [quick start guides of the website](https://www.versatile-thermostat.org/en/quick-start/). For the settings specific to a device, see its page in the [device catalog](https://www.versatile-thermostat.org/en/devices/).

- [Quick Start](#quick-start)
  - [Before You Start](#before-you-start)
  - [Create the VTherm](#create-the-vtherm)
  - [Set Up and Check](#set-up-and-check)
  - [Next Step](#next-step)

## Before You Start

- Versatile Thermostat is installed (see [Installation](installation.md)).
- The equipment to control is available in Home Assistant, as well as a room temperature sensor and an outdoor temperature sensor.
- You know which entity the equipment exposes (`climate`, `switch`, `select` or `number`): it determines the _VTherm_ type (see [Making the right choice](creation.md#making-the-right-choice)).

## Create the VTherm

1. **Add the integration** Versatile Thermostat from the integrations page and choose the _VTherm_ type that fits the equipment (see [Choosing a VTherm](creation.md)). The central configuration is optional: without it, leave the "Use central configuration" boxes unchecked.
2. **Main attributes**: give the _VTherm_ a name and choose the room temperature sensor, then the outdoor temperature sensor. Keep the default cycle duration (see [Choosing Basic Attributes](base-attributes.md)).
3. **Features**: do not enable any for now. You will add them once the _VTherm_ works.
4. **Underlyings**: select the entity of the equipment. The settings depend on the type:
   - [`over_climate`](over-climate.md): keep self-regulation disabled to start with. If the valve opening of a TRV can be controlled, choose [direct valve control](self-regulation.md#self-regulation-by-direct-valve-control) instead.
   - [`over_switch`](over-switch.md): a `switch` is enough. For a pilot wire module (`select`) or a `climate` entity, fill in the [custom commands](over-switch.md#command-customization).
   - [`over_valve`](over-valve.md): select the `number` entity of the valve.

   The settings specific to a device (entities to use, commands, known pitfalls) are on its page in the [device catalog](https://www.versatile-thermostat.org/en/devices/).
5. **TPI parameters**, if this menu is offered: keep the default values (see [the TPI coefficients](algorithms.md#configuring-the-tpi-algorithm-coefficients)).
6. **Presets**: validate the menu (see [Presets](feature-presets.md)).
7. **Advanced parameters**: keep the default values of the safety mode (see [Safety Parameters](feature-advanced.md#safety-parameters)).
8. **All done**: the _VTherm_ is created.

## Set Up and Check

1. Set the temperature of each preset with the entities of the _VTherm_ (see [Presets](feature-presets.md)).
2. Put the _VTherm_ in Heat mode and choose the Comfort preset, with a setpoint above the room temperature.
3. Check that the equipment reacts: the device receives the setpoint, the radiator turns on or the valve opens.

If nothing happens, see [Troubleshooting](troubleshooting.md), then [download the logs](feature-logs-collector.md) and open them in the [log analyzer](https://www.versatile-thermostat.org/en/debugger/) of the website.

## Next Step

Once this basic _VTherm_ works:

- install the UI card and a scheduler, presented in [Some Essential Add-Ons](additions.md),
- enable the useful [features](base-attributes.md#choosing-the-features-to-use) one at a time, checking each time that the _VTherm_ reacts correctly: [automatic start/stop](feature-auto-start-stop.md), [window detection](feature-window.md), [presence management](feature-presence.md)...
- then, if needed: [central configuration](creation.md#centralized-configuration), [centralized control](feature-central-mode.md), [central boiler](feature-central-boiler.md), [self-regulation tuning](self-regulation.md) and [tuning examples](tuning-examples.md).
