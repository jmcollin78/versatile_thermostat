# Release Notes

![New](images/new-icon.png)

## Release 8.2
> Added a feature to lock / unlock a VTherm with an optional code. More information [here](documentation/en/feature-lock.md)

## Release 8.1
> - For `over_climate` with regulation by direct valve control, two new parameters are added to the existing `minimum_opening_degrees`. The parameters are now the following:
>    - `opening_threshold`: the valve opening value under which the valve should be considered as closed (and then 'max_closing_degree' will apply),
>    - `max_closing_degree`: the closing degree maximum value. The valve will never be closed above this value. Set it to 100 to fully close the valve when no heating is needed,
>    - `minimum_opening_degrees`: the opening degree minimum value for each underlying device when ``opening_threshold` is exceeded, comma separated. Default to 0. Example: 20, 25, 30. When the heating starts, the valve will start opening with this value and will continuously increase as long as more heating is needed.
>
> ![alt text](images/opening-degree-graph.png)
> More informations can be found the discussion thread about this here: https://github.com/jmcollin78/versatile_thermostat/issues/1220

## Release 8.0
> This is a major release. It rewrites a significant part of the internal mechanisms of Versatile Thermostat by introducing several new features:
>    1. _requested state / current state_: VTherm now has 2 states. The requested state is the state requested by the user (or Scheduler). The current state is the state currently applied to the VTherm. The latter depends on the different VTherm functions. For example, the user can request (requested state) to have heating on with Comfort preset but since the window has been detected open, the VTherm is actually off. This dual management always preserves the user's request and applies the result of the different functions on this user request to get the current state. This better handles cases where multiple functions want to act on the VTherm state (window opening and power shedding for example). It also ensures a return to the user's initial request when no detection is in progress anymore,
>    2. _time filtering_: the time filtering operation has been revised. Time filtering prevents sending too many commands to a controlled equipment to avoid consuming too much battery (battery-powered TRV for example), changing setpoints too frequently (heat pump, pellet stove, underfloor heating, ...). The new operation is now as follows: explicit user (or Scheduler) requests are always immediately taken into account. They are not filtered. Only changes related to external conditions (room temperature for example) are potentially filtered. Filtering consists of resending the desired command later and not ignoring the command as was previously the case. The `auto_regulation_dtemp` parameter allows adjusting the delay,
>    3. _hvac_action improvement_: the `hvac_action` reflects the current activation state of the controlled equipment. For an `over_switch` type it reflects the switch activation state, for an `over_valve` or valve regulation, it is active when the valve opening is greater than the minimum valve opening (or 0 if not configured), for an `over_climate` it reflects the underlying `climate`'s `hvac_action` if available or a simulation otherwise.
>    4. _custom attributes_: the organization of custom attributes accessible in Developer Tools / States has been reorganized into sections depending on the VTherm type and each activated function. More information [here](documentation/en/reference.md#custom-attributes).
>    5. _power shedding_: the power shedding algorithm now takes into account equipment shutdown between two measurements of home power consumption. Suppose you have power consumption feedback every 5 minutes. If a radiator is turned off between 2 measurements then turning on a new one may be authorized. Before, only turn-ons were taken into account between 2 measurements. As before, the next power consumption feedback will possibly shed more or less.
>    6. _auto-start/stop_: auto-start/stop is only useful for `over_climate` type VTherm without direct valve control. The option has been removed for other VTherm types.
>    7. _VTherm UI Card_: all these modifications allowed a major evolution of the [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card) to integrate messages explaining the current state (why does my VTherm have this target temperature?) and if time filtering is in progress - so the underlying state update has been delayed.
>    8. _log improvements_: logs have been improved to simplify debugging. Logs in the form `--------------------> NEW EVENT: VersatileThermostat-Inversed ...` inform of an event impacting the VTherm state.
>
> ⚠️ **Warning**
>
> This major release includes breaking changes from the previous version:
> - `versatile_thermostat_security_event` has been renamed to `versatile_thermostat_safety_event`. If your automations use this event, you must update them,
> - custom attributes have been reorganized. You must update your automations or Jinja templates that use them,
> - the [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card) must be updated to at least V2.0 to be compatible,
>
> **Despite the 342 automated tests of this integration and the care taken with this major release, I cannot guarantee that its installation will not disrupt your VTherms' states. For each VTherm you must check the preset, hvac_mode and possibly the VTherm setpoint temperature after installation.**

* **Release 7.4**:
- Added thresholds to enable or disable the TPI algorithm when the temperature exceeds the setpoint. This prevents the heater from turning on/off for short periods. Ideal for wood stoves that take a long time to heat up. See [TPI](documentation/en/algorithms.md#the-tpi-algorithm),
- Added a sleep mode for VTherms of type `over_climate` with regulation by direct valve control. This mode allows you to set the thermostat to off mode but with the valve 100% open. It is useful for long periods without heating if the boiler circulates water from time to time. Note: you must update the VTHerm UI Card to view this new mode. See [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card).
* **Release 7.2**:
- Native support for devices controlled via a `select` (or `input_select`) or `climate` entity for _VTherm_ of type `over_switch`. This update makes the creation of virtual switches obsolete for integrating Nodon, Heaty, eCosy, etc. More information [here](documentation/en/over-switch.md#command-customization).
- Documentation links: Version 7.2 introduces experimental links to the documentation from the configuration pages. The link is accessible via the icon [![?](https://img.icons8.com/color/18/help.png)](https://github.com/jmcollin78/versatile_thermostat/blob/main/documentation/en/over-switch.md#configuration). This feature is currently tested on some configuration pages.
* **Release 7.1**:
  - Redesign of the load-shedding function (power management). Load-shedding is now handled centrally (previously, each _VTherm_ was autonomous). This allows for much more efficient management and prioritization of load-shedding on devices that are close to the setpoint. Note that you must have a centralized configuration with power management enabled for this to work. More info [here](./feature-power.md).

* **Release 6.8**:
   - Added a new regulation method for `over_climate` type Versatile Thermostats. This method, called 'Direct Valve Control', allows direct control of a TRV valve and possibly an offset to calibrate the internal thermometer of your TRV. This new method has been tested with Sonoff TRVZB and extended to other TRV types where the valve can be directly controlled via `number` entities. More information [here](over-climate.md#lauto-régulation) and [here](self-regulation.md#auto-régulation-par-contrôle-direct-de-la-vanne).

## **Release 6.5** :
  - Added a new feature for the automatic stop and restart of a `VTherm over_climate` [585](https://github.com/jmcollin78/versatile_thermostat/issues/585)
  - Improved handling of openings on startup. Allows to memorize and recalculate the state of an opening on Home Assistant restart [504](https://github.com/jmcollin78/versatile_thermostat/issues/504)

## **Release 6.0** :
  - Added `number` domain entities to configure preset temperatures [354](https://github.com/jmcollin78/versatile_thermostat/issues/354)
  - Complete redesign of the configuration menu to remove temperatures and use a menu instead of a configuration tunnel [354](https://github.com/jmcollin78/versatile_thermostat/issues/354)

## **Release 5.4** :
  - Added temperature step [#311](https://github.com/jmcollin78/versatile_thermostat/issues/311),
  - Added regulation thresholds for `over_valve` to prevent excessive battery drain for TRVs [#338](https://github.com/jmcollin78/versatile_thermostat/issues/338),
  - Added an option to use the internal temperature of a TRV to force auto-regulation [#348](https://github.com/jmcollin78/versatile_thermostat/issues/348),
  - Added a keep-alive function for `over_switch` VTherms [#345](https://github.com/jmcollin78/versatile_thermostat/issues/345)

<details>
<summary>Older releases</summary>

> * **Release 5.3** : Added a function to control a central boiler [#234](https://github.com/jmcollin78/versatile_thermostat/issues/234) - more info here: [Central Boiler Control](#le-contrôle-dune-chaudière-centrale). Added the ability to disable security mode for the external thermometer [#343](https://github.com/jmcollin78/versatile_thermostat/issues/343)
> * **Release 5.2** : Added a `central_mode` to control all VTherms centrally [#158](https://github.com/jmcollin78/versatile_thermostat/issues/158).
> * **Release 5.1** : Limitation of values sent to valves and to the underlying climate temperature.
> * **Release 5.0** : Added central configuration to combine configurable attributes [#239](https://github.com/jmcollin78/versatile_thermostat/issues/239).
> * **Release 4.3** : Added an auto-fan mode for `over_climate` type to activate ventilation if temperature difference is large [#223](https://github.com/jmcollin78/versatile_thermostat/issues/223).
> * **Release 4.2** : The temperature curve slope is now calculated in °/hour instead of °/min [#242](https://github.com/jmcollin78/versatile_thermostat/issues/242). Fixed automatic opening detection by adding temperature curve smoothing.
> * **Release 4.1** : Added an **Expert** regulation mode where users can specify their own auto-regulation parameters instead of using pre-programmed ones [#194](https://github.com/jmcollin78/versatile_thermostat/issues/194).
> * **Release 4.0** : Added support for **Versatile Thermostat UI Card**. See [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card). Added a **Slow** regulation mode for slow-latency heating devices [#168](https://github.com/jmcollin78/versatile_thermostat/issues/168). Changed how **power is calculated** for VTherms with multi-underlying equipment [#146](https://github.com/jmcollin78/versatile_thermostat/issues/146). Added support for AC and Heat for VTherms via a switch [#144](https://github.com/jmcollin78/versatile_thermostat/pull/144)
> * **Release 3.8**: Added an **auto-regulation** function for `over_climate` thermostats regulated by the underlying climate. See [Auto-regulation](#lauto-régulation) and [#129](https://github.com/jmcollin78/versatile_thermostat/issues/129). Added the **ability to invert control** for `over_switch` thermostats to address installations with pilot wire and diode [#124](https://github.com/jmcollin78/versatile_thermostat/issues/124).
> * **Release 3.7**: Added the `over_valve` Versatile Thermostat type to control a TRV valve directly or any other dimmer type equipment for heating. Regulation is done directly by adjusting the percentage of opening of the underlying entity: 0 means the valve is off, 100 means the valve is fully open. See [#131](https://github.com/jmcollin78/versatile_thermostat/issues/131). Added a bypass function for opening detection [#138](https://github.com/jmcollin78/versatile_thermostat/issues/138). Added Slovak language support.
> * **Release 3.6**: Added the `motion_off_delay` parameter to improve motion detection handling [#116](https://github.com/jmcollin78/versatile_thermostat/issues/116), [#128](https://github.com/jmcollin78/versatile_thermostat/issues/128). Added AC mode (air conditioning) for `over_switch` VTherm. Prepared the GitHub project to facilitate contributions [#127](https://github.com/jmcollin78/versatile_thermostat/issues/127)
> * **Release 3.5**: Multiple thermostats possible in "thermostat over climate" mode [#113](https://github.com/jmcollin78/versatile_thermostat/issues/113)
> * **Release 3.4**: Bug fix and exposure of preset temperatures for AC mode [#103](https://github.com/jmcollin78/versatile_thermostat/issues/103)
> * **Release 3.3**: Added Air Conditioning (AC) mode. This function allows you to use the AC mode of your underlying thermostat. To use it, you must check the "Use AC Mode" option and define temperature values for presets and away presets.
> * **Release 3.2** : Added the ability to control multiple switches from the same thermostat. In this mode, switches are triggered with a delay to minimize the power required at any given time (minimizing overlap periods). See [Configuration](#sélectionnez-des-entités-pilotées)
> * **Release 3.1** : Added window/door open detection by temperature drop. This new feature automatically stops a radiator when the temperature drops suddenly. See [Auto Mode](#le-mode-auto)
> * **Major Release 3.0** : Added thermostat equipment and associated sensors (binary and non-binary). Much closer to the Home Assistant philosophy, you now have direct access to the energy consumed by the radiator controlled by the thermostat and many other sensors useful for your automations and dashboards.
> * **Release 2.3** : Added measurement of power and energy for the radiator controlled by the thermostat.
> * **Release 2.2** : Added a safety function to prevent leaving a radiator heating indefinitely in case of thermometer failure.
> * **Major Release 2.0** : Added the "over climate" thermostat allowing any thermostat to be transformed into a Versatile Thermostat and gain all its functionalities.

</details>

> ![Tip](images/tips.png) _*Notes*_
>
> Complete release notes are available on the [GitHub of the integration](https://github.com/jmcollin78/versatile_thermostat/releases/).