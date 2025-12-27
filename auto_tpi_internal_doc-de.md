# Interne Dokumentation: Auto TPI (Algorithmus für selbstständiges Lernen und Kalibrierung)

Dieses Dokument beschreibt die interne Funktionsweise der in `auto_tpi_manager.py` implementierten Funktion **Auto TPI**.
**Aktualisierung:** Version 2.4 – Ersatz der Echtzeit-Kapazitätserkennung durch einen Kalibrierungsdienst mittels linearer Regression auf Basis historischer Daten.

---

## 1. Allgemeine Grundsätze

Der TPI-Algorithmus (Time Proportional & Integral) berechnet einen Prozentsatz der Heizleistung (`power`) anhand der Abweichung zwischen der Solltemperatur und der Innentemperatur sowie des Einflusses der Außentemperatur.

Die Grundformel lautet:
```python
Power = (Error_In * Coeff_Indoor) + (Error_Out * Coeff_Outdoor) + Offset
```
Wo:
*   `Error_In` = Vorgabe – Innentemperatur
*   `Error_Out` = Vorgabe – Außentemperatur (oder entsprechendes Delta)

Das Ziel von Auto TPI ist es, die optimalen Werte für **`Coeff_Indoor`** und **`Coeff_Outdoor`** zu finden.

---

## 2. Architektur und Integration

Das System basiert auf einer engen Integration zwischen dem Manager, dem Basis-Thermostat und den Sensoren.

### A. Hauptkomponenten

1.  **`AutoTpiManager` (Das Gehirn)**:
    *   Verwaltet den Lebenszyklus des Lernprozesses.
    *   Speichert den Status (`AutoTpiState`) in `.storage/versatile_thermostat_{unique_id}_auto_tpi_v2.json`.
    *   Verwaltet die Persistenz der kalibrierten maximalen Kapazität (`max_capacity_heat` / `max_capacity_cool`).
    *   Zeigt die Zustandsmetriken an (Zuverlässigkeit, Zeitkonstante).
    *   **Aktive Rolle**: Steuert die TPI-Regelschleife über einen eigenen internen Timer (`_tick`).
    *   **Synchronisation & endgültige Persistenz**: Verwaltet die Aktualisierung der Koeffizienten und Kapazitäten in den HA-Konfigurationseinträgen (`async_update_coefficients_config`, `async_update_capacity_config`).
    *   **Kalibrierung**: Er stellt die Methode `service_calibrate_capacity` bereit, die die Abfrage des Verlaufs und die Berechnung der Kapazität koordiniert.
    *   **Benachrichtigung**: Er verwaltet die Benachrichtigung über den Abschluss des Lernvorgangs (`process_learning_completion`).

2.  **`BaseThermostat` (Der Dirigent)**:
    *   Instanziiert `AutoTpiManager` in `post_init` (mit den neuen Parametern aus dem Konfigurationsfluss).
    *   Lädt die persistenten Daten beim Start.
    *   Delegiert die Verwaltung des TPI-Zyklus über `start_cycle_loop` an den Manager.
    *   Liefert Echtzeitdaten (`_get_tpi_data`) und führt Zyklusbefehle aus (`_on_tpi_cycle_start`).
    *   **Delegierungsrolle**: Der Thermostat delegiert alle Aufgaben zur Konfigurationssynchronisierung und Benachrichtigung über das Ende des Lernvorgangs an den AutoTpiManager. Seine Rolle konzentriert sich auf die Instanziierung, das Laden von Daten, die Bereitstellung von Echtzeitdaten und die Ausführung von Befehlen.
    *   **Sicherer Start**: In `async_startup` überprüft der Thermostat, ob der Modus `HEAT` oder `COOL` ist, und erzwingt den Start der Auto-TPI-Schleife (`start_cycle_loop`). Dadurch wird sichergestellt, dass das Lernen nach einem Neustart oder einem Neuladen der Konfiguration fortgesetzt wird, auch wenn sich der HVAC-Modus nicht geändert hat.

3.  **`AutoTpiSensor` (Sichtbarkeit)**:
    *   Zeigt den Lernstatus und interne Metriken an (Anzahl der Zyklen, Konfidenz, berechnete Koeffizienten).

### B. Kontrollfluss (TPI-Schleife)

Im Gegensatz zu einem passiven Ansatz bestimmt der **`AutoTpiManager` den Rhythmus der Zyklen**, wenn das Lernen aktiv ist.

