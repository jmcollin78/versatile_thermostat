# Frühere Protokolle herunterladen - Diagnose und Fehlerbehebung

- [Frühere Protokolle herunterladen - Diagnose und Fehlerbehebung](#frühere-protokolle-herunterladen---diagnose-und-fehlerbehebung)
  - [Warum Protokolle abrufen?](#warum-protokolle-abrufen)
  - [Zugriff auf diese Funktion](#zugriff-auf-diese-funktion)
  - [Aktion aus Home Assistant ausführen](#aktion-aus-home-assistant-ausführen)
    - [Option 1: Über die Benutzeroberfläche (UI)](#option-1-über-die-benutzeroberfläche-ui)
    - [Option 2: Aus einem Skript oder einer Automatisierung](#option-2-aus-einem-skript-oder-einer-automatisierung)
  - [Verfügbare Parameter](#verfügbare-parameter)
    - [Erklärung der Protokollstufen](#erklärung-der-protokollstufen)
  - [Datei empfangen und herunterladen](#datei-empfangen-und-herunterladen)
  - [Format und Inhalt der Protokolldatei](#format-und-inhalt-der-protokolldatei)
  - [Praktische Beispiele](#praktische-beispiele)
    - [Beispiel 1: Abnormale Temperatur über 30 Minuten debuggen](#beispiel-1-abnormale-temperatur-über-30-minuten-debuggen)
    - [Beispiel 2: Überprüfung der korrekten Erfassung der Anwesenheit](#beispiel-2-überprüfung-der-korrekten-erfassung-der-anwesenheit)
    - [Beispiel 3: Überprüfung aller Thermostaten über einen kurzen Zeitraum](#beispiel-3-überprüfung-aller-thermostaten-über-einen-kurzen-zeitraum)
  - [Erweiterte Konfiguration](#erweiterte-konfiguration)
  - [Nutzungstipps](#nutzungstipps)

## Warum Protokolle abrufen?

Versatile Thermostat-Protokolle (_Ereignisjournale_) zeichnen alle Änderungen und Aktionen auf, die vom Thermostat durchgeführt werden. Sie sind nützlich für:

- **Diagnose einer Fehlfunktion**: Verstehen, warum sich der Thermostat nicht wie erwartet verhält
- **Analyse abnormaler Verhalten**: Überprüfung von Thermostat-Entscheidungen über einen bestimmten Zeitraum
- **Fehlerbehebung einer Konfiguration**: Validierung, dass Sensoren und Aktionen ordnungsgemäß erkannt werden
- **Meldung eines Problems**: Bereitstellung einer Verlaufsangabe für Entwickler zur Unterstützung beim Debugging

Die **Log-Download**-Funktion bietet eine einfache Möglichkeit, Protokolle aus einem bestimmten Zeitraum abzurufen und nach Ihren Anforderungen zu filtern.

**Hilfreicher Tipp**: Wenn Sie Support anfordern, müssen Sie Protokolle von dem Zeitpunkt sichern, an dem Ihr Problem aufgetreten ist. Die Verwendung dieser Funktion wird empfohlen, da Protokolle unabhängig von der in Home Assistant konfigurierten Protokollebene erfasst werden (im Gegensatz zum nativen Home Assistant-Logging-System).

## Zugriff auf diese Funktion

Die Aktion `versatile_thermostat.download_logs` ist in Home Assistant verfügbar über:

1. **Automatisierungen** (Skripte > Automatisierungen)
2. **Skripte** (Skripte > Skripte)
3. **Entwickler-Steuerungen** (Einstellungen > Entwickler-Tools > Services)
4. **Die Steueroberfläche bestimmter Integrationen** (abhängig von Ihrer Home Assistant-Version)

## Aktion aus Home Assistant ausführen

### Option 1: Über die Benutzeroberfläche (UI)

So führen Sie die Aktion über Entwickler-Tools aus:

1. Gehen Sie zu **Einstellungen** → **Entwickler-Tools**
2. Registerkarte **Aktionen** (früher **Services** genannt) → wählen Sie `versatile_thermostat: Download logs`
3. Füllen Sie die gewünschten Parameter aus (siehe unten)
4. Klicken Sie auf **Service ausführen**

Danach wird eine **persistente Benachrichtigung** mit einem Download-Link für die Datei angezeigt.

### Option 2: Aus einem Skript oder einer Automatisierung

Beispielaufruf in einer Automatisierung oder einem YAML-Skript:

```yaml
action: versatile_thermostat.download_logs
metadata: {}
data:
  entity_id: climate.wohnzimmer        # Optional: durch Ihren Thermostat ersetzen
  log_level: INFO                      # Optional: DEBUG (Standard), INFO, WARNING, ERROR
  period_start: "2025-03-14T08:00:00"  # Optional: ISO-Format (datetime)
  period_end: "2025-03-14T10:00:00"    # Optional: ISO-Format (datetime)
```

## Verfügbare Parameter

| Parameter      | Erforderlich? | Mögliche Werte                      | Standard              | Beschreibung                                                                 |
| -------------- | ------------- | ----------------------------------- | --------------------- | ---------------------------------------------------------------------------- |
| `entity_id`    | Nein          | `climate.xxx` oder nicht vorhanden  | Alle VTherm           | Gezielter spezifischer Thermostat. Falls nicht vorhanden, alle Thermostaten. |
| `log_level`    | Nein          | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `DEBUG`               | Minimales Schweregrad-Level. Alle Protokolle auf dieser Ebene und darüber.   |
| `period_start` | Nein          | ISO datetime (z.B. `2025-03-14...`) | Vor 60 Minuten        | Beginn des Extraktionszeitraums. ISO-Format mit Datum und Uhrzeit.           |
| `period_end`   | Nein          | ISO datetime (z.B. `2025-03-14...`) | Jetzt (aktuelle Zeit) | Ende des Extraktionszeitraums. ISO-Format mit Datum und Uhrzeit.             |

### Erklärung der Protokollstufen

- **DEBUG**: Detaillierte Diagnosemeldungen (TPI-Berechnungsgeschwindigkeit, Zwischenwerte, etc.). Sehr ausführlich.
- **INFO**: Allgemeine Informationen (Zustandsänderungen, Thermostaten-Entscheidungen, Feature-Aktivierungen).
- **WARNING**: Warnungen (Vorbedingungen nicht erfüllt, abnormale Werte erkannt).
- **ERROR**: Fehler (Sensorfehler, nicht behandelte Ausnahmen).

**Tipp**: Beginnen Sie mit `INFO` für die erste Analyse, wechseln Sie dann zu `DEBUG`, wenn Sie mehr Details benötigen.

## Datei empfangen und herunterladen

Nach dem Aufruf der Aktion wird eine **persistente Benachrichtigung** angezeigt, die Folgendes enthält:

- Eine Zusammenfassung des Exports (Thermostat, Zeitraum, Stufe, Anzahl der Einträge)
- Eine **Download-URL** zum Kopieren/Einfügen in Ihren Browser

Die URL ist ein **absoluter signierter Link** (mit einem 24 Stunden gültigen Authentifizierungstoken). Aufgrund einer Einschränkung des Home Assistant-Frontends **kann der Link nicht direkt angeklickt werden** — Sie müssen ihn **kopieren und einfügen** in einen neuen Browser-Tab, um den Download auszulösen.

Die heruntergeladene Datei ist eine `.log`-Datei, z.B.:
```
vtherm_logs_wohnzimmer_20250314_102500.log
```

Die Datei wird vorübergehend auf Ihrem Home Assistant-Server im über das lokale Netzwerk erreichbaren Ordner gespeichert (unter `config/www/versatile_thermostat/`).

> **Hinweis**: Alte Protokolldateien (> 24h) werden automatisch vom Server gelöscht.

> **Wichtig**: Damit die Download-URL korrekt ist, müssen Sie Ihre interne oder externe URL unter **Einstellungen > System > Netzwerk** in Home Assistant konfigurieren. Andernfalls kann die URL die interne IP-Adresse des Docker-Containers enthalten.

## Format und Inhalt der Protokolldatei

Die Datei enthält:

1. **Ein Header** mit Exportinformationen:
   ```
   ================================================================================
   Versatile Thermostat - Log Export
   Thermostat : Wohnzimmer (climate.wohnzimmer)
   Period     : 2025-03-14 08:00:00 → 2025-03-14 10:00:00 UTC
   Level      : INFO and above
   Entries    : 342
   Generated  : 2025-03-14 10:25:03 UTC
   ================================================================================
   ```

2. **Protokolleinträge**, eine pro Zeile, mit:
   - Zeitstempel (Datum + UTC-Zeit)
   - Stufe (`[INFO]`, `[DEBUG]`, `[WARNING]`, `[ERROR]`)
   - Name des Python-Moduls (wo das Protokoll generiert wurde)
   - Meldung

Beispieleintrag:
```
2025-03-14 08:25:12.456 INFO    [base_thermostat    ] Wohnzimmer - Current temperature is 20.5°C
2025-03-14 08:30:00.001 INFO    [prop_algo_tpi      ] Wohnzimmer - TPI calculated on_percent=0.45
2025-03-14 08:30:00.123 WARNING [safety_manager     ] Wohnzimmer - No temperature update for 35 min
```

Sie können diese Datei dann **analysieren** mit:
- Einem Standard-Texteditor
- Einem Python-Skript zur Datenverarbeitung
- Einem Tool wie `grep`, `awk`, `sed`, etc. zur manuellen Filterung

## Praktische Beispiele

### Beispiel 1: Abnormale Temperatur über 30 Minuten debuggen

**Ziel**: Verstehen, warum der Wohnzimmer-Thermostat seine Temperatur schlecht verwaltet.

**Aktion zum Ausführen**:
```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.wohnzimmer
  log_level: DEBUG              # Wir möchten alle Details
  period_start: "2025-03-14T14:00:00"
  period_end: "2025-03-14T14:30:00"
```

**Dateianalyse**:
- Suchen Sie nach „Current temperature", „Target temperature", um die Entwicklung zu sehen
- Suchen Sie nach „TPI calculated", um die Berechnung des Aktivierungsprozentsatzes zu sehen
- Suchen Sie nach „WARNING" oder „ERROR", um Anomalien zu identifizieren

---

### Beispiel 2: Überprüfung der korrekten Erfassung der Anwesenheit

**Ziel**: Überprüfung, dass der Anwesenheitssensor den Thermostaten-Status korrekt geändert hat.

**Aktion zum Ausführen**:
```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.buero
  log_level: INFO
  period_start: "2025-03-15T12:00:00"      # Beginn des Zeitraums (ISO-Format)
  period_end: "2025-03-15T14:00:00"        # Ende des Zeitraums
```

**Dateianalyse**:
- Suchen Sie nach Meldungen mit „presence" oder „motion"
- Überprüfen Sie, dass Preset-Änderungen ordnungsgemäß protokolliert werden

---

### Beispiel 3: Überprüfung aller Thermostaten über einen kurzen Zeitraum

**Ziel**: Abrufen einer globalen Verlaufsangabe aller Thermostaten für eine Stunde, gefiltert auf Warnungen und Fehler.

**Aktion zum Ausführen**:
```yaml
action: versatile_thermostat.download_logs
data:
  log_level: WARNING            # Keine entity_id → alle VTherm
  period_start: "2025-03-15T13:00:00"
  period_end: "2025-03-15T14:00:00"
```

**Dateianalyse**:
- Die Datei enthält alle WARNING- und ERROR-Protokolle von allen Thermostaten
- Nützlich, um zu überprüfen, dass keine abnormalen Benachrichtigungen aufgetreten sind

---

## Erweiterte Konfiguration

Standardmäßig werden Protokolle **4 Stunden** lang im Speicher auf Ihrem Home Assistant-Server gespeichert. Sie können diese Dauer in `configuration.yaml` anpassen:

```yaml
versatile_thermostat:
  log_buffer_max_age_hours: 6   # Protokolle 6 Stunden statt 4 beibehalten
```

Sie können **jede positive ganze Zahl** (in Stunden) nach Bedarf angeben. Hier sind einige Beispiele mit einer Schätzung des Speicherverbrauchs:

| Dauer    | 10 VTherm-Szenario    | 20 VTherm-Szenario    |
| -------- | --------------------- | --------------------- |
| **1 h**  | ~0,5-1 MB             | ~2-5 MB               |
| **2 h**  | ~1-2 MB               | ~4-10 MB              |
| **4 h**  | ~2-5 MB               | ~8-20 MB              |
| **6 h**  | ~3-7 MB               | ~12-30 MB             |
| **8 h**  | ~4-10 MB              | ~16-40 MB             |
| **24 h** | Begrenzt auf 40-50 MB | Begrenzt auf 40-50 MB |

> **Hinweis**: Eine Erhöhung der Aufbewahrungsdauer verbraucht mehr Speicher auf Ihrem Server. Ein automatischer Schutz begrenzt den Gesamtverbrauch auf max. ~40-50 MB.

---

## Nutzungstipps

1. **Beginnen Sie mit INFO-Level**: Weniger Lärm, leichter zu lesen
2. **Gezielter spezifischer Thermostat**: Relevanter als alle VTherm
3. **Zeitraum reduzieren**: Laden Sie anstelle von 24h nur den problematischen Zeitraum herunter
4. **Verwenden Sie die Website zur Analyse**: Die [Versatile Thermostat-Website](https://www.versatile-thermostat.org/) ermöglicht es Ihnen, Ihre Protokolle zu analysieren und Kurven darzustellen. Sie ist eine wesentliche Ergänzung zu dieser Funktion
5. **Nutzen Sie Verarbeitungstools**: `grep`, `sed`, `awk` oder Python zur Analyse großer Dateien
6. **Header beibehalten**: Nützlich, um Kontexte bei Problemmeldung bereitzustellen

---
