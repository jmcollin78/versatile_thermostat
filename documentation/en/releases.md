# Release Notes

![New](images/new-icon.png)

> * **Release 6.8**:
>   - Added a new regulation method for `over_climate` type Versatile Thermostats. This method, called 'Direct Valve Control', allows direct control of a TRV valve and possibly an offset to calibrate the internal thermometer of your TRV. This new method has been tested with Sonoff TRVZB and extended to other TRV types where the valve can be directly controlled via `number` entities. More information [here](over-climate.md#lauto-régulation) and [here](self-regulation.md#auto-régulation-par-contrôle-direct-de-la-vanne).

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