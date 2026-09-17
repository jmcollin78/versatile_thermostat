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

> ![Tip](images/tips.png) **Versatile Thermostat** is a highly configurable virtual thermostat that transforms any heating equipment (radiators, air conditioners, heat pumps, etc.) into an intelligent and adaptive system. It allows you to consolidate and centrally control multiple different heating systems, while automatically optimizing your energy consumption. Thanks to its advanced algorithms (TPI, auto-TPI) and learning capabilities, the thermostat adapts to your home 🏠 and your habits, providing you with optimal comfort and significant reduction in your heating bills 💰.
> This thermostat integration aims to greatly simplify your heating management automations. Since all typical heating events (nobody home?, activity detected in a room?, window open?, power load shedding?) are natively managed by the thermostat, you don't need to deal with complicated scripts and automations to manage your thermostats. 😉

This custom component for Home Assistant is an upgrade and a complete rewrite of the "Awesome thermostat" component (see [Github](https://github.com/dadge/awesome_thermostat)) with added features.

# Screenshots

Versatile Thermostat UI Card (Available on [Github](https://github.com/jmcollin78/versatile-thermostat-ui-card)) :

![Card1](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/1.png) ![Card2](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/7.png)

# What's New?
![New](images/new-icon.png)

## Release 10.4.0
VTherm can now expose `current_humidity` from an external humidity sensor for all thermostat types. The sensor can be selected in the Humidity menu or automatically detected on the room-temperature sensor device.

`over_valve` thermostats now have the same valve control parameters as `over_climate` thermostats with direct valve control regulation: `opening_threshold_degree`, `min_opening_degrees`, `max_closing_degree`, and `max_opening_degrees`. More information: [valve control](documentation/en/over-valve.md).

`over_valve` thermostats now also support Sleep mode. Sleep displays VTherm as off and sends a raw 100% opening request without requesting central boiler heating. Configured valve-control limits can cap the physical opening. More information: [Sleep mode](documentation/en/over-valve.md#sleep-mode).

## Release 10.3.0
Power units can now be configured. Configuration screens let you select a unit for power measurements (W by default). Calculated energy units match the configured power unit. Existing entries are migrated using the historical device power value: values above 100 are treated as W; other values as kW.

⚠️ **Important change for statistics**
You may see a repair notification such as: `The unit of “Central configuration Total power active for boiler” (sensor.total_power_active_for_boiler) was changed to “kW”`, or a similar log message. This is expected because the unit was previously not specified. Select the repair action `Update the unit of long-term statistics` to correct the statistics.

## Release 10.2.0
The **Auto Fan** feature is now available as an external plugin ([vtherm_auto_fan_extended](https://github.com/jmcollin78/vtherm_auto_fan_extended)). The original (_legacy_) auto-fan version is still available in _VTherm_, but it must be disabled in the thermostat configuration in order to use the plugin. The full documentation is available on the [plugin's GitHub repository](https://github.com/jmcollin78/vtherm_auto_fan_extended).

## Release 10.1
Auto-start/stop stop mode selection. A new `select` entity lets you choose the mode applied when the auto-start/stop feature detects a stop condition: `Off` (default), `Fan only` or `Dry`. The `Fan only` and `Dry` modes are only proposed when the underlying appliance supports them. More information [here](documentation/en/feature-auto-start-stop.md).

Self-regulation is now disabled when an `over_climate` _VTherm_ is not in `Heat` or `Cool` mode: the original (non-regulated) setpoint is sent to the underlying device. More information [here](documentation/en/self-regulation.md).

## Release 10.0
Introduction of the plugin mechanism. This allows the use of external integrations as plugins for _VTherm_. The list of available plugins is available on the [Versatile Thermostat Web site](https://www.versatile-thermostat.org/en/plugins).



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

# ⭐ Star history

[![Star History Chart](https://star-history.dera.page/svg?repos=jmcollin78/versatile_thermostat&type=Date)](https://star-history.dera.page/#jmcollin78/versatile_thermostat&Date)

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
