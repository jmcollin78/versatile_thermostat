[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Versatile Thermostat

Diese README-Datei ist verfügbar in folgenden
Sprachen: [English](README.md) | [Français](README-fr.md) | [Deutsch](README-de.md) | [Čeština](README-cs.md) | [Polski](README-pl.md)

<p align="center">
<img src="https://github.com/jmcollin78/versatile_thermostat/blob/main/images/icon.png" />
</p>

> ![Tipp](images/tips.png) **Versatile Thermostat** ist ein hochgradig konfigurierbarer virtueller Thermostat, der jedes Heizgerät (Heizkörper, Klimaanlagen, Wärmepumpen usw.) in ein intelligentes und adaptives System umwandelt. Er ermöglicht es, mehrere verschiedene Heizsysteme zu stabilisieren und zentral zu steuern, während gleichzeitig automatisch der Energieverbrauch optimiert wird. Dank fortschrittlicher Algorithmen (TPI, Auto-TPI) und Lernfähigkeiten passt sich der Thermostat an Ihr Haus 🏠 und Ihre Gewohnheiten an und bietet optimalen Komfort sowie eine signifikante Senkung Ihrer Heizrechnungen 💰.
> Diese Thermostat-Integration zielt darauf ab, Ihre Heizungsmanagement-Automatisierungen erheblich zu vereinfachen. Da alle typischen Heizungsereignisse (niemand zu Hause?, Aktivität in einem Raum erkannt?, Fenster offen?, Stromlastabwurf?) nativ vom Thermostat verwaltet werden, müssen Sie sich nicht mit komplizierten Skripten und Automatisierungen beschäftigen, um Ihre Thermostate zu verwalten. 😉

Diese benutzerdefinierte Komponente für Home Assistant ist ein Upgrade und eine komplette Neufassung der Komponente "Awesome thermostat" (siehe [Github](https://github.com/dadge/awesome_thermostat)) mit zusätzlichen Funktionen.

# Screenshots

Versatile Thermostat UI Card (Verfügbar auf [Github](https://github.com/jmcollin78/versatile-thermostat-ui-card)) :

![Card1](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/1.png) ![Card2](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/7.png)

# Was ist neu?
![Neu](images/new-icon.png)

## Release 10.4.0
VTherm kann jetzt `current_humidity` mit einem externen Luftfeuchtigkeitssensor für alle Thermostattypen bereitstellen. Der Sensor wird im Menü Luftfeuchtigkeit ausgewählt oder am Gerät des Raumtemperatursensors automatisch erkannt.

`over_valve`-Thermostate verfügen jetzt über dieselben Ventilsteuerungsparameter wie `over_climate`-Thermostate mit direkter Ventilregelung: `opening_threshold_degree`, `min_opening_degrees`, `max_closing_degree` und `max_opening_degrees`. Weitere Informationen: [Ventilsteuerung](documentation/de/over-valve.md).

`over_valve`-Thermostate unterstützen jetzt auch den Ruhemodus. Er zeigt VTherm als ausgeschaltet an und sendet eine rohe Öffnungsanforderung von 100 %, ohne die Zentralheizung anzufordern. Konfigurierte Grenzen der Ventilsteuerung können die physische Öffnung begrenzen. Weitere Informationen: [Ruhemodus](documentation/de/over-valve.md#ruhemodus).

## Release 10.3.0
Leistungseinheiten können nun konfiguriert werden. In den Konfigurationsbildschirmen kann eine Einheit für Leistungsmessungen ausgewählt werden (standardmäßig W). Berechnete Energieeinheiten richten sich nach der konfigurierten Leistungseinheit. Bestehende Einträge werden anhand des historischen Geräteleistungswerts migriert: Werte über 100 werden als W behandelt, andere Werte als kW.

⚠️ **Wichtige Änderung für Statistiken**
Möglicherweise erscheint eine Reparaturbenachrichtigung wie: `Die Einheit von „Central configuration Total power active for boiler“ (sensor.total_power_active_for_boiler) wurde in „kW“ geändert`, oder eine ähnliche Meldung im Protokoll. Dies ist normal, da die Einheit zuvor nicht angegeben war. Wählen Sie die Reparaturaktion `Einheit der Langzeitstatistiken aktualisieren`, um die Statistiken zu korrigieren.

## Release 10.2.0
Die Funktion **Auto Fan** ist jetzt als externes Plugin verfügbar ([vtherm_auto_fan_extended](https://github.com/jmcollin78/vtherm_auto_fan_extended)). Die ursprüngliche (_Legacy_) Auto-Fan-Version ist in _VTherm_ weiterhin verfügbar, muss jedoch in der Thermostatkonfiguration deaktiviert werden, um das Plugin verwenden zu können. Die vollständige Dokumentation ist im [GitHub-Repository des Plugins](https://github.com/jmcollin78/vtherm_auto_fan_extended) verfügbar.

## Release 10.1
Auswahl des Stopp-Modus für Auto-Start/Stopp. Eine neue `select`-Entität ermöglicht die Auswahl des Modus, der angewendet wird, wenn die Auto-Start/Stopp-Funktion eine Stoppbedingung erkennt: `Aus` (Standard), `Nur Lüfter` oder `Trocknen`. Die Modi `Nur Lüfter` und `Trocknen` werden nur angeboten, wenn das zugrunde liegende Gerät sie unterstützt. Weitere Informationen [hier](documentation/en/feature-auto-start-stop.md).

Die Selbstregulierung ist nun deaktiviert, wenn sich ein _VTherm_ vom Typ `over_climate` nicht im Modus `Heizen` oder `Kühlen` befindet: Der ursprüngliche (nicht regulierte) Sollwert wird an das zugehörige Gerät gesendet. Weitere Informationen [hier](documentation/en/self-regulation.md).

## Release 10.0
Einführung des Plugin-Mechanismus. Dadurch können externe Integrationen als Plugins für _VTherm_ verwendet werden. Die Liste der verfügbaren Plugins ist auf der [Versatile Thermostat Web site](https://www.versatile-thermostat.org/de/plugins) verfügbar.



Weitere Informationen [hier](documentation/de/feature-central-boiler.md).

# 🍻 Danke für die Biere 🍻
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jmcollin78)

Ein großes Dankeschön an alle meine Biersponsoren für ihre Spenden und Ermutigungen. Das bedeutet mir sehr viel und motiviert mich, weiterzumachen! Wenn Sie durch diese Integration Geld gespart haben, geben Sie mir im Gegenzug ein Bier aus; ich würde mich sehr darüber freuen!

# Glossar

  `VTherm`: Versatile Thermostat, wie in diesem Dokument beschrieben

  `TRV`: Thermisches RadiatorVentil (Heizkörperventil), ausgestattet mit einem Ventil. Das Ventil öffnet oder schließt sich, um heißes Wasser durchzulassen.

  `AC`: Klimatisierung (Air Conditioning). Ein AC-Gerät kühlt, statt zu heizen. Die Temperaturen sind umgekehrt: Eco ist wärmer als Comfort, was wiederum wärmer ist als Boost. Die Algorithmen berücksichtigen diese Information.

  `EMA`: Exponentieller gleitender Durchschnitt (Exponential Moving Average). Dient zur Glättung der Temperaturmessungen des Sensors. Er stellt einen gleitenden Durchschnitt der Raumtemperatur dar und wird zur Berechnung der Temperaturkurvensteigung verwendet, die sonst bei den Rohdaten zu instabil wäre.

  `slope`: Die Steigung der Temperaturkurve, gemessen in ° (C oder K)/h. Sie ist positiv, wenn die Temperatur steigt, und negativ, wenn sie sinkt. Diese Steigung wird auf Grundlage der `EMA` brechnet.

  `WP`: Wärmepumpe

  `HA`: Home Assistant

  `underlying`: Das von `VTherm` gesteuerte Gerät

# Dokumentation

Die Dokumentation ist jetzt auf mehrere Seiten aufgeteilt, um das Lesen und Suchen zu erleichtern:
1. [Einleitung](documentation/de/presentation.md)
2. [Installation](documentation/de/installation.md)
3. [Schnellstart](documentation/de/quick-start.md)
4. [Wahl eines VTherm-Typs](documentation/de/creation.md)
5. [Grundlegende Merkmale](documentation/de/base-attributes.md)
6. [Konfiguriere ein VTherm als `switch`](documentation/de/over-switch.md)
7. [Konfiguriere ein VTherm als `climate`](documentation/de/over-climate.md)
8. [Konfiguriere ein VTherm als `valve`](documentation/de/over-valve.md)
9. [Voreinstellungen](documentation/de/feature-presets.md)
10. [Fensterverwaltung](documentation/de/feature-window.md)
11. [Anwesenheitsverwaltung](documentation/de/feature-presence.md)
12. [Bewegungsverwaltung](documentation/de/feature-motion.md)
13. [Energieverwaltung](documentation/de/feature-power.md)
14. [Auto Start und Stop](documentation/de/feature-auto-start-stop.md)
15. [Zentrale Kontrolle aller VTherms](documentation/de/feature-central-mode.md)
16. [Steuerung der Zentralheizung](documentation/de/feature-central-boiler.md)
17. [Weiterführende Aspekte, Sicherheitsmodus](documentation/de/feature-advanced.md)
18. [Erkennung von Heizungsstörungen](documentation/de/feature-heating-failure-detection.md)
19. [Selbstregulierung](documentation/de/self-regulation.md)
20. [Auto-TPI-Lernen](documentation/de/feature-autotpi.md)
21. [Lock / Unlock](documentation/de/feature-lock.md)
22. [Temperatur synchronisieren](documentation/de/feature-sync_device_temp.md)
23. [Zeitsteuerung](documentation/de/feature-timed-preset.md)
24. [Algorithmen](documentation/de/algorithms.md)
25. [Referenzdokumentation](documentation/de/reference.md)
26. [Tuning-Beispiele](documentation/de/tuning-examples.md)
27. [Störungsbeseitigung](documentation/de/troubleshooting.md)
28. [Veröffentlichungshinweise](documentation/de/releases.md)

# Einige Ergebnisse

**Temperaturstabilität um den durch die Voreinstellung konfigurierten Zielwert**:

![image](documentation/en/images/results-1.png)

**Durch die Integration `over_climate` berechnete Ein/Aus-Zyklen**:

![image](documentation/en/images/results-2.png)

**Regelung mit einem `over_switch`**:

![image](documentation/en/images/results-4.png)

**Strenge Regulierung in `over_climate`**:

![image](documentation/en/images/results-over-climate-1.png)

**Regelung mit direkter Ventilsteuerung in `over_climate`**:

![image](documentation/en/images/results-over-climate-2.png)

# Einige Anmerkungen zur Integration
|                                               |                                               |                                               |
| --------------------------------------------- | --------------------------------------------- | --------------------------------------------- |
| ![Kundenmeinung 1](images/testimonials-1.png) | ![Kundenmeinung 2](images/testimonials-2.png) | ![Kundenmeinung 3](images/testimonials-3.png) |
| ![Kundenmeinung 4](images/testimonials-4.png) | ![Kundenmeinung 5](images/testimonials-5.png) | ![Kundenmeinung 6](images/testimonials-6.png) |

# ⭐ Star history

[![Star History Chart](https://star-history.dera.page/svg?repos=jmcollin78/versatile_thermostat&type=Date)](https://star-history.dera.page/#jmcollin78/versatile_thermostat&Date)

Viel Spaß!

# Beiträge sind willkommen!

Wenn Sie einen Beitrag leisten möchten, lesen Sie bitte die [contribution guidelines](CONTRIBUTING-de.md).

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
