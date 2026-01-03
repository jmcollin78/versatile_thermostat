# Zeitgesteuertes Preset

- [Zeitgesteuertes Preset](#zeitgesteuertes-preset)
  - [Zweck](#zweck)
  - [Funktionsweise](#funktionsweise)
  - [Zeitgesteuertes Preset aktivieren](#zeitgesteuertes-preset-aktivieren)
  - [Zeitgesteuertes Preset abbrechen](#zeitgesteuertes-preset-abbrechen)
  - [Benutzerdefinierte Attribute](#benutzerdefinierte-attribute)
  - [Ereignisse](#ereignisse)
  - [Automatisierungsbeispiele](#automatisierungsbeispiele)
    - [30-Minuten-Boost bei Ankunft zu Hause](#30-minuten-boost-bei-ankunft-zu-hause)
    - [Benachrichtigung am Ende des Boosts](#benachrichtigung-am-ende-des-boosts)
    - [Boost-Taste im Dashboard](#boost-taste-im-dashboard)

## Zweck

Die Funktion des zeitgesteuerten Presets ermöglicht es, ein Preset für einen _VTherm_ für eine bestimmte Dauer zu erzwingen. Nach Ablauf dieser Dauer wird das ursprüngliche Preset (das in `requested_state` definierte) automatisch wiederhergestellt.

Diese Funktion ist in mehreren Szenarien nützlich:
- **Heiz-Boost**: Temperatur vorübergehend erhöhen (z.B. Komfort-Preset) für 30 Minuten, wenn Sie nach Hause kommen
- **Gästemodus**: Ein wärmeres Preset für einige Stunden aktivieren, wenn Sie Gäste empfangen
- **Trocknung**: Ein hohes Preset für eine begrenzte Zeit erzwingen, um das Trocknen eines Raumes zu beschleunigen
- **Gelegentliche Einsparungen**: Vorübergehend ein Eco-Preset während einer kurzen Abwesenheit erzwingen

## Funktionsweise

1. Sie rufen den Dienst `versatile_thermostat.set_timed_preset` mit einem Preset und einer Dauer auf
2. Der _VTherm_ wechselt sofort zum angegebenen Preset
3. Ein Timer wird für die angegebene Dauer gestartet
4. Nach Ablauf des Timers stellt der _VTherm_ automatisch das ursprüngliche Preset wieder her
5. Bei jeder Änderung wird ein `versatile_thermostat_timed_preset_event`-Ereignis ausgelöst

> ![Tip](images/tips.png) _*Hinweise*_
> - Das zeitgesteuerte Preset hat eine mittlere Priorität: Es wird nach Sicherheits- und Leistungsprüfungen (Lastabwurf) angewendet, aber vor anderen Funktionen (Anwesenheit, Bewegung usw.)
> - Wenn Sie das Preset manuell ändern, während ein zeitgesteuertes Preset aktiv ist, wird der Timer abgebrochen
> - Die maximale Dauer beträgt 1440 Minuten (24 Stunden)

## Zeitgesteuertes Preset aktivieren

Um ein zeitgesteuertes Preset zu aktivieren, verwenden Sie den Dienst `versatile_thermostat.set_timed_preset`:

```yaml
service: versatile_thermostat.set_timed_preset
data:
  preset: "boost"
  duration_minutes: 30
target:
  entity_id: climate.mein_thermostat
```

Parameter:
- `preset`: Der Name des zu aktivierenden Presets. Muss ein gültiges, auf dem _VTherm_ konfiguriertes Preset sein (z.B. `eco`, `comfort`, `boost`, `frost` usw.)
- `duration_minutes`: Die Dauer in Minuten (zwischen 1 und 1440)

## Zeitgesteuertes Preset abbrechen

Um ein zeitgesteuertes Preset vor Ablauf seiner Dauer abzubrechen, verwenden Sie den Dienst `versatile_thermostat.cancel_timed_preset`:

```yaml
service: versatile_thermostat.cancel_timed_preset
target:
  entity_id: climate.mein_thermostat
```

Wenn Sie ein zeitgesteuertes Preset abbrechen, wird das ursprüngliche Preset sofort wiederhergestellt.

## Benutzerdefinierte Attribute

Wenn ein zeitgesteuertes Preset aktiv ist, sind die folgenden Attribute im Abschnitt `timed_preset_manager` der _VTherm_-Attribute verfügbar:

| Attribut                | Bedeutung                                                                        |
| ----------------------- | -------------------------------------------------------------------------------- |
| `timed_preset_active`   | `true` wenn ein zeitgesteuertes Preset aktiv ist, sonst `false`                  |
| `timed_preset_preset`   | Der Name des aktiven zeitgesteuerten Presets (oder `null` wenn keines)           |
| `timed_preset_end_time` | Enddatum/-zeit des zeitgesteuerten Presets (ISO-Format)                          |
| `remaining_time_min`    | Verbleibende Zeit in Minuten bis zum Ende des zeitgesteuerten Presets (Ganzzahl) |

Beispiel für Attribute:
```yaml
timed_preset_manager:
  timed_preset_active: true
  timed_preset_preset: "boost"
  timed_preset_end_time: "2024-01-15T14:30:00+00:00"
  remaining_time_min: 25
```

## Ereignisse

Das Ereignis `versatile_thermostat_timed_preset_event` wird bei Änderungen des zeitgesteuerten Presets ausgelöst.

Ereignisdaten:
- `entity_id`: Die _VTherm_-Kennung
- `name`: Der _VTherm_-Name
- `timed_preset_active`: `true` wenn ein zeitgesteuertes Preset gerade aktiviert wurde, `false` wenn es gerade deaktiviert wurde
- `timed_preset_preset`: Der Name des zeitgesteuerten Presets
- `old_preset`: Das vorherige Preset (vor der Aktivierung des zeitgesteuerten Presets)
- `new_preset`: Das neue aktive Preset

## Automatisierungsbeispiele

### 30-Minuten-Boost bei Ankunft zu Hause

```yaml
automation:
  - alias: "Heiz-Boost bei Ankunft"
    trigger:
      - platform: state
        entity_id: binary_sensor.anwesenheit_zuhause
        to: "on"
    condition:
      - condition: numeric_state
        entity_id: climate.wohnzimmer
        attribute: current_temperature
        below: 19
    action:
      - service: versatile_thermostat.set_timed_preset
        data:
          preset: "boost"
          duration_minutes: 30
        target:
          entity_id: climate.wohnzimmer
```

### Benachrichtigung am Ende des Boosts

```yaml
automation:
  - alias: "Boost-Ende-Benachrichtigung"
    trigger:
      - platform: event
        event_type: versatile_thermostat_timed_preset_event
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.timed_preset_active == false }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Thermostat"
          message: "Der Boost für {{ trigger.event.data.name }} ist beendet"
```

### Boost-Taste im Dashboard

Erstellen Sie eine Schaltfläche mit dem Kartentyp `button`:

```yaml
type: button
tap_action:
  action: call-service
  service: versatile_thermostat.set_timed_preset
  data:
    preset: boost
    duration_minutes: 30
  target:
    entity_id: climate.wohnzimmer
name: Boost 30 min
icon: mdi:fire
```
