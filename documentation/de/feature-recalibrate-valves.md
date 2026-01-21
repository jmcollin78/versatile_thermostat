````markdown
# Ventilkalibrierung (Dienst recalibrate_valves)

- [Ventilkalibrierung (Dienst recalibrate_valves)](#ventilkalibrierung-dienst-recalibrate_valves)
  - [Warum dieses Feature?](#warum-dieses-feature)
  - [Wie es funktioniert](#wie-es-funktioniert)
  - [Einschränkungen und Voraussetzungen](#einschr%C3%A4nkungen-und-voraussetzungen)
  - [Konfiguration / Zugriff auf den Dienst](#konfiguration--zugriff-auf-den-dienst)
  - [Dienstparameter](#dienstparameter)
  - [Detailliertes Verhalten](#detailliertes-verhalten)
  - [Automatisierungsbeispiele](#automatisierungsbeispiele)

## Warum dieses Feature?

Der Dienst `recalibrate_valves` führt ein einfaches Kalibrierungsverfahren für thermostatische Heizkörperventile (TRVs) aus, die von einem VTherm im Ventilregelungsmodus gesteuert werden. Er zwingt die darunterliegenden Ventilantriebe vorübergehend in extreme Positionen (voll geöffnet, dann voll geschlossen), um die Ventilwerte des Thermostats zu kalibrieren.

Dieser Dienst ist nützlich, wenn Sie falsche Öffnungs-/Schließwerte vermuten, Ventile nach der Installation/ Wartung neu kalibrieren wollen oder wenn ein Ventil den Heizkörper heizt, obwohl es geschlossen gemeldet wird.

⚠️ Die tatsächliche Kalibrierung hängt vom darunterliegenden Ventilgerät ab. VTherm sendet nur Öffnungs-/Schließbefehle. Reagiert das Gerät nicht korrekt, wenden Sie sich an den Hersteller des TRV oder nutzen Sie das Kalibrierungsverfahren des Herstellers.

⚠️ Kalibrierungen können die Batterielaufzeit bei batteriebetriebenen TRVs verringern. Verwenden Sie sie nur bei Bedarf.

## Wie es funktioniert

Der Dienst führt die folgenden Schritte für die Ziel-Entität aus:

1. Überprüfen, ob die Zielentität ein `ThermostatClimateValve` ist (Ventilregelung). Andernfalls gibt der Dienst einen Fehler zurück.
2. Überprüfen, ob jedes darunterliegende Ventil zwei `number`-Entitäten für Öffnen und Schließen konfiguriert hat. Fehlt eine Entität, wird die Operation abgelehnt.
3. Den `requested_state` des Thermostats speichern.
4. VTherm auf OFF setzen.
5. `delay_seconds` warten.
6. Für jedes Ventil: Öffnen auf 100% erzwingen (den gemappten Wert an die `number`-Entität senden). `delay_seconds` warten.
7. Für jedes Ventil: Schließen auf 100% erzwingen (den gemappten Wert an die `number`-Entität senden). `delay_seconds` warten.
8. Den ursprünglichen `requested_state` wiederherstellen und Zustände/Attribute aktualisieren.

Während des Verfahrens sendet VTherm direkte Werte an die `number`-Entitäten, wobei normale Algorithmus-Schwellen und Schutzmechanismen umgangen werden. Der Dienst läuft im Hintergrund und gibt sofort `{"message": "calibrage en cours"}` zurück.

Die Verzögerung zwischen den Schritten wird vom Aufrufer festgelegt. Der Dienst akzeptiert Werte zwischen `0` und `300` Sekunden (0–5 Minuten). In der Praxis sind 10–60 Sekunden je nach Ventilgeschwindigkeit angemessen; 10 s ist ein guter Ausgangspunkt.

## Einschränkungen und Voraussetzungen

- Der Dienst ist nur für `ThermostatClimateValve`-Thermostate (Ventilregelung) verfügbar.
- Jedes darunterliegende Ventil muss zwei `number`-Entitäten konfiguriert haben:
  - `opening_degree_entity_id` (Öffnen-Befehl)
  - `closing_degree_entity_id` (Schließen-Befehl)
- `number`-Entitäten können `min` und `max` Attribute definieren; der Dienst mappt 0–100% linear auf diesen Bereich. Fehlen `min`/`max`, wird der Bereich 0–100 angenommen.
- Der Dienst verhindert gleichzeitige Ausführungen für dieselbe Entität: Läuft bereits eine Kalibrierung, wird eine neue Anfrage sofort abgelehnt.

## Konfiguration / Zugriff auf den Dienst

Der Dienst ist als Entity-Service registriert. Rufen Sie ihn auf, indem Sie die passende `climate`-Entität in Home Assistant angeben.

Dienstname: `versatile_thermostat.recalibrate_valves`

Beispiel über Developer Tools / Services:

```yaml
service: versatile_thermostat.recalibrate_valves
target:
  entity_id: climate.my_thermostat
data:
  delay_seconds: 30
```

Der Dienst gibt sofort zurück:

```json
{"message": "calibrage en cours"}
```

## Dienstparameter

| Parameter       | Typ     | Beschreibung                                                                                                                |
| --------------- | ------- | --------------------------------------------------------------------------------------------------------------------------- |
| `delay_seconds` | integer | Verzögerung (Sekunden) nach vollständigem Öffnen und nach vollständigem Schließen. Gültiger Bereich: 0–300 (empfohlen: 10). |

Das Service-Schema begrenzt den Wert auf `0`–`300` Sekunden.

## Detailliertes Verhalten

- Die Operation läuft als Hintergrundtask. Der Aufrufer erhält eine sofortige Bestätigung und kann den Fortschritt in den Home Assistant-Logs verfolgen.
- Am Ende der Operation wird der `requested_state` wiederhergestellt (HVAC-Modus, Zieltemperatur und Preset falls vorhanden) und die Zustände werden aktualisiert. VTherm sollte in seinen ursprünglichen Zustand zurückkehren, sofern die Sensorwerte stabil bleiben.

## Automatisierungsbeispiele

1) Kalibrierung einmal pro Monat (Beispiel):

Die YAML-Auslösung unten startet die Kalibrierung am 1. Tag jedes Monats um 03:00 Uhr:

```yaml
alias: Monatliche Ventilkalibrierung
trigger:
  - platform: time
    at: '03:00:00'
condition:
  - condition: template
    value_template: "{{ now().day == 1 }}"
  - condition: state
    entity_id: climate.my_thermostat
    state: 'off'
action:
  - service: versatile_thermostat.recalibrate_valves
    target:
      entity_id: climate.my_thermostat
    data:
      delay_seconds: 60
  - service: persistent_notification.create
    data:
      title: "🔧 Monatliche Kalibrierung gestartet"
      message: "🔧 Eine Ventilkalibrierung wurde für climate.my_thermostat gestartet"
```

> ![Tip](images/tips.png) _*Hinweis*_
>
> - Testen Sie die Kalibrierung zunächst an einem einzelnen VTherm und prüfen Sie Protokolle und `number` Werte, bevor Sie sie auf mehrere Geräte anwenden.
> - Stellen Sie `delay_seconds` so ein, dass das physische Ventil die Position erreichen kann (60 s ist ein guter Anfang für die meisten Ventile).

````
