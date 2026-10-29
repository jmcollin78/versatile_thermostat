# Versatile Thermostat + Home Assistant MCP

Diese Dokumentation beschreibt das Hinzufügen von LLM/MCP-Werkzeugen zu **Versatile Thermostat (VTherm)** über den offiziellen MCP-Server von Home Assistant.

Die bereitgestellte Datei `llm.py` stellt Folgendes bereit:

- 3 Werkzeuge zum Lesen und Diagnostizieren;
- 3 einfache Aktionswerkzeuge: Temperatur, Preset und HVAC-Modus;
- Beschreibungen und Anweisungen, die auf **Französisch und Englisch** verwendet werden können;
- Links zur VTherm-Dokumentation, zum Log-Sammler und zum Log-Analysator für die Fehlersuche.

> Die Datei erstellt keinen eigenen MCP-Server. Sie verwendet die native LLM-Plattform von Home Assistant; anschließend veröffentlicht der offizielle **Model Context Protocol Server** diese Werkzeuge für MCP-Clients.

---

## 1. Zu installierende Datei

`llm.py` nach folgendem Pfad kopieren:

```text
/config/custom_components/versatile_thermostat/llm.py
```

Verzeichnisstruktur:

```text
/config/custom_components/versatile_thermostat/
├── __init__.py
├── climate.py
├── const.py
├── manifest.json
├── ...
└── llm.py
```

Es ist nicht erforderlich, `manifest.json` zu ändern, um die Plattform `llm` zu deklarieren.

Home Assistant erkennt Integrationsplattformen dynamisch und lädt `llm.py` bei Bedarf, wenn eine LLM-API die Werkzeuge der Integration benötigt.

Nach dem Kopieren der Datei einen **vollständigen Neustart von Home Assistant** durchführen.

> Achtung: Wenn `llm.py` manuell zu einer von HACS verwalteten VTherm-Installation hinzugefügt wurde, kann ein zukünftiges HACS-Update das Integrationsverzeichnis ersetzen. Bewahre eine Kopie der Datei auf, bis sie direkt in das VTherm-Projekt integriert wurde.

---

## 2. Bereitgestellte Werkzeuge

Bei Verwendung der LLM-API `assist` fügt der Home-Assistant-MCP-Server den Werkzeugnamen das Präfix `assist__` hinzu.

### Nur Lesen — Stufe 1

```text
assist__versatile_thermostat__list_vtherms
assist__versatile_thermostat__get_status
assist__versatile_thermostat__diagnose
```

### Aktionen — Stufe 2A

```text
assist__versatile_thermostat__set_temperature
assist__versatile_thermostat__set_preset
assist__versatile_thermostat__set_hvac_mode
```

Die ersten drei Werkzeuge sind wie folgt gekennzeichnet:

```python
read_only=True
destructive=False
idempotent=True
open_world=False
```

Die drei Aktionswerkzeuge sind wie folgt gekennzeichnet:

```python
read_only=False
destructive=False
idempotent=True
open_world=False
```

Sie ändern tatsächlich den Zustand des Thermostats, jedoch ausschließlich über die standardmäßigen Home-Assistant-Dienste `climate.*`.

---

## 3. `list_vtherms`

Dieses Werkzeug listet ausschließlich VTherm-Entitäten auf, die:

- in Home Assistant geladen sind;
- zur Domäne `climate` gehören;
- einem Versatile-Thermostat-Konfigurationseintrag zugeordnet sind;
- für Assist freigegeben sind.

Für jeden Thermostat werden unter anderem folgende Informationen zurückgegeben:

```text
entity_id
name
hvac_mode
hvac_action
preset_mode
current_temperature
target_temperature
target_minus_current
min_temperature
max_temperature
target_temperature_step
hvac_modes
preset_modes
thermostat_type
messages
```

Vereinfachtes Beispiel:

```json
{
  "entity_id": "climate.thermostat_salon",
  "hvac_mode": "heat",
  "hvac_action": "heating",
  "preset_mode": "comfort",
  "current_temperature": 18.7,
  "target_temperature": 19.5,
  "target_minus_current": 0.8,
  "hvac_modes": ["heat", "off"],
  "preset_modes": ["none", "frost", "eco", "comfort", "boost"]
}
```

