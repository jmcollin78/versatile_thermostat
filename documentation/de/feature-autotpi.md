# Auto-TPI-Funktion


## Einleitung

Die Funktion **Auto TPI** (oder Selbstlernfunktion) ist eine wichtige Neuerung des Versatile Thermostat. Damit kann der Thermostat seine Regelungskoeffizienten (Kp und Ki) **automatisch** anpassen, indem er das Temperaturverhalten des Raums analysiert.

Im TPI-Modus (Time Proportional & Integral) berechnet der Thermostat einen Öffnungsprozentsatz oder eine Heizzeit anhand der Abweichung zwischen der Solltemperatur und der Innentemperatur (`Kp`) sowie des Einflusses der Außentemperatur (`Ki`).

Die richtigen Koeffizienten (`tpi_coef_int` und `tpi_coef_ext`) zu finden, ist oft komplex und erfordert zahlreiche Versuche. **Das übernimmt Auto TPI.**

## Voraussetzungen

Damit Auto TPI effizient funktioniert:
1.  **Zuverlässiger Temperatursensor**: Der Sensor darf nicht direkt von der Wärmequelle beeinflusst werden (nicht beim Heizkörper anbringen!).
2.  **Außentemperatursensor**: Eine genaue Messung der Außentemperatur ist unerlässlich.
3.  **TPI-Modus aktiviert**: Diese Funktion ist nur verfügbar, wenn Sie den TPI-Algorithmus verwenden (Thermostat auf Schalter, Ventil oder Klima im TPI-Modus).
4.  **Korrekte Leistungseinstellung**: Stellen Sie die Parameter für die Aufheizzeit korrekt ein (siehe unten).
5.  **Optimaler Start (wichtig)**: Damit der Lernvorgang effektiv startet, wird empfohlen, ihn zu aktivieren, wenn die Abweichung zwischen der aktuellen Temperatur und dem Sollwert erheblich ist (**2 °C** sind ausreichend).
*   *Tipp*: Kühlen Sie den Raum, aktivieren Sie den Lernvorgang und stellen Sie dann den Komfort-Sollwert wieder ein.

## Konfiguration

Die Konfiguration von Auto TPI ist in den TPI-Konfigurationsablauf für **jeden einzelnen Thermostat** integriert.

> **Hinweis**: Der Auto-TPI-Lernvorgang kann nicht über die zentrale Konfiguration eingerichtet werden, da jeder Thermostat einen eigenen Lernvorgang benötigt.

1.  Gehen Sie zur Konfiguration des Versatile Thermostat (**Konfigurieren**).
2.  Wählen Sie **TPI-Einstellungen**.
3.  **Wichtig**: Sie müssen die Option **Zentrale TPI-Konfiguration verwenden** deaktivieren, um auf die lokalen Einstellungen zugreifen zu können.
4.  Aktivieren Sie auf dem nächsten Bildschirm (TPI-Attribute) ganz unten das **Auto-TPI-Lernen aktivieren**.

Sobald diese Option aktiviert ist, wird ein spezieller Konfigurationsassistent in mehreren Schritten angezeigt:

### Schritt 1: Allgemein

