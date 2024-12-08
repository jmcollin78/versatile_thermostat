# `over_switch` Type Thermostat

- [`over_switch` Type Thermostat](#over_switch-type-thermostat)
  - [Prerequisites](#prerequisites)
  - [Configuration](#configuration)
    - [The Underlying Entities](#the-underlying-entities)
    - [Keep-Alive](#keep-alive)
    - [AC Mode](#ac-mode)
    - [Command Inversion](#command-inversion)


## Prerequisites

The installation should look like this:

![installation `over_switch`](images/over-switch-schema.png)

1. The user or automation, or the Scheduler, sets a setpoint via a preset or directly using a temperature.
2. Periodically, the internal thermometer (2) or external thermometer (2b) sends the measured temperature. The internal thermometer should be placed in a relevant spot for the user's comfort: ideally in the middle of the living space. Avoid placing it too close to a window or too near the radiator.
3. Based on the setpoint values, the different temperatures, and the TPI algorithm parameters (see [TPI](algorithms.md#lalgorithme-tpi)), VTherm will calculate a percentage of the on-time.
4. It will then regularly command the turning on and off of the underlying `switch` entities.
5. These underlying switch entities will control the physical switch.
6. The physical switch will turn the radiator on or off.

> The on-time percentage is recalculated each cycle, which is what allows regulating the room temperature.

## Configuration

Click on the "Underlying Entities" option from the menu, and you will see this configuration page:

![image](images/config-linked-entity.png)

### The Underlying Entities
In the "Equipment to Control" list, you should add the switches that will be controlled by VTherm. Only `switch` or `input_boolean` entities are accepted.

The algorithm currently available is TPI. See [algorithm](#algorithm).
If multiple entities are configured, the thermostat staggers the activations to minimize the number of switches on at any given time. This allows for better power distribution, as each radiator will turn on in turn.

VTherm will smooth the consumed power as much as possible by alternating activations. Example of staggered activations:

![image](images/multi-switch-activation.png)

Of course, if the requested power (`on_percent`) is too high, there will be an overlap of activations.

### Keep-Alive

Some equipment requires periodic activation to prevent a safety shutdown. Known as "keep-alive," this function can be activated by entering a non-zero number of seconds in the thermostat's keep-alive interval field. To disable the function or if in doubt, leave it empty or enter zero (default value).

### AC Mode

It is possible to choose a `thermostat_over_switch` to control an air conditioner by checking the "AC Mode" box. In this case, only the cooling mode will be visible.

### Command Inversion

If your equipment is controlled by a pilot wire with a diode, you may need to check the "Invert the Command" box. This will set the switch to `On` when you need to turn off the equipment and to `Off` when you need to turn it on. The cycle times will be inverted with this option.