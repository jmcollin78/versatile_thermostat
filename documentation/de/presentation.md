# Wann man es verwenden sollte und wann nicht
Dieser Thermostat kann 3 Gerätetypen steuern:
1. Einen Heizkörper, der nur im Ein- und Ausschaltmodus funktioniert (genannt `Thermostat_over_switch`). Die erforderliche Mindestkonfiguration zur Verwendung dieser Art von Thermostat ist:
   1. Ein Gerät wie ein Heizkörper (ein `Schalter` oder ähnliches),
   2. Einen Temperatursensor für den Raum (oder eine input_number),
   3. Einen externen Temperatursensor (wenn Sie keinen haben, sollten Sie die Wetterintegration in Betracht ziehen).
2. Ein anderer Thermostat, der seine eigenen Betriebsmodi hat (genannt `thermostat_over_climate`). Für diese Art von Thermostat ist folgende Mindestkonfiguration erforderlich:
   1. Geräte - wie Klimaanlagen oder Thermostatventile - werden von ihrer eigenen `Klimaeinheit` gesteuert.
3. Geräte, die einen Wert von 0 bis 100% annehmen können (genannt `thermostat_over_valve`). Bei 0 ist die Heizung ausgeschaltet, und bei 100% ist sie vollständig geöffnet. Dieser Typ ermöglicht die Steuerung eines Thermostatventils (z. B. Shelly-Ventil), das eine Entität des Typs `number` besitzt, mit dem die Öffnung des Ventils direkt gesteuert werden kann. Versatile Thermostat regelt die Raumtemperatur durch Anpassung des Öffnungsprozentsatzes, wobei sowohl die internen als auch die externen Temperatursensoren und der unten beschriebene TPI-Algorithmus verwendet werden.

Mit dem Typ `over_climate` können Sie alle von VersatileThermostat angebotenen Funktionen zu Ihren vorhandenen Geräten hinzufügen. Die VersatileThermostat `climate`-Entität steuert Ihre zugrunde liegende `climate`-Entität, schaltet sie aus, wenn Fenster geöffnet sind, schaltet in den Eco-Modus, wenn niemand anwesend ist, usw. Siehe [hier](#pourquoi-un-nouveau-thermostat-implémentation). Bei dieser Art von Thermostat werden alle Heizzyklen von der zugrunde liegenden `Klima`-Einheit und nicht vom Versatile Thermostat selbst gesteuert. Eine optionale Autoregulierungsfunktion ermöglicht es dem Versatile Thermostat, die Solltemperatur an die zugrunde liegende Einheit anzupassen, um den Sollwert zu erreichen.

Bei Installationen mit einem Pilotdraht und einer Aktivierungsdiode gibt es eine Option, die die Umkehrung der Ein/Aus-Steuerung des darunter liegenden Heizkörpers ermöglicht. Verwenden Sie dazu den Typ `over_switch` und aktivieren Sie die Option „Invert command“.

# Warum eine neue Thermostat-Implementierung?

Diese Komponente mit der Bezeichnung __Versatile Thermostat__ verwaltet die folgenden Anwendungsfälle:
- Konfiguration über die grafische Standard-Integrationsschnittstelle (unter Verwendung des Config-Entry-Ablaufs),
- Volle Nutzung des **Voreinstellungsmodus**,
- Deaktiviert den Voreinstellungsmodus, wenn die Temperatur **manuell** an einem Thermostat eingestellt wird,
- Schaltet ein Thermostat aus/ein oder ändert nach einer bestimmten Verzögerung die Voreinstellung, wenn eine **Tür oder ein Fenster  geöffnet/geschlossen** wird,
- Ändert die Voreinstellung, wenn **Aktivität erkannt** wird oder niemand für eine bestimmte Zeit im Raum ist,
- Verwendung eines **TPI (Time Proportional Interval/Zeitproportionales Intervall)**-Algorithmus, dank an [[Argonaute] (https://forum.hacf.fr/u/argonaute/summary)],
- Fügt ein **Lastabwurf**-Management oder eine Regelung hinzu, um eine bestimmte Gesamtleistung nicht zu überschreiten. Wenn die maximale Leistung überschritten wird, wird eine verborgene Voreinstellung von „Leistung“ auf die Entität `climate` gesetzt. Wenn die Leistung unter das Maximum sinkt, wird die vorherige Voreinstellung wiederhergestellt.
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

