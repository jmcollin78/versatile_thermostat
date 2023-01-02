[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]


_Component developed by using the amazing development template [blueprint][blueprint]._

This custom component for Home Assistant is an upgrade and complete rewrite of the component "Awesome thermostat" (see [Github](https://github.com/dadge/awesome_thermostat)) with addition of features.

## Why another thermostat implementation ?
For my personnal usage, I needed to add a couple of features and also to update the behavior that I implemented in my previous component "Awesome thermostat".
This new component "Versatile thermostat" now manage the following use cases :
- Configuration through GUI using Config Entry flow,
- Explicitely define the temperature for all presets mode,
- Unset the preset mode when the temperature is manually defined on a thermostat,
- Turn off/on a thermostat when a door or windows is opened/closed after a certain delay,
- Set a preset when an activity is detected in a room, and another one after no activity has been detected for a defined time,
- Use a proportional algorithm with two function (see below),
- Add power management to avoid exceeding a defined total power. When max power is exceeded, a new 'power' preset is set on the climate entity. When power goes below the max, the previous preset is restored.

## How to install this incredible thermostat

### HACS installation

1. Install [HACS](https://hacs.xyz/). That way you get updates automatically.
2. Add this Github repository as custom repository in HACS settings.
3. search and install "Versatile Thermostat" in HACS and click `install`.
4. Restart Home Assistant,
5. Then you can add an Versatile Thermostat integration in the integration page. You add as many Versatile Thermostat that you need (typically one per heater that should be managed)

### Manual installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `versatile_thermostat`.
4. Download _all_ the files from the `custom_components/versatile_thermostat/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. Configure new Versatile Thermostat integration

## Minimum requirements

* This implementation can override or superseed the core generic thermostat

## Configuration

No configuration in configuration.yaml is needed because all configuration is done through the standard GUI when adding the integration.
Click on Add integration button in the integration page
![image](https://github.com/jmcollin78/versatile_thermostat/blob/dev/images/add-an-integration.png?raw=true)

Follow the configurations steps as follow:

### Minimal configuration update
![image](https://github.com/jmcollin78/versatile_thermostat/blob/dev/images/config-page-1.png?raw=true)

Give the main mandatory attributes:
1. a name (will be the integration name and also the climate entity name)
2. an equipment entity id which represent the heater. This equipment should be able to switch on or off,
3. a sensor entity id which gives the temperature of the room in which the heater is installed,
4. a cycle duration in minutes. At each cycle, the heater will be turned on then off for a calculated period in order to reach the targeted temperature (see presents below)
5. a function used by the algorithm. 'linear' is the most common function. 'atan' is more aggressive and the targeted temperature will be reach sooner (but the power consumption is greater). Use it for room badly isolated,
6. a bias value of type float. Proportional algorithm are known to never reach the targeted temperature. Depending of the room and heater configuration set a bias to reach the target. To evaluate the correct value, set it to 0, set the preset to a target temperature and see the current temperature reach. If it is below the target temperature, set the bias accordingly.

### Configure the preset temperature
Click on 'Validate' on the previous page and you will get there:
![image](https://github.com/jmcollin78/versatile_thermostat/blob/dev/images/config-page-2.png?raw=true)

Concerning the preset modes, you first have to know that, as defined in the core development documentation (https://developers.home-assistant.io/docs/core/entity/climate/), the preset mode handled are the following :
 - ECO : Device is running an energy-saving mode
 - AWAY :	Device is in away mode
 - BOOST : Device turn all valve full up
 - COMFORT :	Device is in comfort mode
 - POWER :	An extra preset used when the power management detects an overpowering situation

'None' is always added in the list of modes, as it is a way to not use the presets modes but a manual temperature instead.

!!! IMPORTANT !!! Changing manually the target temperature, set the preset to None (no preset). This way you can always set a target temperature even if no preset are available.

### Configure the doors/windows turning on/off the thermostats
Click on 'Validate' on the previous page and you will get there:
![image](https://github.com/jmcollin78/versatile_thermostat/blob/dev/images/config-page-3.png?raw=true)

Give the following attributes:
1. an entity id of a window/door sensor. This should be a binary_sensor or a input_boolean. The state of the entity should be 'on' or 'off'
2. a delay in secondes before any change. This allow to quickly open a window without stopping the heater.

And that's it ! your thermostat will turn off when the windows is open and be turned back on when it's closed afer the delay.

Note 1 : this implementation is based on 'normal' door/windows behavior, that's mean it considers it's closed when the state is 'off' and open when the state is 'on'

Note 2 : If you want to use several door/windows sensors to automatize your thermostat, just create a group with the regular behavior (https://www.home-assistant.io/integrations/binary_sensor.group/).

### Configure the activity mode or motion detection
Click on 'Validate' on the previous page and you will get there:
![image](https://github.com/jmcollin78/versatile_thermostat/blob/dev/images/config-page-4.png?raw=true)

We will now see how to configure the new Activity mode.
What we need:
- a motion sensor. The entity id of a motion sensor. Motion sensor states should be 'on' (motion detected) or 'off' (no motion detected)
- a "motion delay" duration defining how many time we leave the temperature like in "motion" mode after the last motion is detected.
- a target "motion" preset. We will used the same temperature than this preset when an activity is detected.
- a target "no motion" preset. We will used the same temperature than this preset when no activity is detected.

So imagine we want to have the following behavior :
- we have room with a thermostat set in activity mode, the "motion" mode chosen is comfort (21.5C), the "no motion" mode chosen is Eco (18.5 C) and the motion delay is 5 min.
- the room is empty for a while (no activity detected), the temperature of this room is 18.5 C
- somebody enters into the room, an activity is detected the temperature is set to 21.5 C
- the person leaves the room, after 5 min the temperature is set back to 18.5 C

For this to work, the climate thermostat should be in 'activity' preset mode.

Be aware that as for the others preset modes, Activity will only be proposed if it's correctly configure. In other words, the 4 configuration keys have to be set if you want to see Activity in home assistant Interface

### Configure the power management
This feature allows you to regulate the power consumption of your radiators. Give a sensor to the current power consumption of your house, a sensor to the max power that should not be exceeded, the power consumption of your radiator and the algorithm will not start a radiator if the max power will be exceeded after radiator starts.

![image](https://github.com/jmcollin78/versatile_thermostat/blob/dev/images/config-page-5.png?raw=true)

Note that all power values should have the same units (kW or W for example).
This allows you to change the max power along time using a Sceduler or whatever you like.


## Algorithm
This integration uses a proportional algorithm. A Proportional algorithm is useful to avoid the oscillation around the target temperature. This algorithm is based on a cycle which alternate heating and stop heating. The proportion of heating vs not heating is determined by the difference between the temperature and the target temperature. Bigger the difference is and bigger is the proportion of heating inside the cycle.
This algorithm make the temperature converge and stop oscillating.

Depending of your area and heater, the convergente temperature can be under the targeted temperature. So a bias parameter is available to fix this. To find the right value of biais, just set it to 0 (no biais), let the temperature converge and see if it is near the targeted temperature. If not adjust the biais. A good value is 0.25 with my accumulator radiator (which are long to heat but keeps the heat for a long time).

A function parameter is available. Set it to "Linear" to have a linéar growth of temperature or set it to "Atan" to have a more aggressive curve to target temperature depending of your need.


Enjoy !

## Even Better with Scheduler Component !

In order to enjoy the full power of Versatile Thermostat, I invite you to use it with https://github.com/nielsfaber/scheduler-component
Indeed, the scheduler component porpose a management of the climate base on the preset modes. This feature has limited interest with the generic thermostat but it becomes highly powerfull with Awesome thermostat :

Starting here, I assume you have installed Awesome Thermostat and Scheduler Component.

In Scheduler, add a schedule :

![image](https://user-images.githubusercontent.com/1717155/119146454-ee1a9d80-ba4a-11eb-80ae-3074c3511830.png)

Choose "climate" group, choose one (or multiple) entity/ies, select "MAKE SCHEME" and click next :
(it is possible to choose "SET PRESET", but I prefer to use "MAKE SCHEME")

![image](https://user-images.githubusercontent.com/1717155/119147210-aa746380-ba4b-11eb-8def-479a741c0ba7.png)

Set your mode scheme and save :


![image](https://user-images.githubusercontent.com/1717155/119147784-2f5f7d00-ba4c-11eb-9de4-5e62ff5e71a8.png)

In this example I set ECO mode during the night and the day when nobody's at home BOOST in the morning and COMFORT in the evening.


I hope this example helps you, don't hesitate to give me your feedbacks !

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[versatile_thermostat]: https://github.com/jmcollin78/versatile_thermostat
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