---

## 4. `get_status`

`get_status` gibt den vollständigen Rohzustand der VTherm-Entität zurück:

```text
entity_id
state
last_changed
last_updated
attributes
```

`attributes` enthält die Home-Assistant-Attribute sowie die auf der Entität verfügbaren VTherm-spezifischen Attribute.

Dieses Werkzeug ist nützlich, wenn der Agent Informationen benötigt, die nicht in die strukturierte Diagnoseausgabe übernommen wurden.

---

## 5. `diagnose`

`diagnose` ist das bevorzugte Werkzeug für Anfragen wie:

- „Warum heizt mein Thermostat nicht?“
- „Warum ist er im Zustand idle?“
- „Wird er wegen Lastabwurf deaktiviert?“
- „Gibt es ein Problem mit einem Fenster?“
- „Warum wurde VTherm gestoppt?“
- „Debug the living-room thermostat.“
- „Diagnose why this VTherm is not heating.“

Es gibt unter anderem Folgendes zurück:

### Aktueller Zustand

```text
hvac_mode
hvac_action
preset_mode
current_temperature
target_temperature
target_minus_current
hvac_modes
preset_modes
```

### VTherm-Gründe

Die Datei priorisiert Informationen, die von VTherm selbst berechnet wurden:

```text
specific_states.messages
hvac_off_reason
hvac_mode_reason
should_device_be_active
device_actives
unavailable_underlying_entities
temperature_slope
is_sleeping
is_recalculate_scheduled
```

Ziel ist es zu verhindern, dass das Modell allein aus der Differenz zwischen aktueller Temperatur und Solltemperatur eine Ursache erfindet.

### Diagnoseabschnitte

Sofern vorhanden, werden die folgenden Abschnitte vollständig zurückgegeben:

```text
configuration
current_state
requested_state
specific_states
preset_temperatures
presence_manager
motion_manager
power_manager
window_manager
safety_manager
auto_start_stop_manager
lock_manager
heating_failure_detection
vtherm_over_switch
vtherm_over_climate
vtherm_over_valve
```

Ein Abschnitt, der auf der Entität nicht vorhanden ist, wird einfach nicht zurückgegeben.

---

## 6. VTherm-Dokumentation und Fehlersuche

Das Ergebnis von `diagnose` enthält außerdem `support_resources` mit französischen **und** englischen Ressourcen:

```text
documentation_fr
documentation_en
reference_fr
reference_en
log_collector_fr
log_collector_en
log_analyzer
official_repository
log_download_action
```

Wichtige Links:

- Französische Dokumentation: https://www.versatile-thermostat.org/fr/
- Englische Dokumentation: https://www.versatile-thermostat.org/en/
- Französische Referenz: https://www.versatile-thermostat.org/fr/docs/reference/
- Englische Referenz: https://www.versatile-thermostat.org/en/docs/reference/
- Französischer Log-Sammler: https://www.versatile-thermostat.org/fr/docs/feature-logs-collector/
- Englischer Log-Sammler: https://www.versatile-thermostat.org/en/docs/feature-logs-collector/
- Log-Analysator: https://www.versatile-thermostat.org/fr/debugger/
- Offizielles VTherm-Repository: https://github.com/jmcollin78/versatile_thermostat

Für komplexe Fehlersuche weist der an das LLM übergebene Prompt das Modell an:

1. zuerst die von VTherm zurückgegebenen Informationen zu verwenden;
2. keine Ursache zu erfinden, die nicht in den Daten enthalten ist;
3. die französische oder englische Dokumentation passend zur Sprache der Anfrage aufzurufen, sofern der Client Webzugriff hat;
4. den Log-Sammler und anschließend den Log-Analysator vorzuschlagen, wenn der momentane Zustand keine eindeutige Schlussfolgerung zulässt.

### Wichtig

`llm.py` **lädt selbst keine Webseiten herunter**.

