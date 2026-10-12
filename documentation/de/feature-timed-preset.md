# Zeitgesteuerte Voreinstellung

- [Zeitgesteuerte Voreinstellung](#zeitgesteuerte-voreinstellung)
  - [Zweck](#zweck)
  - [Funktionsweise](#funktionsweise)
  - [Zeitgesteuerte Voreinstellung aktivieren](#zeitgesteuerte-voreinstellung-aktivieren)
  - [Zeitgesteuerte Voreinstellung abbrechen](#zeitgesteuerte-voreinstellung-abbrechen)
  - [Benutzerdefinierte Attribute](#benutzerdefinierte-attribute)
  - [Ereignisse](#ereignisse)
  - [Manuelle Übersteuerung mit automatischer Rückkehr](#manuelle-übersteuerung-mit-automatischer-rückkehr)
  - [Automatisierungsbeispiele](#automatisierungsbeispiele)
    - [30-Minuten-Boost bei Ankunft zu Hause](#30-minuten-boost-bei-ankunft-zu-hause)
    - [Benachrichtigung am Ende des Boosts](#benachrichtigung-am-ende-des-boosts)
    - [Boost-Taste im Dashboard](#boost-taste-im-dashboard)

## Zweck

Die Funktion der zeitgesteuerten Voreinstellung ermöglicht es, eine Vorgabe für einen _VTherm_ für eine bestimmte Dauer zu erzwingen. Nach Ablauf dieser Dauer wird die ursprüngliche Vorgabe (das in `requested_state` definierte) automatisch wiederhergestellt.

Diese Funktion ist in mehreren Szenarien nützlich:
- **Heiz-Boost**: Temperatur vorübergehend erhöhen (z.B. Komfort-Vorgabe) für 30 Minuten, wenn Sie nach Hause kommen
- **Gästemodus**: Eine wärmere Vorgabe für einige Stunden aktivieren, wenn Sie Gäste empfangen
- **Trocknung**: Eine hohe Vorgabe für eine begrenzte Zeit erzwingen, um das Trocknen eines Raumes zu beschleunigen
- **Gelegentliche Einsparungen**: Vorübergehend ein Eco-Vorgabe während einer kurzen Abwesenheit erzwingen

## Funktionsweise

1. Sie rufen den Dienst `versatile_thermostat.set_timed_preset` mit einem Vorgabewert und einer Dauer auf
2. Der _VTherm_ wechselt sofort zum angegebenen Vorgabewert
3. Ein Timer wird für die angegebene Dauer gestartet
4. Nach Ablauf des Timers stellt der _VTherm_ automatisch den ursprünglichen Vorgabewert wieder her
5. Bei jeder Änderung wird ein `versatile_thermostat_timed_preset_event`-Ereignis ausgelöst

> ![Tip](images/tips.png) _*Hinweise*_
> - Die zeitgesteuerte Voreinstellung hat eine mittlere Priorität: Es wird nach Sicherheits- und Leistungsprüfungen (Lastabwurf) angewandt, aber noch vor anderen Funktionen (Anwesenheit, Bewegung usw.)
> - Wenn Sie den Vorgabewert manuell ändern, während eine zeitgesteuerte Voreinstellung aktiv ist, wird der Timer abgebrochen
> - Die maximale Dauer beträgt 1440 Minuten (24 Stunden)

## Zeitgesteuerte Voreinstellung aktivieren

Um eine zeitgesteuerte Vorgabe zu aktivieren, verwenden Sie den Dienst `versatile_thermostat.set_timed_preset`:

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

## Zeitgesteuerte Voreinstellung abbrechen

Um eine zeitgesteuerte Vorgabe vor Ablauf seiner Dauer abzubrechen, verwenden Sie den Dienst `versatile_thermostat.cancel_timed_preset`:

```yaml
service: versatile_thermostat.cancel_timed_preset
target:
  entity_id: climate.mein_thermostat
```

Sobald eine zeitgesteuerte Vorgabe abgebrochen wird, wird die ursprüngliche Vorgabe sofort wiederhergestellt.

## Benutzerdefinierte Attribute

Wenn eine zeitgesteuerte Preset aktiv ist, sind die folgenden Attribute im Abschnitt `timed_preset_manager` der _VTherm_-Attribute verfügbar:

| Attribut             | Bedeutung                                                                                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `is_active`          | `true` wenn ein zeitgesteuertes Preset aktiv ist, sonst `false`                                                                                   |
| `preset`             | Der Name des aktiven zeitgesteuerten Presets (oder `null` wenn keines)                                                                            |
| `original_preset`    | Das Preset, das am Ende des zeitgesteuerten Presets wiederhergestellt wird (oder `null` wenn keines)                                              |
| `end_time`           | Enddatum/-zeit des zeitgesteuerten Presets (ISO-Format, oder `null` wenn keines)                                                                  |
| `remaining_time_min` | Verbleibende Zeit in Minuten bis zum Ende des zeitgesteuerten Presets (Ganzzahl)                                                                  |
| `is_manual_override` | `true`, wenn das aktive zeitgesteuerte Preset eine manuelle Übersteuerung ist (siehe [unten](#manuelle-übersteuerung-mit-automatischer-rückkehr)) |
| `resume_preset`      | Das durch die manuelle Übersteuerung unterbrochene zeitgesteuerte Preset, das an ihrem Ende fortgesetzt wird (oder `null`)                        |
| `resume_end_time`    | Enddatum/-zeit des unterbrochenen zeitgesteuerten Presets (ISO-Format, oder `null`)                                                               |

Beispiel für Attribute:
```yaml
timed_preset_manager:
  is_active: true
  preset: "boost"
  original_preset: "comfort"
  end_time: "2024-01-15T14:30:00+00:00"
  remaining_time_min: 25
  is_manual_override: false
  resume_preset: null
  resume_end_time: null
```

## Ereignisse

Das Ereignis `versatile_thermostat_timed_preset_event` wird bei Änderungen des zeitgesteuerten Presets ausgelöst.

Ereignisdaten:
- `entity_id`: Die _VTherm_-Kennung
- `name`: Der _VTherm_-Name
- `state_attributes`: Die Zustandsattribute des _VTherm_ zum Zeitpunkt des Ereignisses
- `type`: `start`, wenn ein zeitgesteuertes Preset (oder eine manuelle Übersteuerung) startet, `end`, wenn es endet
- `preset`: Das betroffene zeitgesteuerte Preset (das startende oder das soeben beendete)

Zusätzliche Daten eines `start`-Ereignisses:
- `duration_minutes`: Die Dauer des zeitgesteuerten Presets in Minuten
- `end_time`: Enddatum/-zeit des zeitgesteuerten Presets (ISO-Format)
- `original_preset`: Das Preset, das am Ende wiederhergestellt wird
- `manual_override`: `true`, wenn das Ereignis eine manuelle Übersteuerung betrifft

Zusätzliche Daten eines `end`-Ereignisses:
- `cause`: Grund für das Ende des zeitgesteuerten Presets: `expired` (die Dauer ist abgelaufen), `cancelled` (der Dienst `cancel_timed_preset` wurde aufgerufen) oder `preset_selected` (ein Preset wurde manuell ausgewählt)
- `restored_preset`: Das nach dem Ende wiederhergestellte Preset (kann `null` sein, wenn ein Preset manuell ausgewählt wurde)
- `manual_override`: `true`, wenn das Ereignis eine manuelle Übersteuerung betrifft

## Manuelle Übersteuerung mit automatischer Rückkehr

Wenn Sie die Zieltemperatur manuell ändern, wechselt _VTherm_ normalerweise zur Voreinstellung `none` und bleibt dort, bis Sie wieder eine Voreinstellung auswählen. Ist eine **Dauer der manuellen Übersteuerung** konfiguriert, kehrt _VTherm_ nach dieser Dauer automatisch zurück.

Die Dauer wird in der erweiterten Konfiguration festgelegt (`manual_override_duration_min`, in Minuten). Sie kann in der zentralen Konfiguration definiert und pro _VTherm_ überschrieben werden. Siehe [erweiterte Konfiguration](feature-advanced.md#dauer-der-manuellen-übersteuerung). Der Standardwert `0` deaktiviert die Funktion, das Verhalten bleibt dann unverändert.

Funktionsweise:
1. Eine manuelle Änderung der Zieltemperatur (über die Oberfläche, über eine Automatisierung mit `climate.set_temperature` oder über das zugrunde liegende Gerät, wenn `Follow underlying temperature change` aktiviert ist) startet eine manuelle Übersteuerung. Die manuelle Temperatur gilt sofort.
2. Eine weitere manuelle Änderung während der Übersteuerung startet den Timer mit der vollen Dauer neu.
3. Wenn der Timer abläuft, wird die Voreinstellung wiederhergestellt, die vor der manuellen Änderung aktiv war.
4. War beim manuellen Ändern eine zeitgesteuerte Voreinstellung aktiv, wird sie am Ende der Übersteuerung bis zu ihrer eigenen Endzeit fortgesetzt. Ist diese Endzeit bereits verstrichen, wird die Voreinstellung wiederhergestellt, die vor der zeitgesteuerten Voreinstellung aktiv war.
5. War vor der manuellen Änderung keine Voreinstellung aktiv (`none`), wird keine Übersteuerung gestartet.

Die manuelle Übersteuerung nutzt den Mechanismus der zeitgesteuerten Voreinstellungen: Sie erscheint als zeitgesteuerte Voreinstellung `none` und übersteht einen Neustart von Home Assistant.

> ![Tipp](images/tips.png) _*Hinweise*_
> - Die Auswahl einer Voreinstellung während der manuellen Übersteuerung bricht sie ab: Die gewählte Voreinstellung gilt, und später wird nichts zurückgesetzt.
> - Das Setzen einer zeitgesteuerten Voreinstellung während der manuellen Übersteuerung ersetzt diese.
> - Das Abbrechen der zeitgesteuerten Voreinstellung während der manuellen Übersteuerung stellt die Voreinstellung wieder her, die vor der manuellen Änderung aktiv war.
> - Fenster, Sicherheit, Lastabwurf und zentraler Modus behalten während der manuellen Übersteuerung ihre Priorität.

Die Attribute `is_manual_override`, `resume_preset` und `resume_end_time` von `timed_preset_manager` sind in der Tabelle unter [Benutzerdefinierte Attribute](#benutzerdefinierte-attribute) beschrieben. Das Feld `manual_override` des Ereignisses `versatile_thermostat_timed_preset_event` steht auf `true`, wenn das Ereignis eine manuelle Übersteuerung betrifft.

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
        value_template: "{{ trigger.event.data.type == 'end' }}"
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
