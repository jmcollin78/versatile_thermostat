# Quick Start

This page outlines the steps to quickly set up a basic yet operational _VTherm_. It is structured by equipment type.

- [Quick Start](#quick-start)
  - [Nodon SIN-4-FP-21 or similar (pilot wire)](#nodon-sin-4-fp-21-or-similar-pilot-wire)
  - [Heatzy, eCosy, or similar (`climate` entity)](#heatzy-ecosy-or-similar-climate-entity)
  - [Simple switch such as Aqara T1, Nous B2Z, Sonoff ZBMini, Sonoff POW, ...](#simple-switch-such-as-aqara-t1-nous-b2z-sonoff-zbmini-sonoff-pow-)
  - [Sonoff TRVZB or similar (TRV with valve control)](#sonoff-trvzb-or-similar-trv-with-valve-control)
  - [Reversible HP Units, Air Conditioning, or Devices Controlled via a `climate` Entity](#reversible-hp-units-air-conditioning-or-devices-controlled-via-a-climate-entity)
- [Next Steps](#next-steps)
- [Call for Contributions](#call-for-contributions)

## Nodon SIN-4-FP-21 or similar (pilot wire)

This module allows controlling a radiator via a pilot wire. It appears in _HA_ as a `select` entity that lets you choose the heating preset to apply.

_VTherm_ will regulate the temperature by periodically changing the preset via customized commands until the setpoint is reached.

For this to work, the preset used for heating control must be higher than the maximum temperature you will need (24°C is a good value).

To integrate it into _VTherm_, you must:
1. Create a _VTherm_ of type `over_switch`. See [creating a _VTherm_](creation.md),
2. Assign it the main attributes (name, room temperature sensor, and outdoor temperature sensor at a minimum). See [main attributes](base-attributes.md),
3. Assign one or more underlying devices to control. The underlying device here is the `select` entity that controls the Nodon. See [underlying devices](over-switch.md),
4. Provide custom on/off commands (mandatory for the Nodon). See [command customization](over-switch.md#command-customization). The custom commands follow the format `select_option/option:<preset>` as indicated in the link.

After completing these four steps, you will have a fully functional _VTherm_ that controls your Nodon or similar device.

## Heatzy, eCosy, or similar (`climate` entity)

This module allows controlling a radiator that appears in _HA_ as a `climate` entity, enabling you to choose the heating preset or mode (Heat / Cool / Off).

_VTherm_ will regulate the temperature by turning the device on/off via customized commands at regular intervals until the setpoint is reached.

To integrate it into _VTherm_, you must:
1. Create a _VTherm_ of type `over_switch`. See [creating a _VTherm_](creation.md),
2. Assign it the main attributes (name, room temperature sensor, and outdoor temperature sensor at a minimum). See [main attributes](base-attributes.md),
3. Assign one or more underlying devices to control. The underlying device here is the `climate` entity that controls the Heatzy or eCosy. See [underlying devices](over-switch.md),
4. Provide custom on/off commands (mandatory). See [command customization](over-switch.md#command-customization). The custom commands follow the format `set_hvac_mode/hvac_mode:<mode>` or `set_preset_mode/preset_mode:<preset>` as indicated in the link.

After completing these four steps, you will have a fully functional _VTherm_ that controls your Heatzy, eCosy, or similar device.

## Simple switch such as Aqara T1, Nous B2Z, Sonoff ZBMini, Sonoff POW, ...

This module allows controlling a radiator via a simple switch. It appears in _HA_ as a `switch` entity that directly turns the radiator on or off.

_VTherm_ will regulate the temperature by periodically turning the `switch` on and off until the setpoint is reached.

To integrate it into _VTherm_, you must:
1. Create a _VTherm_ of type `over_switch`. See [creating a _VTherm_](creation.md),
2. Assign it the main attributes (name, room temperature sensor, and outdoor temperature sensor at a minimum). See [main attributes](base-attributes.md),
3. Assign one or more underlying devices to control. The underlying device here is the `switch` entity that controls the switch. See [underlying devices](over-switch.md).

After completing these three steps, you will have a fully functional _VTherm_ that controls your `switch` or similar device.

## Sonoff TRVZB or similar (TRV with valve control)

This type of _TRV_ device controls the opening of a valve that allows more or less hot water from a boiler or heat pump to flow. It appears in _HA_ as a `climate` entity along with `number` entities that control the valve. These `number` entities may be hidden and need to be explicitly added in some cases.

_VTherm_ will adjust the valve opening degree until the setpoint temperature is reached.

To integrate it into _VTherm_, you must:
1. Create a _VTherm_ of type `over_climate`. See [creating a _VTherm_](creation.md),
2. Assign it the main attributes (name, room temperature sensor, and outdoor temperature sensor at a minimum). See [main attributes](base-attributes.md),
3. Assign one or more underlying devices to control. The underlying device here is the `climate` entity that controls the TRV. See [underlying devices](over-climate.md),
4. Specify the regulation type as `Direct valve control` only. Leave the option `Compensate for underlying temperature` unchecked. See [auto-regulation](over-climate.md#auto-regulation),
5. Provide the `number` entities named `opening_degree`, `closing_degree` and `calibration_offset`. See [underlying devices](over-switch.md).

For this to work, the `closing degree` must be set to the maximum (100%). Do not immediately enable the `Follow underlying temperature change` option until you have verified that this basic configuration is working properly.

After completing these five steps, you will have a fully functional _VTherm_ that controls your Sonoff TRVZB or similar device.

## Reversible HP Units, Air Conditioning, or Devices Controlled via a `climate` Entity

Reversible heat pumps (HP) or similar devices are represented in _HA_ as a `climate` entity, allowing you to select the heating preset or mode (Heat / Cool / Off).)

_VTherm_ will regulate the temperature by controlling the target temperature and mode of the device through commands sent to the underlying `climate` entity.

To integrate it into _VTherm_, you need to:
1. Create a _VTherm_ of type `over_climate`. See [creating a _VTherm_](creation.md),
2. Assign it the main attributes (name, room temperature sensor, and outdoor temperature sensor at minimum). See [main attributes](base-attributes.md),
3. Define one or more underlying devices to control. The underlying entity here is the `climate` entity that manages the heat pump or air conditioner. See [underlying devices](over-climate.md),

After these three steps, you will have a fully operational _VTherm_ to control your heat pump, air conditioner, or similar device.

To go further, self-regulation may be necessary depending on how well your device operates. Self-regulation involves _VTherm_ slightly adjusting the target temperature to encourage the device to heat or cool more or less until the desired setpoint is reached. Self-regulation is explained in detail here: [self-regulation](self-regulation.md).

# Next Steps

Once created, you need to configure the preset temperatures. See [presets](feature-presets.md) for a minimal configuration.
You can also (optional but recommended) install the dedicated UI card for your dashboards. (See [VTHerm UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card))

Once this minimal setup is functional—and only once it works correctly—you can add additional features such as presence detection to avoid heating when no one is present. Add them one by one, verifying that _VTherm_ reacts correctly at each step before proceeding to the next.

You can then set up centralized configurations to share settings across all _VTherm_ instances, enable central mode for unified control of all _VTherms_ ([centralized configuration](feature-central-mode.md)), or integrate a central boiler control ([central boiler](feature-central-boiler.md)). This is not an exhaustive list—please refer to the table of contents for a complete list of _VTherm_ features.

# Call for Contributions

This page is open for contributions. Feel free to suggest additional equipment and minimal configuration setups.