1.  **Start**:
    Die Schleife wird in zwei Fällen gestartet (`manager.start_cycle_loop`):
    *   **Moduswechsel**: Wenn der Thermostat in den Modus `HEAT` oder `COOL` wechselt (über `BaseThermostat.update_states`).
    *   **Initialisierung**: Beim Start der Integration (`async_startup`), wenn der wiederhergestellte Modus bereits `HEAT` oder `COOL` ist.

2.  **Schleife (`_tick`)**:
    Der Manager führt alle `cycle_min` Minuten eine Endlosschleife (über den Timer `async_call_later`) aus.
    *   **Schritt 1: Datenabruf**: Er ruft `BaseThermostat._get_tpi_data` auf, um die vom Proportionalalgorithmus berechneten Parameter (EIN-Zeit, AUS-Zeit, Prozentsatz) abzurufen.
        > **Synchronisierung der Koeffizienten**: Die gelernten Koeffizienten werden zu Beginn jedes Aufrufs von `_get_tpi_data()` an `PropAlgorithm` weitergegeben, wodurch sichergestellt wird, dass die TPI-Berechnung immer die zuletzt gelernten Werte verwendet.
    *   **Schritt 2: Snapshot**: Er ruft seine interne Methode `on_cycle_started` auf, um den Zustand (Temperaturen, Sollwert) zu Beginn des Zyklus festzuhalten. Dieser Snapshot dient als Referenz für das Lernen am Ende des Zyklus.
    *   **Schritt 3: Ausführung**: Er ruft `BaseThermostat._on_tpi_cycle_start` auf. Der Thermostat leitet das Ereignis dann an die zugrunde liegenden Einheiten (`UnderlyingEntity`) weiter, damit diese sich nach der berechneten Verzögerungszeit einschalten (ON) und dann ausschalten (OFF).

3.  **Ende des Zyklus**:
    Beim nächsten Tick überprüft der Manager die verstrichene Zeit. Entspricht sie `cycle_min`, bestätigt er das Ende des vorherigen Zyklus (`on_cycle_completed`) und löst dann die Lernlogik aus (sofern die Bedingungen erfüllt sind).

**Hinweis zum Regelungsmodus:** Die Lernlogik und die Leistungsberechnung basieren ausschließlich auf dem `hvac_mode` des Thermostats (`HEAT` oder `COOL`). Der Status der Heiz-/Kühlsteuerung (`hvac_action`: `heating`/`cooling`/`idle`) wird **nicht** verwendet, um zu bestimmen, ob das Lernen stattfinden soll, da ein vollständiger TPI-Zyklus natürlich die Phasen `heating`/`cooling` (EIN) und `idle` (AUS) umfasst.

---

## 3. Lernmechanismus

Das Lernen ist **zyklisch**. Es beginnt am Ende jedes abgeschlossenen Zyklus.

### A. Lernbedingungen (`_should_learn`)
Damit ein Zyklus gültig ist:
1.  **Aktivierung**: `autolearn_enabled` muss auf "True" gesetzt sein.
2.  **Signifikante Leistung**: Die Leistung muss zwischen 0 % und 100 % (ausgeschlossen) liegen. Bei Sättigungszyklen kann die Feinsteuerung nicht gelernt werden (außer bei Erkennung einer Unterdimensionierung).
3.  **Stabilität**: Weniger als 3 aufeinanderfolgende Fehler.
4.  **Signifikante Dauer**: Die Aktivierungszeit (`on_time`) muss länger sein als die effektive Aufheizzeit (`effective_heating_time`).
5.  **Ausschluss des ersten Zyklus**: Der Zyklus nach einem Start (vorheriger Zustand "stop") wird ignoriert, da das System nicht stabilisiert ist (Kaltstart).
6.  **Signifikante Außendifferenz**: `|Sollwert - Temp_Ext| >= 1,0`. Verhindert das Lernen bei zu geringen Temperaturunterschieden.

### B. Maximale Kapazität und Trägheit
**(ENTFERT)** Der Mechanismus zum Erlernen der Kapazität in Echtzeit (`_detect_max_capacity`) wurde durch einen Kalibrierungsdienst ersetzt, der auf einer linearen Regression der historischen Daten basiert. Siehe Abschnitt **„Neuer Kalibrierungsdienst”** weiter unten.

### C. Aktualisierungslogik (`_perform_learning`)

Der Algorithmus folgt einer strengen Abfolge von Validierungen und Berechnungen.

#### 1. Voraussetzungen (Validierungen)
Vor jeder Berechnung werden die folgenden Bedingungen überprüft.
*   **Modus**: Das System muss sich im Modus „Heizen” oder „Kühlen” befinden.
*   **Ausreichendes Außendelta**: „|Sollwert – Außentemperatur| >= 0,1”.

