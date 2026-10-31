# Versatile Thermostat + Home Assistant MCP

Diese Dokumentation beschreibt das Hinzufügen von LLM/MCP-Werkzeugen zu **Versatile Thermostat (VTherm)** über den offiziellen MCP-Server von Home Assistant.

Die bereitgestellte Datei `llm.py` stellt Folgendes bereit:

- 4 Werkzeuge zum Lesen, Diagnostizieren und für den Verlauf;
- 3 einfache Aktionswerkzeuge: Temperatur, Preset und HVAC-Modus;
- 2 TPI-Lesewerkzeuge und 1 TPI-Werkzeug für explizite Änderungen;
- Beschreibungen und Anweisungen, die auf **Französisch und Englisch** verwendet werden können;
- Links zur VTherm-Dokumentation, zum Log-Sammler und zum Log-Analysator für die Fehlersuche.

> Die Datei erstellt keinen eigenen MCP-Server. Sie verwendet die native LLM-Plattform von Home Assistant; anschließend veröffentlicht der offizielle **Model Context Protocol Server** diese Werkzeuge für MCP-Clients.

---

## 1. Zu installierende Datei

Die folgenden vier Dateien in das Integrationsverzeichnis kopieren:

```text
/config/custom_components/versatile_thermostat/llm.py
/config/custom_components/versatile_thermostat/recorder_export.py
/config/custom_components/versatile_thermostat/tpi_history.py
/config/custom_components/versatile_thermostat/tpi_identification.py
```

Verzeichnisstruktur:

```text
/config/custom_components/versatile_thermostat/
├── __init__.py
├── climate.py
├── const.py
├── manifest.json
├── ...
├── llm.py
├── recorder_export.py
├── tpi_history.py
└── tpi_identification.py
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
assist__versatile_thermostat__get_history
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

Die drei obigen Climate-Aktionen verwenden diese Schutzmechanismen (die TPI-Aktion wird separat beschrieben):

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
set_tpi_coefficients
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

Zur Installation und Konfiguration des offiziellen Home-Assistant-MCP-Servers siehe die [Home-Assistant-Referenzdokumentation](https://www.home-assistant.io/integrations/mcp_server/).

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
assist__versatile_thermostat__get_history
assist__versatile_thermostat__set_temperature
assist__versatile_thermostat__set_preset
assist__versatile_thermostat__set_hvac_mode
assist__versatile_thermostat__check_tpi_optimization
assist__versatile_thermostat__analyze_tpi_coefficients
assist__versatile_thermostat__set_tpi_coefficients
```

Der vollständige Katalog enthält sechs Lese- und vier Schreibwerkzeuge. Mit **Read only** bleiben nur die sechs Lesewerkzeuge sichtbar.

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
/config/custom_components/versatile_thermostat/recorder_export.py
/config/custom_components/versatile_thermostat/tpi_history.py
/config/custom_components/versatile_thermostat/tpi_identification.py
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

# TPI-Koeffizienten anhand des Verlaufs optimieren

Eine einfache Frage genügt, etwa: „Sind die Koeffizienten des Thermostats im Elternschlafzimmer optimal?“ oder „Sind meine Koeffizienten gut eingestellt?“. Die Werkzeugbeschreibungen führen den Assistenten zur schreibgeschützten TPI-Prüfung und Berechnung; bei Bedarf wird der Raumname aufgelöst. Werkzeugnamen oder eine `entity_id` sind in der Frage nicht erforderlich, ebenso wenig der Zugriff auf das Dashboard. Der gewählte Konnektor muss jedoch `check_tpi_optimization` und `analyze_tpi_coefficients` bereitstellen: Eine andere Formulierung macht fehlende Werkzeuge nicht verfügbar. Ergebnisse bleiben explorative Schätzungen, kein Nachweis eines Optimums.

Drei Werkzeuge ergänzen die bisherigen Funktionen:

