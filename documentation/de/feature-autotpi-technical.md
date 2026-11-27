# 🧠 Auto TPI: Detaillierter technischer Leitfaden

> [!NOTE]
> Dieses Dokument richtet sich an fortgeschrittene Benutzer, die verstehen möchten, wie Auto TPI funktioniert. Für eine einfachere Einführung siehe den [Auto TPI Benutzerleitfaden](feature-autotpi.md).

---

## Inhaltsverzeichnis

1. [Der TPI-Algorithmus](#der-tpi-algorithmus)
2. [Raummodell und Zielkoeffizienten](#raummodell-und-zielkoeffizienten)
3. [Lernzyklus](#lernzyklus)
4. [Kint-Lernen](#kint-lernen)
5. [Kext-Lernen](#kext-lernen)
6. [Kontinuierliches Kext-Lernen](#kontinuierliches-kext-lernen)
7. [Parameter und Konstanten](#parameter-und-konstanten)
8. [Dienste und API](#dienste-und-api)
9. [Diagnose und Fehlerbehebung](#diagnose-und-fehlerbehebung)

---

## Der TPI-Algorithmus

### Grundprinzip

Der **TPI**-Algorithmus (Time Proportional & Integral) berechnet bei jedem Zyklus einen **Leistungsprozentsatz**. Dieser Prozentsatz bestimmt, wie lange die Heizung während des Zyklus aktiv ist (z. B. 60 % bei einem 10-Minuten-Zyklus = 6 Minuten Heizen).

### Grundformel

```
Power = (Kint × ΔT_indoor) + (Kext × ΔT_outdoor)
```

Dabei gilt:
- **Kint** (`tpi_coef_int`): Innenkoeffizient, reagiert auf die Abweichung zum Sollwert
- **Kext** (`tpi_coef_ext`): Außenkoeffizient, kompensiert thermische Verluste
- **ΔT_indoor** = Sollwert − Innentemperatur
- **ΔT_outdoor** = Sollwert − Außentemperatur

Die Leistung ist auf 0–100 % begrenzt. Im Kühlbetrieb sind die Differenzen umgekehrt.

### Rolle der Koeffizienten

| Koeffizient | Rolle | Lernsituation |
|-------------|------|-------------------|
| **Kint** | Legt die **Reaktivität** fest: Je höher er ist, desto stärker reagiert die Heizung auf eine Abweichung | Während eines **Temperaturanstiegs** (Abweichung ≥ 0,3 °C zu Beginn eines Fensters, Leistung zwischen 0 und 100 %) |
| **Kext** | Kompensiert die **Wärmeverluste**: Er liefert die Leistung, die zum Halten des Sollwerts nötig ist | Wenn der Raum **nahe am Sollwert eingeschwungen** ist |

---

## Raummodell und Zielkoeffizienten

Auto TPI stützt sich auf ein einfaches Raummodell (eine thermische Kapazität, ein Verlust nach außen):

```
dT/dt = a × P − b × (T − T_ext)
```

- `a` (°C/h): Anstiegsrate der Temperatur bei 100 % Leistung ohne Verluste
- `b` (1/h): Verlustrate, Kehrwert der Zeitkonstante des Raumes
- `P`: Heizleistung (0–1)

**Kext**: Am Sollwert beträgt die benötigte Leistung `P = (b/a) × (Setpoint − T_ext)`. Der ideale Kext ist somit `b/a`. Mit diesem Wert hält allein der Außenanteil den Sollwert, und es bleibt keine statische Abweichung übrig.

**Kint**: Sobald Kext die Verluste kompensiert, steigt der Raum mit `a × Kint × Abweichung`. Um die Abweichung mit der Zeitkonstante `T_cl` zu schließen, muss Kint `1 / (a × T_cl)` betragen. Ein schwacher Heizkörper (kleines `a`) braucht daher ein größeres Kint.

`T_cl` ist die Ziel-Zeitkonstante des geschlossenen Regelkreises. Sie wird aus der **Heizzeit** des Heizkörpers abgeleitet:

```
T_cl = 2 × (heating_time + cycle / 2)     begrenzt auf [30 min, 180 min]
```

Ein träger Heizkörper (lange Heizzeit) ergibt ein größeres `T_cl`, also eine sanftere Regelung ohne Overshoot.

Weder `a` noch `b` muss bekannt sein: Beide Koeffizienten werden aus Beobachtungen in kleinen Schritten in Richtung dieser Ziele gelernt.

---

## Lernzyklus

Am Ende jedes TPI-Zyklus prüft der Manager den Zyklus und aktualisiert das Lernen.

### Zyklus-Snapshot

Zu Beginn jedes Zyklus zeichnet das System Innen- und Außentemperatur, Sollwert, Leistung und HVAC-Modus auf. Am Ende des Zyklus wird die tatsächlich angewendete Leistung (nach zeitlichen Einschränkungen) verwendet.

### Gültigkeitsbedingungen eines Zyklus

Ein Zyklus wird für das Lernen ignoriert, wenn:

| Bedingung | Grund |
|-----------|--------|
| Leistung ≤ 0 % oder ≥ 100 % | Ein gesättigter Zyklus sagt nichts über die anzuwendende Leistung aus |
| Zyklus kürzer oder länger als erwartet | Unterbrochener Zyklus oder Lücke in den Daten |
| Leistungsabschaltung während des Zyklus | Die Heizung wurde durch ein anderes Feature begrenzt |
| Zentralkessel aus | Der Heizkörper hat nicht geheizt |
| Heizungsausfall erkannt | Der Heizkörper hat nicht wie angefordert geheizt |
| Erster Zyklus nach einem Stopp | Kein vorheriger Zustand vorhanden |
| Sollwert während des Zyklus geändert | Der Zyklus vermischt zwei Ziele |
| \|Sollwert − T_ext\| < 1 °C (Kext) | Der Außenanteil ist zu klein, um gelernt zu werden |

### Ende der Sitzung

Die Sitzung endet, wenn Kint über **15 Fenster** und Kext über **50 Zyklen** gelernt wurde. Die Koeffizienten werden dann in die Konfiguration geschrieben und eine Benachrichtigung wird gesendet.

---

## Kint-Lernen

Kint wird über **Fenster** aus mehreren aufeinanderfolgenden Zyklen gelernt, niemals über einen einzelnen Zyklus: Bei einem 5-Minuten-Zyklus liegt die Temperaturänderung in der gleichen Größenordnung wie die Auflösung des Sensors (oft 0,1 °C).

### Fensterregeln

- Ein Fenster öffnet sich, wenn der Raum mindestens **0,3 °C** vom Sollwert entfernt ist, und erst **T_cl / 2** nach der letzten Sollwertänderung, Modusänderung, einem Zyklus bei 0 % oder einem ungültigen Zyklus (der Heizkörper braucht diese Zeit, um zu reagieren). Ein Zyklus bei 100 % schließt das Fenster, ohne diese Verzögerung neu zu starten: Der Heizkörper läuft bereits.
- Jeder Zyklus des Fensters muss gültig sein, mit einer Leistung zwischen 0 und 100 %. Andernfalls wird das Fenster ohne Lernen geschlossen.
- Die Fensterdauer wird beim Öffnen anhand der Anstiegsgeschwindigkeit der vorangegangenen 20 Minuten festgelegt, sodass das Fenster etwa 0,3 °C Änderung erfasst: zwischen 10 Minuten (und mindestens 2 Zyklen) bei schnellem Anstieg und **max(30 min, T_cl)** bei langsamem Anstieg. Es verwendet nur Daten, die älter als das Fenster sind, und hängt daher nie von der Änderung ab, die das Fenster misst. Das nächste Fenster beginnt dort, wo das vorherige endet, unter derselben 0,3-°C-Bedingung.
- Ein Fenster wird nur anhand seiner Dauer und seiner Anfangsabweichung akzeptiert. Es hängt niemals von der gemessenen Temperaturänderung ab: Andernfalls würden nur die Fenster behalten, in denen Rauschen den Anstieg verstärkt hat, was Kint verfälschen würde.

### Aktualisierungsformel

```
mean_gap    = Setpoint − (T_start + T_end) / 2
target_rate = mean_gap / T_cl
rate        = (T_end − T_start) / duration
ratio       = target_rate / rate          (1.15 if rate ≤ 0)
Kint_new    = Kint × clamp(ratio, 1/1.15, 1.15)
```

Kint ändert sich pro Fenster um höchstens ±15 % und bleibt im Bereich [0.01, 1.0]. Ein begrenzter Schritt konvergiert zum Median des Verhältnisses: Ein einzelnes Fenster, das durch Rauschen oder Sonne gestört ist, kann Kint nicht stark verschieben.

Hat der Raum während des Fensters den Sollwert überschritten (`mean_gap ≤ 0`), wird das Fenster nicht verwendet.

---

## Kext-Lernen

### Einschwingbedingung

Der Anstieg nach einer Sollwertänderung gehört zu Kint. Kext wird nur gelernt:
- mindestens **3 × T_cl** nach der letzten Sollwertänderung,
- und sobald der Raum wieder innerhalb von **0,3 °C** des Sollwerts liegt, oder nach **12 × T_cl**, damit ein sehr falscher Kext (große statische Abweichung) trotzdem korrigiert werden kann.

### Formel

Wenn der Raum eingeschwungen ist und die Abweichung klein ist (|Abweichung| ≤ 1 °C, oder jede Abweichung über dem Sollwert bei einer Leistung von mindestens 10 %):

```
Kext_target = Kext + Kint × (ΔT_indoor / ΔT_outdoor)
```

Die verbleibende Innenabweichung wird in die Außenleistung umgerechnet, die sie beseitigen würde. Kext_target ist auf 1.2 begrenzt.

Proben über dem Sollwert werden bei sehr niedriger Leistung ignoriert (der Raum kühlt sich natürlich ab oder wird durch eine externe Quelle erwärmt).

### Glättung

Die Proben werden mit einem **gewichteten Mittelwert** kombiniert:

```
Kext_new = (Kext × n + Kext_target) / (n + 1)       n = Anzahl der Proben, begrenzt auf 50
```

Der konfigurierte Kext hat kein Gewicht: Die erste Probe ersetzt ihn, dann zählt jede Probe mit 1/(n+1). Für eine feste Größe liefert der Mittelwert die am wenigsten verrauschte Schätzung.

---

## Kontinuierliches Kext-Lernen

Wenn **Continuous Kext Learning** aktiviert ist, wird Kext auch nach der Sitzung weiter angepasst, um langsamen Änderungen der Verluste zu folgen.

### Voraussetzungen
- Mindestens eine Kext-Probe aus einer Lernsitzung.
- Dieselben Zyklus- und Einschwingbedingungen wie beim Kext-Lernen.

### Formel

```
Kext_new = Kext × (1 − α) + Kext_target × α        α = 0.04
```

Ein fester Gewichtungsfaktor lässt Kext einer langsam driftenden Größe folgen. Der neue Wert wird in die Konfiguration geschrieben, wenn er sich um mehr als 0.001 ändert, und die Regelung verwendet ihn sofort.

---

## Parameter und Konstanten

### Konfigurierbare Parameter

| Parameter | Beschreibung |
|-----------|-------------|
| `heater_heating_time` | Heizzeit des Heizkörpers (Min.). Legt `T_cl` fest. |
| `auto_tpi_continuous_kext` | Kontinuierliches Kext-Lernen nach der Sitzung. |

### Interne Konstanten

| Konstante | Wert | Rolle |
|----------|------|-------|
| Mindestabweichung für ein Kint-Fenster | 0.3 °C | Kint wird nur gelernt, wenn der Raum eine Abweichung zu schließen hat |
| Fensterdauer | 10 Min. bis max(30 Min., T_cl), anhand der vorherigen Anstiegsgeschwindigkeit festgelegt | Etwa 0.3 °C Änderung pro Fenster |
| Maximaler Kint-Schritt | ×1.15 / ÷1.15 | Begrenzter Schritt pro Fenster |
| Grenzen für Kint | 0.01 – 1.0 | |
| Kint-Fenster bis zum Ende der Sitzung | 15 | |
| Kext-Zyklen bis zum Ende der Sitzung | 50 | |
| Kext-Einschwingen | 3 × T_cl, danach nahe am Sollwert (oder 12 × T_cl) | Kext wird während eines Anstiegs nicht gelernt |
| Maximale Abweichung für Kext | 1.0 °C | |
| Maximales Kext | 1.2 | |
| Alpha des kontinuierlichen Kext | 0.04 | |

---

## Dienste und API

### `versatile_thermostat.set_auto_tpi_mode`

Startet oder stoppt eine Lernsitzung.

| Parameter | Typ | Beschreibung |
|-----------|-----|-------------|
| `auto_tpi_mode` | boolean | `true` zum Starten, `false` zum Stoppen |
| `reinitialise` | boolean | `true` (Standard): erneut mit den konfigurierten Koeffizienten starten. `false`: vorherige Sitzung fortsetzen |

```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.living_room
data:
  auto_tpi_mode: true
  reinitialise: true
```

---

## Diagnose und Fehlerbehebung

### Diagnosesensor

Entität: `sensor.<name>_auto_tpi_learning_state`

Zustand: `active` während einer Sitzung, sonst `off`.

| Attribut | Beschreibung |
|-----------|-------------|
| `heating_cycles_count` | Gesamtzahl beobachteter Zyklen |
| `coeff_int_cycles` | Gelernte Kint-Fenster |
| `coeff_ext_cycles` | Gelernte Kext-Zyklen |
| `model_confidence` | Fortschritt der Sitzung 0.0 – 1.0 |
| `calculated_coef_int` | Aktuelles Kint |
| `calculated_coef_ext` | Aktuelles Kext |
| `last_learning_status` | Ergebnis des letzten Zyklus |
| `learning_start_dt` | Beginn der Sitzung |

### Häufige Lernstatus

| Status | Bedeutung |
|--------|---------|
| `learned_indoor_heat` / `learned_indoor_cool` | Kint am Ende eines Fensters aktualisiert |
| `learned_outdoor_heat` / `learned_outdoor_cool` | Kext aktualisiert |
| `kext_waiting_settling` | Kext wartet, bis der Raum sich nach einer Sollwertänderung eingeschwungen hat |
| `kint_window_crossed_setpoint` | Der Raum hat während des Fensters den Sollwert überschritten, Fenster nicht verwendet |
| `power_out_of_range(...)` | Leistung bei 0 % oder 100 %, Zyklus ignoriert |
| `cycle_gap_detected` / `cycle_too_short` | Ungewöhnliche Zyklusdauer, Zyklus ignoriert |
| `setpoint_changed_during_cycle` | Sollwert während des Zyklus geändert |
| `outdoor_delta_too_small(...)` | Außentemperatur zu nah am Sollwert |
| `gap_too_large_for_outdoor(...)` | Abweichung über 1 °C, Kext nicht gelernt |
| `cooling_down_naturally` / `warming_up_naturally` | Raum kehrt von selbst zum Sollwert zurück, Kext unverändert |
| `continuous_kext_learned_heat` / `continuous_kext_learned_cool` | Kext durch kontinuierliches Lernen aktualisiert |

### Fehlerbehebung

| Symptom | Wahrscheinliche Ursache | Maßnahme |
|---------|--------------|--------|
| Kint kommt nicht voran | Kein Anstieg von mindestens 0.3 °C bei nicht gesättigter Leistung | Sollwert für einige Stunden um 1–2 °C senken und dann wieder einstellen |
| Overshoot nach jedem Anstieg | Heizzeit zu kurz für den Heizkörper | Heizzeit erhöhen, dann eine Sitzung neu starten |
| Langsamer Anstieg, kein Overshoot | Heizzeit zu lang | Heizzeit verringern, dann eine Sitzung neu starten |
| Raum liegt immer unter oder über dem Sollwert | Kext noch nicht gelernt oder Verluste haben sich geändert | Sitzung enden lassen oder kontinuierliches Kext-Lernen aktivieren |
| Lernen kommt überhaupt nicht voran | Heizung immer bei 100 % (extreme Kälte) | Auf milderes Wetter warten |

### Persistenzdatei

**Speicherort**: `.storage/versatile_thermostat.auto_tpi.<unique_id>`

Diese Datei enthält den Lernzustand und wird beim Neustart von Home Assistant wiederhergestellt. Solange noch kein Lernzyklus erfasst wurde, werden die konfigurierten Koeffizienten verwendet. Außerhalb einer Lernsitzung gilt die Konfiguration als Referenz: Ein in der Konfiguration (Optionen oder Dienst `set_tpi_parameters`) geänderter Koeffizient ersetzt den gespeicherten.