Die Datei stellt dem LLM-Client URLs und Anweisungen bereit. Wenn der verwendete Client (Codex, Gemini, Claude usw.) über Webzugriff verfügt, kann er die Dokumentation aufrufen. Andernfalls kann er dem Benutzer zumindest die Links bereitstellen.

Die Website versatile-thermostat.org weist selbst darauf hin, dass es sich um eine Community-Website handelt, und stellt klar, dass die offizielle Quelle des Projekts weiterhin das VTherm-GitHub-Repository ist.

---

## 7. Log-Sammler

VTherm stellt folgende Aktion bereit:

```text
versatile_thermostat.download_logs
```

Die Datei `llm.py` führt diese Aktion nicht automatisch aus; sie weist lediglich als Ressource für die Fehlersuche darauf hin.

Home-Assistant-Beispiel:

```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.thermostat_salon
  log_level: DEBUG
```

Die erzeugte Datei kann anschließend in den Analysator geladen werden:

```text
https://www.versatile-thermostat.org/fr/debugger/
```

---

# Stufe 2 — Aktionen

## 8. `set_temperature`

Verwendet:

```text
climate.set_temperature
```

MCP-Parameter:

```json
{
  "entity_id": "climate.thermostat_salon",
  "temperature": 19.5
}
```

Vor dem Aufruf prüft das Werkzeug:

- dass VTherm für Assist freigegeben ist;
- dass dem Aufruf ein authentifizierter Home-Assistant-Benutzer zugeordnet ist;
- dass der Benutzer die Berechtigung besitzt, diese Entität zu steuern;
- dass die angeforderte Temperatur innerhalb der Min-/Max-Werte des Thermostats liegt, sofern diese verfügbar sind.

Das Ergebnis enthält:

```text
success
action
requested
state_after_call
note
```

`state_after_call` ermöglicht dem Modell, den Zustand direkt nach dem Befehl zu überprüfen.

VTherm kann den effektiven Zustand anschließend entsprechend seinen eigenen Regeln ändern: Zentralmodus, Fenster, Lastabwurf, Sicherheit, Preset, Auto-Start/-Stopp, Regelung usw.

---

## 9. `set_preset`

Verwendet:

```text
climate.set_preset_mode
```

Parameter:

```json
{
  "entity_id": "climate.thermostat_salon",
  "preset": "comfort"
}
```

Vor der Aktion muss das angeforderte Preset in folgendem Attribut vorhanden sein:

```text
preset_modes
```

und zwar für die Zielentität.

Ein Modell kann daher nicht beliebig ein Preset anfordern, das für diesen Thermostat nicht verfügbar ist.

---

## 10. `set_hvac_mode`

Verwendet:

```text
climate.set_hvac_mode
```

Parameter:

```json
{
  "entity_id": "climate.thermostat_salon",
  "hvac_mode": "heat"
}
```

Der Modus muss in folgendem Attribut enthalten sein:

```text
hvac_modes
```

Um einen Thermostat auszuschalten, wenn `off` unterstützt wird:

```json
{
  "entity_id": "climate.thermostat_salon",
  "hvac_mode": "off"
}
```

Die Datei stellt bewusst kein `toggle`-Werkzeug bereit: Der gewünschte Zustand muss explizit angegeben werden.

---

## 11. Sicherheit der Aktionen

Die Werkzeuge der Stufe 2 verwenden mehrere Schutzmechanismen:

1. ausschließlich für Assist freigegebene VTherm-Entitäten;
2. ein Home-Assistant-Benutzerkontext ist für Schreibvorgänge zwingend erforderlich;
3. die Berechtigung `CONTROL` wird geprüft;
4. Presets und HVAC-Modi werden gegen die tatsächliche Entität validiert;
5. der zulässige Temperaturbereich wird geprüft;
6. es werden ausschließlich die standardmäßigen Dienste `climate.*` verwendet;
7. die interne VTherm-Konfiguration wird nicht verändert;
8. TPI, Lastabwurf, Fenster-, Sicherheits- oder Algorithmuseinstellungen werden nicht verändert.