#### 2. Zyklus-Abbruchbehandlung

Um die Gültigkeit der Lerndaten sicherzustellen, werden Zyklen bei bestimmten Unterbrechungsszenarien ungültig gemacht (Lernen übersprungen):

1.  **Ausschluss des ersten Zyklus**: Die Logik erfordert zwingend einen gültigen `previous_state` und `last_order`.
    -   Wenn der Thermostat neu startet (z. B. nach einem "Fenster öffnen -> schließen"-Ereignis oder einem Neustart von Home Assistant), wird der `last_order` auf 0 zurückgesetzt.
    -   Die Lernlogik lehnt Zyklen, bei denen `last_order` 0 ist, ausdrücklich ab.
    -   **Ergebnis**: Der erste Regelungszyklus nach einem Neustart/einer Unterbrechung wird **immer ignoriert**, damit sich die Raumtemperatur stabilisieren kann, bevor das Lernen fortgesetzt wird.

2.  **Leistungsabwurf (Überlastung)**:
    -   Wenn der Power Manager eine Überlastung feststellt, schaltet er die zugeordneten Heizungen zwangsweise aus, aber der Thermostat bleibt möglicherweise im Modus `HEAT` (je nach Konfiguration).
    - Dadurch wird die Verbindung zwischen "Heat Mode ON" (Heizmodus eingeschaltet) und "Temperature Rise" (Temperaturanstieg) unterbrochen.
    - **Ergebnis**: Das `BaseThermostat` meldet diesen Zustand ausdrücklich an den `AutoTpiManager`. Jeder Zyklus, der ein Power Shedding-Ereignis enthält, wird als `interrupted` (unterbrochen) markiert und das **Lernen wird übersprungen**.

#### 3. Fall 1: Lernen des Innenkoeffizienten (`_learn_indoor`)
Dies ist die bevorzugte Methode, unterliegt jedoch nun strengen Auflagen, um Fehlalarme zu vermeiden und dem Lernen im Außenbereich eine Chance zu geben.

**Aktivierungsbedingungen:**
1.  **Unsättigte Leistung**: `0 < Leistung < 0,99` (es wird nicht bis zur Sättigung gelernt, außer bei Kapazitätserkennung).
2.  **Signifikanter Fortschritt**: `temp_progress > 0,05 °C` (verhindert das Lernen anhand von Rauschen).
3.  **Signifikanter Abstand**: `target_diff > 0,01 °C` (es ist noch ein Weg zurückzulegen).

**Wenn diese Bedingungen erfüllt sind:**
Der Algorithmus versucht, den Indoor-Koeffizienten anzulernen.
*   **Erfolg**: Wenn `_learn_indoor` `True` zurückgibt, wird der Lernzyklus hier beendet (`return`).
*   **Misserfolg**: Wenn `_learn_indoor` fehlschlägt (z. B. ungültiges Verhältnis, zu geringer Anstieg trotz Vorabprüfung), **fährt** das System mit dem Outdoor-Lernen fort.

(Siehe Abschnitt **Algorithmus für den Innenkoeffizienten (Detail)** weiter unten).

#### 4. Fall 2: Lernen des Außenkoeffizienten (`_learn_outdoor`)
Das Lernen im Außenbereich wird versucht, wenn das Lernen im Innenbereich nicht erfolgreich war.

**Aktivierungsbedingungen:**
1.  **Kohärente Außensteuerung**: Heat (`Text < Sollwert`) oder Cool (`Text > Sollwert`).
2.  **Signifikante Lücke**: `abs(gap_in) > 0,05` (Es wird versucht, selbst kleine, anhaltende Abweichungen zu korrigieren).

**Intelligente Validierung (Overshoot):**
*   **Problem**: Ein Overshoot (T_in > Sollwert in Heat) kann durch Sonneneinstrahlung (= externe Anomalie) ODER einen zu hohen Kext-Koeffizienten verursacht werden.
*   **Lösung**: Man schaut sich die Leistung an.
    *   Wenn **Leistung < 1 %** und Überschreitung: Wahrscheinlich ist es die Sonne (Heizung ausgeschaltet), wir wissen es nicht.
*   Wenn **Leistung >= 1 %** und Überschreitung: Die Heizung läuft, OBWOHL wir über dem Sollwert liegen. Das bedeutet, dass der Kext-Koeffizient zu hoch ist (er erzwingt unnötiges Heizen). **Wir lernen** (was Kext senken wird).
*   *Hinweis*: Der Schwellenwert wurde von 20 % auf 1 % gesenkt, um die Koeffizienten wieder zu senken.

