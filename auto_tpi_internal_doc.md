# Documentation Interne : Auto TPI (Algorithme d'Auto-Apprentissage et de Calibration)

Ce document décrit le fonctionnement interne de la fonctionnalité **Auto TPI** implémentée dans `auto_tpi_manager.py`.
**Mise à jour :** Version 2.4 - Remplacement de la détection de capacité en temps réel par un service de calibration via régression linéaire sur historique.

---

## 1. Principes Généraux

L'algorithme TPI (Time Proportional & Integral) calcule un pourcentage de puissance de chauffe (`power`) en fonction de l'écart entre la température de consigne et la température intérieure, et de l'influence de la température extérieure.

La formule de base est :
```python
Power = (Error_In * Coeff_Indoor) + (Error_Out * Coeff_Outdoor) + Offset
```
Où :
*   `Error_In` = Consigne - Température Intérieure
*   `Error_Out` = Consigne - Température Extérieure (ou delta équivalent)

L'objectif de l'Auto TPI est de trouver les valeurs optimales pour **`Coeff_Indoor`** et **`Coeff_Outdoor`**.

---

## 2. Architecture et Intégration

Le système repose sur une intégration étroite entre le manager, le thermostat de base et les capteurs.

### A. Composants Principaux

1.  **`AutoTpiManager` (Le Cerveau)** :
    *   Gère le cycle de vie de l'apprentissage.
    *   Persiste l'état (`AutoTpiState`) dans `.storage/versatile_thermostat_{unique_id}_auto_tpi_v2.json`.
    *   Gère la persistance de la capacité maximale calibrée (`max_capacity_heat` / `max_capacity_cool`).
    *   Expose les métriques de santé (confiance, constante de temps).
    *   **Rôle Actif** : Il pilote la boucle de régulation TPI via son propre timer interne (`_tick`).
    *   **Synchronisation & Persistance Finale** : Il gère la mise à jour des coefficients et capacités dans les entrées de configuration HA (`async_update_coefficients_config`, `async_update_capacity_config`).
    *   **Calibration** : Il expose la méthode `service_calibrate_capacity` qui orchestre la récupération d'historique et le calcul de capacité.
    *   **Notification** : Il gère la notification de fin d'apprentissage (`process_learning_completion`).

