[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Versatile Thermostat

This README file is available in
languages : [English](README.md) | [French](README-fr.md) | [German](README-de.md) | [Czech](README-cs.md) | [Polish](README-pl.MD)

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
> * **Release 7.4**:
>
> - Added thresholds to enable or disable the TPI algorithm when the temperature exceeds the setpoint. This prevents the heater from turning on/off for short periods. Ideal for wood stoves that take a long time to heat up. See [TPI](documentation/en/algorithms.md#the-tpi-algorithm),
>
> - Added a sleep mode for VTherms of type `over_climate` with regulation by direct valve control. This mode allows you to set the thermostat to off mode but with the valve 100% open. It is useful for long periods without heating if the boiler circulates water from time to time. Note: you must update the VTHerm UI Card to view this new mode. See [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card).
>
> * **Release 7.2**:
>
> - Native support for devices controlled via a `select` (or `input_select`) or `climate` entity for _VTherm_ of type `over_switch`. This update makes the creation of virtual switches obsolete for integrating Nodon, Heaty, eCosy, etc. More information [here](documentation/en/over-switch.md#command-customization).
>
> - Documentation links: Version 7.2 introduces experimental links to the documentation from the configuration pages. The link is accessible via the icon [![?](https://img.icons8.com/color/18/help.png)](https://github.com/jmcollin78/versatile_thermostat/blob/main/documentation/en/over-switch.md#configuration). This feature is currently tested on some configuration pages.

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
21. [Reference documentation](documentation/en/reference.md)
22. [Tuning examples](documentation/en/tuning-examples.md)
23. [Troubleshooting](documentation/en/troubleshooting.md)
24. [Release notes](documentation/en/releases.md)

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
