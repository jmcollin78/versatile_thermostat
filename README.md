[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Versatile Thermostat

This README file is available in
languages : [English](README.md) | [Français](README-fr.md) | [Deutsch](README-de.md) | [Čeština](README-cs.md) | [Polski](README-pl.md)
<div> <br> </div>
<p align="center">
<img src="https://github.com/jmcollin78/versatile_thermostat/blob/main/images/icon.png" />
</p>

> ![Tip](images/tips.png) This thermostat integration aims to greatly simplify your heating management automations. Since all typical heating events (nobody home?, activity detected in a room?, window open?, power load shedding?), are natively managed by the thermostat, you don’t need to deal with complicated scripts and automations to manage your thermostats. ;-).

This custom component for Home Assistant is an upgrade and a complete rewrite of the "Awesome thermostat" component (see [Github](https://github.com/dadge/awesome_thermostat)) with added features.

# Screenshots

Versatile Thermostat UI Card (Available on [Github](https://github.com/jmcollin78/versatile-thermostat-ui-card)) :

![Card1](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/1.png) ![Card2](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/7.png)

# What's New?
![New](images/new-icon.png)

## Release 8.3
1. Addition of a configurable delay for activating the central boiler.
2. Addition of a trigger for the central boiler when the total activated power exceeds a threshold. To make this feature work you must:
   - Configure the power threshold that will trigger the boiler. This is a new entity available in the `central configuration` device.
   - Configure the power values of the VTherms. This can be found on the first configuration page of each VTherm.
   - Check the `Used by central boiler` box.

Each time a VTherm is activated, its configured power is added to the total and, if the threshold is exceeded, the central boiler will be activated after the delay configured in item 1.

The previous counter for the number of activated devices and its threshold still exist. To disable one of the thresholds (the power threshold or the activated-devices count threshold), set it to zero. As soon as either of the two non-zero thresholds is exceeded, the boiler is activated. Therefore a logical "or" is applied between the two thresholds.

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
>
>
# 🍻 Thanks for the beers 🍻
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jmcollin78)

A big thank you to all my beer sponsors for their donations and encouragements. It means a lot to me and motivates me to keep going! If this integration has saved you money, buy me a beer in return; I would greatly appreciate it!

# Glossary

  `VTherm`: Versatile Thermostat as referred to in this document

  `TRV`: Thermostatic Radiator Valve equipped with a valve. The valve opens or closes to allow hot water to pass.

  `AC`: Air Conditioning. An AC device cools instead of heats. Temperatures are reversed: Eco is warmer than Comfort, which is warmer than Boost. The algorithms take this information into account.

  `EMA`: Exponential Moving Average. Used to smooth sensor temperature measurements. It represents a moving average of the room's temperature and is used to calculate the slope of the temperature curve, which would be too unstable on the raw data.

  `slope`: The slope of the temperature curve, measured in ° (C or K)/h. It is positive when the temperature increases and negative when it decreases. This slope is calculated based on the `EMA`.

  `PAC`: Heat pump

  `HA`: Home Assistant

  `underlying`: the device controlled by `VTherm`

# Documentation

The documentation is now divided into several pages for easier reading and searching:
1. [Introduction](documentation/en/presentation.md)
2. [Installation](documentation/en/installation.md)
3. [Quick start](documentation/en/quick-start.md)
4. [Choosing a VTherm type](documentation/en/creation.md)
5. [Basic attributes](documentation/en/base-attributes.md)
6. [Configuring a VTherm on a `switch`](documentation/en/over-switch.md)
7. [Configuring a VTherm on a `climate`](documentation/en/over-climate.md)
8. [Configuring a VTherm on a valve](documentation/en/over-valve.md)
9. [Presets](documentation/en/feature-presets.md)
10. [Window management](documentation/en/feature-window.md)
11. [Presence management](documentation/en/feature-presence.md)
12. [Motion management](documentation/en/feature-motion.md)
13. [Power management](documentation/en/feature-power.md)
14. [Auto start and stop](documentation/en/feature-auto-start-stop.md)
15. [Centralized control of all VTherms](documentation/en/feature-central-mode.md)
16. [Central heating control](documentation/en/feature-central-boiler.md)
17. [Advanced aspects, security mode](documentation/en/feature-advanced.md)
18. [Self-regulation](documentation/en/self-regulation.md)
19. [Tuning examples](documentation/en/tuning-examples.md)
20. [Algorithms](documentation/en/algorithms.md)
21. [Lock / Unlock](documentation/en/feature-lock.md)
22. [Reference documentation](documentation/en/reference.md)
23. [Tuning examples](documentation/en/tuning-examples.md)
24. [Troubleshooting](documentation/en/troubleshooting.md)
25. [Release notes](documentation/en/releases.md)

# Some results

**Temperature stability around the target configured by preset**:

![image](documentation/en/images/results-1.png)

**On/off cycles calculated by the integration `over_climate`**:

![image](documentation/en/images/results-2.png)

**Regulation with an `over_switch`**:

![image](documentation/en/images/results-4.png)

**Strong regulation in `over_climate`**:

![image](documentation/en/images/results-over-climate-1.png)

**Regulation with direct valve control in `over_climate`**:

![image](documentation/en/images/results-over-climate-2.png)

# Some comments about the integration
|                                             |                                             |                                             |
| ------------------------------------------- | ------------------------------------------- | ------------------------------------------- |
| ![testimonial 1](images/testimonials-1.png) | ![testimonial 2](images/testimonials-2.png) | ![testimonial 3](images/testimonials-3.png) |
| ![testimonial 4](images/testimonials-4.png) | ![testimonial 5](images/testimonials-5.png) | ![testimonial 6](images/testimonials-6.png) |

Enjoy!

# Contributions are welcome!

If you wish to contribute, please read the [contribution guidelines](CONTRIBUTING.md).

***

[versatile_thermostat]: https://github.com/jmcollin78/versatile_thermostat
[buymecoffee]: https://www.buymeacoffee.com/jmcollin78
[buymecoffeebadge]: https://img.shields.io/badge/Buy%20me%20a%20beer-%245-orange?style=for-the-badge&logo=buy-me-a-beer
[commits-shield]: https://img.shields.io/github/commit-activity/y/jmcollin78/versatile_thermostat.svg?style=for-the-badge
[commits]: https://github.com/jmcollin78/versatile_thermostat/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacs_badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/jmcollin78/versatile_thermostat.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Joakim%20Sørensen%20%40ludeeus-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/jmcollin78/versatile_thermostat.svg?style=for-the-badge
[releases]: https://github.com/jmcollin78/versatile_thermostat/releases