*   **Auto-TPI aktivieren**: Ermöglicht das Aktivieren oder Deaktivieren des Lernvorgangs.
*   **Benachrichtigung**: Wenn diese Option aktiviert ist, wird **nur** dann eine Benachrichtigung gesendet, wenn der Lernvorgang als abgeschlossen gilt (50 Zyklen pro Koeffizient).
*   **Konfiguration aktualisieren**: Wenn diese Option aktiviert ist, werden die erlernten TPI-Koeffizienten **automatisch** in der Konfiguration des Thermostats gespeichert, aber **nur wenn der Lernvorgang als abgeschlossen gilt**. Wenn diese Option deaktiviert ist, werden die erlernten Koeffizienten für die aktuelle TPI-Regelung verwendet, aber nicht in der Konfiguration gespeichert.
* **Kontinuierliches Lernen** (`auto_tpi_continuous_learning`): Wenn diese Option aktiviert ist, wird das Lernen auch nach Abschluss der ersten 50 Zyklen unbegrenzt fortgesetzt. Dadurch kann sich der Thermostat kontinuierlich an allmähliche Veränderungen der thermischen Umgebung anpassen (z. B. saisonale Veränderungen, Alterung des Hauses). Wenn diese Option aktiviert ist, werden die gelernten Parameter am Ende jedes Zyklus in der Konfiguration gespeichert (sofern **Konfigurationsaktualisierung** ebenfalls aktiviert ist), sobald das Modell als „stabil” gilt (z. B. nach den ersten 50 Zyklen).
    *   **Fehlerrobustheit**: Im kontinuierlichen Modus stoppen aufeinanderfolgende Fehler das Lernen nicht. Das System ignoriert fehlerhafte Zyklen und setzt seine Anpassung fort.
    *   **Erkennung von Betriebsänderungen**: Wenn das kontinuierliche Lernen aktiviert ist, überwacht das System die letzten Lernfehler. Wird eine **systematische Verzerrung** festgestellt (z. B. aufgrund eines Wechsels der Jahreszeit, der Isolierung oder des Heizsystems), wird die Lernrate (Alpha) **vorübergehend erhöht** (auf bis zum Dreifachen des Basiswerts, begrenzt auf 15 %), um die Anpassung zu beschleunigen. Dank dieser Funktion kann sich der Thermostat schnell und ohne manuelles Eingreifen an neue Temperaturbedingungen anpassen.
