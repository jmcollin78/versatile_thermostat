# Dokumentation von Versatile Thermostat

Versatile Thermostat (_VTherm_) ist eine Home-Assistant-Integration, die Wasserheizkörper mit Thermostatventilen (TRV) in intelligente Thermostate verwandelt: Voreinstellungen, Fenstererkennung, Anwesenheit, direkte Ventilsteuerung und die Ansteuerung eines zentralen Heizkessels.

_VTherm_ steuert auch Wärmepumpen, Klimaanlagen und elektrische Heizkörper. Alle Funktionen werden über die Oberfläche von Home Assistant konfiguriert, ohne Skripte oder komplizierte Automatisierungen: Niemand ist zu Hause, ein Fenster ist offen, der Heizkessel soll anspringen? Der Thermostat erledigt das selbst.

- [Dokumentation von Versatile Thermostat](#dokumentation-von-versatile-thermostat)
  - [Installationsbeispiel](#installationsbeispiel)
  - [Welcher VTherm-Typ für welches Gerät?](#welcher-vtherm-typ-für-welches-gerät)
  - [Voraussetzungen](#voraussetzungen)
  - [Geräte](#geräte)
  - [Inhalt der Dokumentation](#inhalt-der-dokumentation)
    - [Erste Schritte](#erste-schritte)
    - [VTherm-Typen](#vtherm-typen)
    - [Funktionen](#funktionen)
    - [Regelung](#regelung)
    - [Hilfe und Referenz](#hilfe-und-referenz)
    - [Weiterführende Themen](#weiterführende-themen)
  - [Nächster Schritt](#nächster-schritt)

## Installationsbeispiel

Für Thermostatventile:

1. Ist die Ventilöffnung Ihres TRV in Home Assistant steuerbar (z. B. Sonoff TRVZB), erstellen Sie ein _VTherm_ vom Typ [`over_climate`](over-climate.md) mit [direkter Ventilsteuerung](self-regulation.md#selbstregulierung-bei-direkter-ventilkontrolle): _VTherm_ regelt dann die Raumtemperatur über die Ventilöffnung. Ein Ventil, das nur als `number`-Entity verfügbar ist, steuern Sie mit einem _VTherm_ vom Typ [`over_valve`](over-valve.md).
2. Die [Schnellstart-Anleitung für TRV](https://www.versatile-thermostat.org/de/quick-start/trv/) der Website beschreibt die Konfiguration Schritt für Schritt.
3. Gleichen Sie bei Bedarf das interne Thermometer des TRV mit der [Synchronisierung der internen Gerätetemperatur](feature-sync_device_temp.md) ab und nutzen Sie die [Ventilkalibrierung](feature-recalibrate-valves.md), wenn die Ventile nicht mehr richtig öffnen oder schließen.
4. Fügen Sie die nützlichen Funktionen hinzu: [Steuerung der Zentralheizung](feature-central-boiler.md), um den Heizkessel einzuschalten, sobald ein Raum Wärme benötigt, [Erkennung offener Fenster](feature-window.md) und [Anwesenheitsverwaltung](feature-presence.md).

## Welcher VTherm-Typ für welches Gerät?

| Gerät | _VTherm_-Typ | Zum Einstieg |
|---|---|---|
| Thermostatventil (TRV) mit steuerbarer Ventilöffnung | [`over_climate`](over-climate.md) mit [direkter Ventilsteuerung](self-regulation.md#selbstregulierung-bei-direkter-ventilkontrolle) | [TRV-Anleitung](https://www.versatile-thermostat.org/de/quick-start/trv/) |
| Ventil, das nur als `number`-Entity verfügbar ist | [`over_valve`](over-valve.md) | [Schnellstart](quick-start.md) |
| Einfaches TRV ohne Ventilsteuerung | [`over_climate`](over-climate.md) mit [Selbstregulierung](self-regulation.md) | [Schnellstart](quick-start.md#einfaches-trv-wie-avatto-trv06-moes-tuya-trv-ohne-ventilsteuerung) |
| Wärmepumpe, Klimaanlage, Gerät mit `climate`-Entity | [`over_climate`](over-climate.md) | [Wärmepumpen-Anleitung](https://www.versatile-thermostat.org/de/quick-start/heat-pump/) |
| Elektrischer Heizkörper mit Schalter (`switch`) | [`over_switch`](over-switch.md) | [Schnellstart](quick-start.md#einfache-schalter-wie-aqara-t1-nous-b2z-sonoff-zbmini-sonoff-pow-) |
| Elektrischer Heizkörper mit Steuerleitung (Fil Pilote) | [`over_switch`](over-switch.md) mit [Befehlsanpassung](over-switch.md#befehlsanpassung) | [Steuerleitungs-Anleitung](https://www.versatile-thermostat.org/de/quick-start/pilot-wire/) |
| Pelletofen | [`over_switch`](over-switch.md) mit dem Plugin [VTherm Pellet stove](https://www.versatile-thermostat.org/de/plugins/#jmcollin78/vtherm_pellet_stove) | [Pelletofen-Anleitung](https://www.versatile-thermostat.org/de/quick-start/pellet-stove/) |

Einen ausführlicheren Vergleich der Typen finden Sie unter [Wahl eines VTherm](creation.md).

## Voraussetzungen

- Home Assistant und die über HACS installierte Integration Versatile Thermostat (siehe [Installation](installation.md)),
- das zu steuernde Gerät, in Home Assistant verfügbar,
- ein Temperatursensor für den Raum: Jeder in Home Assistant verfügbare Sensor kann verwendet werden, ebenso eine `input_number`,
- ein Außentemperatursensor: Die Wetterintegration von Home Assistant reicht aus.

## Geräte

Die mit _VTherm_ getesteten Thermostatventile sind im [Gerätekatalog](https://www.versatile-thermostat.org/de/devices/?type=trv) der Website aufgeführt, mit ihrem Unterstützungsgrad und Konfigurationshinweisen. Der Katalog enthält außerdem [Thermometer](https://www.versatile-thermostat.org/de/devices/?type=sensor), [Geräte mit `climate`-Entity](https://www.versatile-thermostat.org/de/devices/?type=climate) und [Geräte für elektrische Heizungen](https://www.versatile-thermostat.org/de/devices/?type=electric).

Dieser Katalog ist nicht vollständig: Ein Gerät, das nicht aufgeführt ist, ist nicht unbedingt inkompatibel. Die [inkompatiblen Geräte](https://www.versatile-thermostat.org/de/devices/?state=unsupported) und die [teilweise unterstützten Geräte](https://www.versatile-thermostat.org/de/devices/?state=partially) werden dort mit ihren bekannten Einschränkungen beschrieben.

## Inhalt der Dokumentation

### Erste Schritte

- [Installation](installation.md): die Integration mit HACS installieren.
- [Schnellstart](quick-start.md): ein funktionierendes _VTherm_ in wenigen Schritten, je nach Gerät.
- [Wahl eines VTherm](creation.md): zentrale Konfiguration oder nicht, Wahl des _VTherm_-Typs.
- [Auswahl der grundlegenden Attribute](base-attributes.md): Name, Temperatursensoren und zu aktivierende Funktionen.

### VTherm-Typen

- [`over_climate` Thermostattyp](over-climate.md): Thermostatventile, Wärmepumpen und Klimaanlagen mit `climate`-Entity.
- [`over_valve` Thermostattyp](over-valve.md): Ventile, die über eine `number`-Entity gesteuert werden.
- [`over_switch` Thermostattyp](over-switch.md): elektrische Heizkörper mit Schalter oder Steuerleitung.

### Funktionen

- **Komfort und Einsparungen**
  - [Voreinstellungen](feature-presets.md): voreingestellte Temperaturen (Komfort, Eco, Frostschutz...).
  - [Zeitgesteuerte Voreinstellung](feature-timed-preset.md): eine Voreinstellung für eine bestimmte Dauer anwenden.
  - [Anwesenheits-/Abwesenheitsverwaltung](feature-presence.md): den Sollwert absenken, wenn niemand zu Hause ist.
  - [Erkennung von Bewegung oder Aktivität](feature-motion.md): die Voreinstellung je nach Aktivität im Raum ändern.
  - [Erkennung offener Türen/Fenster](feature-window.md): reagieren, wenn eine Tür oder ein Fenster geöffnet wird.
  - [Externer Luftfeuchtigkeitssensor](feature-humidity.md): die von einem externen Sensor gemessene Luftfeuchtigkeit anzeigen.
- **Steuerung der Anlage**
  - [Steuerung der Zentralheizung](feature-central-boiler.md): den Heizkessel einschalten, wenn ein _VTherm_ heizen muss.
  - [Zentralisierte Steuerung](feature-central-mode.md): alle _VTherm_ auf einmal steuern.
  - [Energieverwaltung (Lastabwurf)](feature-power.md): die verfügbare Leistung nicht überschreiten.
  - [Auto-Start / Auto-Stopp](feature-auto-start-stop.md): ein `over_climate` anhalten, wenn es nicht gebraucht wird.
  - [Sperrfunktion](feature-lock.md): Änderungen über die Oberfläche oder Automatisierungen verhindern.
- **Sicherheit**
  - [Erweiterte Konfiguration und Sicherheitsmodus](feature-advanced.md): Sensor, der nicht mehr antwortet, falscher Gerätezustand.
  - [Erkennung von Heizungsstörungen](feature-heating-failure-detection.md): die Temperatur folgt dem Befehl nicht.

### Regelung

- [Selbstregulierung](self-regulation.md): den an ein `over_climate` gesendeten Sollwert anpassen oder das Ventil direkt steuern.
- [Ventilkalibrierung](feature-recalibrate-valves.md): der Dienst `recalibrate_valves`.
- [Synchronisierung der internen Gerätetemperatur](feature-sync_device_temp.md): das interne Thermometer des Geräts an die Raumtemperatur angleichen.
- [Die verschiedenen benutzten Algorithmen](algorithms.md): TPI, SmartPI und weitere Algorithmen als Plugins.
- [Auto TPI](feature-autotpi.md): automatisches Lernen der TPI-Koeffizienten.
  - [Auto TPI: Detaillierter technischer Leitfaden](feature-autotpi-technical.md)
- [Tuning-Beispiele](tuning-examples.md): kommentierte Einstellungen für verschiedene Installationsarten.

### Hilfe und Referenz

- [Störungsbeseitigung](troubleshooting.md): häufige Probleme und ihre Lösungen.
- [Frühere Protokolle herunterladen](feature-logs-collector.md): gezielte Protokolle sammeln und im [Log-Analyser](https://www.versatile-thermostat.org/de/debugger/) der Website öffnen.
- [Referenzdokumentation](reference.md): Parameter, Sensoren, Aktionen, Ereignisse und Attribute.
- [Anmerkungen zum Release](releases.md)

### Weiterführende Themen

- [Einige unverzichtbare Ergänzungen](additions.md): UI-Karte, Zeitplaner, Kurven, Benachrichtigungen.
- [Plugin-Katalog](https://www.versatile-thermostat.org/de/plugins/): Algorithmen, Karten und Gerätehilfen.
- [Gerätekatalog](https://www.versatile-thermostat.org/de/devices/): getestete Geräte und ihr Unterstützungsgrad.
- [Vergleiche](https://www.versatile-thermostat.org/de/versus/): _VTherm_ im Vergleich zum generischen Thermostat, zu Better Thermostat und anderen Lösungen.

## Nächster Schritt

[Installation](installation.md): Versatile Thermostat in Home Assistant installieren.

Für gängige Geräte fasst der [Schnellstart](quick-start.md) die gesamte Konfiguration auf einer Seite zusammen.
