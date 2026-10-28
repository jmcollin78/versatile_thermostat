# Schnellstart

Diese Seite fasst die Schritte zusammen, um ein funktionierendes _VTherm_ zu erhalten, unabhängig vom gesteuerten Gerät. Jeder Schritt verweist auf die Seite, die ihn ausführlich beschreibt. Eine Anleitung nach Heizungsart (Thermostatventil, Wärmepumpe, Steuerleitung, Pelletofen) finden Sie in den [Schnellstart-Anleitungen der Website](https://www.versatile-thermostat.org/de/quick-start/). Die gerätespezifischen Einstellungen stehen auf der Seite des Geräts im [Gerätekatalog](https://www.versatile-thermostat.org/de/devices/).

- [Schnellstart](#schnellstart)
  - [Bevor Sie beginnen](#bevor-sie-beginnen)
  - [Das VTherm erstellen](#das-vtherm-erstellen)
  - [Einstellen und prüfen](#einstellen-und-prüfen)
  - [Nächster Schritt](#nächster-schritt)

## Bevor Sie beginnen

- Versatile Thermostat ist installiert (siehe [Installation](installation.md)).
- Das zu steuernde Gerät ist in Home Assistant verfügbar, ebenso ein Raumtemperatursensor und ein Außentemperatursensor.
- Sie wissen, welche Entity das Gerät bereitstellt (`climate`, `number`, `switch` oder `select`): Sie bestimmt den _VTherm_-Typ (siehe [Wähle das Richtige aus](creation.md#wähle-das-richtige-aus)).

## Das VTherm erstellen

1. **Fügen Sie die Integration** Versatile Thermostat über die Seite der Integrationen hinzu und wählen Sie den zum Gerät passenden _VTherm_-Typ (siehe [Wahl eines VTherm](creation.md)). Die zentrale Konfiguration ist optional: Ohne sie lassen Sie die Kästchen „Zentrale Konfiguration verwenden“ deaktiviert.
2. **Wichtigste Eigenschaften**: Geben Sie dem _VTherm_ einen Namen und wählen Sie den Raumtemperatursensor, dann den Außentemperatursensor. Behalten Sie die Standard-Zyklusdauer bei (siehe [Auswahl der grundlegenden Attribute](base-attributes.md)).
3. **Funktionen**: Aktivieren Sie vorerst keine. Sie fügen sie hinzu, sobald das _VTherm_ funktioniert.
4. **Basiswerte**: Wählen Sie die Entity des Geräts. Die Einstellungen hängen vom Typ ab:
   - [`over_climate`](over-climate.md): Ist die Ventilöffnung eines TRV steuerbar, wählen Sie die [direkte Ventilsteuerung](self-regulation.md#selbstregulierung-bei-direkter-ventilkontrolle). Andernfalls lassen Sie die Selbstregulierung zunächst deaktiviert.
   - [`over_valve`](over-valve.md): Wählen Sie die `number`-Entity des Ventils.
   - [`over_switch`](over-switch.md): Ein `switch` genügt. Für ein Steuerleitungsmodul (`select`) oder eine `climate`-Entity geben Sie die [angepassten Befehle](over-switch.md#befehlsanpassung) ein.

   Die gerätespezifischen Einstellungen (zu verwendende Entities, Befehle, bekannte Fallstricke) stehen auf der Seite des Geräts im [Gerätekatalog](https://www.versatile-thermostat.org/de/devices/).
5. **TPI-Parameter**, wenn dieses Menü angeboten wird: Behalten Sie die Standardwerte bei (siehe [die TPI-Koeffizienten](algorithms.md#konfigurieren-der-tpi-algorithmusfaktoren)).
6. **Temperaturvoreinstellungen**: Bestätigen Sie das Menü (siehe [Voreinstellungen](feature-presets.md)).
7. **Erweiterte Einstellungen**: Behalten Sie die Standardwerte des Sicherheitsmodus bei (siehe [Sicherheitsparameter](feature-advanced.md#sicherheitsparameter)).
8. **Alles erledigt**: Das _VTherm_ ist erstellt.

## Einstellen und prüfen

1. Stellen Sie die Temperatur jeder Voreinstellung über die Entities des _VTherm_ ein (siehe [Voreinstellungen](feature-presets.md)).
2. Schalten Sie das _VTherm_ in den Heizmodus und wählen Sie die Voreinstellung Komfort, mit einem Sollwert über der Raumtemperatur.
3. Prüfen Sie, ob das Gerät reagiert: Das Ventil öffnet sich, das Gerät erhält den Sollwert oder der Heizkörper schaltet sich ein.

Wenn nichts passiert, lesen Sie die [Störungsbeseitigung](troubleshooting.md), [laden Sie dann die Protokolle herunter](feature-logs-collector.md) und öffnen Sie sie im [Log-Analyser](https://www.versatile-thermostat.org/de/debugger/) der Website.

## Nächster Schritt

Sobald dieses Basis-_VTherm_ funktioniert:

- Installieren Sie die UI-Karte und einen Zeitplaner, vorgestellt in [Einige unverzichtbare Ergänzungen](additions.md).
- Aktivieren Sie die nützlichen [Funktionen](base-attributes.md#auswahl-der-zu-verwendenden-eigenschaften) nacheinander und prüfen Sie jedes Mal, ob das _VTherm_ richtig reagiert: [Erkennung offener Fenster](feature-window.md), [Anwesenheitsverwaltung](feature-presence.md), [Steuerung der Zentralheizung](feature-central-boiler.md)...
- Danach bei Bedarf: [zentrale Konfiguration](creation.md#zentrale-konfiguration), [zentralisierte Steuerung](feature-central-mode.md), [Ventilkalibrierung](feature-recalibrate-valves.md), [Einstellung der Selbstregulierung](self-regulation.md) und [Tuning-Beispiele](tuning-examples.md).