#### 5. Algorithmus für den Innenkoeffizienten (Detail)
 
 **Berechnungsalgorithmus für Innenräume:**
 1.  **Sicherheit**: `real_rise` muss > 0,01 °C sein (Filterung des Sensorrauschens).
 2.  **Referenzkapazität (`ref_capacity`)**:
     *   Die Referenzkapazität ist die **adiabatische Kapazität** des Systems (gemessen in °C/h). Sie wird extern vom Dienst **`auto_tpi_calibrate_capacity`** berechnet und in `max_capacity_heat`/`cool` gespeichert.
     *   *Fallback*: Wenn noch keine Kapazität kalibriert ist (`max_capacity` <= 0), wird ein Standardwert von **1,0 °C/h** verwendet, um den Start des Kint-Lernvorgangs zu ermöglichen.
     *   **Wenn die Kapazität null oder nicht definiert ist** (und kein Fallback zutrifft), wird das Lernen für diesen Zyklus übersprungen (Status `no_capacity_defined`).
 3.  **Berechnung der effektiven Kapazität (dynamische Sättigungsschwelle)**:
     *   **Prinzip**: Vor der Berechnung des theoretischen Anstiegs werden die Wärmeverluste erneut auf die Referenzkapazität angewendet, um die tatsächliche Kapazität des Augenblicks zu erhalten.
     *   $C_{eff} = C_{ref} \cdot (1 - K_{ext} \cdot \Delta T_{ext})$
     *   $C_{eff}$ ist die tatsächliche maximale Temperaturanstiegskapazität in °C/h unter den aktuellen Wetterbedingungen.
     * Dieser Wert ($C_{eff}$) wird zur Berechnung des `saturation_threshold` verwendet, der nun dynamisch ist.
 4.  **Berechnung des maximal möglichen Anstiegs (`max_achievable_rise`)**:
     *   `max_achievable_rise = effective_capacity (°C/h) * cycle_duration (h) * efficiency`.
     *   *Beispiel*: Wenn die effektive Kapazität 2,0 °C/h beträgt, der Zyklus 15 min (0,25 h) dauert und der Wirkungsgrad 80 % beträgt, dann ist `max_achievable_rise = 2,0 * 0,25 * 0,8 = 0,4 °C`.
 5.  **Berechnung des angepassten theoretischen Deltas**:
     *   `adjusted_theoretical = min(target_diff, max_achievable_rise)`.
     *   **Das Ziel ist es, die gesamte Differenz** (`target_diff`) auszugleichen, **jedoch begrenzt durch die physikalische Kapazität**.
     *   *Grund*: Es ist sinnlos, vom Koeffizienten einen physikalisch unmöglichen Anstieg zu verlangen. Dadurch wird verhindert, dass der Koeffizient bei großen Differenzen unnötig in die Höhe schießt (Sättigung).
 6.  **Berechnung des Verhältnisses**: `Ratio = adjusted_theoretical / real_rise`.
 7.  **Neuer Koeffizient**: `Coeff_New = Ancien_Coeff * Ratio`.
 8.  **Validierung und Obergrenze**:
     *   Muss abgeschlossen sein und > 0 sein.
     *   **Obergrenze (Cap)**: Wenn `Coeff_New > auto_tpi_max_coef_int` (Standardwert 0,9), wird es auf diese Obergrenze reduziert. Dadurch werden zu aggressive Koeffizienten vermieden, die Schwankungen verursachen. Dieser Parameter ist konfigurierbar (max. 3,0).
 9.  **Endgültige Berechnung (gemäß der konfigurierten Methode)**:
    Der Benutzer kann über die Konfiguration zwischen zwei Berechnungsmethoden wählen:

    *   **EMA-Methode (Exponential Moving Average) – Standard**:
        *   `Coeff_Final = (Ancien_Coeff * (1 - Alpha)) + (Coeff_New * Alpha)`.
        *   `Alpha` ist konfigurierbar (`auto_tpi_ema_alpha`, Standardwert 0,2).
        *   Ermöglicht eine Glättung, bei der die aktuellen Werte ein festes Gewicht haben (z. B. 20 %).
        *   **Adaptives Alpha**: Bei der EMA-Methode nimmt Alpha gemäß `α(n) = α₀ / (1 + k·n)` ab. Dies vereinheitlicht konzeptionell die EMA- und die Durchschnittsmethode: Mit `k=1` und `α₀=1` ist die adaptive EMA mathematisch gleichbedeutend mit dem gewichteten Durchschnitt.

    *   **Gewichtete Durchschnittsmethode (Average)**:
        *   `Coeff_Final = ((Ancien_Coeff * Poids_Ancien) + Coeff_New) / (Poids_Ancien + 1)`.
        *   `Poids_Ancien` entspricht der Anzahl der vorherigen Lernzyklen (Zähler).
        *   **Anfangsgewicht**: Der Zähler wird auf `auto_tpi_avg_initial_weight` (Standardwert 1) initialisiert. Dadurch kann dem Standard-Anfangswert mehr oder weniger Trägheit verliehen werden.
        *   Bei dieser Methode wird neuen Werten mit zunehmender Anzahl von Zyklen immer weniger Gewicht beigemessen (starke Stabilisierung auf lange Sicht).