| Werkzeug (Suffix `versatile_thermostat__…`) | Zugriff | Schritt |
| --- | --- | --- |
| `check_tpi_optimization` | Nur Lesen | 1/3 — Prüfung |
| `analyze_tpi_coefficients` | Nur Lesen | 2/3 — Analyse |
| `set_tpi_coefficients` | Explizites Schreiben | 3/3 — optionale Anwendung |

Lesewerkzeuge benötigen nur `entity_id`. Der Client kündigt jeden Schritt vor dem Aufruf an; Hintergrundarbeit wird nicht simuliert. Jede Antwort enthält `stage`, `stage_number`, `stage_total` und `state_changed`.

Die Analyse erfordert klassisches TPI (`proportional_function=tpi`), ohne konfiguriertes Auto-TPI, aktives Lernen oder kontinuierliche Außenkompensation. Diese Version unterstützt `over_switch` mit einem oder mehreren physischen Schaltern. Aufgezeichnete EIN-Zeiten werden integriert und gemäß VTherms gleichen Leistungsanteilen `device_power / N` gemittelt, einschließlich versetzter Phasen und Übergänge innerhalb einer Minute. Die absolute Heizleistung ist nicht erforderlich. Unterschiedliche individuelle Heizleistungen werden dadurch nicht gemessen.

Für `over_climate`, `over_valve` und Climate-Ventilregelung liefert die Antwort ausdrücklich `eligible: false`, `supported: false`, `reason: unsupported_thermostat_type`: Für diesen Typ ist die Analyse noch nicht verfügbar. Mehrdeutige virtuelle Befehle werden ebenfalls abgelehnt; kein blinder Rückgriff auf `hvac_action`.

Recorder liefert höchstens die **letzten 14 Tage**. Nach Ausschlüssen sind mindestens **7 Tage tatsächlich nutzbarer Minuten** erforderlich. Innen- und Außensensor stammen aus der effektiven VTherm-Konfiguration einschließlich zentraler Konfiguration. Ergebnisse enthalten `sources`, `history_requested_days`, `history_available_days`, `history_usable_days`, Ausschlüsse und aktuelle Einstellungen. Eine Recorder-Aufbewahrungsdauer wird nicht vorausgesetzt.

Die Antwort enthält `applicability_note` (FR/EN): Die Koeffizienten sind explorative Schätzungen aus dem analysierten Zeitraum; ihre Eignung unter anderen Bedingungen ist nicht nachgewiesen. Bei wesentlichen Änderungen der Heizbedingungen oder Wohnungsnutzung oder bei einer Verschlechterung der Regelung die Analyse für einen repräsentativen Zeitraum wiederholen, bevor eine Anpassung erwogen wird. Eine Änderung der Außentemperatur allein erfordert keine Neuberechnung.

Der Kalman-Vergleich ist in der MCP-Antwort deaktiviert: Simulationen zeigen, dass Koeffizienten innerhalb der Grenzen dennoch ungenau sein können. `experimental_estimator` meldet `unavailable` mit dem Grund `experimental_model_not_validated_for_application`, ohne Kalman-Berechnung oder Koeffizienten. Für Offline-Untersuchungen bleibt der Schätzer verfügbar; Werte außerhalb `[0, 10]` (innen) und `[0, 1]` (außen), unzureichende Anregung und instabile Schätzungen werden abgelehnt. Beschneiden macht aus einer fehlgeschlagenen Schätzung kein brauchbares Ergebnis. Diese Filter beweisen keine Zuverlässigkeit; OLS bleibt explorativ und die Anwendung erfolgt niemals automatisch. Bootstrap-Intervalle bleiben unkalibriert und werden nicht auf die Dienstgrenzen gekürzt.

