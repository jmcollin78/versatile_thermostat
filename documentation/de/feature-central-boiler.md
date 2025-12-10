# Steuerung der Zentralheizung

- [Steuerung der Zentralheizung](#steuerung-der-zentralheizung)
  - [Prinzip](#prinzip)
  - [Konfiguration](#konfiguration)
    - [Wie findet man die richtige Maßnahme?](#wie-findet-man-die-richtige-maßnahme)
  - [Ereignisse](#ereignisse)
  - [Warnhinweis](#warnhinweis)

Sie können einen Zentralheizungskessel steuern. Solange es möglich ist, den Heizkessel vom Home Assistant aus zu starten oder zu stoppen, kann der Versatile Thermostat ihn direkt steuern.

## Prinzip

<please update translation from English version>

Grundlegend funktioniert das so:
1. Eine neue Entität des Typs `binary_sensor` mit dem Standardnamen `binary_sensor.central_boiler` wird hinzugefügt.
2. In der Konfiguration des _VTherms_ legen Sie fest, ob das _VTherm_ den Heizkessel steuern soll. In einer heterogenen Installation sollen einige _VTherms_ den Kessel steuern, andere nicht. Daher müssen Sie in jeder _VTherm_-Konfiguration angeben, ob sie den Heizkessel steuert.
3. Der `binary_sensor.central_boiler` lauscht auf Zustandsänderungen in den Geräten der _VTherms_, die als Kesselsteuerung gekennzeichnet sind.
4. Wenn die Anzahl der vom _VTherm_ gesteuerten Geräte, die eine Heizung anfordern (d. h. wenn seine `hvac_action` auf `Heizen` wechselt), einen konfigurierbaren Schwellenwert überschreitet, schaltet sich der `binary_sensor.central_boiler` ein, und **wenn ein Aktivierungsdienst konfiguriert wurde, wird dieser Dienst aufgerufen**.
5. Wenn die Anzahl der Geräte, die eine Heizung anfordern, unter den Schwellenwert fällt, schaltet sich der `binary_sensor.central_boiler` aus, und **wenn ein Deaktivierungsdienst konfiguriert wurde, wird dieser Dienst aufgerufen**.
6. Sie haben Zugang zu zwei Entitäten:
   - Eine `number`-Entity, die standardmäßig den Namen `number.boiler_activation_threshold` trägt und die Aktivierungsschwelle angibt. Dieser Schwellwert ist die Anzahl der Geräte (Heizkörper), die eine Heizung anfordern.
   - Eine `sensor`-Entity mit dem Standardnamen `sensor.nb_device_active_for_boiler`, die die Anzahl der Geräte angibt, die eine Heizung anfordern. Bei einem _VTherm_ mit 4 Ventilen, von denen 3 eine Heizung anfordern, zeigt dieser Sensor z.B. 3 an. Es werden nur die Geräte von _VTherms_ gezählt, die zur Steuerung des zentralen Heizkessels gekennzeichnet sind.

Sie haben also jederzeit die Möglichkeit, die Auslösung des Heizkessels zu steuern und anzupassen.

Alle diese Entities sind mit dem zentralen Konfigurationsdienst verbunden:

![Kesselsteuer-Entities](images/entitites-central-boiler.png)

## Konfiguration
Um diese Funktion zu konfigurieren, benötigen Sie eine zentrale Konfiguration (siehe [Konfiguration](#konfiguration)) und markieren das Kästchen 'Zentralheizung hinzufügen':

![Zentralheizung hinzufügen](images/config-central-boiler-1.png)

Auf der nächsten Seite können Sie die Aktionen (z. B. Dienste) konfigurieren, die beim Ein- und Ausschalten des Heizkessels aufgerufen werden sollen:

![Hinzufügen einer Zentralheizung](images/config-central-boiler-2.png)

Die Aktionen (z. B. Dienste) werden wie auf der Seite beschrieben konfiguriert:
1. Das allgemeine Format ist `entity_id/service_id[/attribute:value]` (wobei `/attribute:value` optional ist).
2. `entity_id` ist der Name der Entity, die den Kessel steuert, in der Form `domain.entity_name`. Zum Beispiel: `switch.heizungsanlage` für einen Kessel, der von einem Schalter gesteuert wird, oder `climate.heizungsanlage` für einen Kessel, der von einem Thermostat gesteuert wird, oder jede andere Entity, die eine Kesselsteuerung erlaubt (es gibt keine Einschränkung). Sie können auch Eingänge (`Helfer`) wie `input_boolean` oder `input_number` umschalten.
3. `service_id` ist der Name des aufzurufenden Dienstes in der Form `domain.service_name`. Beispielsweise: `switch.turn_on`, `switch.turn_off`, `climate.set_temperature`, `climate.set_hvac_mode` sind gültige Beispiele.
4. Einige Dienste benötigen einen Parameter. Dies könnte der 'HVAC-Modus' für `climate.set_hvac_mode` oder die Zieltemperatur für `climate.set_temperature` sein. Dieser Parameter sollte im Format `Attribut:Wert` am Ende des Strings konfiguriert werden.

Beispiele (zur Anpassung an Ihre Gegebenheiten):
- `climate.heizungsanlage/climate.set_hvac_mode/hvac_mode:heat`: um den Kesselthermostat im Heizbetrieb einzuschalten.
- `climate.heizungsanlage/climate.set_hvac_mode/hvac_mode:off`: zum Ausschalten des Kesselthermostats.
- `switch.pumpe_heizungsanlage/switch.turn_on`: zum Einschalten des Schalters, der die Kesselpumpe steuert.
- `switch.pumpe_heizungsanlage/switch.turn_off`: zum Ausschalten des Schalters, der die Kesselpumpe steuert.
- ...

### Wie findet man die richtige Maßnahme?
Um den richtige Auslöser zu finden, gehen Sie am besten zu "Entwicklertools / Dienste" und suchen Sie nach der aufzurufenden Aktion, der zu steuernden Entität und allen erforderlichen Parametern.
Klicken Sie auf 'Dienst aufrufen'. Wenn sich Ihr Kessel einschaltet, haben Sie die richtige Konfiguration. Wechseln Sie dann in den YAML-Modus und kopieren Sie die Parameter.

Beispiel:

Unter "Entwicklertools / Aktionen":

![Servicekonfiguration](images/dev-tools-turnon-boiler-1.png)

Im YAML-Mmode:

![Service Configuration](images/dev-tools-turnon-boiler-2.png)

Der zu konfigurierende Dienst wird dann sein: `climate.sonoff/climate.set_hvac_mode/hvac_mode:heat` (beachten Sie das Entfernen der Leerzeichen in `hvac_mode:heat`).

Machen Sie das Gleiche für den ausgeschalteten Dienst, und schon sind Sie startklar.

## Ereignisse

Bei jeder erfolgreichen Aktivierung oder Deaktivierung des Kessels wird ein Ereignis vom Versatile Thermostat gesendet. Dieses kann z. B. von einer Automatisierung erfasst werden, um Sie über die Änderung zu informieren.
Die Ereignisse sehen so aus:

Ein Aktivierungs-Ereignis:
```yaml
event_type: versatile_thermostat_central_boiler_event
data:
  central_boiler: true
  entity_id: binary_sensor.central_boiler
  name: Central boiler
  state_attributes: null
origin: LOCAL
time_fired: "2024-01-14T11:33:52.342026+00:00"
context:
  id: 01HM3VZRJP3WYYWPNSDAFARW1T
  parent_id: null
  user_id: null
```yaml
event_type: versatile_thermostat_central_boiler_event
data:
  central_boiler: true
  entity_id: binary_sensor.central_boiler
  name: Central boiler
  state_attributes: null
origin: LOCAL
time_fired: "2024-01-14T11:33:52.342026+00:00"
context:
  id: 01HM3VZRJP3WYYWPNSDAFARW1T
  parent_id: null
  user_id: null
```

Ein Ausschalt-Ereignis:
```yaml
event_type: versatile_thermostat_central_boiler_event
data:
  central_boiler: false
  entity_id: binary_sensor.central_boiler
  name: Central boiler
  state_attributes: null
origin: LOCAL
time_fired: "2024-01-14T11:43:52.342026+00:00"
context:
  id: 01HM3VZRJP3WYYWPNSDAFBRW1T
  parent_id: null
  user_id: null
```

## Warnhinweis

> ![Tipp](images/tips.png) _*Hinweise*_
>
> Die Steuerung einer Zentralheizungsanlage durch Software oder Hausautomation kann deren ordnungsgemäßen Betrieb gefährden. Vergewissern Sie sich vor der Nutzung dieser Funktionen, dass Ihr Heizkessel über geeignete Sicherheitsvorrichtungen verfügt und dass diese korrekt funktionieren. Wenn Sie beispielsweise einen Heizkessel mit geschlossenen Ventilen einschalten, kann ein Überdruck entstehen.