#### 6. Algorithme Coefficient Extérieur (Détail)
**Algorithme :**
1.  **Calcul des Gaps**.
2.  **Calcul de l'Influence** : `Ratio_Influence = Gap_In / Gap_Out`.
3.  **Calcul du Coefficient Cible (Incrémental)** :
    *   `Correction = Kint * (Gap_In / Gap_Out)`.
    *   `Target_Outdoor = Current_Outdoor + Correction`.
    *   Si Gap_In est négatif (overshoot), la correction est négative -> **Kext diminue**.

4.  **Validation & Plafonnement** : 
    *   Vérification que le coefficient est fini et > 0.
    *   Plafond à 1.2 (légèrement supérieur à la recommandation 1.0 pour tolérance).
5.  **Lissage (EMA ou Moyenne Pondérée)** : 
    *   La nouvelle valeur cible (`Coeff_New = Target_Outdoor`) est lissée avec l'ancienne valeur.

#### 6. Cas d'Échec
Si aucune des priorités n'est déclenchée, le statut `no_valid_conditions` est enregistré.

### D. Sécurités et Détection d'Échecs
*   **Détection d'Échec** : Si la température évolue dans le mauvais sens (ex: baisse alors qu'on chauffe) de manière significative (> 1°C d'écart).
*   **Protection** : 3 échecs consécutifs désactivent l'apprentissage pour éviter la divergence.

### E. Sécurité d'Activation (Safety Logic)
Pour éviter un démarrage accidentel ou non souhaité de l'apprentissage :
1.  **Pré-requis Configuration** : Le service `set_auto_tpi_mode(True)` est rejeté si la fonctionnalité n'est pas explicitement activée dans la configuration du thermostat (`CONF_AUTO_TPI_MODE`).
2.  **Arrêt sur Changement de Config** : Au démarrage (ou rechargement après modification de config), si l'apprentissage était actif (état stocké) mais que la fonctionnalité est désormais désactivée dans la configuration, l'apprentissage est **forcé à l'arrêt** (`stop_learning()`).
3.  **Continuation de l'Apprentissage Extérieur (`auto_tpi_keep_ext_learning`)** :
    *   Le paramètre `auto_tpi_keep_ext_learning` modifie le critère d'arrêt de l'apprentissage du Coefficient Extérieur (`Kext`).
    *   **Logique de non-arrêt de Kext (Apprentissage)** : Lorsque cette option est cochée, le comptage des cycles pour `Kext` continue même après avoir atteint le minimum de 50 cycles, **tant que le Coefficient Intérieur (`Kint`) n'est pas stable**.
    *   **Logique de Persistance (`process_learning_completion`)** : L'enregistrement final des coefficients dans la configuration HA (`async_update_coefficients_config`) est toujours conditionné à la **stabilité des deux coefficients** (`is_int_finished` ET `is_ext_finished`).
    *   *Utilité* : Prolonge la fenêtre d'apprentissage de Kext pour une meilleure précision sans affecter le seuil de persistance requis.

---

## 4. Métriques de Qualité (Exposées par `AutoTpiSensor`)

*   **`confidence`** (0.0 - 1.0) : Fiabilité du modèle. Augmente avec le nombre de cycles (plafonné à 50 cycles pour le calcul de Kint et Kext), diminue avec les échecs.
*   **`time_constant`** (heures) : Inertie thermique estimée (`1 / coeff_indoor`).
*   **`heating_cycles_count`** : Nombre total de cycles observés.
*   **`coeff_int_cycles` / `coeff_ext_cycles`** : Nombre de cycles d'apprentissage validés pour chaque coefficient.
*   **`max_capacity_heat` / `max_capacity_cool`** : Capacité maximale détectée (en °C/h).
*   **`learning_start_dt`** : Date et heure du début de l'apprentissage (utile pour les graphiques).

---

## 5. Détection de Changement de Régime (Regime Change Detection)

### A. Principe

L'algorithme Auto TPI intègre un mécanisme de détection de **changement systémique de régime thermique** (ex: changement de saison, modification de l'isolation, ajout d'un radiateur). Ce mécanisme permet d'accélérer l'adaptation du modèle en cas de **biais systématique** détecté sur les erreurs d'apprentissage.

### B. Activation

La détection de changement de régime est **uniquement active** lorsque l'apprentissage continu est activé (`auto_tpi_continuous_learning: true`).

### C. Mécanisme

1.  **Suivi des Erreurs** :
    *   À chaque cycle d'apprentissage indoor réussi, l'erreur (`adjusted_theoretical - real_rise`) est enregistrée dans `state.recent_errors`.
    *   Seules les **20 dernières erreurs** sont conservées (fenêtre glissante).

2.  **Détection Statistique** :
    *   La méthode `_detect_regime_change` applique un **test t de Student** sur les 10 dernières erreurs.
    *   **Hypothèse nulle** : Les erreurs sont centrées autour de 0 (pas de biais systématique).
    *   **Hypothèse alternative** : Les erreurs ont une moyenne significative (biais systématique).
    *   **Seuil** : Si la statistique t > 2.0 (95% de confiance), un changement de régime est détecté.

3.  **Réponse Adaptative** :
    *   Si un changement de régime est détecté, le flag `state.regime_change_detected` est activé.
    *   La méthode `_get_adaptive_alpha` utilise ce flag pour **booster temporairement l'alpha** (jusqu'à 3x la valeur de base, plafonné à 0.15).
    *   **Effet** : Le coefficient EMA s'adapte plus rapidement aux nouvelles conditions.

