# Sperrfunktion

## Überblick

Die Sperrfunktion verhindert Änderungen an einem Thermostat über die Benutzeroberfläche oder Automatisierungen, während der Thermostat weiterhin funktioniert.

## Konfiguration

Die Sperrfunktion wird in den Thermostateinstellungen im Abschnitt "Sperren" konfiguriert. Sie können Folgendes sperren:

- **Benutzer**: Verhindert Änderungen über die Home Assistant-Benutzeroberfläche.
- **Automatisierungen & Integrationen**: Verhindert Änderungen durch Automatisierungen, Skripte und andere Integrationen.

Sie können auch einen optionalen **Sperrcode** konfigurieren:

- **Sperrcode**: Ein 4-stelliger numerischer PIN-Code (z. B. "1234"). Wenn gesetzt, ist dieser Code erforderlich, um den Thermostat zu sperren/zu entsperren. Dies ist optional und wenn nicht konfiguriert, ist kein Code erforderlich.

Sie können auch eine zentrale Konfiguration für die Sperreinstellungen verwenden.

## Verwendung

Verwenden Sie diese Dienste, um den Sperrzustand zu steuern:

- `versatile_thermostat.lock` - Sperrt den Thermostat
- `versatile_thermostat.unlock` - Entsperrt den Thermostat (erfordert `code` falls konfiguriert)

Beispiel für eine Automatisierung:

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

Beispiel für eine Entsperrungsautomatisierung mit Code:

```yaml
service: versatile_thermostat.unlock
target:
  entity_id: climate.my_thermostat
data:
  code: "1234"
```

## Sperrzustand

Der Sperrzustand ist:

- Sichtbar in den Attributen `is_locked`, `lock_users` und `lock_automations` der Klimaentität
- Wird bei Neustarts von Home Assistant beibehalten (einschließlich PIN-Code, falls gesetzt)
- Pro Thermostat (jeder Thermostat hat seine eigene Sperre und optionalen PIN-Code)

## Im gesperrten Zustand

**Blockiert (von UI / Automatisierungen / externen Aufrufen):**

- Änderungen des HLK-Modus (einschließlich Ein/Aus)
- Änderungen der Ziel-Temperatur
- Änderungen von Voreinstellungen und VTherm Voreinstellungs-Konfigurationsdiensten
- Änderungen des Anwesenheitsstatus über VTherm-Dienste
- Änderungen der Sicherheitskonfiguration über VTherm-Dienste
- Änderungen der Fensterumgehung über VTherm-Dienste
- Lüfter-/Schwenk-/Lüftungsmodi, wenn sie von VTherm bereitgestellt werden

**Erlaubt (interne VTherm-Logik, immer aktiv):**

- Fenstererkennung und -aktionen (Ausschalten oder Eco/Frost bei Öffnen, nur Lüfter, falls zutreffend, Wiederherstellung des Verhaltens bei Schließen)
- Schutzmaßnahmen (z. B. Überhitzungs- / Frostschutz-Voreinstellungen, Sicherheits-Ein/Aus-Handhabung)
- Energie- und Überleistungsmanagement (einschließlich des `PRESET_POWER`-Verhaltens)
- Automatische Regelungsalgorithmen (TPI / PI / PROP) und Regelkreis
- Zentrale/Eltern/Kind-Koordination und andere interne VTherm-Automatisierungen

**Verhaltensgarantie:**

- Fensteraktionen (z. B. Ausschalten bei Öffnen, Wiederherstellen bei Schließen) funktionieren auch bei gesperrtem Thermostat.

**Implementierungshinweis:**

- Die Sperre wird bei externen Aufrufen erzwungen, die die einzige Quelle für `requested_state`-Änderungen sind. Interne VTherm-Operationen (wie `SafetyManager` oder `PowerManager`) umgehen die Sperre, da `StateManager` deren Ausgabe gegenüber externen Anfragen priorisiert. Die Sperre verhindert nur, dass externe Aufrufe den `requested_state` modifizieren.

## Anwendungsfälle

- Verhindern von versehentlichen Änderungen während kritischer Perioden
- Kindersicherung-Funktionalität
- Temporäres Verhindern, dass der Scheduler aktuelle Einstellungen ändert
- Sicherheit gegen unbefugtes Entsperren (mit PIN-Code)