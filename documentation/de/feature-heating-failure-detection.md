# Erkennung von Heizungsstörungen

- [Erkennung von Heizungsstörungen](#erkennung-von-heizungsstörungen)
  - [Warum diese Funktion?](#warum-diese-funktion)
  - [Funktionsprinzip](#funktionsprinzip)
    - [Erkennung einer Heizungsstörung](#erkennung-einer-heizungsstörung)
    - [Erkennung einer Kühlungsstörung](#erkennung-einer-kühlungsstörung)
  - [Konfiguration](#konfiguration)
  - [Parameter](#parameter)
  - [Exponierte Attribute](#exponierte-attribute)
  - [Binärer Sensor](#binärer-sensor)
  - [Ereignisse](#ereignisse)
  - [Automatisierungsbeispiele](#automatisierungsbeispiele)
    - [Dauerhafte Benachrichtigung bei Heizungsstörung](#dauerhafte-benachrichtigung-bei-heizungsstörung)
    - [Dauerhafte Benachrichtigung für alle Arten von Störungen](#dauerhafte-benachrichtigung-für-alle-arten-von-störungen)
    - [Automatische Entfernung der Benachrichtigung, wenn die Störung behoben ist](#automatische-entfernung-der-benachrichtigung-wenn-die-störung-behoben-ist)

## Warum diese Funktion?

Die Erkennung von Heizungsstörungen ermöglicht die Überwachung der ordnungsgemäßen Funktion Ihres Heizsystems. Sie erkennt zwei abnormale Situationen:

1. **Heizungsstörung**: Der Thermostat fordert viel Leistung an (`on_percent` hoch), aber die Temperatur steigt nicht. Dies kann hinweisen auf:
   - einen defekten oder ausgeschalteten Heizkörper,
   - ein blockiertes Thermostatventil,
   - ein nicht erkanntes offenes Fenster,
   - ein Problem mit der Warmwasserzirkulation (Zentralheizung).

2. **Kühlungsstörung**: Der Thermostat fordert keine Leistung an (`on_percent` bei 0), aber die Temperatur steigt weiter. Dies kann hinweisen auf:
   - einen Heizkörper, der trotz Ausschaltbefehl eingeschaltet bleibt,
   - ein Relais, das in der "Ein"-Position blockiert ist,
   - ein zugrunde liegendes Gerät, das nicht mehr reagiert.

> ![Tipp](../../images/tips.png) _*Wichtig*_
>
> Diese Funktion **ändert nicht das Verhalten des Thermostats**. Sie sendet lediglich Ereignisse, um Sie auf eine abnormale Situation aufmerksam zu machen. Es liegt an Ihnen, die notwendigen Automatisierungen zu erstellen, um auf diese Ereignisse zu reagieren (Benachrichtigungen, Warnungen usw.).

## Funktionsprinzip

Diese Funktion gilt nur für _VTherm_, die den TPI-Algorithmus verwenden (over_switch, over_valve oder over_climate mit Ventilregelung). _VTherm_ `over_climate`, die beispielsweise eine Wärmepumpe steuern, sind daher nicht betroffen. In diesem Fall wird die Entscheidung, zu heizen oder nicht, vom zugrunde liegenden Gerät selbst getroffen, was den Zugriff auf zuverlässige Informationen verhindert.

Diese Funktion gilt nur für den Heizmodus (`hvac_mode=heat`). Im Klimatisierungsmodus (`hvac_mode=cool`) wird keine Erkennung durchgeführt, um Fehlalarme zu vermeiden.

### Erkennung einer Heizungsstörung

1. Der _VTherm_ ist im Heizmodus,
2. Der `on_percent` ist größer oder gleich dem konfigurierten Schwellenwert (standardmäßig 90%),
3. Diese Situation dauert länger als die Erkennungsverzögerung (standardmäßig 15 Minuten),
4. Die Temperatur ist in diesem Zeitraum nicht gestiegen.

➡️ Ein Ereignis `versatile_thermostat_heating_failure_event` wird mit `failure_type: heating` und `type: heating_failure_start` gesendet.

Wenn sich die Situation normalisiert (Temperatur steigt oder `on_percent` sinkt), wird ein Ereignis mit `type: heating_failure_end` gesendet.

### Erkennung einer Kühlungsstörung

1. Der _VTherm_ ist im Heizmodus,
2. Der `on_percent` ist kleiner oder gleich dem konfigurierten Schwellenwert (standardmäßig 0%),
3. Diese Situation dauert länger als die Erkennungsverzögerung (standardmäßig 15 Minuten),
4. Die Temperatur steigt weiter.

➡️ Ein Ereignis `versatile_thermostat_heating_failure_event` wird mit `failure_type: cooling` und `type: cooling_failure_start` gesendet.

Wenn sich die Situation normalisiert, wird ein Ereignis mit `type: cooling_failure_end` gesendet.

## Konfiguration

Wie viele Funktionen von _VTherm_ kann diese Funktion **in der zentralen Konfiguration** konfiguriert werden, um die Parameter gemeinsam zu nutzen. Um sie auf die ausgewählten _VTherm_ anzuwenden, muss der Benutzer die Funktion hinzufügen (siehe Menü "Funktionen") und wählen, ob die gemeinsamen Parameter der zentralen Konfiguration verwendet oder neue angegeben werden sollen, die nur für diesen _VTherm_ gelten.

Zugriff:
1. Gehen Sie zur Konfiguration Ihres _VTherm_ vom Typ "Zentrale Konfiguration"
2. Wählen Sie im Menü "Heating failure detection" (Erkennung von Heizungsstörungen)
3. Gehen Sie dann zur Konfiguration der betroffenen _VTherm_,
4. Wählen Sie das Menü "Funktionen",
5. Aktivieren Sie die Funktion "Erkennung von Heizungsstörungen",
6. Wählen Sie, ob die Parameter der zentralen Konfiguration verwendet oder neue angegeben werden sollen.

![Konfiguration](../../images/config-heating-failure-detection.png)

## Parameter

| Parameter                                      | Beschreibung                                                                                                        | Standardwert |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------ |
| **Erkennung von Heizungsstörungen aktivieren** | Aktiviert oder deaktiviert die Funktion                                                                             | Deaktiviert  |
| **Schwellenwert für Heizungsstörung**          | Prozentsatz von `on_percent`, über dem die Heizung die Temperatur erhöhen sollte. Wert zwischen 0 und 1 (0.9 = 90%) | 0.9 (90%)    |
| **Schwellenwert für Kühlungsstörung**          | Prozentsatz von `on_percent`, unter dem die Temperatur nicht steigen sollte. Wert zwischen 0 und 1 (0 = 0%)         | 0.0 (0%)     |
| **Erkennungsverzögerung (Minuten)**            | Wartezeit vor der Meldung einer Störung. Vermeidet Fehlalarme durch normale Schwankungen                            | 15 Minuten   |
| **Toleranz für Temperaturänderung (°C)**       | Minimale Temperaturänderung in Grad, um als signifikant zu gelten. Ermöglicht das Filtern von Sensorrauschen        | 0.5°C        |

> ![Tipp](../../images/tips.png) _*Einstellungstipps*_
>
> - **Heizungsschwellenwert**: Wenn Sie Fehlalarme haben (Störungserkennung, obwohl alles funktioniert), erhöhen Sie diesen Schwellenwert auf 0.95 oder 1.0.
> - **Kühlungsschwellenwert**: Wenn Sie einen Heizkörper erkennen möchten, der auch bei niedrigem `on_percent` eingeschaltet bleibt, erhöhen Sie diesen Schwellenwert auf 0.05 oder 0.1.
> - **Erkennungsverzögerung**: Erhöhen Sie diese Verzögerung, wenn Sie Räume mit hoher thermischer Trägheit haben (große Räume, Fußbodenheizung usw.). Sie können sich die Heizkurven ansehen (siehe [Ergänzungen](../../additions.md#courbes-de-régulattion-avec-plotly)) und sehen, wie lange Ihr Thermometer nach dem Einschalten der Heizung steigt. Diese Dauer sollte das Minimum für diesen Parameter sein.
> - **Toleranz**: Wenn Sie ungenaue oder verrauschte Sensoren haben, erhöhen Sie diesen Wert (z. B. 0.8°C). Viele Sensoren haben eine Genauigkeit von ±0.5°C.

## Exponierte Attribute

Die _VTherm_ mit TPI stellen folgende Attribute bereit:

```yaml
is_heating_failure_detection_configured: true
heating_failure_detection_manager:
  heating_failure_state: "off"      # "on", "off", "unknown", "unavailable"
  cooling_failure_state: "off"      # "on", "off", "unknown", "unavailable"
  heating_failure_threshold: 0.9
  cooling_failure_threshold: 0.0
  detection_delay_min: 15
  temperature_change_tolerance: 0.5
  heating_tracking:                 # Verfolgung der Heizungsstörungserkennung
    is_tracking: true               # Erkennung läuft?
    initial_temperature: 19.5       # Temperatur zu Beginn der Verfolgung
    current_temperature: 19.7       # Aktuelle Temperatur
    remaining_time_min: 8.5         # Verbleibende Minuten bis zum Alarm
    elapsed_time_min: 6.5           # Verstrichene Minuten seit Beginn
  cooling_tracking:                 # Verfolgung der Kühlungsstörungserkennung
    is_tracking: false
    initial_temperature: null
    current_temperature: null
    remaining_time_min: null
    elapsed_time_min: null
```

## Binärer Sensor

Wenn die Erkennung von Heizungsstörungen aktiviert ist, wird automatisch ein binärer Sensor für jeden betroffenen _VTherm_ erstellt:

| Entität                                      | Beschreibung                                                   |
| -------------------------------------------- | -------------------------------------------------------------- |
| `binary_sensor.<name>_heating_failure_state` | Zeigt an, ob eine Heizungs- oder Kühlungsstörung erkannt wurde |

Der Anzeigename des Sensors wird entsprechend der Sprache Ihres Home Assistant übersetzt "Status der Heizungsstörung".

Dieser Sensor ist:
- **ON**, wenn eine Störung (Heizung oder Kühlung) erkannt wird
- **OFF**, wenn das System normal funktioniert

Eigenschaften:
- **Device class**: `problem` (ermöglicht native Home Assistant-Warnungen)
- **Symbole**:
  - `mdi:radiator-off`, wenn eine Störung erkannt wird
  - `mdi:radiator`, wenn alles funktioniert

Dieser binäre Sensor kann direkt in Ihren Automatisierungen als Auslöser oder zum Erstellen von Warnungen über native Home Assistant-Benachrichtigungen verwendet werden.

## Ereignisse

Das Ereignis `versatile_thermostat_heating_failure_event` wird bei Erkennung oder Beendigung einer Störung gesendet.

Ereignisdaten:
| Feld                     | Beschreibung                                                                                                |
| ------------------------ | ----------------------------------------------------------------------------------------------------------- |
| `entity_id`              | Die Kennung des _VTherm_                                                                                    |
| `name`                   | Der Name des _VTherm_                                                                                       |
| `type`                   | Ereignistyp: `heating_failure_start`, `heating_failure_end`, `cooling_failure_start`, `cooling_failure_end` |
| `failure_type`           | Störungstyp: `heating` oder `cooling`                                                                       |
| `on_percent`             | Der zum Zeitpunkt der Erkennung angeforderte Leistungsprozentsatz                                           |
| `temperature_difference` | Die während des Erkennungszeitraums beobachtete Temperaturdifferenz                                         |
| `current_temp`           | Die aktuelle Temperatur                                                                                     |
| `target_temp`            | Die Zieltemperatur                                                                                          |
| `threshold`              | Der konfigurierte Schwellenwert, der die Erkennung ausgelöst hat                                            |
| `detection_delay_min`    | Die konfigurierte Erkennungsverzögerung                                                                     |
| `state_attributes`       | Alle Attribute der Entität zum Zeitpunkt des Ereignisses                                                    |

## Automatisierungsbeispiele

### Dauerhafte Benachrichtigung bei Heizungsstörung

Diese Automatisierung erstellt eine dauerhafte Benachrichtigung, wenn eine Heizungsstörung erkannt wird:

```yaml
alias: "Warnung Heizungsstörung"
description: "Erstellt eine dauerhafte Benachrichtigung bei Heizungsstörung"
trigger:
    - platform: event
      event_type: versatile_thermostat_heating_failure_event
condition:
    - condition: template
      value_template: "{{ trigger.event.data.type == 'heating_failure_start' }}"
action:
    - service: persistent_notification.create
      data:
        title: "🔥 Heizungsstörung erkannt"
        message: >
        Der Thermostat **{{ trigger.event.data.name }}** hat eine Heizungsstörung erkannt.

        📊 **Details:**
        - Angeforderte Leistung: {{ (trigger.event.data.on_percent * 100) | round(0) }}%
        - Aktuelle Temperatur: {{ trigger.event.data.current_temp }}°C
        - Zieltemperatur: {{ trigger.event.data.target_temp }}°C
        - Temperaturänderung: {{ trigger.event.data.temperature_difference | round(2) }}°C

        ⚠️ Die Heizung läuft auf Hochtouren, aber die Temperatur steigt nicht.
        Überprüfen Sie, ob der Heizkörper ordnungsgemäß funktioniert.
        notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
```

### Dauerhafte Benachrichtigung für alle Arten von Störungen

Diese Automatisierung behandelt beide Arten von Störungen (Heizung und Kühlung):

```yaml
alias: "Warnung Heizungsanomalie"
description: "Benachrichtigung für alle Arten von Heizungsstörungen"
trigger:
    - platform: event
      event_type: versatile_thermostat_heating_failure_event
condition:
    - condition: template
      value_template: "{{ trigger.event.data.type in ['heating_failure_start', 'cooling_failure_start'] }}"
action:
    - service: persistent_notification.create
      data:
        title: >
        {% if trigger.event.data.failure_type == 'heating' %}
            🔥 Heizungsstörung erkannt
        {% else %}
            ❄️ Kühlungsstörung erkannt
        {% endif %}
      message: >
        Der Thermostat **{{ trigger.event.data.name }}** hat eine Anomalie erkannt.

        📊 **Details:**
        - Störungstyp: {{ trigger.event.data.failure_type }}
        - Angeforderte Leistung: {{ (trigger.event.data.on_percent * 100) | round(0) }}%
        - Aktuelle Temperatur: {{ trigger.event.data.current_temp }}°C
        - Zieltemperatur: {{ trigger.event.data.target_temp }}°C
        - Temperaturänderung: {{ trigger.event.data.temperature_difference | round(2) }}°C

        {% if trigger.event.data.failure_type == 'heating' %}
        ⚠️ Die Heizung läuft auf {{ (trigger.event.data.on_percent * 100) | round(0) }}%, aber die Temperatur steigt nicht.
        Überprüfen Sie, ob der Heizkörper ordnungsgemäß funktioniert.
        {% else %}
        ⚠️ Die Heizung ist aus, aber die Temperatur steigt weiter.
        Überprüfen Sie, ob der Heizkörper ordnungsgemäß ausschaltet.
        {% endif %}
      notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
```

### Automatische Entfernung der Benachrichtigung, wenn die Störung behoben ist

Diese Automatisierung entfernt die dauerhafte Benachrichtigung, wenn die Störung behoben ist:

```yaml
alias: "Ende der Warnung Heizungsanomalie"
description: "Entfernt die Benachrichtigung, wenn die Störung behoben ist"
trigger:
    - platform: event
      event_type: versatile_thermostat_heating_failure_event
condition:
    - condition: template
      value_template: "{{ trigger.event.data.type in ['heating_failure_end', 'cooling_failure_end'] }}"
action:
    - service: persistent_notification.dismiss
      data:
        notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
    - service: persistent_notification.create
      data:
        title: "✅ Anomalie behoben"
        message: >
        Der Thermostat **{{ trigger.event.data.name }}** funktioniert wieder normal.
        notification_id: "heating_failure_resolved_{{ trigger.event.data.entity_id }}"
    # Entfernt die Lösungsbenachrichtigung automatisch nach 1 Stunde
    - delay:
        hours: 1
    - service: persistent_notification.dismiss
      data:
        notification_id: "heating_failure_resolved_{{ trigger.event.data.entity_id }}"
```

> ![Tipp](../../images/tips.png) _*Hinweise*_
>
> 1. Dauerhafte Benachrichtigungen bleiben angezeigt, bis der Benutzer sie schließt oder sie durch eine Automatisierung entfernt werden.
> 2. Die Verwendung von `notification_id` ermöglicht das Aktualisieren oder Entfernen einer bestimmten Benachrichtigung.
> 3. Sie können diese Automatisierungen anpassen, um Benachrichtigungen an Mobilgeräte, Telegram oder einen anderen Benachrichtigungsdienst zu senden.
> 4. Diese Funktion funktioniert nur mit _VTherm_, die den TPI-Algorithmus verwenden (over_switch, over_valve oder over_climate mit Ventilregelung).