4.  **Réinitialisation** :
    *   Le flag `regime_change_detected` est réinitialisé après le premier cycle d'apprentissage qui utilise l'alpha boosté.
    *   Cela garantit que le boost est **temporaire** et ne persiste pas après adaptation.

### D. Impact sur l'Apprentissage

*   **Avantage** : Permet une adaptation rapide en cas de changement brutal des conditions thermiques.
*   **Sécurité** : Le boost est limité (max 15%) et temporaire (réinitialisé après utilisation).
*   **Robustesse** : Le test statistique évite les fausses détections (bruit, anomalies ponctuelles).

---

## 6. Persistance et Restauration

## 5. Persistance et Restauration

*   **Fichier** : `.storage/versatile_thermostat_{unique_id}_auto_tpi_v2.json`
*   **Version** : 8
*   **Données** : Coefficients (Heat/Cool), compteurs, snapshot du dernier cycle, capacités maximales (`max_capacity_heat` / `max_capacity_cool`) et date de début (`learning_start_date`).
*   **Restauration** : Au démarrage d'Home Assistant, le `BaseThermostat` recharge cet état. Deux actions sont effectuées au chargement :
    1.  **Clamping (Plafonnement)**: Les coefficients intérieurs (`coeff_indoor_heat`/`cool`) chargés depuis le stockage sont **immédiatement plafonnés** à la valeur configurée de `CONF_AUTO_TPI_MAX_COEF_INT` (nouvellement prise en compte après un changement de configuration). Cela garantit que si un utilisateur baisse la limite, l'ancien coefficient (si supérieur) est ramené à la nouvelle limite pour les calculs futurs.
    2.  **Application des Valeurs** : Si des coefficients valides sont trouvés, que la configuration l'autorise (`auto_tpi_enable_update_config`) **ET** que l'apprentissage est actif (`learning_active`), ils écrasent les valeurs de la configuration HA au démarrage, si ces dernières ont été écrites. Sinon, les valeurs de configuration sont utilisées.