2.  **`BaseThermostat` (Le Chef d'Orchestre)** :
    *   Instancie `AutoTpiManager` dans `post_init` (avec les nouveaux paramètres issus du flux de configuration).
    *   Charge les données persistantes au démarrage.
    *   Délègue la gestion du cycle TPI au manager via `start_cycle_loop`.
    *   Fournit les données temps réel (`_get_tpi_data`) et exécute les ordres de cycle (`_on_tpi_cycle_start`).
    *   **Rôle de Délégation** : Le thermostat délègue toutes les tâches de synchronisation de configuration et de notification de fin d'apprentissage à l'AutoTpiManager. Son rôle se concentre sur l'instanciation, le chargement des données, la fourniture des données temps réel et l'exécution des ordres.
    *   **Démarrage Sécurisé** : Dans `async_startup`, le thermostat vérifie si le mode est `HEAT` ou `COOL` et force le démarrage de la boucle Auto TPI (`start_cycle_loop`). Cela garantit que l'apprentissage reprend après un redémarrage ou un rechargement de configuration, même si le mode HVAC n'a pas changé.

3.  **`AutoTpiSensor` (La Visibilité)** :
    *   Expose l'état de l'apprentissage et les métriques internes (nombre de cycles, confiance, coefficients calculés).
    *   **Création Conditionnelle** : L'entité est créée uniquement si :
        1.  Le thermostat est TPI-capable (type `switch`, `valve`, ou `climate` avec régulation valve).
        2.  L'algorithme TPI est sélectionné (`CONF_PROP_FUNCTION == PROPORTIONAL_FUNCTION_TPI`).
        3.  L'Auto TPI est activé dans la configuration (`CONF_AUTO_TPI_MODE == True`).
    *   **Nettoyage Automatique** : Lorsque l'Auto TPI est désactivé ou que l'algorithme TPI n'est plus utilisé, l'entité orpheline est automatiquement supprimée du registre des entités via `cleanup_orphan_entity()` (dans `commons.py`) lors du rechargement de la config entry. Cette fonction générique peut être réutilisée pour d'autres entités conditionnelles.

### B. Flux de Contrôle (La Boucle TPI)

Contrairement à une approche passive, c'est l'**`AutoTpiManager` qui rythme les cycles** lorsque l'apprentissage est actif.

1.  **Démarrage** :
    La boucle est démarrée (`manager.start_cycle_loop`) dans deux cas :
    *   **Changement de mode** : Lorsque le thermostat passe en mode `HEAT` (via `BaseThermostat.update_states`).
    *   **Initialisation** : Au démarrage de l'intégration (`async_startup`), si le mode restauré est déjà `HEAT`.

2.  **Boucle (`_tick`)** :
    Le manager exécute une boucle infinie (via timer `async_call_later`) toutes les `cycle_min` minutes.
    *   **Étape 1 : Récupération des Données** : Il appelle `BaseThermostat._get_tpi_data` pour obtenir les paramètres calculés par l'algorithme proportionnel (temps ON, temps OFF, pourcentage).
        > **Synchronisation des Coefficients** : Les coefficients appris sont propagés à `PropAlgorithm` au début de chaque appel à `_get_tpi_data()`, garantissant que le calcul TPI utilise toujours les dernières valeurs apprises.
    *   **Étape 2 : Snapshot** : Il appelle sa méthode interne `on_cycle_started` pour figer l'état (températures, consigne) au début du cycle. C'est ce snapshot qui servira de référence pour l'apprentissage à la fin du cycle.
    *   **Étape 3 : Exécution** : Il appelle `BaseThermostat._on_tpi_cycle_start`. Le thermostat propage alors l'événement aux entités sous-jacentes (`UnderlyingEntity`) pour qu'elles s'activent (ON) puis se désactivent (OFF) après le délai calculé.

3.  **Fin de Cycle** :
    Au tick suivant, le manager vérifie la durée écoulée. Si elle correspond à `cycle_min`, il valide la fin du cycle précédent (`on_cycle_completed`), puis déclenche la logique d'apprentissage (si conditions réunies).

**Précision sur le Mode de Régulation :** La logique d'apprentissage et le calcul de puissance se basent uniquement sur le `hvac_mode` du thermostat (`HEAT`). Le statut de commande de chauffe/refroidissement (`hvac_action`: `heating`/`idle`) n'est **pas** utilisé pour déterminer si l'apprentissage doit avoir lieu, car un cycle TPI complet inclut naturellement les phases `heating` (ON) et `idle` (OFF).

---

#### 6. Apprentissage de la Capacité (Max Check)
L'algorithme tente d'estimer la puissance physique de l'installation (`max_capacity_heat` en °C/h).
Cette valeur sert de référence pour calculer l'efficacité relative des cycles suivants.

**Conditions d'apprentissage :**
*   Mode bootstrap (count < 3) ou apprentissage continu.
*   **Puissance élevée** : Le cycle doit avoir injecté beaucoup d'énergie (Power > 80%) pour être représentatif.
*   **Montée significative** : La température doit avoir monté d'au moins 0.05°C.
*   **Gap suffisant** : L'écart à la consigne doit être suffisant (> 1°C en bootstrap, > 0.3°C sinon).

**Timeout de Bootstrap (Sécurité) :**
Pour éviter que les systèmes à forte inertie (ex: plancher chauffant) ne restent bloqués indéfiniment en mode bootstrap (coefficients agressifs 1.0/0.1), une sécurité a été ajoutée :
*   Si le système échoue à apprendre la capacité pendant **plus de 5 cycles consécutifs** en bootstrap...
*   ... l'algorithme force la sortie du mode bootstrap.
*   Il assigne une capacité par défaut de **0.3 °C/h** (valeur sécuritaire pour système lent).
*   L'apprentissage reprend ensuite normalement avec des coefficients non forcés.

**Pré-calibration avant Bootstrap (`_try_pre_bootstrap_calibration`) :**
Avant de démarrer le mode bootstrap agressif, le système tente de calibrer la capacité à partir de l'historique existant :
*   Appel interne à `service_calibrate_capacity` avec `min_power_threshold=80%` et `save_to_config=false`.
*   Si `reliability >= MIN_PRE_BOOTSTRAP_CALIBRATION_RELIABILITY` (20% par défaut) et `max_capacity > 0`, la capacité calibrée est utilisée et le bootstrap est sauté.
*   Sinon, le bootstrap normal se déclenche avec les coefficients agressifs.
*   **Justification du seuil** : Le bootstrap n'utilise que 3 mesures. Avec la formule de fiabilité `reliability = 100 × min(samples/20, 1) × max(0, 1 - CV/2)`, 20% correspond à environ 4 échantillons avec une variance moyenne, ce qui est déjà plus robuste que 3 cycles de bootstrap.

**Formule (inspirée de regul2.py) :**
1.  **Capacité Observée** : `Rise / (Duration * Efficiency)`
2.  **Correction Adiabatique** : On ajoute les pertes estimées pour obtenir la capacité "brute" (isolation parfaite).
    `Adiabatic_Capacity = Observed + (Kext * Delta_T)`
3.  **Lissage (EWMA)** :
    *   Alpha = 0.4 (Rapide) pendant le bootstrap.
    *   Alpha = 0.15 (Lent) ensuite.

### B. Capacité Maximale et Inertie
**(SUPPRIMÉ)** Le mécanisme d'apprentissage de la capacité en temps réel (`_detect_max_capacity`) a été remplacé par un service de calibration basé sur la régression linéaire d'historique. Voir Section **"Nouveau Service de Calibration"** ci-dessous.

### C. Logique de Mise à Jour (`_perform_learning`)

L'algorithme suit une séquence stricte de validations et de calculs.

#### 1. Pré-requis (Validations)
Avant tout calcul, les conditions suivantes sont vérifiées.
*   **Mode** : Le système doit être en mode `heat`.
*   **Delta Extérieur Suffisant** : `|Consigne - Temp_Ext| >= 0.1`.

#### 2. Cycle Interruption Handling

To ensure learning data is valid, cycles are invalidated (learning skipped) in specific interruption scenarios:

1.  **First Cycle Exclusion**: logic strictly requires a valid `previous_state` and `last_order`.
    -   When the thermostat restarts (e.g. after a Window Open -> Close event, or Home Assistant restart), the `last_order` is reset to 0.
    -   The learning logic explicitly rejects cycles where `last_order` is 0.
    -   **Result**: The first regulation cycle after any restart/interruption is **always ignored**, allowing the room temperature to stabilize before learning resumes.

2.  **Power Shedding (Overpowering)**:
    -   When the Power Manager detects an overpowering condition, it forces the underlying heaters OFF, but the Thermostat may remain in `HEAT` mode (depending on configuration).
    -   This breaks the correlation between "Heat Mode ON" and "Temperature Rise".
    -   **Result**: The `BaseThermostat` explicitly flags this state to `AutoTpiManager`. Any cycle containing a Power Shedding event is marked as `interrupted` and **learning is skipped**.

3.  **Heating/Cooling Failure**:
    -   If a failure (heating not effective or cooling not stopping) is detected by the `FeatureHeatingFailureDetectionManager`, the cycle is marked as interrupted and learning is skipped to avoid learning from a faulty system state.

#### 2.3. Near-Field vs Far-Field Learning Separation

The learning process is designed to separate the responsibilities of `Kint` (near-field, dynamic response) and `Kext` (far-field, equilibrium losses) to ensure robustness and prevent misattribution of errors.

*   **Case 1: Indoor Coefficient**. This is the primary learning mechanism. It adjusts `CoeffInt` based on the actual temperature rise versus the expected rise.
    *   **Important**: Indoor coefficient learning is **blocked** if the temperature gap is too small (< 0.05°C). This prevents `Kint` from overreacting to minor fluctuations when the system is near the setpoint.
*   **Case 2: Outdoor Coefficient**. If indoor learning was not possible and the temperature gap is significant (> 0.1°C), it adjusts `CoeffExt` to compensate for losses.
    *   **Important**: Outdoor coefficient learning is **blocked** if the temperature gap is too large (> 0.5°C), **except during active overshoot with significant power** (>= 10%). This ensures that `Kext` (which represents equilibrium losses) is not skewed by ramp-up dynamic issues (which are the responsibility of `Kint`), while still allowing correction when overshooting.
*   **Case 3: Rapid Corrections (Boost/Deboost)**. In parallel, the system monitors critical anomalies:

#### 2.5. Constantes Configurables

Les constantes suivantes sont définies en haut du fichier `auto_tpi_manager.py` et contrôlent le comportement de l'algorithme :

| Constante | Valeur par défaut | Description |
|-----------|-------------------|-------------|
| `MIN_KINT` | 0.05 | Seuil minimal pour Kint pour maintenir la réactivité à la température |
| `MIN_DEBOOST_CYCLES` | 20 | Nombre minimum de cycles d'apprentissage avant que le deboost Kint puisse s'activer |
| `OVERSHOOT_THRESHOLD` | 0.2°C | Seuil de dépassement de température pour déclencher la correction agressive de Kext |
| `OVERSHOOT_POWER_THRESHOLD` | 0.05 (5%) | Puissance minimale pour considérer le dépassement comme une erreur de Kext |
| `OVERSHOOT_CORRECTION_BOOST` | 2.0 | Multiplicateur pour alpha (EMA) ou diviseur de poids (Average) lors de la correction |
| `NATURAL_RECOVERY_POWER_THRESHOLD` | 0.20 (20%) | Puissance maximale en dessous de laquelle on considère qu'un retour à la consigne est naturel (pas d'apprentissage Kext) |
| `INSUFFICIENT_RISE_GAP_THRESHOLD` | 0.5°C | Écart minimum entre consigne et température pour déclencher la correction Kint si stagnation |
| `INSUFFICIENT_RISE_BOOST_FACTOR` | 1.08 | Facteur d'augmentation de Kint (8%) par cycle de stagnation |
| `MAX_CONSECUTIVE_KINT_BOOSTS` | 5 | Nombre maximum de boosts Kint consécutifs avant avertissement (chauffage sous-dimensionné) |
| `MIN_PRE_BOOTSTRAP_CALIBRATION_RELIABILITY` | 20.0 (%) | Fiabilité minimale de la calibration historique pour sauter le bootstrap |