Aktionen sind mit `read_only=False` gekennzeichnet. Dadurch kann der Home-Assistant-MCP-Server sie ausblenden, wenn seine Option **Read only** aktiviert ist.

---

# Installation des offiziellen Home-Assistant-MCP-Servers

## 12. MCP-Server aktivieren

In Home Assistant:

```text
Einstellungen
→ System
→ KI
→ Model Context Protocol
```

Den MCP-Server bei Bedarf aktivieren.

Er kann auch über folgenden Weg hinzugefügt werden:

```text
Einstellungen
→ Geräte & Dienste
→ Integration hinzufügen
→ Model Context Protocol Server
```

Home Assistant stellt anschließend eine MCP-URL bereit, typischerweise im lokalen Netzwerk:

```text
http://homeassistant.local:8123/api/mcp
```

---

## 13. Empfohlene Konfiguration des MCP-Servers

In den Optionen des **Model Context Protocol Server**:

```text
Expose all LLM APIs      : OFF (empfohlen, um die freigegebene Oberfläche zu begrenzen)
Control Home Assistant   : Assist / Device control
Require administrator    : ON
Read only                : OFF für Stufe 2
```

### Wenn `Read only` aktiviert ist

Die Aktionswerkzeuge:

```text
set_temperature
set_preset
set_hvac_mode
```

werden aus dem MCP-Katalog gefiltert, da sie als `read_only=False` deklariert sind.

Die Diagnosewerkzeuge bleiben verfügbar.

Das ist nützlich, wenn vorübergehend wieder nur Stufe 1 verwendet werden soll, ohne `llm.py` zu ändern.

---

## 14. VTherm für Assist freigeben

Die Werkzeuge greifen nur auf Thermostate zu, die für Assist freigegeben sind.

In Home Assistant die benötigten Entitäten freigeben, zum Beispiel:

```text
climate.thermostat_salon
climate.thermostat_cuisine
climate.thermostat_salle
```

Es ist nicht erforderlich, alle Geräte im Haus freizugeben.

---

# Verbindung mit Codex

## 15. MCP-Server hinzufügen

```bash
codex mcp add homeassistant \
  --url http://homeassistant.local:8123/api/mcp
```

Codex öffnet Home Assistant im Browser für die OAuth-Authentifizierung.

Überprüfung:

```bash
codex mcp list
```

Beispiel:

```text
homeassistant  http://homeassistant.local:8123/api/mcp  enabled
```

---

## 16. VTherm-Werkzeuge überprüfen

Prompt:

```text
Verwende ausschließlich den MCP-Server homeassistant.
Liste alle auf diesem Server verfügbaren Werkzeuge auf, deren Name
versatile_thermostat enthält. Führe keine Aktion aus.
```

Mit Stufe 2A sollten folgende Werkzeuge verfügbar sein:

```text
assist__versatile_thermostat__list_vtherms
assist__versatile_thermostat__get_status
assist__versatile_thermostat__diagnose
assist__versatile_thermostat__set_temperature
assist__versatile_thermostat__set_preset
assist__versatile_thermostat__set_hvac_mode
```

Wenn nur die ersten drei erscheinen, prüfen, ob die MCP-Option **Read only** aktiviert ist.

---

# Beispielfragen

## 17. Französisch — Lesen und Diagnose

```text
Liste mes Versatile Thermostat et donne-moi leur température actuelle,
leur consigne et leur état de chauffe.
```

```text
Diagnostique climate.thermostat_salon et explique pourquoi il ne chauffe pas.
N'invente aucune cause non présente dans les données VTherm.
```

```text
Pourquoi le thermostat du salon est-il idle alors que la température est
inférieure à la consigne ? Regarde aussi le délestage, la sécurité et les fenêtres.
```

```text
Fais un diagnostic de climate.thermostat_salon. Si les données ne suffisent pas,
indique quelle documentation VTherm consulter et rappelle-moi comment utiliser
le collecteur et l'analyseur de logs.
```

---

## 18. Französisch — Aktionen

```text
Mets la consigne du thermostat du salon à 19,5 °C.
```

```text
Passe climate.thermostat_salon en preset comfort.
```