*   **Sécurité Concurrente** : L'écriture du fichier est protégée par un `asyncio.Lock` (`_save_lock`) pour éviter les "Race Conditions" si plusieurs sauvegardes sont déclenchées simultanément (ex: fin de cycle + interaction utilisateur). Cela garantit que le fichier temporaire `.tmp` n'est pas écrasé par un autre thread avant d'être renommé.
*   **Service de Calibration (`auto_tpi_calibrate_capacity`)** :
    *   Ce service permet de déterminer la **Capacité Adiabatique** du système (`max_capacity`) en analysant l'historique des capteurs.
    *   **Objectif** : Utiliser l'historique des capteurs `temperature_slope` et `power_percent` pour calculer la capacité adiabatique du radiateur (en °C/h).
    *   **Algorithme (V3 - Basé sur les capteurs)** :
        1.  **Récupération des Historiques** : Le service récupère l'historique des capteurs `sensor.{nom}_temperature_slope` et `sensor.{nom}_power_percent` sur la période spécifiée (par défaut 30 jours).
        2.  **Filtrage par Puissance** : Pour chaque point de l'historique du slope, on cherche la valeur de puissance correspondante. Seuls les points où `power >= min_power_threshold` (défaut 95%) sont conservés.
        3.  **Filtrage par Direction** : En mode `heat`, seuls les slopes positifs sont gardés (la température monte). En mode `cool`, seuls les slopes négatifs sont gardés.
        4.  **Élimination des Outliers** : La méthode IQR (Interquartile Range) est utilisée pour éliminer les valeurs aberrantes (pics dus au soleil, cuisson, etc.).
        5.  **Calcul du 75ème Percentile** : Le 75ème percentile des slopes filtrés est utilisé (plutôt que la médiane) pour biaiser vers les valeurs les plus élevées, plus proches de l'adiabatique.
        6.  **Correction Adiabatique** : Une compensation est appliquée : `Capacity_adiabatique = Slope_75p + Kext_config × ΔT_moyen`. Le Kext utilisé est celui configuré par l'utilisateur dans le config flow (pas la valeur apprise).
    *   **Résultats et Métriques** : Le service retourne :
        *   **`capacity`** : La capacité adiabatique estimée en °C/h.
        *   **`observed_capacity`** : Le 75ème percentile brut (avant correction).
        *   **`kext_compensation`** : La valeur de correction Kext × ΔT.
        *   **`avg_delta_t`** : Le ΔT moyen utilisé pour la correction.
        *   **`reliability`** : Indice de fiabilité en % basé sur le nombre d'échantillons et la variance.
        *   **`samples_used`** : Nombre d'échantillons utilisés après filtrage.
        *   **`outliers_removed`** : Nombre d'outliers éliminés par IQR.
        *   **`min_power_threshold`** : Le seuil de puissance utilisé.
        *   **`period`** : La durée en jours de l'historique analysé.

### G. Persistance et Restauration

*   **Fichier** : `.storage/versatile_thermostat_{unique_id}_auto_tpi_v2.json`
*   **Version** : 8
*   **Données** : Coefficients (Heat/Cool), compteurs, snapshot du dernier cycle, et capacités maximales (`max_capacity_heat` / `max_capacity_cool`).
*   **Restauration** : Au démarrage d'Home Assistant, le `BaseThermostat` recharge cet état. Une action est effectuée au chargement :
    1.  **Clamping (Plafonnement)**: Les coefficients intérieurs (`coeff_indoor_heat`/`cool`) chargés depuis le stockage sont **immédiatement plafonnés** à la valeur configurée de `CONF_AUTO_TPI_MAX_COEF_INT` (nouvellement prise en compte après un changement de configuration). Cela garantit que si un utilisateur baisse la limite, l'ancien coefficient (si supérieur) est ramené à la nouvelle limite pour les calculs futurs.
*   **Sécurité Concurrente** : L'écriture du fichier est protégée par un `asyncio.Lock` (`_save_lock`) pour éviter les "Race Conditions" si plusieurs sauvegardes sont déclenchées simultanément (ex: fin de cycle + interaction utilisateur). Cela garantit que le fichier temporaire `.tmp` n'est pas écrasé par un autre thread avant d'être renommé.
*   **Réinitialisation Complète (`reset_learning_data`)**:
    *   Cette méthode n'est plus exposée comme un service externe. Elle est utilisée en interne si un reset complet était nécessaire.
    *   **Action** : Réinitialisation complète de l'état d'apprentissage (`AutoTpiState`), incluant coefficients, compteurs, et capacités.
*   **Démarrage (`start_learning`)** : L'appel à `start_learning(reset_data)` (ex: via le service `set_auto_tpi_mode(true)` ou initialisation) :
    *   **Paramètre `reset_data`** (défaut: `True`) : Contrôle la réinitialisation des données d'apprentissage.
        *   Si `reset_data=True` : Réinitialise les compteurs, les coefficients (sauf si fournis) et la date de démarrage `learning_start_dt`. La capacité calibrée est **conservée**.
        *   Si `reset_data=False` : Reprend l'apprentissage en conservant les coefficients, les compteurs et la date de démarrage existants. Seul le flag `autolearn_enabled` est activé.
