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
![New](images/new-icon.png)

## Release 8.3
1. Hinzufügen einer konfigurierbaren Verzögerung vor der Heizkesselaktivierung,
2. Hinzufügen eines Heizkesselstriggers, sobald die gesamte aktivierte Leistung einen Schwellenwert überschreitet. Um diese Funktion zu aktivieren, muss:
- der Schwellenwert für die Leistung konfiguriert sein, bei dessen Überschreiten der Heizkessel gestartet wird. Dies ist eine neue Funktion, die im Gerät 'Zentrale Konfiguration' verfügbar ist.
- die Leistungen der VTherms konfiguriert sein. Diese befindet sich auf der ersten Konfigurationsseite der VTherms.
- das Kästchen `Vom Zentralheizkessel verwendet` ankreuzt sein.

Jedes Mal, wenn ein VTherm aktiviert wird, wird seine konfigurierte Leistung hinzugefügt, und sobald der Schwellenwert überschritten wird, wird der Zentralheizungskessel nach der in 1 konfigurierten Verzögerungszeit aktiviert.

Der alte Zähler für die Anzahl der aktivierten Geräte und sein Schwellenwert sind weiterhin vorhanden. Um einen der Schwellenwerte (den Leistungsschwellenwert oder den Schwellenwert für die Anzahl der aktivierten Geräte) zu deaktivieren, muss er auf Null gesetzt werden. Sobald einer der beiden Schwellenwerte ungleich Null überschritten wird, wird der Heizkessel aktiviert. Es handelt sich also um eine „logische ODER-Verknüpfung” zwischen den beiden Schwellenwerten.

Weitere Informationen [hier](documentation/de/feature-central-boiler.md).

## Release 8.2
> - Hinzufügen einer Funktion zum Sperren/Entsperren eines _VTherm_ mit einem möglichen Code. Weitere Informationen [hier](documentation/de/feature-lock.md)

