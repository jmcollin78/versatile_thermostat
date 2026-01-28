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

## Release 8.6
> 1. added `max_opening_degrees` parameter for `over_climate_valve` VTherms allowing to limit the maximum opening percentage of each valve to control hot water flow and optimize energy consumption or other use cases.
> 2. added a valve recalibration function for an _VTherm_ `over_climate_valve` allowing to force a maximum opening then a maximum closing to attempt recalibration of a TRV. More information [here](documentation/en/feature-recalibrate-valves.md).

## Release 8.5
> 1. added heating failure detection for VTherms using the TPI algorithm. This feature detects two types of anomalies:
>    - **heating failure**: the radiator is heating strongly (high on_percent) but the temperature is not increasing,
>    - **cooling failure**: the radiator is not heating (on_percent at 0) but the temperature keeps rising.
>
> These anomalies may indicate an open window, a faulty radiator, or an external heat source. The feature sends events that can be used to trigger automations (notifications, alerts, etc.). More information [here](documentation/en/feature-heating-failure-detection.md).

## Release 8.4
> 1. added auto TPI (experimental). This new feature allows automatically calculating the best coefficients for the TPI algorithm. More information [here](documentation/en/feature-auto_tpi.md)
> 2. added a temperature synchronization function for a device controlled in `over_climate` mode. Depending on your device's capabilities, _VTherm_ can control an offset calibration entity or directly an external temperature entity. More information [here](documentation/en/feature-sync_device_temp.md),
> 3. added a feature named "timed preset" which aims to select a preset for a certain duration and come back to the previous preset after the expiration of the delay. The new feature is totally described [here](documentation/en/feature-timed-preset.md).


## Release 8.3
1. Addition of a configurable delay before activating the central boiler.
2. Addition of a trigger for the central boiler when the total activated power exceeds a threshold. To make this feature work you must:
   - Configure the power threshold that will trigger the boiler. This is a new entity available in the `central configuration` device.
   - Configure the power values of the VTherms. This can be found on the first configuration page of each VTherm.
   - Check the `Used by central boiler` box.

Each time a VTherm is activated, its configured power is added to the total and, if the threshold is exceeded, the central boiler will be activated after the delay configured in item 1.

The previous counter for the number of activated devices and its threshold still exist. To disable one of the thresholds (the power threshold or the activated-devices count threshold), set it to zero. As soon as either of the two non-zero thresholds is exceeded, the boiler is activated. Therefore a logical "or" is applied between the two thresholds.

More informations [here](documentation/en/feature-central-boiler.md).

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
18. [Heating Failure Detection](documentation/en/feature-heating-failure-detection.md)
19. [Self-regulation](documentation/en/self-regulation.md)
20. [Auto TPI learning](documentation/en/feature-autotpi.md)
21. [Algorithms](documentation/en/algorithms.md)
22. [Lock / Unlock](documentation/en/feature-lock.md)
23. [Temperature synchronisation](documentation/en/feature-sync_device_temp.md)
24. [Timed preset](documentation/en/feature-timed-preset.md)
25. [Reference documentation](documentation/en/reference.md)
26. [Tuning examples](documentation/en/tuning-examples.md)
27. [Troubleshooting](documentation/en/troubleshooting.md)
28. [Release notes](documentation/en/releases.md)

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
