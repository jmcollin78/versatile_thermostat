
# Störungsbeseitigung

- [Störungsbeseitigung](#störungsbeseitigung)
  - [Verwendung eines Heatzy](#verwendung-eines-heatzy)
  - [Verwendung eines Heizkörpers mit Steuerleitung (Nodon SIN-4-FP-21)](#verwendung-eines-heizkörpers-mit-steuerleitung-nodon-sin-4-fp-21)
  - [Verwendung eines Netatmo-Systems](#verwendung-eines-netatmo-systems)
  - [Nur der erste Heizkörper heizt](#nur-der-erste-heizkörper-heizt)
  - [Der Heizkörper heizt, obwohl die Solltemperatur überschritten wird, oder er heizt nicht, wenn die Raumtemperatur deutlich unter dem Sollwert liegt](#der-heizkörper-heizt-obwohl-die-solltemperatur-überschritten-wird-oder-er-heizt-nicht-wenn-die-raumtemperatur-deutlich-unter-dem-sollwert-liegt)
    - [Typ `over_switch` oder `over_valve`](#typ-over_switch-oder-over_valve)
    - [Typ `over_climate`](#typ-over_climate)
  - [Einstellen der Parameter für die Erkennung von offenen Fenstern im Automodus](#einstellen-der-parameter-für-die-erkennung-von-offenen-fenstern-im-automodus)
  - [Warum geht mein Versatile Thermostat in den Sicherheitsmodus?](#warum-geht-mein-versatile-thermostat-in-den-sicherheitsmodus)
    - [Wie wird der Sicherheitsmodus erkannt?](#wie-wird-der-sicherheitsmodus-erkannt)
    - [Wie kann ich benachrichtigt werden, wenn dies geschieht?](#wie-kann-ich-benachrichtigt-werden-wenn-dies-geschieht)
    - [Wie kann man das beheben?](#wie-kann-man-das-beheben)
  - [Eine Personengruppe als Anwesenheitssensor verwenden](#eine-personengruppe-als-anwesenheitssensor-verwenden)
  - [Aktivieren von Protokollen für das Versatile Thermostat](#aktivieren-von-protokollen-für-das-versatile-thermostat)
  - [VTherm verfolgt keine Sollwertänderungen, die direkt am zugehörigen Gerät vorgenommen werden (`over_climate`)](#vtherm-verfolgt-keine-sollwertänderungen-die-direkt-am-zugehörigen-gerät-vorgenommen-werden-over_climate)
  - [VTherm schaltet automatisch in den Modus 'Kühlen' oder 'Heizen' um](#vtherm-schaltet-automatisch-in-den-modus-kühlen-oder-heizen-um)
  - [Erkennung von offenen Fenstern verhindert keine Änderungen der Voreinstellungen](#erkennung-von-offenen-fenstern-verhindert-keine-änderungen-der-voreinstellungen)
    - [Beispiel:](#beispiel)


## Verwendung eines Heatzy

Der Heatzy wird jetzt nativ von _VTherm_ unterstützt. Siehe [Schnellstart](quick-start.md#heatzy-ecosy-oder-ähnlich-climate-entity).

Diese Konfiguration wird nur als Referenz aufbewahrt.

Die Verwendung eines Heatzy oder Nodon ist möglich, sofern Sie einen virtuellen Schalter mit diesem Modell verwenden:

```yaml
- platform: template
  switches:
    chauffage_sdb:
      unique_id: chauffage_sdb
      friendly_name: Bathroom heating
      value_template: "{{ is_state_attr('climate.bathroom', 'preset_mode', 'comfort') }}"
      icon_template: >-
        {% if is_state_attr('climate.bathroom', 'preset_mode', 'comfort') %}
          mdi:radiator
        {% elif is_state_attr('climate.bathroom', 'preset_mode', 'away') %}
          mdi:snowflake
        {% else %}
          mdi:radiator-disabled
        {% endif %}
      turn_on:
        service: climate.set_preset_mode
        entity_id: climate.bathroom
        data:
          preset_mode: "comfort"
      turn_off:
        service: climate.set_preset_mode
        entity_id: climate.bathroom
        data:
          preset_mode: "eco"
```
Vielen Dank an @gael für dieses Beispiel.

## Verwendung eines Heizkörpers mit Steuerleitung (Nodon SIN-4-FP-21)

Der Nodon wird jetzt nativ von _VTherm_ unterstützt. Siehe [Schnellstart](quick-start.md#nodon-sin-4-fp-21-oder-ähnlich-pilotdraht).

Diese Konfiguration wird nur als Referenz aufbewahrt.


Wie beim Heatzy oben können Sie einen virtuellen Schalter verwenden, der die Voreinstellung Ihres Heizkörpers auf der Grundlage des Ein/Aus-Zustands des VTherm ändert.
Beispiel:

```yaml
- platform: template
  switches:
    chauffage_chb_parents:
      unique_id: chauffage_chb_parents
      friendly_name: Chauffage chambre parents
      value_template: "{{ is_state('select.fp_chb_parents_pilot_wire_mode', 'comfort') }}"
      icon_template: >-
        {% if is_state('select.fp_chb_parents_pilot_wire_mode', 'comfort') %}
          mdi:radiator
        {% elif is_state('select.fp_chb_parents_pilot_wire_mode', 'frost_protection') %}
          mdi:snowflake
        {% else %}
          mdi:radiator-disabled
        {% endif %}
      turn_on:
        service: select.select_option
        target:
          entity_id: select.fp_chb_parents_pilot_wire_mode
        data:
          option: comfort
      turn_off:
        service: select.select_option
        target:
          entity_id: select.fp_chb_parents_pilot_wire_mode
        data:
          option: eco
```

Ein anderes, komplexeres Beispiel ist [hier](https://github.com/jmcollin78/versatile_thermostat/discussions/431#discussioncomment-11393065)

## Verwendung eines Netatmo-Systems

Das System, das auf Netatmo TRVs basiert, funktioniert nicht gut mit _VTherm_. Sie können eine Diskussion über das spezifische Verhalten von Netatmo-Systemen (in Französisch) hier finden: [https://forum.hacf.fr/t/vannes-netatmo-et-vtherm/56063](https://forum.hacf.fr/t/vannes-netatmo-et-vtherm/56063).

Einige Benutzer haben jedoch _VTherm_ erfolgreich in Netatmo integriert, indem sie einen virtuellen Schalter zwischen _VTherm_ und der Netatmo-Klimaeinheit wie folgt eingebaut haben:

```
TODO
```


## Nur der erste Heizkörper heizt

Wenn im Modus `over_switch` mehrere Heizkörper für denselben VTherm konfiguriert sind, wird die Heizung nacheinander ausgelöst, um die Verbrauchsspitzen so gut wie möglich zu glätten.
Dies ist völlig normal und gewollt. Es wird hier beschrieben: [For a thermostat of type ```thermostat_over_switch```](#for-a-thermostat-of-type-thermostat_over_switch)

## Der Heizkörper heizt, obwohl die Solltemperatur überschritten wird, oder er heizt nicht, wenn die Raumtemperatur deutlich unter dem Sollwert liegt

### Typ `over_switch` oder `over_valve`
Bei einem VTherm vom Typ `over_switch` oder `over_valve` zeigt dieses Problem einfach an, dass die Parameter des TPI-Algorithmus nicht richtig konfiguriert sind. Siehe [TPI-Algorithmus](#tpi-algorithm) zur Optimierung der Einstellungen.

### Typ `over_climate`
Bei einem VTherm des Typs `over_climate` wird die Regelung direkt vom zugehörigen `climate` übernommen, und VTherm überträgt lediglich die Sollwerte dorthin. Wenn also der Heizkörper heizt, obwohl die Solltemperatur überschritten ist, ist es wahrscheinlich, dass seine interne Temperaturmessung verzerrt ist. Das passiert oft bei TRVs und reversiblen Klimaanlagen, die einen internen Temperatursensor haben, der entweder zu nahe am Heizelement liegt (so dass es im Winter zu kalt ist).

Beispiele von Diskussionen zu diesen Themen: [#348](https://github.com/jmcollin78/versatile_thermostat/issues/348), [#316](https://github.com/jmcollin78/versatile_thermostat/issues/316), [#312](https://github.com/jmcollin78/versatile_thermostat/discussions/312), [#278](https://github.com/jmcollin78/versatile_thermostat/discussions/278)

Um dieses Problem zu lösen, ist VTherm mit einer Funktion namens Selbstregulierung ausgestattet, die es ihm ermöglicht, den an das zugehörige Gerät gesendeten Sollwert anzupassen, bis der Sollwert erreicht ist. Diese Funktion kompensiert die Verzerrung der internen Temperatursensoren. Wenn die Verzerrung erheblich ist, sollte auch die Regelung erheblich sein. Zur Konfiguration, siehe [Selfregulierung](self-regulation.md).

## Einstellen der Parameter für die Erkennung von offenen Fenstern im Automodus

Wenn Sie die automatische Fensteröffnungserkennung nicht konfigurieren können (siehe [auto](feature-window.md#auto-mode)), können Sie versuchen, die Parameter des Temperaturglättungsalgorithmus zu ändern.
Die automatische Erkennung des offenen Fensters basiert auf der Berechnung der Temperatursteigung. Um Artefakte zu vermeiden, die durch einen ungenauen Temperatursensor verursacht werden, wird diese Steigung anhand einer mit einem Algorithmus namens Exponential Moving Average (EMA) geglätteten Temperatur berechnet.
Dieser Algorithmus hat 3 Parameter:
1. `lifecycle_sec`: die Dauer in Sekunden, die für die Glättung berücksichtigt wird. Je höher dieser Wert ist, desto glatter wird die Temperatur, aber auch die Erkennungsverzögerung nimmt zu.
2. `max_alpha`: Wenn zwei Temperaturmesswerte zeitlich weit auseinander liegen, wird der zweite Messwert viel stärker gewichtet. Dieser Parameter begrenzt das Gewicht eines Messwerts, der weit nach dem vorhergehenden liegt. Dieser Wert muss zwischen 0 und 1 liegen. Je niedriger er ist, desto weniger weit entfernte Messwerte werden berücksichtigt. Der Standardwert ist 0,5, was bedeutet, dass ein neuer Temperaturmesswert nie mehr als die Hälfte des gleitenden Durchschnitts wiegt.
3. `precision`: Die Anzahl der Nachkommastellen, die für die Berechnung des gleitenden Durchschnitts beibehalten werden.

Um diese Parameter zu ändern, müssen Sie die Datei `configuration.yaml` ändern und den folgenden Abschnitt hinzufügen (die folgenden Werte sind die Standardwerte):

```yaml
versatile_thermostat:
  short_ema_params:
    max_alpha: 0.5
    halflife_sec: 300
    precision: 2
```

Diese Parameter sind empfindlich und ziemlich schwierig zu justieren. Bitte verwenden Sie sie nur, wenn Sie wissen, was Sie tun, und wenn Ihre Temperaturmesswerte nicht bereits geglättet sind.

## Warum geht mein Versatile Thermostat in den Sicherheitsmodus?

Der Sicherheitsmodus ist nur für die VTherm-Typen `over_switch` und `over_valve` verfügbar. Er tritt ein, wenn eines der beiden Thermometer (das entweder die Raumtemperatur oder die Außentemperatur liefert) länger als `safety_delay_min` keinen Wert gesendet hat, und der Heizkörper mindestens `safety_min_on_percent` geheizt hat. Siehe [Sicherheitsmodus](feature-advanced.md#safety-mode)

Da sich der Algorithmus auf Temperaturmessungen stützt, besteht, wenn diese nicht mehr vom VTherm empfangen werden, die Gefahr einer Überhitzung und eines Brandes. Um dies zu verhindern, wird die Heizung auf den Parameter `safety_default_on_percent` begrenzt, wenn die oben genannten Bedingungen erkannt werden. Dieser Wert sollte daher einigermaßen niedrig sein (10 % ist ein guter Wert). Er trägt dazu bei, einen Brand zu vermeiden und verhindert gleichzeitig, dass der Heizkörper vollständig abgeschaltet wird (Gefahr des Einfrierens).

Alle diese Parameter werden auf der letzten Seite der VTherm-Konfiguration konfiguriert: "Erweiterte Einstellungen".

### Wie wird der Sicherheitsmodus erkannt?
Das erste Symptom ist eine ungewöhnlich niedrige Temperatur mit einer kurzen und gleichmäßigen Aufheizzeit während jedes Zyklus.
Beispiel:

[Sicherheitsmodus](images/security-mode-symptome1.png)

Wenn Sie die [Versatile Thermostat UI Card] (https://github.com/jmcollin78/versatile-thermostat-ui-card) installiert haben, wird das betroffene VTherm wie folgt angezeigt:

[Sicherheitsmodus UI Card](images/security-mode-symptome2.png)

Sie können auch die Attribute von VTherm auf die Daten der letzten empfangenen Werte überprüfen. **Die Attribute sind in den Developer Tools / States verfügbar**.

Beispiel:

```yaml
safety_state: true
last_temperature_datetime: "2023-12-06T18:43:28.346010+01:00"
last_ext_temperature_datetime: "2023-12-06T13:04:35.164367+01:00"
last_update_datetime: "2023-12-06T18:43:28.351103+01:00"
...
safety_delay_min: 60
```

Das können wir sehen:
1. Das VTherm befindet sich tatsächlich im Sicherheitsmodus (`safety_state: true`),
2. Die aktuelle Zeit ist der 12.06.2023 um 18:43:28 (`last_update_datetime: „2023-12-06T18:43:28.351103+01:00“`),
3. Der letzte Empfangszeitpunkt der Raumtemperatur ist der 12.06.2023 um 18:43:28 (`last_temperature_datetime: „2023-12-06T18:43:28.346010+01:00“`), sie ist also aktuell,
4. Der letzte Empfangszeitpunkt der Außentemperatur ist der 12.06.2023 um 13:04:35 (`last_ext_temperature_datetime: „2023-12-06T13:04:35.164367+01:00“`). Die Außentemperatur ist mehr als 5 Stunden zu spät, was den Sicherheitsmodus auslöst, da der Schwellenwert auf 60 Minuten eingestellt ist (`safety_delay_min: 60`).

### Wie kann ich benachrichtigt werden, wenn dies geschieht?
Das VTherm sendet ein Ereignis, sobald dies geschieht, und erneut am Ende des Sicherheitsalarms. Sie können diese Ereignisse in einer Automatisierung erfassen und eine Benachrichtigung senden, ein Licht blinken lassen, eine Sirene auslösen, usw. Das bleibt Ihnen überlassen.

Zur Behandlung von Ereignissen, die von VTherm erzeugt werden, siehe [Events](#events).

### Wie kann man das beheben?
Das hängt von der Ursache des Problems ab:
1. Wenn ein Sensor defekt ist, sollte er repariert werden (Batterien ersetzen oder austauschen, die Wetterintegration, die die Außentemperatur liefert, überprüfen usw.),
2. Wenn der Parameter `safety_delay_min` zu klein ist, kann er viele Fehlalarme erzeugen. Ein korrekter Wert liegt bei etwa 60 Minuten, insbesondere wenn Sie batteriebetriebene Temperatursensoren haben. Siehe [meine Einstellungen](tuning-examples.md#batteriebetriebener-temperatursensor),
3. Einige Temperatursensoren senden keine Messungen, wenn sich die Temperatur nicht geändert hat. Wenn also die Temperatur lange Zeit sehr stabil bleibt, kann der Sicherheitsmodus ausgelöst werden. Dies ist kein großes Problem, da er deaktiviert wird, sobald das VTherm eine neue Temperatur empfängt. Bei einigen Thermometern (z. B. TuYA oder Zigbee) können Sie eine maximale Verzögerung zwischen zwei Messungen erzwingen. Die maximale Verzögerung sollte auf einen Wert gesetzt werden, der kleiner ist als `safety_delay_min`,
4. Sobald die Temperatur wieder empfangen wird, schaltet sich der Sicherheitsmodus aus, und die vorherigen Werte für Voreinstellung, Zieltemperatur und Modus werden wiederhergestellt.
5. Wenn der externe Temperatursensor defekt ist, können Sie die Auslösung des Sicherheitsmodus deaktivieren, da er nur minimale Auswirkungen auf die Ergebnisse hat. Siehe dazu [hier](feature-advanced.md#safety-mode).
6. some Zigbee sensors have an entity named Last Seen. They are often hidden and need to be enabled to be usable. Once enabled, you can configure it in the VTherm main configuration screen. See main configuration screen.


## Eine Personengruppe als Anwesenheitssensor verwenden

Leider werden Personengruppen nicht als Präsenzmelder erkannt. Daher können Sie sie nicht direkt in VTherm verwenden.
Eine Abhilfe besteht darin, eine binäre Sensorvorlage mit dem folgenden Code zu erstellen:

Datei `template.yaml`:

```yaml
- binary_sensor:
    - name: maison_occupee
      unique_id: maison_occupee
      state: "{{is_state('person.person1', 'home') or is_state('person.person2', 'home') or is_state('input_boolean.force_presence', 'on')}}"
      device_class: occupancy
```

In diesem Beispiel ist die Verwendung eines `input_boolean` namens `force_presence` zu beachten, das den Sensor auf `True` setzt und damit jedes VTherm, das ihn verwendet, zu einer aktiven Anwesenheit zwingt. Dies kann z.B. verwendet werden, um ein Vorheizen des Hauses auszulösen, wenn man die Arbeit verlässt oder wenn eine unbekannte Person in HA anwesend ist.

Datei `configuration.yaml`:

```yaml
...
template: !include templates.yaml
...
```

## Aktivieren von Protokollen für das Versatile Thermostat

Manchmal müssen Sie Protokolle aktivieren, um Ihre Analyse zu verfeinern. Dazu bearbeiten Sie die Datei `logger.yaml` in Ihrer Konfiguration und konfigurieren die Protokolle wie folgt:

```yaml
default: xxxx
logs:
  custom_components.versatile_thermostat: info
```
Sie müssen die YAML-Konfiguration neu laden (Entwicklertools / YAML / Alle YAML-Konfiguration neu laden) oder den Home Assistant neu starten, damit diese Änderung wirksam wird.

Seien Sie vorsichtig, im Debug-Modus ist Versatile Thermostat sehr gesprächig und kann den Home Assistant schnell verlangsamen oder Ihre Festplatte überlasten. Wenn Sie zur Analyse von Anomalien in den Fehlersuchmodus wechseln, tun Sie dies nur für die Zeit, die zur Reproduktion des Fehlers erforderlich ist, und deaktivieren Sie den Fehlersuchmodus unmittelbar danach.

## VTherm verfolgt keine Sollwertänderungen, die direkt am zugehörigen Gerät vorgenommen werden (`over_climate`)

Einzelheiten zu dieser Funktion finden Sie [hier](over-climate.md#track-underlying-temperature-changes).

## VTherm schaltet automatisch in den Modus 'Kühlen' oder 'Heizen' um

Einige reversible Wärmepumpen verfügen über Modi, mit denen die Wärmepumpe entscheiden kann, ob sie heizen oder kühlen soll. Diese Modi sind je nach Marke als 'Auto' oder 'Heat_cool' gekennzeichnet. Diese beiden Modi sollten nicht mit _VTherm_ verwendet werden, da die Algorithmen von _VTherm_ explizit wissen müssen, ob sich das System im Heiz- oder Kühlmodus befindet, was in diesen Modi nicht der Fall ist.

Sie sollten nur die folgenden Modi verwenden: `Heizen`, `Kühlen`, `Aus`, oder optional `Lüfter` (obwohl `Lüfter` bei _VTherm_ keinen praktischen Nutzen hat).

## Erkennung von offenen Fenstern verhindert keine Änderungen der Voreinstellungen

In der Tat werden voreingestellte Änderungen berücksichtigt, während ein Fenster geöffnet ist, und dies ist das erwartete Verhalten.
Wenn der Aktionsmodus auf _Ausschalten_ oder _Nur Lüfter_ eingestellt ist, werden die voreingestellte Änderung und die Anpassung der Solltemperatur sofort übernommen. Da das Gerät entweder ausgeschaltet ist oder sich im reinen Lüfterbetrieb befindet, besteht keine Gefahr der Aufheizung des Außenbereichs. Wenn der Gerätemodus auf Heizen oder Kühlen umschaltet, werden die Voreinstellung und die Temperatur übernommen und verwendet.

Wenn der Aktionsmodus auf _Frostschutz_ oder _Eco_ eingestellt ist, wird die voreingestellte Temperatur angewendet, **aber die Voreinstellung selbst bleibt unverändert**. Auf diese Weise kann die Voreinstellung bei geöffnetem Fenster geändert werden, ohne die Solltemperatur zu verändern, die wie im Aktionsmodus programmiert bleibt.

### Beispiel:
1. **Initial state**: Fenster geschlossen, Aktionsmodus auf _Frostschutz_ eingestellt, Voreinstellung auf Komfort und Solltemperatur auf 19°C.
2. **Window opens and system waits**: Die Voreinstellung bleibt auf Komfort, **aber die Solltemperatur wechselt auf 10°C** (Frostschutz). Dieser Zustand kann inkonsistent erscheinen, weil die angezeigte Voreinstellung nicht mit der angewendeten Solltemperatur übereinstimmt.
3. **Änderung der Voreinstellung zu Boost** (durch den Benutzer oder den Scheduler): Die Voreinstellung wechselt zu Boost, aber die Solltemperatur bleibt bei 10°C (Frostschutz). Dieser Zustand kann auch inkonsistent erscheinen.
4. **Fenster wird geschlossen**: Die Voreinstellung bleibt auf Boost, und die Solltemperatur ändert sich auf 21°C (Boost). Die Inkonsistenz verschwindet, und die Änderung der Voreinstellung durch den Benutzer wird korrekt übernommen.