Temperaturen werden auf einem Minutenraster kausal höchstens 60 Minuten gehalten. Anders als bei der Außeninterpolation des Referenzskripts werden keine zukünftigen Messungen verwendet. Binäre HA-Zustände gelten bis zum nächsten Ereignis; `unknown`/`unavailable` machen das Intervall ungültig. Physische sowie Diagnose-Sensoren für Sicherheit, Lastabwurf und Fenster werden über Recorder gelesen, da Climate-Diagnoseabschnitte oft nicht aufgezeichnet werden. Fehlende notwendige Filterquellen führen zur Ablehnung. HVAC-Zeiträume außerhalb von `heat`, aktive Schutzfunktionen, offene Fenster und Datenlücken werden ausgeschlossen. Jede Auflösung meldet ausgeschlossene Fensterzyklen. Diese Version erfordert eine VTherm-Konfiguration in °C; Quellsensoren in °F werden in °C umgerechnet.

Das Modell behält `ΔT = g × (T_ext - T_int) + B × u + q`, `coef_ext = g/B`, `A = 1-g` und `coef_int = (A-exp(-dt/tau_cl))/B` bei. Bevorzugte Konvergenz bleibt **6 h**, mit einer Tabelle für 3/4/5/6/8/10/12 h. Tatsächliches `cycle_min` hat Vorrang neben 10/20/30/60 Minuten; gegebenenfalls erfolgt ein ausdrücklich gemeldeter Rückgriff auf die nächste gültige Auflösung. Jeder Fit erfordert 40 Zyklen, 80 % gültige Minuten und die physikalischen Grenzen des Referenzskripts. Fehlende Intervalle werden nie unbemerkt zu längeren Zyklen.

Chronologische Aufteilung 70 % Training / 30 % Validierung, OLS `numpy.linalg.lstsq`, MAE, RMSE, ΔT-R² und Konditionierung bleiben erhalten. Zeitlicher Bootstrap verwendet 1000 Wiederholungen, 24-Stunden-Blöcke und Seed `20261030`; Lücken verkürzen die Blöcke nicht. Ungefähre 95%-Konfidenzintervalle werden ausgegeben. Weniger als 30 akzeptierte physikalische Wiederholungen führen zu `bootstrap_failed`. Nichtphysikalische Modelle oder Konditionszahlen ≥1000 werden abgelehnt; 100–1000 erfordert Vorsicht. Ein niedriges R² allein ist kein Ablehnungsgrund. Relative `coef_ext`-Spannweite über 25 %, weniger als drei Auflösungen oder ein breites Intervall erzeugen Warnungen. Bei `recommendation_reliable: false` darf der Kandidat nicht als zuverlässig beschrieben werden. CSV, Grafiken, Berichte oder andere Dateien sind weder erforderlich noch werden sie erzeugt; keine zusätzlichen pandas/matplotlib-Abhängigkeiten.

Die Analyse **wendet niemals** Koeffizienten an. Ergebnisse, Grenzen und Vergleich darstellen, dann die Benutzerentscheidung abwarten. Eine explizite direkte Änderung benötigt weder Verlauf noch Analyse:

```json
{"entity_id": "climate.thermostat_salon", "coef_int": 0.35, "coef_ext": 0.025}
```

Mindestens ein Koeffizient ist erforderlich; Teiländerungen sind möglich. VTherm-Dienstgrenzen: `0 <= coef_int <= 10`, `0 <= coef_ext <= 1`, nur endliche Werte. Das Werkzeug prüft Assist-Freigabe, klassisches TPI, authentifizierten Benutzer und `CONTROL` erneut und ruft ausschließlich `versatile_thermostat.set_tpi_parameters` mit diesem Kontext auf. Zentrale Konfiguration und Sperren werden weiterhin vom vorhandenen Dienst geprüft. Der Dienst kann Einstellungen speichern; das Werkzeug schreibt niemals direkt in eine ConfigEntry.

`large_change` bedeutet eine absolute Änderung von **0.15 für coef_int**, **0.01 für coef_ext** oder eine relative Änderung von **50 %** (jede Änderung ausgehend von null gilt als groß). Dies sind Bestätigungsschwellen, keine thermischen Sicherheitsgarantien. Ohne Schreibzugriff liefert das Werkzeug `large_change_confirmation_required`, `confirmation_required: true`, Vergleich und `confirmation_token`. Nach zusätzlicher ausdrücklicher Benutzerbestätigung dieselben Werte mit `confirm_large_change: true` und dem Token erneut aufrufen. Er läuft nach 10 Minuten ab und gilt nur für Benutzer, Thermostat und exakten Vergleich; geänderte aktuelle Einstellungen machen ihn ungültig.