#### 2.6. Cas 0 : Correction de Dépassement (`_correct_kext_overshoot`)

**Priorité maximale** : Cette correction est exécutée AVANT l'apprentissage Indoor et Outdoor.

**Problème résolu** : Dans les systèmes à forte inertie thermique (radiateurs à eau, chauffage central), Kext peut augmenter de façon agressive pendant la montée en température, mais ne redescend pas assez vite lors des dépassements. Cela provoque une surchauffe persistante.
    
**Activation :** Cette correction est optionnelle et doit être activée via le service `set_auto_tpi_mode` (paramètre `allow_kext_compensation_on_overshoot`).

**Conditions de déclenchement :**
1.  **Température qui ne descend pas malgré le dépassement** (mode Heat) : La température doit stagner ou monter (`Temp_Actuelle >= Temp_Début_Cycle - 0.02°C`) pour déclencher la correction. Si la température descend naturellement (ex: après baisse de consigne), le système fonctionne correctement.
2.  **Dépassement significatif** : `Temp_Actuelle > Consigne + OVERSHOOT_THRESHOLD` (0.2°C par défaut)
3.  **Puissance significative** : `power > OVERSHOOT_POWER_THRESHOLD` (5% par défaut)

*Note : Pour le mode Cool, la condition est inversée (température en baisse malgré le sous-dépassement).*