## Release 8.1
> - Für einen VTherm vom Typ `over_climate` mit direkter Ventilsteuerung wurden dem bestehenden Parameter `minimum_opening_degrees` zwei neue Parameter hinzugefügt, die eine wesentlich feinere Steuerung der minimalen Ventilöffnung ermöglichen. Die Parameter lauten nun:
>    - `opening_threshold`: die minimale Ventilöffnung, unterhalb derer das Ventil als geschlossen gilt und somit der Parameter 'max_closing_degree' gilt,
>    - `max_closing_degree`: der absolute maximale Schließungsprozentsatz. Das Ventil schließt niemals mehr als in diesem Wert angegeben. Wenn Sie das vollständige Schließen des Ventils zulassen möchten, lassen Sie diesen Parameter auf 100 stehen.
>    - `minimum_opening_degrees`: Der minimale Öffnungsgrad, wenn der `opening_threshold` überschritten wird und das VTherm heizen muss. Dieses Feld kann bei einem VTherm mit mehreren Ventilen für jedes Ventil individuell angepasst werden. Sie geben die Liste der Mindestöffnungen durch Kommas getrennt an. Der Standardwert ist 0. Beispiel: '‚20, 25, 30'. Wenn die Heizung startet (d. h. die angeforderte Öffnung ist größer als `opening_threshold`), öffnet sich das Ventil mit einem Wert, der größer oder gleich diesem ist, und erhöht sich bei Bedarf weiter gleichmäßig.
>
> Wenn man die vom TPI-Algorithmus angeforderte Öffnung auf der x-Achse und die tatsächlich an das Ventil gesendete Öffnung auf der y-Achse darstellt, erhält man folgende Kurve:
> ![alt text](images/opening-degree-graph).
>
> Diese Entwicklung wurde [hier](https://github.com/jmcollin78/versatile_thermostat/issues/1220) ausführlich diskutiert.

## Release 8.0
> Diese Version ist eine Hauptversion. Es wurde ein Großteil der internen Mechanismen des Versatile Thermostat neu geschrieben und führt mehrere Neuerungen ein:
>    1. _Gewünschter Zustand / aktueller Zustand_: VTherm hat nun zwei Zustände. Der gewünschte Zustand ist der vom Benutzer (oder vom Scheduler) angeforderte Zustand. Der aktuelle Zustand ist der derzeit auf VTherm angewendete Zustand. Letzterer hängt von den verschiedenen Funktionen von VTherm ab. Der Benutzer kann beispielsweise anfordern (gewünschter Zustand), dass die Heizung mit der Voreinstellung „Komfort” eingeschaltet wird, aber da das Fenster als geöffnet erkannt wurde, ist VTherm tatsächlich ausgeschaltet. Diese doppelte Verwaltung ermöglicht es, die Anfrage des Benutzers immer beizubehalten und das Ergebnis der verschiedenen Funktionen auf diese Anfrage des Benutzers anzuwenden, um den aktuellen Zustand zu erhalten. Dies ermöglicht eine bessere Verwaltung von Fällen, in denen mehrere Funktionen auf den Zustand des VTherm einwirken wollen (z. B. Öffnen eines Fensters und Lastabwurf). Dies gewährleistet auch eine Rückkehr zur ursprünglichen Anfrage des Benutzers, wenn keine Erkennung mehr stattfindet.
>    2. _Zeitfilterung_: Die Funktionsweise der Zeitfilterung wurde überarbeitet. Die Zeitfilterung verhindert, dass zu viele Befehle an ein gesteuertes Gerät gesendet werden, um einen zu hohen Batterieverbrauch (z. B. bei batteriebetriebenen Thermostaten) oder zu häufige Änderungen der Sollwerte (Wärmepumpe, Pelletofen, Fußbodenheizung usw.) zu vermeiden. Die neue Funktionsweise ist nun wie folgt: Explizite Anfragen des Benutzers (oder Schedulers) werden immer sofort berücksichtigt. Sie werden nicht gefiltert. Nur Änderungen, die mit äußeren Bedingungen zusammenhängen (z. B. Raumtemperaturen), werden möglicherweise gefiltert. Die Filterung besteht darin, den gewünschten Befehl später erneut zu senden und ihn nicht wie bisher zu ignorieren. Mit dem Parameter `auto_regulation_dtemp` kann die Verzögerungszeit eingestellt werden.
>    3. _Verbesserung der hvac_action_: Die `hvac_action` spiegelt den aktuellen Aktivierungsstatus der gesteuerten Anlage wider. Bei einem Typ `over_switch` spiegelt sie den Aktivierungsstatus des Schalters wider, bei einem `over_valve` oder einer Ventilregelung ist sie aktiv, wenn die Ventilöffnung größer als die minimale Ventilöffnung ist (oder 0, wenn nicht konfiguriert). Bei einem `over_climate` spiegelt sie die `hvac_action` des verknüpften `climate` wider, sofern verfügbar, andernfalls eine Simulation.
>    4. _Benutzerdefinierte Attribute_: Die Organisation der benutzerdefinierten Attribute, die unter Entwicklertools/Status zugänglich sind, wurde neu strukturiert und hängt nun vom Typ des VTherm und den jeweils aktivierten Funktionen ab. Mehr Information [hier](documentation/de/reference.md#custom-attributes).
> 5. _Lastabwurf_: Der Lastabwurf-Algorithmus berücksichtigt nun das Abschalten eines Geräts zwischen zwei Messungen des Stromverbrauchs der Wohnung. Nehmen wir an, Sie haben alle 5 Minuten einen Anstieg des Stromverbrauchs. Wenn zwischen zwei Messungen ein Heizkörper ausgeschaltet wird, kann das Einschalten eines neuen Heizkörpers zugelassen werden. Zuvor wurden zwischen zwei Messungen nur Einschaltungen berücksichtigt. Wie zuvor wird der nächste Anstieg des Stromverbrauchs möglicherweise zu einer mehr oder weniger starken Lastabsenkung führen.
>    6. _auto-start/stop_: Die automatische Start-/Stoppfunktion ist nur für Vtherm-Typen vom Typ `over_climate` ohne direkte Ventilsteuerung nützlich. Die Option wurde für andere VTherm-Typen entfernt.
>    7. _VTherm UI Card_: All diese Änderungen haben zu einer wesentlichen Weiterentwicklung der [VTherm UI Card](documentation/de/additions.md#versatile-thermostat-ui-card) geführt, sodass nun Meldungen integriert sind, die den aktuellen Status erklären (warum hat mein VTherm diese Zieltemperatur?) und ob eine Zeitfilterung läuft – wodurch die Aktualisierung des Status des Basiswerts verzögert wurde.
>    8. _Verbesserung der Protokolle_: Die Protokolle wurden verbessert, um die Fehlersuche zu vereinfachen. Protokolle in der Form `--------------------> NEW EVENT: VersatileThermostat-Inversed ...` informieren über ein Ereignis, das sich auf den Status des VTherm auswirkt.
>
> ⚠️ **Warnung**
>
> Diese Hauptversion enthält Änderungen, die mit der vorherigen Version nicht kompatibel sind:
> - `versatile_thermostat_security_event` wurde in `versatile_thermostat_safety_event` umbenannt. Wenn Ihre Automatisierungen dieses Ereignis verwenden, müssen Sie diese aktualisieren.
> - Die benutzerdefinierten Attribute wurden neu organisiert. Sie müssen Ihre Automatisierungen oder Jinja-Vorlagen, die diese verwenden, aktualisieren.
> - Die [VTherm UI Card](documentation/de/additions.md#versatile-thermostat-ui-card) muss mindestens auf V2.0 aktualisiert werden, um kompatibel zu sein.
>
> **Trotz der 342 automatisierten Tests dieser Integration und der Sorgfalt, mit der diese wichtige Version erstellt wurde, kann ich nicht garantieren, dass die Installation keine Störungen an Ihren VTherm-Geräten verursacht. Für jedes VTherm-Gerät müssen Sie nach der Installation die Voreinstellung, den hvac_mode und gegebenenfalls die Solltemperatur des VTherm überprüfen.**
>

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
19. [Algorithmen](documentation/de/algorithms.md)
20. [Referenzdokumentation](documentation/de/reference.md)
21. [Tuning-Beispiele](documentation/de/tuning-examples.md)
22. [Störungsbeseitigung](documentation/de/troubleshooting.md)
23. [Veröffentlichungshinweise](documentation/de/releases.md)

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
