# When to Use and Not Use It
This thermostat can control 3 types of equipment:
1. A radiator that only works in on/off mode (called `thermostat_over_switch`). The minimum configuration required to use this type of thermostat is:
   1. An equipment like a radiator (a `switch` or equivalent),
   2. A temperature sensor for the room (or an input_number),
   3. An external temperature sensor (consider the weather integration if you don't have one).
2. Another thermostat that has its own modes of operation (called `thermostat_over_climate`). For this type of thermostat, the minimum configuration requires:
   1. Equipment – like air conditioning, a thermostatic valve – controlled by its own `climate` entity.
3. Equipment that can take a value from 0 to 100% (called `thermostat_over_valve`). At 0, heating is off, and at 100% it is fully open. This type allows controlling a thermostatic valve (e.g., Shelly valve) that exposes a `number` type entity, enabling direct control of the valve's opening. Versatile Thermostat regulates the room temperature by adjusting the opening percentage, using both the internal and external temperature sensors, and utilizing the TPI algorithm described below.

The `over_climate` type allows you to add all the features offered by VersatileThermostat to your existing equipment. The VersatileThermostat `climate` entity will control your underlying `climate` entity, turn it off if windows are open, switch to Eco mode if no one is present, etc. See [here](#pourquoi-un-nouveau-thermostat-implémentation). For this type of thermostat, all heating cycles are controlled by the underlying `climate` entity and not by the Versatile Thermostat itself. An optional auto-regulation function allows Versatile Thermostat to adjust the setpoint temperature to the underlying entity in order to reach the setpoint.

Installations with a pilot wire and activation diode benefit from an option that allows inverting the on/off control of the underlying radiator. To do this, use the `over_switch` type and check the "Invert command" option.

# Why a New Thermostat Implementation?

This component, called __Versatile Thermostat__, manages the following use cases:
- Configuration via the standard integration graphical interface (using the Config Entry flow),
- Full use of **preset mode**,
- Disable preset mode when the temperature is **set manually** on a thermostat,
- Turn off/on a thermostat or change preset when a **door or windows are opened/closed** after a certain delay,
- Change preset when **activity is detected** or not in a room for a defined time,
- Use a **TPI (Time Proportional Interval)** algorithm thanks to [[Argonaute](https://forum.hacf.fr/u/argonaute/summary)],
- Add **load shedding** management or regulation to not exceed a defined total power. When the maximum power is exceeded, a hidden preset of "power" is set on the `climate` entity. When the power goes below the maximum, the previous preset is restored.
- **Presence management**. This feature allows dynamically modifying the preset temperature based on the presence sensor in your home.
- **Actions to interact with the thermostat** from other integrations: you can force presence/non-presence using a service, and you can dynamically change preset temperatures and modify security settings.
- Add sensors to view the thermostat's internal states,
- Centralized control of all Versatile Thermostats to stop them all, set them all to frost protection, force them all to heating mode (in winter), force them all to cooling mode (in summer).
- Control of a central heating boiler and VTherms that must control this boiler.
- Automatic start/stop based on usage prediction for `over_climate`.

All these functions are configurable either centrally or individually depending on your needs.

# Equipment

To operate _VTherm_, you will need some hardware. The list below is not exhaustive but includes the most commonly used devices that are fully compatible with Home Assistant and _VTherm_. These are affiliate links to the partner store [Domadoo](https://www.domadoo.fr/fr/?domid=97), which allows me to receive a small percentage if you purchase through these links. Ordering from [Domadoo](https://www.domadoo.fr/fr/?domid=97) gives you competitive prices, a return guarantee, and a very short delivery time comparable to other major online retailers. Their 4.8/5 rating speaks for itself.

⭐ : The most used and therefore the best choice.

## Thermometers
Essential in a _VTherm_ setup, an externalized temperature measurement device placed where you live ensures reliable, comfortable, and stable temperature control.

- [⭐ Sonoff SNZB Zigbee](https://www.domadoo.fr/fr/suivi-energie/6614-sonoff-capteur-de-temperature-et-d-humidite-zigbee-30-avec-ecran-6920075740004.html??domid=97)
- [⭐ 4 x Sonoff SNZB Zigbee](https://www.domadoo.fr/fr/suivi-energie/6968-sonoff-pack-4x-capteurs-de-temperature-et-d-humidite-zigbee-ecran.html?domid=97)
- [ Neo Tuya Zigbee](https://www.domadoo.fr/fr/produits-compatibles-jeedom/7564-neo-capteur-de-temperature-et-humidite-zigbee-30-tuya.html?domid=97)
- [ Moes Tuya Zigbee](https://www.domadoo.fr/fr/domotique/6667-moes-capteur-de-temperature-et-humidite-avec-ecran-zigbee-tuya.html?domid=97)

## Switches
To directly control an electric heater. Usable with _VTherm_ [`over_switch`](over-switch.md):

- [⭐ Sonoff Power Switch 25 A Wifi](https://www.domadoo.fr/fr/peripheriques/5853-sonoff-commutateur-intelligent-wifi-haute-puissance-25a-6920075776768.html?domid=97)
- [⭐ Nodon SIN-4-1-20 Zigbee](https://www.domadoo.fr/fr/peripheriques/5688-nodon-micromodule-commutateur-multifonctions-zigbee-16a-3700313925188.html?domid=97)
- [Sonoff 4-channel Wifi](https://www.domadoo.fr/fr/peripheriques/5279-sonoff-commutateur-intelligent-wifi-433-mhz-4-canaux-6920075775815.html?domid=97)
- [Smart plug for small heating equipment Zigbee](https://www.domadoo.fr/fr/peripheriques/5880-sonoff-prise-intelligente-16a-zigbee-30-version-fr.html?domid=97)

## Pilot wire switches
To directly control an electric heater equipped with a pilot wire. Usable with _VTherm_ [`over_switch`](over-switch.md) and [customized commands](over-switch.md#la-personnalisation-des-commandes):

- [⭐ Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6828-nodon-module-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)
- [⭐ 4 x Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7050-nodon-pack-4x-modules-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)

## Thermostatic valves
To control a water radiator. Works with a _VTherm_ [`over_valve`](over-valve.md) or [`over_climate` with direct valve control](over-climate.md#thermostat-de-type-over_climate):

- [⭐ Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6776-sonoff-tete-thermostatique-connectee-zigbee-30.html?domid=97) with [`over_climate` with direct valve control](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 2 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7477-sonoff-pack-de-2x-tete-thermostatique-connectee-zigbee-30.html?domid=97) with [`over_climate` with direct valve control](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 4 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7478-sonoff-pack-de-4x-tete-thermostatique-connectee-zigbee-30.html?domid=97) with [`over_climate` with direct valve control](over-climate.md#thermostat-de-type-over_climate),
- [Shelly BLU TRV BLE](https://www.domadoo.fr/fr/black-friday-domotique/7567-shelly-robinet-thermostatique-de-radiateur-a-commande-bluetooth-shelly-blu-trv-3800235264980.html?domid=97) with [`over_valve`](over-valve.md),
- [Moes TRV Zigbee](https://www.domadoo.fr/fr/peripheriques/5783-moes-tete-thermostatique-intelligente-zigbee-30-brt-100-trv-blanc.html?domid=97) with [`over_climate` (without direct valve control)](over-climate.md#thermostat-de-type-over_climate)
- [Schneider Wiser TRV Zigbee](https://www.domadoo.fr/fr/controle-chauffage-clim/5497-schneider-electric-tete-de-vanne-thermostatique-connectee-zigbee-3606489582821.html?domid=97) with [`over_climate` (without direct valve control)](over-climate.md#thermostat-de-type-over_climate)

## Incompatibilities
Some TRV type thermostats are known to be incompatible with Versatile Thermostat. This includes the following valves:
1. Danfoss POPP valves with temperature feedback. It is impossible to turn off this valve as it auto-regulates itself, causing conflicts with VTherm.
2. "Homematic" thermostats (and possibly Homematic IP) are known to have issues with Versatile Thermostat due to the limitations of the underlying RF protocol. This problem particularly arises when trying to control multiple Homematic thermostats at once in a single VTherm instance. To reduce service cycle load, you can, for example, group thermostats using Homematic-specific procedures (e.g., using a wall-mounted thermostat) and let Versatile Thermostat control only the wall-mounted thermostat directly. Another option is to control a single thermostat and propagate mode and temperature changes via automation.
3. Heatzy type thermostats that do not support `set_temperature` commands.
4. Rointe type thermostats tend to wake up on their own. The rest works normally.
5. TRVs like Aqara SRTS-A01 and MOES TV01-ZB, which lack the `hvac_action` state feedback to determine whether they are heating or not. Therefore, state feedback is inaccurate, but the rest seems functional.
6. Airwell air conditioners with the "Midea AC LAN" integration. If two VTherm commands are too close together, the air conditioner stops itself.
7. Climates based on the Overkiz integration do not work. It seems impossible to turn off or even change the temperature on these systems.
8. Heating systems based on Netatmo perform poorly. Netatmo schedules conflict with _VTherm_ programming. Netatmo devices constantly revert to `Auto` mode, which is poorly managed with _VTherm_. In this mode, _VTherm_ cannot determine whether the system is heating or cooling, making it impossible to select the correct algorithm. Some users have managed to make it work using a virtual switch between _VTherm_ and the underlying system, but stability is not guaranteed. An example is provided in the [troubleshooting](troubleshooting.md) section.