**Algorithme :**
1.  **Calcul de la réduction nécessaire** : 
    -   `needed_reduction = (overshoot × Kint) / delta_ext`
    -   Cette formule calcule combien Kext doit être réduit pour permettre à la température de redescendre.
2.  **Kext cible** : `target_kext = max(0.001, current_kext - needed_reduction)`
3.  **Application avec boost** :
    -   **Mode EMA** : `alpha_boosted = min(alpha × OVERSHOOT_CORRECTION_BOOST, 0.3)`
    -   **Mode Average** : `weight_boosted = max(1, weight / OVERSHOOT_CORRECTION_BOOST)`
4.  **Lissage** : Le nouveau Kext est calculé en mélangeant l'ancien avec le cible, en utilisant l'alpha/poids boosté.

**Résultat** : Si la correction s'applique, le cycle d'apprentissage s'arrête (pas d'apprentissage Indoor/Outdoor pour ce cycle).

#### 2.7. Cas 0.5 : Correction de Stagnation (`_correct_kint_insufficient_rise`)

**Problème résolu** : Lorsque la température stagne ou baisse malgré un écart significatif avec la consigne (> 0.3°C) et que la puissance n'est pas à saturation, Kint est probablement trop bas. Sans cette correction, le système tombe dans l'apprentissage Outdoor et augmente Kext à tort.
    
**Activation :** Cette correction est optionnelle et doit être activée via le service `set_auto_tpi_mode` (paramètre `allow_kint_boost_on_stagnation`).

**Conditions de déclenchement :**
1.  **Écart significatif** : `target_diff > INSUFFICIENT_RISE_GAP_THRESHOLD` (0.5°C par défaut)
2.  **Température stagnante** : `temp_progress < 0.02°C` (la température n'a pas augmenté pendant le cycle)
3.  **Puissance non saturée** : `power < 0.99` (le système peut encore augmenter la puissance)
4.  **Limite non atteinte** : `consecutive_boosts < MAX_CONSECUTIVE_KINT_BOOSTS` (5 par défaut)

**Algorithme :**
1.  **Calcul de la cible (Target Kint)** :
    -   `gap_factor = min(target_diff / 0.3, 2.0)`
    -   `boost_percent = (0.08 × gap_factor)`
    -   `target_kint = current_kint * (1.0 + boost_percent)`
2.  **Application pondérée (Cohérence avec apprentissage)** :
    -   Pour éviter des sauts brutaux si le modèle est déjà fiable (nombre de cycles élevé), on applique la correction comme une "observation pondérée", exactement comme pour l'apprentissage standard mais avec un **poids boosté** (car c'est une correction urgente).
    -   **Méthode Moyenne** : `weight = effective_count / OVERSHOOT_CORRECTION_BOOST`. On fait la moyenne entre `current` et `target`.
    -   **Méthode EMA** : `alpha = adaptive_alpha * OVERSHOOT_CORRECTION_BOOST`. On applique l'EMA vers `target`.
3.  **Plafonnement** : Kint est plafonné à `_max_coef_int` et floored à `MIN_KINT`.
4.  **Incrémentation** : `consecutive_boosts += 1`

**Protection contre le sous-dimensionnement :**
-   Si `consecutive_boosts >= MAX_CONSECUTIVE_KINT_BOOSTS` :
    -   Le boost est ignoré (le système ne booste plus Kint)
    -   Une notification persistent est envoyée (si activé) pour alerter l'utilisateur
    -   L'apprentissage normal (CASE 1 et 2) continue
-   Le compteur `consecutive_boosts` est réinitialisé à 0 dès que l'apprentissage indoor réussit (la température monte)

**Résultat** : Si la correction s'applique, le cycle d'apprentissage s'arrête. Le status est `corrected_kint_insufficient_rise` ou `max_kint_boosts_reached`.

#### 3. Cas 1 : Apprentissage du Coefficient Intérieur (`_learn_indoor`)


C'est la méthode privilégiée, mais elle est désormais soumise à des conditions strictes pour éviter les faux positifs et laisser sa chance à l'apprentissage extérieur.