*   **Externen Koeffizienten beibehalten** (`auto_tpi_keep_ext_learning`): Wenn diese Option aktiviert ist, wird der externe Koeffizient (`Kext`) auch nach Erreichen von 50 Zyklen weiter gelernt, solange der interne Koeffizient (`Kint`) noch nicht stabil ist.
**Hinweis:** Die Beibehaltung der Konfiguration erfolgt nur, wenn beide Koeffizienten stabil sind.
*   **Aufheiz-/Abkühlzeit**: Legen Sie die Trägheit Ihres Kühlers fest ([siehe Thermische Konfiguration](#kritische-thermische-konfiguration)).
*   **Obergrenze für den Innenkoeffizienten**: Sicherheitsgrenzen für den Innenkoeffizienten (`max 3,0`). **Hinweis**: Bei einer Änderung dieses Grenzwerts im Konfigurationsfluss wird der neue Wert **sofort** auf die gelernten Koeffizienten angewendet, wenn diese über dem neuen Grenzwert liegen (was ein Neuladen der Integration erfordert, was nach dem Speichern einer Änderung über die Optionen der Fall ist).

*   **Heizrate** (`auto_tpi_heating_rate`): Zielwert für die Temperaturanstiegsrate in °C/h. ([siehe Konfiguration der Raten](#configuration-des-taux-de-chauffe) )\n*   **Aggressivität** (`auto_tpi_aggressiveness`): Prozentualer Anteil der erlernten Wärmekapazität, der verwendet werden soll (50-100 %, Standardwert 90 %). Niedrigere Werte führen zu konservativeren Koeffizienten, wodurch das Risiko einer Überschreitung des Sollwerts verringert wird.

    *Hinweis: Es ist nicht unbedingt erforderlich, die maximale Heizrate zu verwenden. Je nach Dimensionierung der Heizung können Sie durchaus einen niedrigeren Wert verwenden, **was sogar sehr empfehlenswert ist**.
    Je näher Sie an der maximalen Kapazität liegen, desto höher ist der beim Lernen ermittelte Kint-Koeffizient.*

    *Sobald Ihre Kapazität durch den dafür vorgesehenen Dienst definiert oder manuell geschätzt wurde, sollten Sie  einen angemessenen Heizgrad verwenden.
   **Das Wichtigste ist, dass Sie nicht über das hinausgehen, was Ihr Heizkörper in diesem Raum leisten kann.**
    Beispiel: Ihre gemessene adiabatische Kapazität beträgt 1,5 °C/h, 1 °C/h ist eine Standardkonstante, deren Verwendung sinnvoll ist.*

### Schritt 2: Methode

Wählen Sie den Lernalgorithmus:
*   **Durchschnitt (Average)**: Einfacher gewichteter Durchschnitt. Ideal für schnelles und einmaliges Lernen (leicht zurückzusetzen).
*   **EMA (Exponential Moving Average)**: Exponentieller gleitender Durchschnitt. Sehr empfehlenswert für kontinuierliches Lernen und Feinabstimmung, da er aktuelle Werte bevorzugt.

### Schritt 3: Verfahrenseinstellungen

Konfigurieren Sie die spezifischen Parameter für die gewählte Methode:
*   **Durchschnitt**: Anfangsgewichtung.
*   **EMA**: Anfangs-Alpha und Abklingrate (Decay).


### Thermische Konfiguration (kritisch)

Der Algorithmus muss die Reaktionsfähigkeit Ihres Heizungssystems verstehen.

#### `heater_heating_time` (Thermische Reaktionszeit)
Dies ist die Gesamtzeit, die das System benötigt, um eine messbare Wirkung auf die Raumtemperatur zu erzielen.

Sie umfasst:
*  Die Aufheizzeit des Heizkörpers (materielle Trägheit).
*  Die Zeit, die die Wärme benötigt, um sich im Raum bis zum Sensor auszubreiten.

**Empfohlene Werte:**

| Heizungstyp                                            | Empfohlener Wert |
|--------------------------------------------------------|------------------|
| Elektroheizkörper (Konvektor), Nahsensor               | 2-5 min          |
| Speicherheizung (Ölbad, Gusseisen), Nahsensor          | 5-10 min         |
| Fußbodenheizung oder großer Raum mit entferntem Sensor | 10-20 min        |

> Ein falscher Wert kann die Berechnung der Effizienz verfälschen und das Lernen verhindern.

#### `heater_cooling_time` (Kühlzeit des Heizkörpers)
Zeit, die der Heizkörper benötigt, um nach dem Ausschalten abzukühlen. Wird verwendet, um über den `cold_factor` zu schätzen, ob der Heizkörper zu Beginn eines Zyklus „warm” oder „kalt” ist. Der `cold_factor` ermöglicht es, die Trägheit des Heizkörpers zu korrigieren, und dient als **Filter**: Wenn die Aufheizzeit im Vergleich zur geschätzten Aufwärmzeit zu kurz ist, wird das Lernen für diesen Zyklus ignoriert (um Störungen zu vermeiden).

### Automatisches Lernen der Wärmekapazität ⚡

Die Wärmekapazität (Temperaturanstiegsrate in °C/h) wird nun während des anfänglichen Lernvorgangs dank **Bootstrap** **automatisch gelernt**.

#### Wie funktioniert das?

Das System startet mit **aggressiven TPI-Koeffizienten** für die ersten drei Zyklen, um einen deutlichen Temperaturanstieg zu bewirken und die tatsächliche Leistung Ihrer Heizung zu messen. Anschließend wechselt es automatisch in den normalen TPI-Modus.

#### Die 2 Startstrategien

1. **Automatikmodus (empfohlen)** ✅:
   - Lassen Sie `auto_tpi_heating_rate` auf **0** (Standard)
   - Das System erkennt automatisch, dass die Kapazität unbekannt ist
   - Es führt 3 Zyklen mit **aggressiven TPI-Koeffizienten** (200,0/5,0) durch, um einen Temperaturanstieg zu bewirken und die Kapazität zu messen
   - **Dies ist der empfohlene Modus für einen Start ohne Konfiguration**

2. **Manueller Modus**:
   - Setzen Sie `auto_tpi_heating_rate` auf einen bekannten Wert (z. B. 1,5 °C/h).
   - Der Bootstrap wird vollständig übersprungen.
   - Das System startet sofort mit dieser Kapazität im TPI-Modus.
   - Verwenden Sie diesen Modus, wenn Sie Ihre Kapazität bereits kennen.

#### Konfiguration

In Schritt 1 der Auto-TPI-Konfiguration:
- **Heizrate** (`auto_tpi_heating_rate`): Lassen Sie den Wert auf **0**, um den automatischen Bootstrap zu aktivieren

> 💡 **Tipp**: Für einen optimalen Start des Bootstraps aktivieren Sie das Lernen, wenn die Abweichung zwischen der aktuellen Temperatur und dem Sollwert mindestens 2 °C beträgt.

#### Kalibrierdienst (optional)

Wenn Sie dennoch die Kapazität anhand der Historie schätzen möchten, ohne auf das Bootstrap zu warten:

```yaml
service: versatile_thermostat.auto_tpi_calibrate_capacity
target:
  entity_id: climate.my_thermostat
data:
  save_to_config: true
```

Dieser Dienst analysiert den Verlauf und schätzt die Kapazität, indem er die Momente identifiziert, in denen die Heizung mit voller Leistung läuft.

## Funktionsweise

Auto TPI arbeitet zyklisch:

1.  **Beobachtung**: Bei jedem Zyklus (z. B. alle 10 Minuten) misst der Thermostat (der sich im Modus „HEAT” befindet) die Temperatur zu Beginn und am Ende sowie die verbrauchte Leistung.
2.  **Validierung**: Es wird überprüft, ob der Zyklus für das Lernen gültig ist:
    *   Das Lernen basiert auf dem Modus `HEAT` des Thermostats, unabhängig vom aktuellen Status des Wärmesenders (`heating`/`idle`).
    *   Die Leistung war nicht ausgelastet (zwischen 0 % und 100 % ausgeschlossen).
    *   Die Temperaturabweichung ist signifikant.
    *   Das System ist stabil (keine aufeinanderfolgenden Fehler).
    *   Der Zyklus wurde nicht durch eine Leistungsreduzierung (Power Shedding) oder das Öffnen eines Fensters unterbrochen.
    *   **Fehler erkannt**: Der Lernvorgang wird unterbrochen, wenn eine Anomalie bei der Heizung oder Klimatisierung erkannt wird (z. B. Temperatur steigt trotz Heizung nicht an), um das Einlernen falscher Koeffizienten zu vermeiden.
    * **Zentralheizungskessel**: Wenn der Thermostat von einem Zentralheizungskessel abhängig ist, wird der Lernvorgang unterbrochen, wenn der Kessel nicht aktiviert ist (auch wenn der Thermostat eine Anforderung sendet).
3.  **Berechnung (Lernen)**:
    *   **Fall 1: Interner Koeffizient**. Wenn sich die Temperatur deutlich in die richtige Richtung entwickelt hat (> 0,05 °C), berechnet er das Verhältnis zwischen der tatsächlichen Entwicklung **(über den gesamten Zyklus, einschließlich Trägheit)** und der erwarteten theoretischen Entwicklung (korrigiert durch die kalibrierte Kapazität). Es passt `CoeffInt` an, um die Abweichung zu verringern.
    *   **Fall 2: Außenkoeffizient**. Wenn das interne Lernen nicht möglich war und die Temperaturabweichung signifikant ist (> 0,1 °C), passt es `CoeffExt` an, um die Verluste auszugleichen.
        *   **Wichtig**: Das Lernen des Außenkoeffizienten wird **blockiert**, wenn die Temperaturabweichung zu groß ist (> 0,5 °C). Dadurch wird sichergestellt, dass `Kext` (der die Verluste im Gleichgewicht darstellt) nicht durch Probleme mit der Temperaturanstiegsdynamik (die unter `Kint` fallen) verfälscht wird.
    *   **Fall 3: Schnelle Korrekturen (Boost/Deboost)**. Parallel dazu überwacht das System kritische Anomalien:
        *   **Boost Kint**: Wenn die Temperatur trotz Heizbedarf stagniert, wird der Innenkoeffizient erhöht. (Optional über `allow_kint_boost_on_stagnation`)
        *   **Deboost Kext**: Wenn die Temperatur den Sollwert überschreitet und nicht wieder sinkt, wird der Außenkoeffizient reduziert. (Optional über `allow_kext_compensation_on_overshoot`)
        * Diese Korrekturen werden anhand der Zuverlässigkeit des Modells gewichtet: Je mehr Daten (Lernzyklen) das System hat, desto moderater sind die Korrekturen, um eine Destabilisierung eines zuverlässigen Modells zu vermeiden.*
4.  **Aktualisierung**: Die neuen Koeffizienten werden geglättet und für den nächsten Zyklus gespeichert.

### Aktivierungssicherheit
Um unbeabsichtigte Aktivierungen zu vermeiden:
1. Der Dienst `set_auto_tpi_mode` lehnt die Aktivierung des Lernmodus ab, wenn "Auto-TPI-Lernmodus aktivieren" in der Konfiguration des Thermostats nicht aktiviert ist.
2. Sollte das Kontrollkästchen in der Konfiguration deaktiviert werden, während der Lernmodus aktiv war, wird dieser beim Neuladen der Integration automatisch beendet.

## Attribute und Sensoren

Ein spezieller Sensor `sensor.<Thermostatname>_auto_tpi_learning_state` ermöglicht die Verfolgung des Lernstatus.

**Verfügbare Attribute:**

*   `active`: Das Lernen ist aktiviert.
*   `heating_cycles_count`: Gesamtzahl der beobachteten Zyklen.
*   `coeff_int_cycles`: Anzahl der Anpassungen des internen Koeffizienten.
*   `coeff_ext_cycles`: Anzahl der Anpassungen des Außenkoeffizienten.
*   `model_confidence`: Vertrauensindex (0,0 bis 1,0) für die Qualität der Einstellungen. Begrenzt auf 100 % nach 50 Zyklen für jeden Koeffizienten (auch wenn das Lernen fortgesetzt wird).
*   `last_learning_status`: Aktueller Status des Lernvorgangs oder Grund für das letzte Ergebnis. Lebenszykluswerte: `learning_started` (neues Lernen), `learning_resumed` (Wiederaufnahme nach Pause), `learning_stopped` (unterbrochen). Beispiele für Lernergebnisse: `learned_indoor_heat`, `power_out_of_range`.
*   `calculated_coef_int` / `calculated_coef_ext`: Aktuelle Werte der Koeffizienten.
*   `learning_start_dt`: Datum und Uhrzeit des Beginns des Lernvorgangs (nützlich für Grafiken).
*   `allow_kint_boost_on_stagnation`: Gibt an, ob der Kint-Boost bei Stagnation aktiviert ist.
*   `allow_kext_compensation_on_overshoot`: Gibt an, ob die Kext-Korrektur bei Überschreitung aktiviert ist.
*   `capacity_heat_status`: Status des Lernens der Wärmekapazität (`learning` oder `learned`).
*   `capacity_heat_value`: Der Wert der gelernten Wärmekapazität (in °C/h).
*   `capacity_heat_count`: Die Anzahl der Bootstrap-Zyklen, die zum Lernen der Kapazität durchgeführt wurden.

## Services

### Kalibrierungsdienst (`versatile_thermostat.auto_tpi_calibrate_capacity`)

Dieser Dienst ermöglicht es, die **adiabatische Kapazität** Ihres Systems (`max_capacity` in °C/h) durch Analyse der historischen Sensordaten zu schätzen.

**Prinzip:** Der Dienst nutzt den Verlauf der **Sensoren** `temperature_slope` und `power_percent`, um die Zeitpunkte zu ermitteln, zu denen die Heizung mit voller Leistung lief. Er verwendet das **75. Perzentil** (das näher an der adiabatischen Temperatur liegt als der Median) und wendet eine **Kext-Korrektur** an: `Capacity = P75 + Kext_config × ΔT`.

```yaml
service: versatile_thermostat.auto_tpi_calibrate_capacity
target:
  entity_id: climate.my_thermostat
data:
  start_date: "2023-11-01T00:00:00+00:00" # Optional. Standardmäßig 30 Tage vor "end_date".
  end_date: "2023-12-01T00:00:00+00:00"   # Optional. Standardmäßig jetzt.
  min_power_threshold: 95          # Optional. Seuil de puissance en % (0-100). Défaut 95.
  capacity_safety_margin: 20       # Optional. Sicherheitsmarge in % (0-100), die von der berechneten Kapazität abgezogen werden soll. Standardwert 20.
  save_to_config: true             # Optional. Die empfohlene Kapazität (nach Marge) in der Konfiguration speichern. Standardwert false.
```

> **Ergebnis**: Der Wert der adiabatischen Kapazität (`max_capacity_heat`) wird in den Attributen des Lernzustandssensors mit dem **empfohlenen Wert** (berechnete Kapazität – Sicherheitsmarge) aktualisiert.
>
> Der Dienst gibt außerdem die folgenden Informationen zurück, um die Qualität der Kalibrierung zu analysieren:
> *   **`max_capacity`**: Die geschätzte adiabatische Bruttokapazität (in °C/h).
> *   **`recommended_capacity`**: Die empfohlene Kapazität nach Anwendung der Sicherheitsmarge (in °C/h). Dieser Wert wird gespeichert.
> *   **`margin_percent`**: Die angewandte Sicherheitsmarge (in %).
> *   **`observed_capacity`**: Das 75. Perzentil brutto (vor Kext-Korrektur).
> *   **`kext_compensation`**: Der angewandte Korrekturwert (Kext × ΔT).
> *   **`avg_delta_t`**: Der für die Korrektur verwendete durchschnittliche ΔT-Wert.
> *   **`reliability`**: Zuverlässigkeitsindex (in %) basierend auf der Anzahl der Stichproben und der Varianz.
> *   **`samples_used`**: Anzahl der nach der Filterung verwendeten Stichproben.
> *   **`outliers_removed`**: Anzahl der entfernten Ausreißer.
> *   **`min_power_threshold`**: Verwendeter Leistungsschwellenwert.
> *   **`period`**: Anzahl der analysierten Tage im Verlauf.
>
> Die TPI-Koeffizienten (`Kint`/`Kext`) werden dann durch die normale Lernschleife unter Verwendung dieser Fähigkeit als Referenz gelernt oder angepasst.

### Lernen aktivieren/deaktivieren (`versatile_thermostat.set_auto_tpi_mode`)

Mit diesem Service kann das Auto-TPI-Lernen ohne Konfiguration des Thermostats gesteuert werden.

#### Parameter

| Parameter                              | Typ     | Standard | Beschreibung                                              |
|----------------------------------------|---------|----------|-----------------------------------------------------------|
| `auto_tpi_mode`                        | boolean | -        | Aktiviert (`true`) oder deaktiviert (`false`)  das Lernen |
| `reinitialise`                         | boolean | `true`   | Steuert das Zurücksetzen der Daten bei Aktivierung        |
| `allow_kint_boost_on_stagnation`       | boolean | `false`  | Erlaubt den Boost von Kint bei Temperaturstagnation       |
| `allow_kext_compensation_on_overshoot` | boolean | `false`  | Erlaubt Kext-Ausgleich bei Überschreitung (Overshoot)     |

#### Verhalten des Parameters `reinitialise`

Der Parameter `reinitialise` bestimmt, wie vorhandene Trainingsdaten bei der Aktivierung behandelt werden:

- **`reinitialise: true`** (Standard): Löscht alle Lerndaten (Koeffizienten und Zähler) und beginnt den Lernvorgang von vorne. Die kalibrierten Kapazitäten (`max_capacity_heat`/`cool`) bleiben erhalten.
- **`reinitialise: false`**: Setzt das Lernen mit den vorhandenen Daten fort, ohne diese zu löschen. Die vorherigen Koeffizienten und Zähler bleiben erhalten und das Lernen wird anhand dieser Werte fortgesetzt.

**Anwendungsfall:** Ermöglicht es, das Lernen vorübergehend zu deaktivieren (z. B. während einer Urlaubszeit oder bei Bauarbeiten) und es anschließend wieder zu aktivieren, ohne die bereits erzielten Fortschritte zu verlieren.

#### Beispiele

**Neuen Lernvorgang starten (vollständiges Zurücksetzen):**
```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.mon_thermostat
data:
  auto_tpi_mode: true
  reinitialise: true  # oder weggelassen, weil das der Fehler ist.
```

**Das Lernen fortsetzen, ohne Daten zu verlieren:**
```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.mon_thermostat
data:
  auto_tpi_mode: true
  reinitialise: false
```

**Das Lernen beenden:**

Wenn die Lernphase beendet ist:

- Das Lernen ist **deaktiviert**, aber die gelernten Daten bleiben in den Attributen der Entität **auto_tpi_learning_state** **sichtbar**.
- Die Regelung verwendet die **Konfigurationskoeffizienten** (nicht die gelernten Koeffizienten).


## Berechnungsmethode Gewichteter Durchschnitt

La méthode **Moyenne Pondérée** (Average) est une approche simple et efficace pour l'apprentissage des coefficients TPI. Elle est particulièrement adaptée pour un apprentissage rapide et unique, ou lorsque vous souhaitez réinitialiser facilement les coefficients.

### Verhalten

La méthode Moyenne Pondérée calcule une moyenne pondérée entre les coefficients existants et les nouvelles valeurs calculées. Comme la méthode EMA, elle réduit progressivement l'influence des nouveaux cycles au fur et à mesure de l'apprentissage, mais utilise une approche différente.

**Caractéristique clé** : Plus le nombre de cycles augmente, plus le poids du coefficient existant devient important par rapport au nouveau coefficient. Cela signifie que l'influence des nouveaux cycles diminue progressivement au fur et à mesure de l'apprentissage.

### Parameter

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Poids initial** (`avg_initial_weight`) | Poids initial donné aux coefficients de configuration au démarrage | 1 |

### Formel

```
avg_coeff = ((old_coeff × weight_old) + coeff_new) / (weight_old + 1)
```

Où :
- `old_coeff` est le coefficient actuel
- `coeff_new` est le nouveau coefficient calculé pour ce cycle
- `weight_old` est le nombre de cycles d'apprentissage déjà effectués (avec un minimum de 1)

**Exemple d'évolution du poids** :
- Cycle 1 : weight_old = 1 → nouveau coefficient a un poids de 50%
- Cycle 10 : weight_old = 10 → nouveau coefficient a un poids de ~9%
- Cycle 50 : weight_old = 50 → nouveau coefficient a un poids de ~2%
- Cycle 100+ : weight_old = 50 (plafonné) → nouveau coefficient a encore un poids ~2% pour assurer la réactivité

### Hauptmerkmale

1. **Simplicité** : La méthode est facile à comprendre
2. **Réinitialisation facile** : Les coefficients peuvent être facilement réinitialisés en redémarrant l'apprentissage
3. **Apprentissage progressif** : L'influence des nouveaux cycles diminue au fur et à mesure, stabilisant progressivement les coefficients
4. **Convergence rapide** : La méthode atteint une stabilité après environ 50 cycles

### Vergleich mit EMA

| Aspect | Moyenne Pondérée | EMA |
|--------|------------------|-----|
| **Complexité** | Simple | Plus complexe |
| **Mécanisme de réduction** | Poids basé sur le nombre de cycles | Alpha adaptatif avec décroissance |
| **Stabilité** | Stable après 50 cycles | Stable après 50 cycles avec décroissance alpha |
| **Adaptation continue** | Moins adaptée | Plus adaptée (meilleure pour les changements progressifs) |
| **Réinitialisation** | Très facile | Facile |

### Nutzungsempfehlungen

- **Apprentissage initial** : La méthode Moyenne Pondérée est excellente pour un premier apprentissage rapide
- **Réglages ponctuels** : Idéale lorsque vous souhaitez ajuster les coefficients une seule fois
- **Environnements stables** : Bien adaptée aux environnements thermiques relativement stables

### Beispiel für Lernfortschritte

| Cycle | Poids ancien | Poids nouveau | Nouveau coefficient | Résultat |
|-------|--------------|---------------|---------------------|----------|
| 1 | 1 | 1 | 0.15 | (0.10 × 1 + 0.15 × 1) / 2 = 0.125 |
| 2 | 2 | 1 | 0.18 | (0.125 × 2 + 0.18 × 1) / 3 = 0.142 |
| 10 | 10 | 1 | 0.20 | (0.175 × 10 + 0.20 × 1) / 11 = 0.177 |
| 50 | 50 | 1 | 0.19 | (0.185 × 50 + 0.19 × 1) / 51 = 0.185 |

**Note** : Après 50 cycles, le coefficient est considéré comme stable et l'apprentissage s'arrête (sauf si l'apprentissage continu est activé). À ce stade, le nouveau coefficient n'a plus qu'un poids d'environ 2% dans la moyenne.

## Adaptive EMA-Berechnungsmethode

La méthode EMA (Exponential Moving Average) utilise un coefficient **alpha** qui détermine
l'influence de chaque nouveau cycle sur les coefficients appris.

### Verhalten

Au fil des cycles, **alpha décroît progressivement** pour stabiliser l'apprentissage :

| Cycles | Alpha (avec α₀=0.2, k=0.1) | Influence du nouveau cycle |
|--------|----------------------------|---------------------------|
| 0 | 0.20 | 20% |
| 10 | 0.10 | 10% |
| 50 | 0.033 | 3.3% |
| 100 | 0.033 | 3.3% (plafonné à 50 cycles) |

### Parameter

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Alpha initial** (`ema_alpha`) | Influence au démarrage | 0.2 (20%) |
| **Taux de décroissance** (`ema_decay_rate`) | Vitesse de stabilisation | 0.1 |

### Formel

```
alpha(n) = alpha_initial / (1 + decay_rate × n)
```

Où `n` est le nombre de cycles d'apprentissage (plafonné à 50).

### Sonderfälle

- **decay_rate = 0** : Alpha reste fixe (comportement EMA classique)
- **decay_rate = 1, alpha = 1** : Équivalent à la méthode "Moyenne Pondérée"

### Empfehlungen

| Situation | Alpha (`ema_alpha`) | Taux de Décroissance (`ema_decay_rate`) |
|---|---|---|
| **Apprentissage initial** | `0.15` | `0.08` |
| **Apprentissage fin** | `0.08` | `0.12` |
| **Apprentissage continu** | `0.05` | `0.02` |

**Explications:**

- **Apprentissage initial:**

  *Alpha:* 0.15 (15% de poids initial)

  *Avec ces paramètres, le système garde en tête principalement les 20 derniers cycles*

  * Cycle 1: α = 0.15 (forte réactivité initiale)
  * Cycle 10: α = 0.083 (commence à stabiliser)
  * Cycle 25: α = 0.050 (filtrage accru)
  * Cycle 50: α = 0.036 (robustesse finale)


  *Taux de décroissance:* 0.08

  Décroissance modérée permettant une adaptation rapide aux 10 premiers cycles
  Balance optimale entre vitesse (éviter stagnation) et stabilité (éviter sur-ajustement)

- **Apprentissage fin**

  *Alpha:* 0.08 (8% de  poids initial)

  *Avec ces paramètres, le système garde en tête principalement les 50 derniers cycles*

  Démarrage conservateur (coefficients déjà bons)
  Évite les sur-corrections brutales

  * Cycle 1 : α = 0.08
  * Cycle 25 : α = 0.024
  * Cycle 50+ : α = 0.013 (plafonné)


  *Taux de décroissance:*: 0.12

  Décroissance plus rapide que l'apprentissage initial
  Converge vers un filtrage très fort (stabilité)
  Adaptation majoritaire dans les 15 premiers cycles

- **Apprentissage continu**
  
  *Alpha* = 0.05 (5% de poids initial)

  *Avec ces paramètres, le système garde en tête principalement les 100 derniers cycles*

  Très conservateur pour éviter dérive
  Réactivité modérée aux changements graduels

  * Cycle 1 : α = 0.05
  * Cycle 50 : α = 0.025
  * Cycle 100+ : α = 0.025 (plafonné)


  *Taux de décroissance:* = 0.02

  Décroissance très lente (apprentissage à long terme)
  Maintient une capacité d'adaptation même après des centaines de cycles
  Adapté aux variations saisonnières (hiver/été)