# Typ termostatu `Termostat na Zaworze`

> ![Attention](images/tips.png) _*Notes*_
> 1. The `termostat na zaworze` type is often confused with the `over_climate` type equipped with auto-regulation and direct valve control.
> 2. You should only choose this type when you do not have an associated `climate` entity for your _TRV_ in Home Assistant, and if you only have a `number` type entity to control the valve's opening percentage. The `over_climate` with auto-regulation on the valve is much more powerful than the `over_valve` type.

## Prerequisites

The installation should be similar to the `over_switch` VTherm setup, except that the controlled equipment is directly the valve of a _TRV_:

![installation `over_valve`](images/over-valve-schema.png)

1. The user or automation, or the Scheduler, sets a setpoint via a preset or directly using a temperature.
2. Periodically, the internal thermometer (2) or external thermometer (2b) or internal thermometer of the equipment (2c) sends the measured temperature. The internal thermometer should be placed in a relevant spot for the user's comfort: ideally in the middle of the living space. Avoid placing it too close to a window or too near the equipment.
3. Based on the setpoint values, the different temperatures, and the TPI algorithm parameters (see [TPI](algorithms.md#lalgorithme-tpi)), VTherm will calculate the valve's opening percentage.
4. It will then modify the value of the underlying `number` entities.
5. These underlying `number` entities will control the valve opening rate on the _TRV_.
6. This will regulate the radiator's heating.

> The opening rate is recalculated each cycle, which allows regulating the room temperature.

## Configuration

First, configure the main settings common to all _VTherms_ (see [main settings](base-attributes.md)).
Then, click on the "Underlying Entities" option from the menu, and you will see this configuration page, you should add the `number` entities that will be controlled by VTherm. Only `number` or `input_number` entities are accepted.

![image](images/config-linked-entity3.png)

The algorithm currently available is TPI. See [algorithm](#algorithm).

It is possible to choose a `thermostat_over_valve` to control an air conditioner by checking the "AC Mode" box. In this case, only the cooling mode will be visible.