Nach dem Aufruf werden Werte vom geladenen VTherm-Objekt erneut gelesen, auch nach einem Neuladen: `previous`, `requested`, `applied`. Fehler nach einem Dienstaufruf liefern `state_changed: null` und erfordern eine Prüfung; sie behaupten nicht, dass nichts geändert wurde. Ablehnungen vor dem Aufruf melden, dass kein Koeffizient geändert wurde. Ablehnungen niemals über generische Dienste umgehen.

MCP **Read only** behält beide Analysewerkzeuge und blendet `set_tpi_coefficients` wie die anderen Aktionen aus.

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


---

## Recorder-Verlauf: CSV-Exporte und Diagramme

Bei „Erstelle ein professionelles, kommentiertes Diagramm des Küchenthermostats über 48 Stunden“ wird der Assistent zu `get_history` und anschließend zur Diagrammerstellung im Client nach Abruf aller Seiten geführt. ApexCharts-/Lovelace-YAML wird nur bei ausdrücklichem Wunsch nach Dashboard-Konfiguration angeboten. Der Climate-Verlauf von SmartPI kann dargestellt werden, obwohl die TPI-Koeffizientenanalyse SmartPI ablehnt. Anmerkungen müssen auf aufgezeichneten Ereignissen beruhen; das Werkzeug liefert weder historische SmartPI-Leistung noch physische Relaisverläufe. Aktuelle Werte können diese Reihen nicht rekonstruieren. Fehlt `get_history` im Konnektorkatalog, muss der Assistent diese Grenze erklären.

Das Lesewerkzeug `versatile_thermostat__get_history` übermittelt dem MCP-Client den aufgezeichneten Verlauf der VTherm-climate-Entität: Zustand, gemessene Temperatur, Sollwert, HVAC-Aktion und Preset, soweit aufgezeichnet. Es unterstützt alle VTherm-Typen unabhängig von der TPI-Analyse. Es gibt weder den gesamten Recorder noch die Verläufe zugehöriger Sensoren und Relais frei.

Der Client (ChatGPT, Claude, Gemini, Codex usw.) ruft die Daten ab und erstellt je nach seinen Fähigkeiten CSV-Dateien oder Diagramme. Beispiele: „Exportiere eine Woche Wohnzimmerverlauf als CSV“ oder „Zeichne Bürotemperatur und Sollwert über zwei Tage“.

Parameter: `entity_id`, `start_time`, `end_time` (ISO 8601 mit Zeitzone), `offset` (Standard 0) und `limit` (Standard 500, maximal 500). Ein Zeitraum umfasst höchstens 14 Tage; längere Zeiträume aufteilen. Alle Seiten mit `next_offset` und unveränderten Zeitgrenzen bis `null` abrufen. Ergebnisse enthalten `rows`, `total_rows`, `next_offset`, `pagination_complete`, UTC-Zeitstempel und verfügbare aufgezeichnete Attribute. Die Seitennavigation ist kein eingefrorener Recorder-Schnappschuss.

Nur weiterhin für Assist freigegebene VTherms sind mit einem authentifizierten Benutzer mit Leseberechtigung zugänglich. Punkte sind aufgezeichnete Änderungen und keine regelmäßigen Messungen; Recorder kann einen Zustand zum Periodenbeginn fortschreiben. Fehlende Felder bleiben `null`, und `unknown`/`unavailable` bleiben ausdrücklich erhalten. Aufbewahrung, Ausschlüsse und Ausfälle können die Daten begrenzen; vollständig abgerufene Seiten garantieren keinen vollständigen Verlauf. Der Client muss diese Grenzen nennen und darf fehlende Werte nicht erfinden. Es wird keine Konfiguration geändert.
