# Sperrfunktion

## Übersicht

Die Sperrfunktion verhindert Änderungen an der Konfiguration eines Thermostats über die Benutzeroberfläche oder Automatisierungen, während der Thermostat weiterhin normal arbeitet.

## Verwendung

Verwenden Sie die folgenden Dienste, um den Sperrstatus zu steuern:

- `versatile_thermostat.lock` - Sperrt den Thermostat
- `versatile_thermostat.unlock` - Entsperrt den Thermostat

Beispiel für eine Automation:

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

## Sperrstatus

Der Sperrstatus ist:

- Sichtbar im Attribut `is_locked` der `climate`-Entität
- Über Home Assistant-Neustarts hinweg persistent
- Pro Thermostat getrennt (jeder Thermostat hat seine eigene Sperre)

## Wenn der Thermostat gesperrt ist

**Blockierte Aktionen:**

- Ändern des HVAC-Modus (Heizen / Kühlen / Aus)
- Ein- und Ausschalten
- Ändern der Solltemperatur
- Ändern der Presets
- Ändern von Lüfter- und Belüftungsmodus
- VTherm-spezifische Dienste (Präsenz, Preset-Temperaturen, Sicherheit, Fenster-Bypass)

**Weiterhin aktiv:**

- Temperaturregelung und Regelkreis
- Sicherheitsfunktionen (Überhitzungsschutz, Sicherheitsmodus)
- Automatische Funktionen (Fenstererkennung, Bewegungserkennung, Leistungsmanagement)
- Sensoraktualisierungen und Messwerte

## Anwendungsfälle

- Verhindern versehentlicher Änderungen in kritischen Zeiträumen
- Kindersicherung zum Schutz vor unbeabsichtigten Anpassungen