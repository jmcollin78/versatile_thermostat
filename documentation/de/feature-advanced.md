# Erweiterte Konfiguration

- [Erweiterte Konfiguration](#erweiterte-konfiguration)
  - [Warum diese Funktion?](#warum-diese-funktion)
  - [Sicherheitskontext](#sicherheitskontext)
  - [Funktionsprinzip des Sicherheitsmodus](#funktionsprinzip-des-sicherheitsmodus)
    - [Was ist der Sicherheitsmodus?](#was-ist-der-sicherheitsmodus)
    - [Wann wird er aktiviert?](#wann-wird-er-aktiviert)
    - [Einschränkungen](#einschränkungen)
  - [Konfiguration](#konfiguration)
  - [Sicherheitsparameter](#sicherheitsparameter)
  - [Verfügbare Attribute](#verfügbare-attribute)
  - [Verfügbare Aktionen](#verfügbare-aktionen)
  - [Erweiterte globale Konfiguration](#erweiterte-globale-konfiguration)
  - [Praktische Tipps](#praktische-tipps)
  - [Behebung von falschem Gerätezustand](#behebung-von-falschem-gerätezustand)
    - [Warum diese Funktion?](#warum-diese-funktion-1)
    - [Anwendungsfälle](#anwendungsfälle)
    - [Funktionsprinzip](#funktionsprinzip)
    - [Konfiguration](#konfiguration-1)
    - [Parameter](#parameter)
    - [Verfügbare Attribute](#verfügbare-attribute-1)
    - [Einschränkungen und Sicherheit](#einschränkungen-und-sicherheit)

## Warum diese Funktion?

Die erweiterte Konfiguration von _VTherm_ bietet grundlegende Tools, um die Sicherheit und Zuverlässigkeit Ihres Heizsystems zu gewährleisten. Diese Parameter ermöglichen es Ihnen, Situationen zu verwalten, in denen Temperatursensoren nicht mehr richtig kommunizieren, was zu gefährlichen oder unwirksamen Befehlen führen könnte.

## Sicherheitskontext

Das Fehlen oder die Fehlfunktion eines Temperatursensors kann **sehr gefährlich** für Ihr Zuhause sein. Betrachten Sie dieses konkrete Beispiel:

- Ihr Temperatursensor bleibt bei einem Wert von 10° stecken
- Ihr _VTherm_ vom Typ `over_climate` oder `over_valve` erkennt eine sehr niedrige Temperatur
- Es befiehlt maximales Heizen der zugrunde liegenden Geräte
- **Ergebnis**: der Raum überhitzt sich erheblich

Die Folgen können von einfachen Materialschäden bis hin zu schwereren Risiken wie Brand oder Explosion (bei einem fehlerhaften elektrischen Heizkörper) reichen.

## Funktionsprinzip des Sicherheitsmodus

### Was ist der Sicherheitsmodus?

Der Sicherheitsmodus ist ein Schutzmechanismus, der erkennt, wenn Temperatursensoren nicht mehr regelmäßig reagieren. Wenn ein Datenmangel erkannt wird, aktiviert _VTherm_ einen speziellen Modus, der:

1. **Sofortiges Risiko reduziert**: das System befiehlt nicht mehr maximale Leistung
2. **Minimale Heizung aufrechterhält**: stellt sicher, dass sich das Haus nicht übermäßig abkühlt
3. **Sie warnt**: durch Änderung des Thermostatzustandes, sichtbar in Home Assistant

### Wann wird er aktiviert?

Der Sicherheitsmodus wird aktiviert, wenn:

- **Innentemperatur fehlt**: seit der konfigurierten maximalen Verzögerung keine Messung empfangen
- **Außentemperatur fehlt**: seit der konfigurierten maximalen Verzögerung keine Messung empfangen (optional)
- **Sensor steckt**: der Sensor sendet keine Wertänderungen mehr (typisches Verhalten von batteriebetriebenen Sensoren)

Eine besondere Herausforderung stellen batteriebetriebene Sensoren dar, die nur Daten senden, wenn sich ein Wert **ändert**. Es ist daher möglich, stundenlang keine Updates zu erhalten, ohne dass der Sensor wirklich fehlerhaft ist. Deshalb sind die Parameter konfigurierbar, um die Erkennung an Ihre Einrichtung anzupassen.

### Einschränkungen

- **_VTherm_ vom Typ `over_climate` mit Selbstregulierung**: der Sicherheitsmodus ist automatisch deaktiviert. Es gibt kein Risiko, wenn sich das Gerät selbst regelt (es behält seine eigene Temperatur). Das einzige Risiko ist eine unbequeme Temperatur, kein physisches Risiko.

## Konfiguration

Um erweiterte Sicherheitsparameter zu konfigurieren:

1. Öffnen Sie die Konfiguration Ihres _VTherm_
2. Greifen Sie auf die Parameter der allgemeinen Konfiguration zu
3. Scrollen Sie nach unten zum Abschnitt "Erweiterte Konfiguration"

Das Formular für erweiterte Konfiguration sieht wie folgt aus:

![image](images/config-advanced.png)

> ![Tipp](images/tips.png) _*Ratschlag*_
>
> Wenn Ihr Thermometer ein Attribut `last_seen` oder ähnliches hat, das die Zeit des letzten Kontakts angibt, **konfigurieren Sie dieses Attribut** in den Hauptselektionen Ihres _VTherm_. Dies verbessert die Erkennung erheblich und reduziert falsche Warnungen. Siehe [Konfiguration der Basisattribute](base-attributes.md#auswahl-der-basisattribute) und [Fehlerbehebung](troubleshooting.md#warum-geht-mein-versatile-thermostat-in-den-sicherheitsmodus-) für weitere Details.

## Sicherheitsparameter

| Parameter | Beschreibung | Standardwert | Attributname |
| --- | --- | --- | --- |
| **Maximale Verzögerung vor Sicherheitsmodus** | Maximal zulässige Verzögerung zwischen zwei Temperaturmessungen, bevor _VTherm_ in den Sicherheitsmodus wechselt. Falls nach dieser Verzögerung keine neue Messung empfangen wird, wird der Sicherheitsmodus aktiviert. | 60 Minuten | `safety_delay_min` |
| **Minimaler `on_percent`-Schwellenwert für Sicherheit** | Mindestprozentsatz von `on_percent`, unter dem der Sicherheitsmodus nicht aktiviert wird. Dies verhindert die Aktivierung des Sicherheitsmodus, wenn der Heizkörper sehr wenig läuft (`on_percent` niedrig), da kein unmittelbares Überhitzungsrisiko besteht. `0.00` aktiviert immer den Modus, `1.00` deaktiviert ihn vollständig. | 0.5 (50%) | `safety_min_on_percent` |
| **Standard-`on_percent`-Wert im Sicherheitsmodus** | Die Heizleistung, die verwendet wird, wenn sich der Thermostat im Sicherheitsmodus befindet. `0` stoppt die Heizung vollständig (Gefrierrisiko), `0.1` behält minimale Heizung bei, um Gefrieren bei längerer Sensorausfallzeit zu verhindern. | 0.1 (10%) | `safety_default_on_percent` |

## Verfügbare Attribute

Wenn der Sicherheitsmodus aktiv ist, stellt _VTherm_ folgende Attribute bereit:

```yaml
safety_mode: "on"                # "on" oder "off"
safety_delay_min: 60             # Konfigurierte Verzögerung in Minuten
safety_min_on_percent: 0.5       # on_percent-Schwellenwert (0.0 bis 1.0)
safety_default_on_percent: 0.1   # Leistung im Sicherheitsmodus (0.0 bis 1.0)
last_safety_event: "2024-03-20 14:30:00"  # Zeitpunkt des letzten Ereignisses
```

## Verfügbare Aktionen

Eine _VTherm_-Aktion ermöglicht die dynamische Neukonfiguration der 3 Sicherheitsparameter ohne Neustart von Home Assistant:

- **Service**: `versatile_thermostat.set_safety_parameters`
- **Parameter**:
  - `entity_id`: der _VTherm_ zum Neukonfigurieren
  - `safety_delay_min`: neue Verzögerung (Minuten)
  - `safety_min_on_percent`: neuer Schwellenwert (0.0 bis 1.0)
  - `safety_default_on_percent`: neue Leistung (0.0 bis 1.0)

Dies ermöglicht die dynamische Anpassung der Empfindlichkeit des Sicherheitsmodus entsprechend Ihrer Nutzung (z. B. Verzögerung reduzieren, wenn Menschen zu Hause sind, oder erhöhen, wenn das Haus leer ist).

## Erweiterte globale Konfiguration

Es ist möglich, die Überprüfung des **Außenthermometers** für den Sicherheitsmodus zu deaktivieren. Der Außensensor hat generell wenig Auswirkungen auf die Regelung (je nach Einstellung) und kann abwesend sein, ohne die Sicherheit des Hauses zu gefährden.

Fügen Sie dazu die folgenden Zeilen in Ihre `configuration.yaml` ein:

```yaml
versatile_thermostat:
  safety_mode:
    check_outdoor_sensor: false
```

> ![Wichtig](images/tips.png) _*Wichtig*_
>
> - Diese Änderung ist **für alle _VTherm_** im System gemeinsam
> - Sie beeinflusst die Erkennung des Außenthermometers für alle Thermostate
> - **Home Assistant muss neu gestartet werden**, damit die Änderungen wirksam werden
> - Standardmäßig kann das Außenthermometer den Sicherheitsmodus auslösen, wenn es keine Daten mehr sendet

## Praktische Tipps

> ![Tipp](images/tips.png) _*Hinweise und Best Practices*_

1. **Wiederherstellung nach Korrektur**: Wenn der Temperatursensor wieder zum Leben erwacht und Daten sendet, wird der Voreinstellungsmodus auf seinen vorherigen Wert zurückgesetzt.

2. **Zwei Temperaturen erforderlich**: Das System benötigt sowohl die Innen- als auch die Außentemperatur, um richtig zu funktionieren. Wenn eine der beiden fehlt, wechselt der Thermostat in den Sicherheitsmodus.

3. **Beziehung zwischen Parametern**: Für natürliches Verhalten sollte der Wert `safety_default_on_percent` **kleiner als** `safety_min_on_percent` sein. Beispielsweise: `safety_min_on_percent = 0.5` und `safety_default_on_percent = 0.1`.

4. **Anpassung an Ihren Sensor**:
   - Bei **falschen Warnungen** die Verzögerung (`safety_delay_min`) erhöhen oder `safety_min_on_percent` verringern
   - Bei batteriebetriebenen Sensoren die Verzögerung weiter erhöhen (z. B.: 2-4 Stunden)
   - Bei Verwendung des Attributs `last_seen` kann die Verzögerung verkürzt werden (das System ist genauer)

5. **Visualisierung in der Benutzeroberfläche**: Wenn Sie die [_Versatile Thermostat UI_-Karte](additions.md#besser-mit-der-versatile-thermostat-ui-card) verwenden, wird ein _VTherm_ im Sicherheitsmodus visuell angezeigt durch:
   - Einen gräulichen Schleier über dem Thermostat
   - Anzeige des fehlerhaften Sensors
   - Verstrichene Zeit seit der letzten Aktualisierung

   ![Sicherheitsmodus](images/safety-mode-icon.png).

## Behebung von falschem Gerätezustand

### Warum diese Funktion?

Bei der Verwendung eines _VTherm_ mit Heizgeräten (`over_switch`, `over_valve`, `over_climate`, `over_climate_valve`) kann es vorkommen, dass das Gerät dem vom Thermostat gesendeten Befehl nicht richtig folgt. Zum Beispiel:

- Ein klemmender Schalter, der nicht in den befohlenen Zustand wechselt
- Ein thermostatisches Ventil, das Befehle nicht beachtet
- Ein vorübergehender Kommunikationsverlust mit dem Gerät
- Geräte, die zu lange brauchen, um zu reagieren

Die Funktion **"Falschen Status reparieren"** erkennt diese Situationen und sendet den Befehl automatisch erneut, um den aktuellen Zustand mit dem gewünschten Zustand zu synchronisieren.

### Anwendungsfälle

Diese Funktion ist besonders nützlich für:

- **Instabile Relais**: Relais, die haften oder nicht immer richtig wechseln
- **Intermittierende Zigbee/WiFi-Kommunikation**: Geräte, die gelegentlich die Verbindung verlieren
- **Langsame Ventile**: thermostatische Ventile, die langsam auf Befehle reagieren
- **Fehlerhafte Geräte**: Elektroradiatoren oder Ventile, die nicht mehr auf Befehle reagieren
- **Wärmepumpen**: um sicherzustellen, dass die Wärmepumpe Heiz-/Kühlbefehle richtig ausführt

### Funktionsprinzip

Bei jedem Thermostat-Regelzyklus führt die Funktion folgende Schritte durch:

1. **Vergleicht Zustände**: überprüft, ob der tatsächliche Zustand jedes Geräts mit dem befohlen Zustand übereinstimmt
2. **Erkennt Abweichungen**: wenn das Gerät dem Befehl nicht folgte, ist das eine Abweichung
3. **Sendet den Befehl erneut**: wenn eine Abweichung erkannt wird, sendet es den Befehl erneut, um den Zustand zu synchronisieren
4. **Zählt Versuche**: die Anzahl der Reparaturen wird begrenzt, um Endlosschleifen zu vermeiden
5. **Steuert die Aktivierungsverzögerung**: die Funktion wird nur nach einer Mindestverzögerung aktiviert, damit die Geräte ihre Initialisierung abschließen können

### Konfiguration

Diese Funktion wird in der _VTherm_-Konfigurationsoberfläche konfiguriert:

1. Öffnen Sie Ihre _VTherm_-Konfiguration
2. Greifen Sie auf die Parameter der allgemeinen Konfiguration zu
3. Scrollen Sie nach unten zum Abschnitt "Erweiterte Konfiguration"
4. Aktivieren Sie die Option **"Falschen Gerätezustand reparieren"**

### Parameter

| Parameter | Beschreibung | Standardwert |
| --- | --- | --- |
| **Falschen Status reparieren** | Aktiviert oder deaktiviert die automatische Erkennung und Reparatur von Zustandsabweichungen. Wenn aktiviert, wird bei jeder erkannten Abweichung der Befehl erneut gesendet. | Deaktiviert |

> ![Tipp](images/tips.png) _*Interne Systemparameter*_
>
> Einige Parameter werden auf Systemebene konfiguriert und können nicht geändert werden:
> - **Mindestverzögerung vor Aktivierung**: 30 Sekunden nach dem Start des Thermostats (ermöglicht allen Geräten, zu initialisieren)
> - **Maximale aufeinanderfolgende Versuche**: 5 aufeinanderfolgende Reparaturen vor temporärem Stopp
> - **Zurücksetzverzögerung**: der Reparaturzähler wird zurückgesetzt, sobald Geräte den korrekten Zustand wieder erreichen

### Verfügbare Attribute

Wenn die Reparaturfunktion aktiviert ist, stellt _VTherm_ das folgende Attribut bereit:

```yaml
repair_incorrect_state_manager:
  consecutive_repair_count: 2       # Anzahl der durchgeführten Reparaturen
  max_attempts: 5                   # Grenzwert vor temporärem Stopp
  min_delay_after_init_sec: 30      # Mindestverzögerung vor Aktivierung
is_repair_incorrect_state_configured: true  # Funktionsstatus
```

Der Zähler `consecutive_repair_count` ermöglicht es Ihnen:
- Häufige Hardwareprobleme zu diagnostizieren
- Fehlerhafte Geräte zu identifizieren
- Die Stabilität Ihrer Anlage zu überwachen

### Einschränkungen und Sicherheit

> ![Wichtig](images/tips.png) _*Wichtig*_

1. **Keine Verhaltensänderung**: Diese Funktion ändert nicht die Heizlogik. Sie stellt lediglich sicher, dass Ihre Befehle ordnungsgemäß ausgeführt werden.

2. **Sicherheitsgrenzen**: Die maximalen aufeinanderfolgenden Versuche (5) verhindern Endlosschleifen. Wenn diese Grenze erreicht wird, wird ein Fehler protokolliert und die Reparaturen werden vorübergehend gestoppt.

3. **Startverzögerung**: Die Funktion wird erst nach 30 Sekunden aktiviert, um allen Geräten Zeit zur vollständigen Initialisierung zu geben.

4. **Für alle _VTherm_-Typen anwendbar**: Diese Funktion funktioniert für alle Typen `over_switch`, `over_valve`, `over_climate` und `over_climate_valve` (die `over_climate` mit direkter Ventilregelung). Für letztere wird der Zustand des zugrunde liegenden `climate` sowie der Ventilöffnungszustand überprüft.

5. **Symptome von Überaktivität**: Wenn Sie regelmäßig Warnmeldungen über Reparaturen sehen, deutet dies auf ein Hardwareproblem hin:
   - Überprüfen Sie die Geräteverbindung
   - Überprüfen Sie die Netzwerkstabilität (Zigbee/WiFi)
   - Testen Sie das Gerät manuell über Home Assistant
   - Erwägen Sie den Austausch bei anhaltendem Problem

6. **Zähler zurücksetzen**: Der Zähler wird automatisch zurückgesetzt, sobald die Geräte den korrekten Zustand wieder erreichen, was neue Versuche bei intermittierenden Problemen ermöglicht.

7. **Regelmäßige Wiederholung**: Nach 5 fehlgeschlagenen Reparaturversuchen wird die Reparatur unterbrochen, um Endlosschleifen zu vermeiden. Sie wird nach 10 Zyklen ohne Reparatur wiederaufgenommen und ermöglicht neue Versuche bei intermittierenden Problemen.
