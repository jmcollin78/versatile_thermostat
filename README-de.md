[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Versatile Thermostat

Diese README-Datei ist verfügbar in folgenden
Sprachen: [English](README.md) | [Français](README-fr.md) | [Deutsch](README-de.md) | [Czech](README-cs.md) | [Polski](README-pl.md)

<p align="center">
<img src="https://github.com/jmcollin78/versatile_thermostat/blob/main/images/icon.png" />
</p>

> ![Tipp](images/tips.png) Diese Thermostat-Integration zielt darauf ab, Ihre Heizungsmanagement-Automatisierungen erheblich zu vereinfachen. Da alle typischen Heizungsereignisse (niemand zu Hause?, Aktivität in einem Raum erkannt?, Fenster offen?, Stromlastabwurf?) nativ vom Thermostat verwaltet werden, müssen Sie sich nicht mit komplizierten Skripten und Automatisierungen beschäftigen, um Ihre Thermostate zu verwalten. ;-).

Diese benutzerdefinierte Komponente für Home Assistant ist ein Upgrade und eine komplette Neufassung der Komponente "Awesome thermostat" (siehe [Github](https://github.com/dadge/awesome_thermostat)) mit zusätzlichen Funktionen.

# Screenshots

Versatile Thermostat UI Card (Verfügbar auf [Github](https://github.com/jmcollin78/versatile-thermostat-ui-card)) :

![Card1](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/1.png) ![Card2](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/7.png)

# Was ist neu?
![Neu](images/new-icon.png)

## Release 8.6
> 1. Hinzufügen des Parameters `max_opening_degrees` für `over_climate_valve` VTherms, der es ermöglicht, den maximalen Öffnungsgrad jedes Ventils zu begrenzen, um den Heißwasserdurchfluss zu steuern und den Energieverbrauch zu optimieren.
> 2. Hinzufügen einer Ventil-Neukalibrierungsfunktion für ein _VTherm_ `over_climate_valve`, mit der ein maximales Öffnen und anschließend ein maximales Schließen erzwungen werden kann, um eine Neukalibrierung eines TRV zu versuchen. Weitere Informationen [hier](documentation/de/feature-recalibrate-valves.md).

## Release 8.5
> 1. Hinzufügen der Erkennung von Heizungsstörungen für VTherms, die den TPI-Algorithmus verwenden. Diese Funktion erkennt zwei Arten von Anomalien:
>    - **Heizungsstörung**: Der Heizkörper heizt stark (hohes on_percent), aber die Temperatur steigt nicht,
>    - **Kühlungsstörung**: Der Heizkörper heizt nicht (on_percent bei 0), aber die Temperatur steigt weiter.
>
> Diese Anomalien können auf ein offenes Fenster, einen defekten Heizkörper oder eine externe Wärmequelle hinweisen. Die Funktion sendet Ereignisse, die zum Auslösen von Automatisierungen (Benachrichtigungen, Warnungen usw.) verwendet werden können. Weitere Informationen [hier](documentation/de/feature-heating-failure-detection.md).

## Release 8.4
1. Hinzufügen der automatischen TPI-Funktion (experimental). Diese neue Funktion dient dazu, automatisch die besten Koeffizienten für den TPI-Algorithmus zu berechnen. Weitere Informationen gibt es [hier](documentation/en/feature-autotpi.md).
2. added a temperature synchronization function for a device controlled in `over_climate` mode. Depending on your device's capabilities, _VTherm_ can control an offset calibration entity or directly an external temperature entity. More information [here](documentation/de/feature-sync_device_temp.md)
3. added a feature named "timed preset" which aims to select a preset for a certain duration and come back to the previous preset after the expiration of the delay. The new feature is totally described [here](documentation/de/feature-timed-preset.md).

## Release 8.3
1. Hinzufügen einer konfigurierbaren Verzögerung vor der Heizkesselaktivierung,
2. Hinzufügen eines Heizkesselstriggers, sobald die gesamte aktivierte Leistung einen Schwellenwert überschreitet. Um diese Funktion zu aktivieren, muss:
- der Schwellenwert für die Leistung konfiguriert sein, bei dessen Überschreiten der Heizkessel gestartet wird. Dies ist eine neue Funktion, die im Gerät 'Zentrale Konfiguration' verfügbar ist.
- die Leistungen der VTherms konfiguriert sein. Diese befindet sich auf der ersten Konfigurationsseite der VTherms.
- das Kästchen `Vom Zentralheizkessel verwendet` ankreuzt sein.

Jedes Mal, wenn ein VTherm aktiviert wird, wird seine konfigurierte Leistung hinzugefügt, und sobald der Schwellenwert überschritten wird, wird der Zentralheizungskessel nach der in 1 konfigurierten Verzögerungszeit aktiviert.

Der alte Zähler für die Anzahl der aktivierten Geräte und sein Schwellenwert sind weiterhin vorhanden. Um einen der Schwellenwerte (den Leistungsschwellenwert oder den Schwellenwert für die Anzahl der aktivierten Geräte) zu deaktivieren, muss er auf Null gesetzt werden. Sobald einer der beiden Schwellenwerte ungleich Null überschritten wird, wird der Heizkessel aktiviert. Es handelt sich also um eine „logische ODER-Verknüpfung” zwischen den beiden Schwellenwerten.

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
21. [Lock / Unlock](documentation/en/feature-lock.md)
22. [Temperature synchronisation](documentation/en/feature-sync_device_temp.md)
23. [Timed preset](documentation/en/feature-timed-preset.md)
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

# Some comments on the integration
|                                             |                                             |                                             |
| ------------------------------------------- | ------------------------------------------- | ------------------------------------------- |
| ![testimonial 1](images/testimonials-1.png) | ![testimonial 2](images/testimonials-2.png) | ![testimonial 3](images/testimonials-3.png) |
| ![testimonial 4](images/testimonials-4.png) | ![testimonial 5](images/testimonials-5.png) | ![testimonial 6](images/testimonials-6.png) |

Viel Spaß!

# ⭐ Star history

[![Star History Chart](https://api.star-history.com/svg?repos=jmcollin78/versatile_thermostat&type=Date)](https://star-history.com/#jmcollin78/versatile_thermostat&Date)

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