**Conditions d'activation :**
1.  **Puissance non saturée** : `0 < power < 0.99` (on n'apprend pas à saturation sauf détection capacité).
2.  **Progression significative** : `temp_progress > 0.05°C` (évite d'apprendre sur du bruit).
3.  **Gap significatif** : `target_diff > 0.01°C` (il reste du chemin à parcourir).

**Si ces conditions sont réunies :**
L'algorithme tente d'apprendre le coefficient indoor.
*   **Succès** : Si `_learn_indoor` retourne `True`, le cycle d'apprentissage s'arrête ici (`return`).
*   **Échec** : Si `_learn_indoor` échoue (ex: ratio invalide, montée trop faible malgré le pré-check), le système **continue** vers l'apprentissage outdoor.

(Voir section **Algorithme Coefficient Intérieur (Détail)** ci-dessous).

#### 4. Cas 2 : Apprentissage du Coefficient Extérieur (`_learn_outdoor`)
L'apprentissage extérieur est tenté si l'apprentissage Indoor n'a pas abouti.

**Conditions d'activation :**
1.  **Direction Extérieure Cohérente** : Heat (`Text < Consigne`).
2.  **Gap Significatif** : `abs(gap_in) > 0.05` (On cherche à corriger même les petits écarts persistants).

**Validation Intelligente (Overshoot) :**
*   **Problème** : Un overshoot (T_in > Consigne en Heat) peut être dû au soleil (= anomalie externe) OU à un coefficient Kext trop fort.
*   **Solution** : On regarde la puissance.
    *   Si **Power < 1%** et Overshoot : C'est probablement le soleil (chauffage coupé), on ignore.
    *   Si **Power >= 1%** et Overshoot : Le chauffage tourne ALORS QU'ON est au dessus de la consigne. C'est que le terme Kext est trop fort (il force du chauffage inutile). **On apprend** (ce qui fera baisser Kext).
    *   *Note* : Le seuil a été abaissé de 20% à 1% pour permettre la redescente des coefficients.
    
**Protection Directionnelle (Natural Recovery) :**   
*   **Problème** : Lors d'une baisse de consigne (ex: 21° -> 19°), la température est au-dessus de la consigne (Overshoot) et le chauffage peut être encore légèrement actif (Kext). Si l'algorithme apprend à ce moment, il va baisser Kext alors que la température est déjà en train de descendre naturellement vers la cible.
*   **Solution** : Si on est en Overshoot (Temp > Consigne en Heat) MAIS que la température est en train de descendre (`Temp < Last_Temp`) **ET que la puissance est basse** (`< NATURAL_RECOVERY_POWER_THRESHOLD`, soit 20%), on **saute l'apprentissage**.
*   **Exception Overshoot avec puissance significative** : Si la puissance est >= 20%, on considère que le système chauffe activement malgré l'overshoot. Cela indique que Kext est trop élevé et doit être corrigé → l'apprentissage a lieu.
*   *Même logique pour le mode Cool (Undershoot mais température qui remonte).*

#### 5. Algorithme Coefficient Intérieur (Détail)
 
 **Algorithme de calcul Indoor :**
 1.  **Sécurité** : `real_rise` doit être > 0.01°C (filtrage du bruit capteur).
 2.  **Capacité de Référence (`ref_capacity`)** :
     *   La Capacité de Référence est la **capacité adiabatique** du système (mesurée en °C/h). Elle est calculée de manière externe par le service **`auto_tpi_calibrate_capacity`** et stockée dans `max_capacity_heat`.
     *   *Fallback* : Si aucune capacité n'est encore calibrée (`max_capacity` <= 0), on utilise une valeur par défaut de **1.0 °C/h** pour permettre le démarrage de l'apprentissage du Kint.
     *   **Si la capacité est nulle ou non définie** (et qu'aucun fallback ne s'applique), l'apprentissage est sauté pour ce cycle (statut `no_capacity_defined`).
 3.  **Calcul de la Capacité Effective (Seuil de Saturation Dynamique)** :
     *   **Principe** : Avant de calculer la montée théorique, on "réapplique" les pertes thermiques à la Capacité de Référence pour obtenir la capacité réelle du moment.
     *   $C_{eff} = C_{ref} \cdot (1 - K_{ext} \cdot \Delta T_{ext})$
     *   $C_{eff}$ est la capacité maximale réelle de montée en température en °C/h dans les conditions météo actuelles.
     *   Cette valeur ($C_{eff}$) est utilisée pour le calcul du `saturation_threshold` qui est désormais dynamique.
 4.  **Calcul de la Montée Maximale Possible (`max_achievable_rise`)** :
     *   `max_achievable_rise = effective_capacity (°C/h) * cycle_duration (h) * efficiency`.
     *   *Exemple* : Si la capacité effective est 2.0 °C/h, le cycle dure 15 min (0.25h) et l'efficacité est 80%, alors `max_achievable_rise = 2.0 * 0.25 * 0.8 = 0.4°C`.
 5.  **Calcul du Delta Théorique Ajusté** :
     *   `adjusted_theoretical = min(target_diff, max_achievable_rise)`.
     *   **On vise à combler tout l'écart** (`target_diff`), **mais plafonné par la capacité physique**.
     *   *Raison* : Il est inutile de demander au coefficient d'atteindre une montée physiquement impossible. Cela évite que le coefficient ne s'envole inutilement (saturation) face à de grands écarts.
 6.  **Calcul du Ratio** : 
     *   `Ratio = (adjusted_theoretical / real_rise) * aggressiveness`.
     *   **L'aggressiveness** (défaut 0.9) est appliqué directement au ratio pour obtenir des coefficients plus conservateurs.
     *   *Effet* : Un `aggressiveness` de 0.9 réduit systématiquement le ratio cible de 10%, ce qui donne des coefficients plus faibles.
 7.  **Nouveau Coefficient** : `Coeff_New = Ancien_Coeff * Ratio`.
 8.  **Validation et Plafond** :
     *   Doit être fini et > 0.
     *   **Plafond (Cap)** : Si `Coeff_New > auto_tpi_max_coef_int` (défaut 0.9), il est ramené à ce plafond. Cela évite des coefficients trop agressifs qui créent des oscillations. Ce paramètre est configurable (max 3.0).
     *   **Plancher (Floor)** : Si `Coeff_Final < MIN_KINT` (défaut 0.05), il est remonté à ce plancher. Cela garantit que le thermostat reste réactif à la température intérieure et évite qu'il ne devienne entièrement dépendant de Kext.
 9.  **Calcul Final (Selon la méthode configurée)** :
    L'utilisateur peut choisir entre deux méthodes de calcul via la configuration :

    *   **Méthode EMA (Exponential Moving Average) - Défaut** :
        *   `Coeff_Final = (Ancien_Coeff * (1 - Alpha)) + (Coeff_New * Alpha)`.
        *   `Alpha` est configurable (`auto_tpi_ema_alpha`, défaut 0.2).
        *   Permet un lissage où les valeurs récentes ont un poids fixe (ex: 20%).
        *   **Alpha Adaptatif** : En méthode EMA, alpha décroît selon `α(n) = α₀ / (1 + k·n)`. Cela unifie conceptuellement les méthodes EMA et Average : avec `k=1` et `α₀=1`, l'EMA adaptatif est mathématiquement équivalent à la moyenne pondérée.

    *   **Méthode Moyenne Pondérée (Average)** :
        *   `Coeff_Final = ((Ancien_Coeff * Poids_Ancien) + Coeff_New) / (Poids_Ancien + 1)`.
        *   `Poids_Ancien` correspond au nombre de cycles d'apprentissage précédents (compteur).
        *   **Poids Initial** : Le compteur est initialisé à `auto_tpi_avg_initial_weight` (défaut 1). Cela permet de donner plus ou moins d'inertie à la valeur initiale par défaut.
        *   Cette méthode donne de moins en moins de poids aux nouvelles valeurs au fur et à mesure que le nombre de cycles augmente (stabilisation forte sur le long terme).

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
*   **Détection d'Échec** : Si la température évolue dans le mauvais sens (ex: baisse alors qu'on chauffe) de manière significative (> 1°C d'écart) **ET que le système est à saturation de puissance** (power >= saturation_threshold). Une variation de température à puissance partielle est considérée comme une situation d'apprentissage normale, non un échec.
*   **Protection (Mode Standard)** : 3 échecs consécutifs désactivent l'apprentissage pour éviter la divergence.
*   **Protection (Mode Continu)** : En mode apprentissage continu (`continuous_learning`), les 3 échecs consécutifs **n'arrêtent pas** l'apprentissage. Le système se contente de loguer un avertissement, de réinitialiser le compteur d'échecs, et de continuer l'apprentissage en ignorant les cycles fautifs.

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
*   **`max_capacity_heat`** : Capacité maximale détectée (en °C/h).
*   **`learning_start_dt`** : Date et heure du début de l'apprentissage (utile pour les graphiques).
*   **`allow_kint_boost_on_stagnation`** : Indique si le boost de Kint en cas de stagnation est activé.
*   **`allow_kext_compensation_on_overshoot`** : Indique si la correction de Kext en cas d'overshoot est activée.
*   **`capacity_heat_status`** : Statut de l'apprentissage de la capacité thermique (`learning` ou `learned`).
*   **`capacity_heat_value`** : La valeur de la capacité thermique apprise (en °C/h).
*   **`capacity_heat_count`** : Le nombre de cycles de bootstrap effectués pour l'apprentissage de la capacité.

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



*   **Fichier** : `.storage/versatile_thermostat_{unique_id}_auto_tpi_v2.json`
*   **Version** : 8
*   **Données** : Coefficient, compteurs, snapshot du dernier cycle, capacités maximales (`max_capacity_heat`) et date de début (`learning_start_date`).
*   **Restauration** : Au démarrage d'Home Assistant, le `BaseThermostat` recharge cet état. Deux actions sont effectuées au chargement :
    1.  **Clamping (Plafonnement)**: Les coefficients intérieurs (`coeff_indoor_heat`/`cool`) chargés depuis le stockage sont **immédiatement plafonnés** à la valeur configurée de `CONF_AUTO_TPI_MAX_COEF_INT` (nouvellement prise en compte après un changement de configuration). Cela garantit que si un utilisateur baisse la limite, l'ancien coefficient (si supérieur) est ramené à la nouvelle limite pour les calculs futurs.
    2.  **Application des Valeurs** : Si des coefficients valides sont trouvés, que la configuration l'autorise (`auto_tpi_enable_update_config`) **ET** que l'apprentissage est actif (`learning_active`), ils écrasent les valeurs de la configuration HA au démarrage, si ces dernières ont été écrites. Sinon, les valeurs de configuration sont utilisées.
*   **Sécurité Concurrente** : L'écriture du fichier est protégée par un `asyncio.Lock` (`_save_lock`) pour éviter les "Race Conditions" si plusieurs sauvegardes sont déclenchées simultanément (ex: fin de cycle + interaction utilisateur). Cela garantit que le fichier temporaire `.tmp` n'est pas écrasé par un autre thread avant d'être renommé.
*   **Service de Calibration (`auto_tpi_calibrate_capacity`)** :
    *   Ce service permet de déterminer la **Capacité Adiabatique** du système (`max_capacity`) en analysant l'historique des capteurs.
    *   **Objectif** : Utiliser l'historique des capteurs `temperature_slope` et `power_percent` pour calculer la capacité adiabatique du radiateur (en °C/h).
    *   **Algorithme (V3 - Basé sur les capteurs)** :
        1.  **Récupération des Historiques** : Le service récupère l'historique des capteurs `sensor.{nom}_temperature_slope` et `sensor.{nom}_power_percent` sur la période spécifiée (par défaut 30 jours).
        2.  **Filtrage par Puissance** : Pour chaque point de l'historique du slope, on cherche la valeur de puissance correspondante en utilisant une logique **sample-and-hold** : on prend la dernière valeur de puissance connue avant ou au moment du timestamp du slope. Cette approche gère correctement les capteurs "event-driven" qui ne rapportent que les changements (fréquent quand la puissance reste à 100% pendant de longues périodes). Seuls les points où `power >= min_power_threshold` (défaut 95%) sont conservés.
        3.  **Filtrage par Direction** : Seuls les slopes positifs sont gardés (la température monte).
        4.  **Élimination des Outliers** : La méthode IQR (Interquartile Range) est utilisée pour éliminer les valeurs aberrantes (pics dus au soleil, cuisson, etc.).
        5.  **Calcul du 75ème Percentile** : Le 75ème percentile des slopes filtrés est utilisé (plutôt que la médiane) pour biaiser vers les valeurs les plus élevées, plus proches de l'adiabatique.
        6.  **Correction Adiabatique** : Une compensation est appliquée : `Capacity_adiabatique = Slope_75p + Kext_config × ΔT_moyen`. Le Kext utilisé est celui configuré par l'utilisateur dans le config flow (pas la valeur apprise).
        7.  **Application de la Marge de Sécurité** : Une marge de sécurité (défaut 20%, configurable via `capacity_safety_margin`) est soustraite de la capacité calculée pour obtenir la **Capacité Recommandée**. C'est cette valeur qui sera utilisée pour éviter de sous-estimer la puissance de chauffe. `Recommended = Capacity × (1 - margin)`.
    *   **Résultats et Métriques** : Le service retourne :
        *   **`max_capacity`** : La capacité adiabatique estimée brute en °C/h.
        *   **`recommended_capacity`** : La capacité recommandée après application de la marge (en °C/h). **C'est la valeur sauvegardée**.
        *   **`margin_percent`** : La marge de sécurité appliquée (en %).
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
*   **Données** : Coefficients (Heat/Cool), compteurs, snapshot du dernier cycle, et capacités maximales (`max_capacity_heat`).
*   **Restauration** : Au démarrage d'Home Assistant, le `BaseThermostat` recharge cet état. Une action est effectuée au chargement :
    1.  **Clamping (Plafonnement)**: Les coefficients intérieurs (`coeff_indoor_heat`/`cool`) chargés depuis le stockage sont **immédiatement plafonnés** à la valeur configurée de `CONF_AUTO_TPI_MAX_COEF_INT` (nouvellement prise en compte après un changement de configuration). Cela garantit que si un utilisateur baisse la limite, l'ancien coefficient (si supérieur) est ramené à la nouvelle limite pour les calculs futurs.
*   **Sécurité Concurrente** : L'écriture du fichier est protégée par un `asyncio.Lock` (`_save_lock`) pour éviter les "Race Conditions" si plusieurs sauvegardes sont déclenchées simultanément (ex: fin de cycle + interaction utilisateur). Cela garantit que le fichier temporaire `.tmp` n'est pas écrasé par un autre thread avant d'être renommé.
*   **Réinitialisation Complète (`reset_learning_data`)**:
    *   Cette méthode n'est plus exposée comme un service externe. Elle est utilisée en interne si un reset complet était nécessaire.
    *   **Action** : Réinitialisation complète de l'état d'apprentissage (`AutoTpiState`), incluant coefficients, compteurs, et capacités.
*   **Démarrage (`start_learning`)** : L'appel à `start_learning(reset_data, ...)` (ex: via le service `set_auto_tpi_mode`) :
    *   **Paramètres Optionnels** : le service accepte désormais `allow_kint_boost_on_stagnation` (défaut `False`) et `allow_kext_compensation_on_overshoot` (défaut `False`) pour activer les logiques de correction spécifiques.
    *   **Paramètre `reset_data`** (défaut: `True`) : Contrôle la réinitialisation des données d'apprentissage.
        *   Si `reset_data=True` : Réinitialise les compteurs, les coefficients (sauf si fournis), la date de démarrage `learning_start_dt` et les paramètres du cycle courant (`current_cycle_params`). La capacité calibrée est **conservée**. `last_learning_status` est mis à `learning_started`.
        *   Si `reset_data=False` : Reprend l'apprentissage en conservant les coefficients, les compteurs et la date de démarrage existants. Seul le flag `autolearn_enabled` est activé. `last_learning_status` est mis à `learning_resumed`.
*   **Arrêt de l'apprentissage (`stop_learning`)** : L'appel à `stop_learning()` (ex: via le service `set_auto_tpi_mode` avec `auto_tpi_mode: false`) provoque :
    *   **Désactivation de l'apprentissage** : `autolearn_enabled` est mis à `False`, l'apprentissage s'arrête. `last_learning_status` est mis à `learning_stopped`.
    *   **Préservation de l'état** : Tous les attributs appris (coefficients, compteurs, capacités) sont **conservés** en mémoire et persistés. Cela permet de reprendre l'apprentissage ultérieurement sans perdre les données acquises.
    *   **Synchronisation PropAlgorithm** : Les valeurs de configuration (`_tpi_coef_int`, `_tpi_coef_ext`) sont immédiatement appliquées à l'algorithme proportionnel (`PropAlgorithm.update_parameters()`) pour garantir que la régulation utilise les coefficients de configuration et non les coefficients appris.

## 9. Flux de Configuration (Config Flow)
    
La configuration de l'Auto TPI est intégrée dans le flux de configuration des thermostats **individuels** du Versatile Thermostat. Elle a été restructurée pour simplifier l'expérience utilisateur tout en conservant la puissance de personnalisation pour les experts.

### A. Étapes (Thermostat Individuel)

1.  **Activation** : Une case à cocher "Activer l'apprentissage Auto TPI" (`auto_tpi_mode`) est présente à l'étape `TPI` standard.

2.  **Auto TPI - Configuration** (`auto_tpi_configuration`) :
    *   Cette étape est la seule présentée par défaut.
    *   **Type d'Apprentissage** (`auto_tpi_learning_type`) : Sélecteur principal déterminant la stratégie :
        *   **Découverte (Discovery)** : Pour une première activation. Utilise la méthode **Moyenne Pondérée** (poids 1). Idéal pour converger rapidement vers des coefficients stables.
        *   **Ajustement fin (Fine Tuning)** : Pour affiner des réglages sur la durée. Utilise la méthode **EWMA** (Alpha 0.08, Decay 0.12).
    *   **Taux de chauffe** (`auto_tpi_heating_rate`) : Capacité de montée en température (laisser à 0 pour auto-détection).
    *   **Paramètres de Base** : Temps de chauffe/refroidissement et **Agressivité** (curseur).
    *   **Activer les paramètres avancés** : Case à cocher permettant d'accéder aux réglages de l'algorithme choisi.

3.  **Auto TPI - Paramètres Méthode** (`auto_tpi_avg_settings` ou `auto_tpi_ema_settings`) :
    *   *Visible uniquement si "Activer les paramètres avancés" est coché.*
    *   L'écran affiché dépend de la méthode implicite liée au "Type d'Apprentissage" (Moyenne pour Découverte, EWMA pour Ajustement fin).
    *   Permet d'ajuster finement les hyperparamètres (Poids initial pour Moyenne, Alpha/Decay pour EWMA).

### B. Simplification et Constantes
Pour alléger l'interface, plusieurs options techniques ont été retirées de l'interface utilisateur et fixées dans le code (Hardcoded Constants) dans `ThermostatTPI` et `AutoTpiManager` :
*   `auto_tpi_max_coef_int` : **1.0** (Défini dans `AutoTpiManager`). Le coefficient interne ne peut dépasser 1.0.
*   `auto_tpi_enable_update_config` : **True** (La configuration est toujours mise à jour avec les valeurs apprises).
*   `auto_tpi_enable_notification` : **True** (Les notifications de fin d'apprentissage sont toujours envoyées).
*   `auto_tpi_keep_ext_learning` : **True** (L'apprentissage externe continue tant que l'interne n'est pas stable).
*   `auto_tpi_continuous_learning` : **False** (L'apprentissage s'arrête une fois stable par défaut, sauf réactivation manuelle).

### C. Impact sur le Code
*   **`config_flow.py`** : Implémente la logique de branchement direct (Général -> Méthode) et l'application des valeurs par défaut.
*   **`config_schema.py`** : Définit les nouveaux schémas (`STEP_AUTO_TPI_1_SCHEMA`, `STEP_AUTO_TPI_3_AVG_SCHEMA`, `STEP_AUTO_TPI_3_EMA_SCHEMA`).
*   **`const.py`** : Nettoyage des constantes obsolètes.

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
