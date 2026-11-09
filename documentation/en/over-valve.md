# `thermostat_over_valve` Type Thermostat

> ![Attention](images/tips.png) _*Notes*_
> 1. The `over_valve` type is often confused with the `over_climate` type equipped with auto-regulation and direct valve control.
> 2. You should only choose this type when you do not have an associated `climate` entity for your _TRV_ in Home Assistant, and if you only have a `number` type entity to control the valve's opening percentage. The `over_climate` with auto-regulation on the valve is much more powerful than the `over_valve` type.

## Prerequisites

The thermostatic valves usable with an `over_valve` _VTherm_, such as the [Shelly BLU TRV](https://www.versatile-thermostat.org/en/devices/over-valve/), are listed in the [device catalog](https://www.versatile-thermostat.org/en/devices/?type=trv).

The installation should be similar to the `over_switch` VTherm setup, except that the controlled equipment is directly the valve of a _TRV_:

![installation `over_valve`](images/over-valve-schema.png)

1. The user or automation, or the Scheduler, sets a setpoint via a preset or directly using a temperature.
2. Periodically, the internal thermometer (2) or external thermometer (2b) or internal thermometer of the equipment (2c) sends the measured temperature. The internal thermometer should be placed in a relevant spot for the user's comfort: ideally in the middle of the living space. Avoid placing it too close to a window or too near the equipment.
3. Based on the setpoint values, the different temperatures, and the TPI algorithm parameters (see [TPI](algorithms.md#the-tpi-algorithm) or the [other algorithms](algorithms.md#other-algorithms-plugins)), VTherm will calculate the valve's opening percentage.
4. It will then modify the value of the underlying `number` entities.
5. These underlying `number` entities will control the valve opening rate on the _TRV_.
6. This will regulate the radiator's heating.

> The opening rate is recalculated each cycle, which allows regulating the room temperature.

## Configuration

First, configure the main settings common to all _VTherms_ (see [main settings](base-attributes.md)).
Then configure the underlyings. When the _VTherm_ is created, the wizard shows them after the main attributes. Afterwards, select "Underlyings" in the menu. This menu lists:
- "Common settings": the settings shared by all the valves (algorithm, AC mode, regulation threshold and period, opening threshold, maximum closing),
- one entry for each controlled valve, with its entity and its openings,
- "Add a device".

"Add a device" first asks for the `number` entity of the valve. Only `number` or `input_number` entities are accepted. The next screen shows the settings of this valve: its minimum and maximum openings (see [Valve opening control](#valve-opening-control)). Opening a valve in the list shows the same settings, with "Replace entity" and "Remove this device".

The "Algorithm" field of the common settings selects the regulation algorithm: the built-in TPI, or an algorithm installed as a plugin. See [algorithms](algorithms.md).

### Regulation Threshold and Period

Two fields limit the number of commands sent to the valve:
1. **Regulation threshold** (default `10`): minimum change of the opening, in %, below which a new opening is not sent,
2. **Regulation minimum period** (default `5` minutes): minimum time between two calculations of the opening.

### Valve opening control

`over_valve` can adjust the TPI opening command to match the physical limits of
each valve. The configuration uses the same parameters as direct valve control
with `over_climate`:

1. `opening_threshold_degree`, in the common settings: below this raw TPI
	percentage, the valve is considered closed.
2. `max_closing_degree`, in the common settings: maximum closing percentage.
	The command under the threshold is `100 - max_closing_degree`; keep the
	default `100` to close it fully.
3. "Minimum opening (%)" (`min_opening_degrees`), in the settings of each
	valve: applied as soon as the threshold is reached. Defaults to `0`.
4. "Maximum opening (%)" (`max_opening_degrees`), in the settings of each
	valve: the valve never opens more than this value. It cannot exceed the
	maximum supported by the `number` entity, which is the default value.

The physical command never falls below `100 - max_closing_degree`, including
when the raw TPI demand reaches `opening_threshold_degree`; it is monotonically
non-decreasing as demand rises. Heating demand is determined from the positive
raw TPI percentage at or above the threshold, while the observed valve is
active only above its effective physical floor (also constrained by the entity
minimum). At startup or reload, a valve without demand is returned to this
floor.

Each valve has its own minimum and maximum openings. With the defaults
(threshold `0`, minimum `0`, maximum of the valve, maximum closing `100`), the
command sent to the valve remains identical to the raw TPI percentage.

It is possible to choose a `thermostat_over_valve` to control an air conditioner by checking the "AC Mode" box. In this case, only the cooling mode will be visible.

### Sleep mode

`over_valve` supports sleep mode. Selecting `sleep`, or calling the
`versatile_thermostat.set_hvac_mode_sleep` action, presents VTherm as off while
sending a raw 100% opening request to every underlying valve. This request still
uses the normal opening-control conversion: `max_opening_degrees` and the
underlying `number` limits can therefore cap the physical opening. Sleep mode
does not request central boiler heating; `is_sleeping` identifies this state.

## Next Step

[The TPI coefficients](algorithms.md#configuring-the-tpi-algorithm-coefficients): tune the regulation algorithm ("TPI parameters" menu). Without a central configuration, this step is required to finalize the creation.

If you use an algorithm provided by a plugin, such as SmartPI, follow its documentation, then go directly to the [presets](feature-presets.md).
