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
- **Präsenzverwaltung**. Diese Funktion ermöglicht die dynamische Änderung der voreingestellten Temperatur auf Grundlage des Präsenzsensors in Ihrer Wohnung.
- **Aktionen zur Interaktion mit dem Thermostat** aus anderen Integrationen: Sie können die Anwesenheit/Nicht-Anwesenheit über einen Dienst erzwingen und Sie können die voreingestellten Temperaturen dynamisch ändern und die Sicherheitseinstellungen modifizieren.
- Fügt Sensoren hinzu, die die internen Zustände des Thermostats anzeigen,
- Zentrale Steuerung aller Versatile Thermostate, um sie alle zu stoppen, auf Frostschutz zu stellen, in den Heizmodus zu zwingen (im Winter), in den Kühlmodus zu zwingen (im Sommer).
- Steuerung eines Zentralheizungskessels und VTherms, die diesen Kessel steuern müssen.
- Automatischer Start/Stopp auf der Grundlage der Nutzungsvorhersage für `over_climate`.

Alle diese Funktionen sind je nach Bedarf entweder zentral oder individuell konfigurierbar.

# Equipment

Für den Betrieb von _VTherm_ werden einige Geräte benötigt. Die folgende Liste ist nicht vollständig, enthält aber die am häufigsten verwendeten Geräte, die vollständig mit Home Assistant und _VTherm_ kompatibel sind. Dies sind Affiliate-Links zum Partnershop [Domadoo](https://www.domadoo.fr/fr/?domid=97), wodurch ich einen kleinen Prozentsatz erhalte, wenn Sie über diese Links einkaufen. Sollten Sie bei [Domadoo](https://www.domadoo.fr/fr/?domid=97) bestellen, erhalten Sie günstige Preise, eine Rückgabegarantie und eine sehr kurze Lieferzeit, die mit der anderer großer Online-Händler vergleichbar ist. Ihre 4.8/5 Bewertung spricht für sich selbst.

⭐ : Die meistgenutzte und daher beste Wahl.

## Thermometer
Um ein zuverlässige, komfortable und stabile Temperaturregelung zu gewährleisten, ist für eine _VTherm_-Einrichtung ein externes Temperaturmessgerät, welches dort ist, wo sie leben, unerlässlich.

- [⭐ Sonoff SNZB Zigbee](https://www.domadoo.fr/fr/suivi-energie/6614-sonoff-capteur-de-temperature-et-d-humidite-zigbee-30-avec-ecran-6920075740004.html??domid=97)
- [⭐ 4 x Sonoff SNZB Zigbee](https://www.domadoo.fr/fr/suivi-energie/6968-sonoff-pack-4x-capteurs-de-temperature-et-d-humidite-zigbee-ecran.html?domid=97)
- [ Neo Tuya Zigbee](https://www.domadoo.fr/fr/produits-compatibles-jeedom/7564-neo-capteur-de-temperature-et-humidite-zigbee-30-tuya.html?domid=97)
- [ Moes Tuya Zigbee](https://www.domadoo.fr/fr/domotique/6667-moes-capteur-de-temperature-et-humidite-avec-ecran-zigbee-tuya.html?domid=97)

## Schalter (Switches)
Zur direkten Steuerung einer elektrischen Heizung. Verwendbar mit _VTherm_ [`over_switch`](over-switch.md):

- [⭐ Sonoff Power Switch 25 A Wifi](https://www.domadoo.fr/fr/peripheriques/5853-sonoff-commutateur-intelligent-wifi-haute-puissance-25a-6920075776768.html?domid=97)
- [⭐ Nodon SIN-4-1-20 Zigbee](https://www.domadoo.fr/fr/peripheriques/5688-nodon-micromodule-commutateur-multifonctions-zigbee-16a-3700313925188.html?domid=97)
- [Sonoff 4-channel Wifi](https://www.domadoo.fr/fr/peripheriques/5279-sonoff-commutateur-intelligent-wifi-433-mhz-4-canaux-6920075775815.html?domid=97)
- [Smart plug for small heating equipment Zigbee](https://www.domadoo.fr/fr/peripheriques/5880-sonoff-prise-intelligente-16a-zigbee-30-version-fr.html?domid=97)

## Pilotdraht (Pilot wire) Schalter
Zur direkten Steuerung eines elektrischen Heizgeräts mit Pilotdraht. Verwendbar mit _VTherm_ [`over_switch`](over-switch.md) und [individuelle Befehle](over-switch.md#la-personnalisation-des-commandes):

- [⭐ Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6828-nodon-module-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)
- [⭐ 4 x Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7050-nodon-pack-4x-modules-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)

## Thermostatventile
Zur Steuerung eines Wasserheizkörpers. Funktioniert mit einem _VTherm_. [`over_valve`](over-valve.md) oder [`over_climate` mit direkter Ventilsteuerung](over-climate.md#thermostat-de-type-over_climate):

- [⭐ Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6776-sonoff-tete-thermostatique-connectee-zigbee-30.html?domid=97) mit [`over_climate` mit direkter Ventilsteuerung](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 2 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7477-sonoff-pack-de-2x-tete-thermostatique-connectee-zigbee-30.html?domid=97) mit [`over_climate` mit direkter Ventilsteuerung](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 4 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7478-sonoff-pack-de-4x-tete-thermostatique-connectee-zigbee-30.html?domid=97) mit [`over_climate` mit direkter Ventilsteuerung](over-climate.md#thermostat-de-type-over_climate),
- [Shelly BLU TRV BLE](https://www.domadoo.fr/fr/black-friday-domotique/7567-shelly-robinet-thermostatique-de-radiateur-a-commande-bluetooth-shelly-blu-trv-3800235264980.html?domid=97) mit [`over_valve`](over-valve.md),
- [Moes TRV Zigbee](https://www.domadoo.fr/fr/peripheriques/5783-moes-tete-thermostatique-intelligente-zigbee-30-brt-100-trv-blanc.html?domid=97) mit [`over_climate` (ohne direkte Ventilsteuerung)](over-climate.md#thermostat-de-type-over_climate)
- [Schneider Wiser TRV Zigbee](https://www.domadoo.fr/fr/controle-chauffage-clim/5497-schneider-electric-tete-de-vanne-thermostatique-connectee-zigbee-3606489582821.html?domid=97) mit [`over_climate` (ohne direkte Ventilsteuerung)](over-climate.md#thermostat-de-type-over_climate)

## Inkompatibilitäten
Einige Thermostate vom Typ TRV sind bekanntermaßen nicht mit dem Versatile Thermostat kompatibel. Dazu gehören die folgenden Ventile:
1. Danfoss POPP-Ventile mit Temperaturrückführung. Es ist nicht möglich, dieses Ventil abzuschalten, da es sich selbst reguliert und dadurch Konflikte mit VTherm verursacht.
2. "Homematic"-Thermostate (und möglicherweise Homematic IP) sind dafür bekannt, dass sie aufgrund der Einschränkungen des zugrunde liegenden RF-Protokolls Probleme mit Versatile Thermostat haben. Dieses Problem tritt insbesondere dann auf, wenn versucht wird, mehrere Homematic-Thermostate gleichzeitig in einer einzigen VTherm-Instanz zu steuern. Um die Belastung des Servicezyklus zu reduzieren, können Sie beispielsweise Thermostate mit Homematic-spezifischen Verfahren gruppieren (z. B. mit einem an der Wand montierten Thermostat) und nur den an der Wand montierten Thermostat direkt von Versatile Thermostat steuern lassen. Eine andere Möglichkeit ist die Steuerung eines einzelnen Thermostats und die Weitergabe von Modus- und Temperaturänderungen über die Automatisierung.
3. Thermostate vom Typ Heatzy, die den Befehl `set_temperature` nicht unterstützen.
4. Thermostate vom Typ Rointe neigen dazu, von selbst aufzuwachen. Der Rest funktioniert normal.
5. TRVs wie Aqara SRTS-A01 und MOES TV01-ZB, denen die `hvac_action`-Zustandsrückmeldung fehlt, um festzustellen, ob sie heizen oder nicht. Daher ist die Zustandsrückmeldung ungenau, aber der Rest scheint zu funktionieren.
6. Airwell-Klimageräte mit der „Midea AC LAN“-Integration. Wenn zwei VTherm-Befehle zu schnell hintereinander kommen, schaltet sich das Klimagerät selbstständig ab.
7. Klimaanlagen, die auf der Overkiz-Integration basieren, funktionieren nicht. Es scheint unmöglich zu sein, die Temperatur dieser Systeme auszuschalten oder gar zu ändern.
8. Heizsysteme, die auf Netatmo basieren, funktionieren schlecht. Netatmo-Zeitpläne geraten in Konflikt mit der _VTherm_-Programmierung. Netatmo-Geräte schalten ständig in den `Auto´-Modus, der mit _VTherm_ schlecht verwaltet wird. In diesem Modus kann _VTherm_ nicht feststellen, ob das System heizt oder kühlt, so dass es unmöglich ist, den richtigen Algorithmus zu wählen. Einige Benutzer haben es geschafft, einen virtuellen Schalter zwischen _VTherm_ und dem zugrundeliegenden System zu verwenden, aber die Stabilität ist nicht garantiert. Ein Beispiel finden Sie im Abschnitt [troubleshooting](troubleshooting.md).

