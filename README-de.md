[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Versatile Thermostat

Diese README-Datei ist verfügbar in folgenden
Sprachen: [English](README.md) | [French](README-fr.md) | [German](README-de.md) | [Czech](README-cs.md) | [Polski](README-pl.md)

<p align="center">
<img src="https://github.com/jmcollin78/versatile_thermostat/blob/main/images/icon.png" />
</p>

> ![Tipp](images/tips.png) Diese Thermostat-Integration zielt darauf ab, Ihre Heizungsmanagement-Automatisierungen erheblich zu vereinfachen. Da alle typischen Heizungsereignisse (niemand zu Hause?, Aktivität in einem Raum erkannt?, Fenster offen?, Stromlastabwurf?) nativ vom Thermostat verwaltet werden, müssen Sie sich nicht mit komplizierten Skripten und Automatisierungen beschäftigen, um Ihre Thermostate zu verwalten. ;-).

Diese benutzerdefinierte Komponente für Home Assistant ist ein Upgrade und eine komplette Neufassung der Komponente "Awesome thermostat" (siehe [Github](https://github.com/dadge/awesome_thermostat)) mit zusätzlichen Funktionen.

# Screenshots

Versatile Thermostat UI Card (Verfügbar auf [Github](https://github.com/jmcollin78/versatile-thermostat-ui-card)) :

![Card1](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/1.png) ![Card2](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/7.png)

# Was ist neu?
![New](images/new-icon.png)
> * **Release 7.4**:
>
> - Es wurden Schwellenwerte hinzugefügt, um den TPI-Algorithmus zu aktivieren oder zu deaktivieren, wenn die Temperatur den Sollwert überschreitet.
> Dadurch werden kurze Ein-/Ausschaltzyklen eines Heizkörpers verhindert.
>   Siehe [TPI](documentation/de/algorithms.md#the-tpi-algorithm)
>
> - Es wurde ein Schlafmodus für VTherms vom Typ `over_climate` mit Regelung durch direkte Ventilsteuerung hinzugefügt. In diesem Modus können Sie den Thermostat auf "Aus" stellen, dabei bleibt das Ventil jedoch zu 100% geöffnet. Dies ist nützlich für längere Zeiträume ohne Heizung, wenn der Heizkessel von Zeit zu Zeit Wasser zirkulieren lässt. Hinweis: Sie müssen die VTherm-UI-Karte aktualisieren, um diesen neuen Modus anzuzeigen. Siehe [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card).
>
> * **Release 7.2**:
>
> - Native Unterstützung für Geräte, die über eine `select` (oder `input_select`) oder `climate` Entität für _VTherm_ vom Typ `over_switch` gesteuert werden können. Dieses Update macht die Erstellung von virtuellen Schaltern für die Integration von Nodon, Heaty, eCosy, etc. überflüssig. Weitere Informationen [hier](documentation/de/over-switch.md#command-customization).
>
> - Links zur Dokumentation: Version 7.2 führt experimentelle Links zur Dokumentation auf den Konfigurationsseiten ein. Der Link ist über das Symbol [![?](https://img.icons8.com/color/18/help.png)](https://github.com/jmcollin78/versatile_thermostat/blob/main/documentation/de/over-switch.md#configuration) erreichbar. Diese Funktion wird derzeit auf einigen Konfigurationsseiten getestet.

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
6. [Konfiguriere ein VTherm als `Schalter`](documentation/de/over-switch.md)
7. [Konfiguriere ein VTherm als `Klima`](documentation/de/over-climate.md)
8. [Konfiguriere ein VTherm als `Ventil`](documentation/de/over-valve.md)
9. [Voreinstellungen](documentation/de/feature-presets.md)
10. [Fensterverwaltung](documentation/de/feature-window.md)
11. [Anwesenheitsverwaltung](documentation/de/feature-presence.md)
12. [Bewegungsverwaltung](documentation/de/feature-motion.md)
13. [Energieverwaltung](documentation/de/feature-power.md)
14. [Auto Start und Stop](documentation/de/feature-auto-start-stop.md)
15. [Zentrale Kontrolle aller VTherms](documentation/de/feature-central-mode.md)
16. [Steuerung der Zentralheizung](documentation/de/feature-central-boiler.md)
17. [Weiterführende Aspekte, Sicherheitsmodus](documentation/de/feature-advanced.md)
18. [Selbstregulierung](documentation/de/self-regulation.md)
19. [Tuning-Beispiele](documentation/de/tuning-examples.md)
20. [Algorithmen](documentation/de/algorithms.md)
21. [Referenzdokumentation](documentation/de/reference.md)
22. [Tuning-Beispiele](documentation/de/tuning-examples.md)
23. [Störungsbeseitigung](documentation/de/troubleshooting.md)
24. [Veröffentlichungshinweise](documentation/de/releases.md)

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
