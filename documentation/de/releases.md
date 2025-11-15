# Anmerkungen zum Release

![Neu](images/new-icon.png)
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
> * **Release 7.1**:
>   - Umgestaltung der Lastabwurf-Funktion (Energiemanagement). Der Lastabwurf wird jetzt zentral verwaltet (vorher war jedes _VTherm_ autonom). Dies ermöglicht eine wesentlich effizientere Verwaltung und Priorisierung des Lastabwurfs bei Geräten, die sich in der Nähe des Sollwerts befinden. Beachten Sie, dass Sie eine zentralisierte Konfiguration mit aktiviertem Energiemanagement haben müssen, damit dies funktioniert. Weitere Informationen [hier](./feature-power.md).

> * **Release 6.8**:
>   - Es wurde eine neue Regelungsmethode für Versatile Thermostate vom Typ `over_climate` hinzugefügt. Diese Methode mit der Bezeichnung 'Direkte Ventilsteuerung' ermöglicht die direkte Steuerung eines TRV-Ventils und möglicherweise einen Offset zur Kalibrierung des internen Thermometers Ihres TRVs. Diese neue Methode wurde mit Sonoff TRVZB getestet und auf andere TRV-Typen ausgeweitet, bei denen das Ventil direkt über `number`-Entities gesteuert werden kann. Weitere Informationen [hier](over-climate.md#lauto-régulation) und [hier](self-regulation.md#auto-régulation-par-contrôle-direct-de-la-vanne).

## **Release 6.5** :
  - Neue Funktion zum automatischen Stoppen und Neustart eines `VTherm over_climate` [585] (https://github.com/jmcollin78/versatile_thermostat/issues/585)
  - Verbesserte Behandlung von Öffnungen beim Starten. Ermöglicht das Speichern und Neuberechnen des Zustands einer Öffnung beim Neustart des Home Assistant [504](https://github.com/jmcollin78/versatile_thermostat/issues/504)

## **Release 6.0** :
  - `number`-Entitäties hinzugefügt, um voreingestellte Temperaturen zu konfigurieren [354](https://github.com/jmcollin78/versatile_thermostat/issues/354)
  - Komplettes Redesign des Konfigurationsmenüs, um Temperaturen zu entfernen und ein Menü anstelle eines Konfigurationstunnels zu verwenden [354] (https://github.com/jmcollin78/versatile_thermostat/issues/354)

## **Release 5.4** :
  - Temperaturstufe hinzugefügt [#311](https://github.com/jmcollin78/versatile_thermostat/issues/311),
  - Regulierungsschwellenwerte für `over_valve` hinzugefügt, um übermäßige Batterieentladung für TRVs zu verhindern [#338](https://github.com/jmcollin78/versatile_thermostat/issues/338),
  - Option hinzugefügt, um die interne Temperatur eines TRVs zu verwenden, um die automatische Regulierung zu erzwingen [#348](https://github.com/jmcollin78/versatile_thermostat/issues/348),
  - Es wurde eine Keep-Alive-Funktion für `over_switch` VTherms hinzugefügt [#345](https://github.com/jmcollin78/versatile_thermostat/issues/345)

<details>
<summary>Ältere Releases</summary>

> * **Release 5.3** : Eine Funktion zur Steuerung eines zentralen Heizkessels wurde hinzugefügt [#234](https://github.com/jmcollin78/versatile_thermostat/issues/234) - mehr Informationen hier: [Zentrale Kesselsteuerung](#le-contrôle-dune-chaudière-centrale). Es wurde die Möglichkeit hinzugefügt, den Sicherheitsmodus für das externe Thermometer zu deaktivieren [#343](https://github.com/jmcollin78/versatile_thermostat/issues/343)
> * **Release 5.2** : `Zentraler Modus` hinzugefügt, um alle VTherms zentral zu steuern [#158](https://github.com/jmcollin78/versatile_thermostat/issues/158).
> * **Release 5.1** : Begrenzung der an die Ventile gesendeten Werte und der zugehörigen Klimatemperatur.
> * **Release 5.0** : Zentrale Konfiguration hinzugefügt, um konfigurierbare Attribute zu kombinieren [#239](https://github.com/jmcollin78/versatile_thermostat/issues/239).
> * **Release 4.3** : Auto-Ventilator-Modus für den Typ `over_climate` hinzugefügt, um die Lüftung zu aktivieren, wenn der Temperaturunterschied groß ist [#223](https://github.com/jmcollin78/versatile_thermostat/issues/223).
> * **Release 4.2** : Die Steigung der Temperaturkurve wird nun in °/Stunde statt in °/min berechnet. [#242](https://github.com/jmcollin78/versatile_thermostat/issues/242). Die automatische Erkennung von Öffnungen wurde verbessert, indem die Temperaturkurve geglättet wurde.
> * **Release 4.1** : Hinzufügen eines **Experten**-Regulierungsmodus, bei dem die Benutzer ihre eigenen Autoregulierungsparameter festlegen können, anstatt vorprogrammierte Parameter zu verwenden [#194](https://github.com/jmcollin78/versatile_thermostat/issues/194).
> * **Release 4.0** : Unterstützung für **Versatile Thermostat UI Card** hinzugefügt. Siehe [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card). Hinzufügen eines **langsamen** Regelungsmodus für Heizgeräte mit langsamer Latenzzeit [#168](https://github.com/jmcollin78/versatile_thermostat/issues/168). Die Berechnung der **Leistung** für VTherms mit mehreren zugehörigen Geräten wurde geändert. [#146](https://github.com/jmcollin78/versatile_thermostat/issues/146). Unterstützung für AC und Wärme für VTherms über einen Schalter hinzugefügt [#144](https://github.com/jmcollin78/versatile_thermostat/pull/144)
> * **Release 3.8**: Es wurde eine **Autoregulierungsfunktion** für `over_climate` Thermostate hinzugefügt, die durch das dazugehörige Klima reguliert werden. Siehe [Autoregulierung](#lauto-régulation) and [#129](https://github.com/jmcollin78/versatile_thermostat/issues/129). Hinzufügen der **Fähigkeit zur Invertierung der Steuerung** für `over_switch`-Thermostate, um Installationen mit Pilotdraht und Diode zu ermöglichen [#124](https://github.com/jmcollin78/versatile_thermostat/issues/124).
> * **Release 3.7**: Der Typ `over_valve` Versatile Thermostat wurde hinzugefügt, um ein TRV-Ventil oder ein anderes Dimmergerät für die Heizung direkt zu steuern. Die Regelung erfolgt direkt durch die Einstellung des Prozentsatzes der Öffnung der zugehörigen Einheit: 0 bedeutet, dass das Ventil ausgeschaltet ist, 100 bedeutet, dass das Ventil vollständig geöffnet ist. Siehe [#131](https://github.com/jmcollin78/versatile_thermostat/issues/131). Eine Bypass-Funktion für die Öffnungserkennung wurde hinzugefügt [#138](https://github.com/jmcollin78/versatile_thermostat/issues/138). Unterstützung der slowakischen Sprache hinzugefügt.
> * **Release 3.6**: Der Parameter `motion_off_delay` wurde hinzugefügt, um die Handhabung der Bewegungserkennung zu verbessern [#116](https://github.com/jmcollin78/versatile_thermostat/issues/116), [#128](https://github.com/jmcollin78/versatile_thermostat/issues/128). AC-Modus (Klimatisierung) für `over_switch` VTherm hinzugefügt. Das GitHub-Projekt vorbereitet, um Beiträge zu erleichtern [#127](https://github.com/jmcollin78/versatile_thermostat/issues/127)
> * **Release 3.5**: Mehrere Thermostate im Modus "Thermostat über Klima" möglich [#113](https://github.com/jmcollin78/versatile_thermostat/issues/113)
> * **Release 3.4**: Fehlerbehebung und Aussetzen der voreingestellten Temperaturen für den AC-Modus [#103](https://github.com/jmcollin78/versatile_thermostat/issues/103)
> * **Release 3.3**: Klimatisierungsmodus (AC) hinzugefügt. Mit dieser Funktion können Sie den AC-Modus Ihres zugehörigen Thermostats verwenden. Um sie zu nutzen, müssen Sie die Option "AC-Modus verwenden" aktivieren und Temperaturwerte für Voreinstellungen und entfernte Voreinstellungen definieren.
> * **Release 3.2** : Es wurde die Möglichkeit hinzugefügt, mehrere Schalter vom selben Thermostat aus zu steuern. In diesem Modus werden die Schalter mit einer Verzögerung ausgelöst, um die zu einem bestimmten Zeitpunkt benötigte Leistung zu minimieren (Minimierung der Überlappungszeiten). Siehe [Configuration](#sélectionnez-des-entités-pilotées)
> * **Release 3.1** : Erkennung von geöffneten Fenstern/Türen bei Temperaturabfall hinzugefügt. Diese neue Funktion stoppt automatisch einen Heizkörper, wenn die Temperatur plötzlich fällt. Siehe [Auto Mode](#le-mode-auto)
> * **Major Release 3.0** : Hinzufügen von Thermostatgeräten und zugehörigen Sensoren (binär und nicht-binär). Viel näher an der Home Assistant-Philosophie, haben Sie jetzt direkten Zugriff auf die Energie, die durch den vom Thermostat gesteuerten Heizkörper verbraucht wird, und viele andere Sensoren, die für Ihre Automatisierungen und Dashboards nützlich sind.
> * **Release 2.3** : Zusätzliche Messung von Leistung und Energie für den vom Thermostat gesteuerten Heizkörper.
> * **Release 2.2** : Es wurde eine Sicherheitsfunktion hinzugefügt, die verhindert, dass ein Heizkörper im Falle eines Thermometerausfalls unendlich lange geheizt bleibt.
> * **Major Release 2.0** : Hinzufügen des „Über-Klima“-Thermostats, mit dem jedes Thermostat in ein Versatile Thermostat umgewandelt werden kann und alle seine Funktionen erhält.

</details>

> ![Tipp](images/tips.png) _*Hinweise*_
>
> Vollständige Versionshinweise sind auf dem [GitHub der Integration](https://github.com/jmcollin78/versatile_thermostat/releases/) verfügbar.