```text
Passe climate.thermostat_salon en mode HVAC off.
```

```text
Remets climate.thermostat_salon en mode heat puis affiche son état.
```

---

## 19. Englisch — Lesen und Diagnose

```text
List my Versatile Thermostats and show their current temperature,
target temperature and HVAC action.
```

```text
Diagnose climate.thermostat_salon and explain why it is not heating.
Do not infer a cause that is not supported by the VTherm diagnostic data.
```

```text
Debug climate.thermostat_salon. Check power shedding, safety, window detection,
auto start/stop and unavailable underlying entities.
```

```text
If the current diagnostic data is not enough, tell me which VTherm documentation
page or log-analysis workflow I should use next.
```

---

## 20. Englisch — Aktionen

```text
Set climate.thermostat_salon to 19.5 °C.
```

```text
Set climate.thermostat_salon preset to comfort.
```

```text
Set climate.thermostat_salon HVAC mode to off.
```

---

# Fehlersuche

## 21. Kein VTherm-Werkzeug erscheint

Prüfen:

1. ob die Datei hier vorhanden ist:

   ```text
   /config/custom_components/versatile_thermostat/llm.py
   ```

2. Home Assistant wurde neu gestartet;
3. VTherm wurde normal geladen;
4. mindestens eine VTherm-`climate`-Entität ist für Assist freigegeben;
5. die Assist-/Device-Control-API wird vom MCP-Server bereitgestellt;
6. der MCP-Client hat sich nach dem Neustart erneut verbunden.

Die Plattform `llm.py` wird bei Bedarf geladen: Das Fehlen einer Meldung beim Start von Home Assistant bedeutet nicht zwangsläufig, dass sie nicht erkannt wurde.

---

## 22. Lesewerkzeuge erscheinen, Aktionswerkzeuge jedoch nicht

Folgende Option prüfen:

```text
Model Context Protocol Server → Read only
```

Für Stufe 2A:

```text
Read only = OFF
```

---

## 23. Eine Aktion wird abgelehnt

Das Werkzeugergebnis nennt normalerweise den Grund:

- kein authentifizierter Benutzerkontext;
- unzureichende Berechtigung;
- Temperatur außerhalb des zulässigen Bereichs;
- Preset nicht vorhanden;
- HVAC-Modus nicht unterstützt;
- Fehler vom Home-Assistant-Dienst zurückgegeben.

Mit `list_vtherms` oder `get_status` können die tatsächlich von der Entität unterstützten Werte abgerufen werden.

---

# Bewusste Einschränkungen von Stufe 2

Die Datei erlaubt keine Änderung von:

```text
TPI
SmartPI / interne Regelung
Regelungskoeffizienten
Leistungsgrenzen
Prioritäten für Lastabwurf
Fenster-Bypass
Sicherheit
zentrale Konfiguration
Konfiguration der zugrunde liegenden Entitäten
persistente VTherm-Konfiguration
```

Diese Funktionen würden zu einer späteren Stufe gehören und zusätzliche Schutzmechanismen erfordern.

---

# Technische Referenzen

- Home Assistant — Model Context Protocol Server  
  https://www.home-assistant.io/integrations/mcp_server/

- Home Assistant Core — LLM-Plattform `climate`  
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/climate/llm.py

- Home Assistant Core — API `Tool`, `ToolResult`, `ToolAnnotations`  
  https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/llm.py

- Home Assistant Core — Dienste `climate`  
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/climate/

- Home Assistant Core — MCP-Server-Konfiguration (`read_only`, `require_admin`)  
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/mcp_server/config_flow.py

- Versatile Thermostat — offizielles Repository  
  https://github.com/jmcollin78/versatile_thermostat

- Versatile Thermostat — Referenzdokumentation  
  https://www.versatile-thermostat.org/fr/docs/reference/

- Versatile Thermostat — Log-Sammler  
  https://www.versatile-thermostat.org/fr/docs/feature-logs-collector/

- Versatile Thermostat — Log-Analysator  
  https://www.versatile-thermostat.org/fr/debugger/