*   **Arrêt de l'apprentissage (`stop_learning`)** : L'appel à `stop_learning()` (ex: via le service `set_auto_tpi_mode` avec `auto_tpi_mode: false`) provoque :
    *   **Désactivation de l'apprentissage** : `autolearn_enabled` est mis à `False`, l'apprentissage s'arrête.
    *   **Préservation de l'état** : Tous les attributs appris (coefficients, compteurs, capacités) sont **conservés** en mémoire et persistés. Cela permet de reprendre l'apprentissage ultérieurement sans perdre les données acquises.
    *   **Synchronisation PropAlgorithm** : Les valeurs de configuration (`_tpi_coef_int`, `_tpi_coef_ext`) sont immédiatement appliquées à l'algorithme proportionnel (`PropAlgorithm.update_parameters()`) pour garantir que la régulation utilise les coefficients de configuration et non les coefficients appris.

## 9. Flux de Configuration (Config Flow)
    
La configuration de l'Auto TPI est intégrée dans le flux de configuration des thermostats **individuels** du Versatile Thermostat pour une meilleure expérience utilisateur.
Elle est **exclue** du flux de configuration de la configuration centrale, car chaque thermostat requiert ses propres paramètres d'apprentissage.

### A. Étapes (Thermostat Individuel)
1.  **Activation** : Une case à cocher "Activer l'apprentissage Auto TPI" (`auto_tpi_mode`) a été ajoutée à l'étape `TPI` standard.
2.  **Auto TPI - Général** (`auto_tpi_1`) :
    *   Si l'Auto TPI est activé, cette étape permet de configurer les paramètres généraux : mise à jour de la config, notifications, temps de chauffe/refroidissement, coefficient max.
3.  **Auto TPI - Puissance** (`auto_tpi_2`) :
    *   Elle permet de saisir manuellement les capacités de chauffe et de refroidissement (`auto_tpi_heating_rate`, `auto_tpi_cooling_rate`) en °C/h.
271 | 4.  **Auto TPI - Méthode** (`auto_tpi_2`) :
272 |     *   Choix de la méthode de calcul :
273 |         *   **Moyenne (Average)** : Utilise une moyenne pondérée qui accorde de moins en moins d'importance aux nouvelles valeurs. Idéale pour un apprentissage initial rapide et unique. Ne convient pas à l'apprentissage continu.
274 |         *   **Moyenne Mobile Exponentielle (EMA)** : Fortement recommandée pour l'apprentissage continu et le réglage fin à long terme. Elle donne un poids constant aux valeurs récentes, permettant l'adaptation aux changements.
275 | 5.  **Auto TPI - Paramètres Méthode** (`auto_tpi_3_avg` ou `auto_tpi_3_ema`) :
276 |     *   Configuration fine des paramètres spécifiques à la méthode choisie.
277 |     *   **Pour la méthode EMA** :
278 |         *   **Apprentissage initial** : Alpha (0.8 - 0.9) et Decay Rate (0.0) pour une adaptation rapide et de bonnes variations.
279 |         *   **Apprentissage continu/Réglage fin** : Alpha (0.1 - 0.2) et Decay Rate (0.1 - 0.2) pour un comportement très fin.

### B. Impact sur le Code
*   **`config_flow.py`** : La logique de navigation entre ces étapes a été simplifiée (suppression du branchement conditionnel basé sur `use_capacity_as_rate`).
*   **`config_schema.py`** : Les schémas de données pour chaque étape ont été définis.
*   **`const.py`** : Les constantes ont été nettoyées.

---

## 10. Tests (Mise à jour)

Une suite de tests unitaires complète a été mise en place pour garantir la robustesse de la fonctionnalité Auto TPI.

*   **Fichier de test** : `tests/test_auto_tpi.py`
*   **Couverture** :
    *   **Initialisation** : Vérification des valeurs par défaut et de l'initialisation du manager.
    *   **Persistance** : Chargement et sauvegarde de l'état (simulation du stockage).
    *   **Conditions d'apprentissage (`_should_learn`)** :
        *   Vérification des conditions d'activation (puissance, échecs, drift passif).
        *   Exclusion des cycles non pertinents.
    *   **Calibration (`calculate_capacity_from_history`)** :
        *   Test de la régression linéaire.
        *   Test de l'extraction des cycles à pleine puissance.
        *   Test du calcul de la Capacité (Capacity).
    *   **Apprentissage (`_perform_learning`)** :
        *   Apprentissage du coefficient intérieur (`_learn_indoor`).
        *   Apprentissage du coefficient extérieur (`_learn_outdoor`).
    *   **Cycle de vie** : Simulation complète d'un cycle (démarrage, fin, mise à jour des états).

Pour exécuter les tests :
```bash
pytest tests/test_auto_tpi.py