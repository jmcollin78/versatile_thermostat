Ce document décrit le fonctionnement interne de la fonctionnalité **Auto TPI** implémentée dans `auto_tpi_manager.py`.

---

## 1. Principes Généraux

L'algorithme TPI (Time Proportional & Integral) calcule un pourcentage de puissance de chauffe (`power`) en fonction de l'écart entre la consigne et la température intérieure, et de l'écart entre la consigne et la température extérieure.

```python
Power = (Error_In * Coeff_Indoor) + (Error_Out * Coeff_Outdoor)
```
Où :
*   `Error_In` = Consigne - Température Intérieure
*   `Error_Out` = Consigne - Température Extérieure

L'Auto TPI apprend **`Coeff_Indoor`** (Kint) et **`Coeff_Outdoor`** (Kext) par petits pas, sans identifier de modèle de la pièce.

Références (modèle 1R1C `dT/dt = a·P − b·(T − T_ext)`) :
*   Kext visé : `b / a`, la puissance qui compense les pertes à la consigne.
*   Kint visé : `1 / (a · T_cl)`, qui referme l'écart avec une constante de temps `T_cl` quand Kext compense les pertes.
*   `T_cl = 2 · (heater_heating_time + cycle_min / 2)`, borné à [30 ; 180] min (`closed_loop_time_min`).

Ces formules servent de référence aux tests de simulation ; elles ne sont pas calculées en ligne.

---

## 2. Architecture et Intégration

### A. Composants Principaux

1.  **`AutoTpiManager`** :
    *   Gère le cycle de vie de l'apprentissage (`start_learning`, `stop_learning`, `process_learning_completion`).
    *   Persiste l'état (`AutoTpiState`) dans `.storage/versatile_thermostat.auto_tpi.<unique_id>`. `AutoTpiState.from_dict` ignore les clés inconnues.
    *   Écrit les coefficients appris dans la config entry (`async_update_learning_data`) sans recharger l'intégration (`skip_reload_on_config_update`), puis appelle `_coefficients_written_callback` : le `TPIHandler` (`_apply_written_coefficients`) les applique aussitôt à `TpiAlgorithm` (fin de session, Kext continu).
    *   Envoie la notification de fin d'apprentissage.

2.  **`TPIHandler`** (`prop_handler_tpi.py`) :
    *   Instancie le manager avec `heater_heating_time` et `auto_tpi_continuous_kext`.
    *   À chaque `control_heating`, appelle `manager.update(...)` (températures, consigne, mode, délestage, chaudière centrale, défaut de chauffe) puis `manager.calculate()`. Pendant une session, les coefficients courants sont poussés dans `TpiAlgorithm` ; s'ils ont changé, la demande est recalculée avant d'être transmise au `CycleScheduler`.
    *   Enregistre `on_cycle_started` / `on_cycle_completed` comme callbacks du `CycleScheduler` (`on_scheduler_ready`). La puissance réellement appliquée (`e_eff`) est passée en fin de cycle.
    *   Au chargement (`async_added_to_hass`), si une session est active, les coefficients restaurés sont appliqués au thermostat et à `TpiAlgorithm`.

3.  **`AutoTpiSensor`** :
    *   Expose l'état (`active` / `off`) et les métriques (cycles, fenêtres Kint, échantillons Kext, confiance, coefficients calculés, dernier statut).
    *   Accède au manager via la propriété publique `auto_tpi_manager` du thermostat.
    *   Créé uniquement si l'algorithme TPI est sélectionné et l'Auto TPI activé ; sinon l'entité orpheline est supprimée par `cleanup_orphan_entity()` (`commons.py`).

### B. Flux d'un Cycle

1.  `update()` : stocke les valeurs courantes. Un changement de consigne (> 0,05) ou de mode horodate `_last_setpoint_change`, remet `_setpoint_reached` à `False` et ferme la fenêtre Kint. `_setpoint_reached` repasse à `True` dès que |consigne − T| < `KINT_MIN_GAP`.
2.  `on_cycle_started()` : snapshot (`last_temp_in`, `last_temp_out`, `last_order`, `last_power`, `last_state`).
3.  `on_cycle_completed(e_eff)` :
    *   rejette les cycles trop courts (retour immédiat) et marque les cycles trop longs (`cycle_gap_detected`, aucun apprentissage) ;
    *   **Phase Kext** : `_should_learn()` puis `_perform_learning()`, ou `_learn_kext_continuous()` hors session ;
    *   **Phase Kint** : `_process_kint_window(cycle_valid)` ;
    *   remet `_current_cycle_interrupted` à `False` (le délestage ne concerne que le cycle terminé) ;
    *   `process_learning_completion()` puis sauvegarde.

La logique se base sur le `hvac_mode` (`heat` / `cool`), pas sur `hvac_action`.

---

## 3. Apprentissage de Kint (`_process_kint_window`, `_learn_kint_from_window`)

Kint est appris sur des fenêtres de plusieurs cycles, car sur un cycle de 5 min la variation de température est du même ordre que la résolution du capteur.

*   **Cycle valide** : pas de `cycle_gap_detected`, pas de délestage, chaudière centrale active, pas de défaut de chauffe, `0 < last_power < 1`, mode `heat` ou `cool`. Un cycle invalide ferme la fenêtre (`_reset_kint_window`) et horodate `_kint_window_hold_since`.
*   **Ouverture** : au moins `T_cl / 2` après `_kint_window_hold_since` (retard de l'émetteur), et écart ≥ `KINT_MIN_GAP` (0,3 °C). Un cycle saturé (100 %) ferme la fenêtre sans mettre à jour `_kint_window_hold_since` : l'émetteur tourne déjà, sinon une montée courte après saturation (émetteur lent et puissant) n'ouvrirait jamais de fenêtre.
*   **Clôture** : après une durée fixée à l'ouverture par `_kint_window_duration` : `KINT_WINDOW_RISE / vitesse` (0,3 °C), vitesse mesurée sur `KINT_RATE_LOOKBACK_MINUTES` (20 min) avant la fenêtre (`_recent_temps`, enregistré en fin de cycle), bornée à [max(10 min, 2 cycles) ; max(30 min, T_cl)]. Données antérieures à la fenêtre uniquement : pas de biais de sélection. La fenêtre suivante démarre au même point si l'écart est encore ≥ 0,3 °C. Logs DEBUG à l'ouverture, à la fermeture sans apprentissage et quand la fenêtre franchit la consigne.
*   **Acceptation** : uniquement sur la durée et l'écart de départ. Elle ne dépend jamais de la variation mesurée, ce qui évite le biais de sélection.
*   **Pas** :
    ```
    mean_gap    = consigne − (T_début + T_fin) / 2      (inversé en cool)
    target_rate = mean_gap / T_cl
    rate        = (T_fin − T_début) / durée               (inversé en cool)
    ratio       = target_rate / rate   (KINT_MAX_STEP si rate ≤ 0)
    Kint        = clamp(Kint · clamp(ratio, 1/KINT_MAX_STEP, KINT_MAX_STEP), MIN_KINT, MAX_KINT)
    ```
    Si `mean_gap ≤ 0`, la fenêtre n'est pas utilisée (`kint_window_crossed_setpoint`).
*   Le compteur `coeff_indoor_autolearn` démarre à `KINT_COUNT_START` (1). Le pas borné converge vers la médiane du ratio.

---

## 4. Apprentissage de Kext (`_perform_learning`, `_learn_outdoor`)

### A. Pré-requis (`_should_learn`)
*   Session active ou Kext continu activé.
*   `0 < last_power < 1`, cycle non interrompu, chaudière centrale active, pas de défaut de chauffe.
*   Pas de premier cycle après un arrêt, consigne non nulle, |consigne − T_ext| ≥ 1 °C.

### B. Stabilisation (`_is_settled_for_kext`)
*   Au moins `KEXT_SETTLE_FACTOR · T_cl` (3) depuis le dernier changement de consigne,
*   et `_setpoint_reached`, ou au moins `KEXT_FORCE_SETTLE_FACTOR · T_cl` (12) pour qu'un Kext très faux (écart statique important) reste corrigeable.
*   Sinon statut `kext_waiting_settling`. Cette condition évite d'apprendre Kext pendant la fin d'une montée en température (biais à la hausse pour les émetteurs peu puissants).

### C. Calcul
*   Conditions : T_ext du bon côté de la consigne, |écart| > 0,05 et ≤ `KEXT_LEARNING_MAX_GAP` (1 °C), sauf dépassement avec puissance ≥ 10 %.
*   Exclusions : dépassement avec puissance < 1 % (`anomalous_overheating`), retour naturel vers la consigne avec puissance < 10 % (`cooling_down_naturally` / `warming_up_naturally`).
*   Cible : `Kext + Kint · (écart_int / écart_ext)`, limitée à 1,2.
*   Lissage : moyenne pondérée `(Kext · n + cible) / (n + 1)`, `n` = nombre d'échantillons plafonné à 50. Le Kext configuré n'a pas de poids (`n` démarre à 0).

### D. Kext Continu (`_learn_kext_continuous`)
*   Hors session, si `auto_tpi_continuous_kext` est activé et qu'au moins un échantillon Kext existe.
*   Mêmes conditions de cycle et de stabilisation.
*   EMA à poids fixe `CONTINUOUS_KEXT_ALPHA` (0,04) ; la valeur est écrite dans la config dès qu'elle s'écarte de plus de 0,001 de la valeur configurée (comparaison à la config, pas au cycle précédent : un pas d'EMA est bien plus petit). Après chaque écriture, les coefficients de référence du gestionnaire suivent la config.

---

## 5. Fin de Session (`process_learning_completion`)

*   Fin quand `coeff_indoor_autolearn ≥ KINT_WINDOWS_TO_FINISH + KINT_COUNT_START` (15 fenêtres) et `coeff_outdoor_autolearn ≥ 50`.
*   `stop_learning()`, écriture de Kint et Kext dans la config, notification persistante.

---

## 6. Métriques (`AutoTpiSensor`)

| Attribut | Source |
|---|---|
| `coeff_int_cycles` | `int_cycles` : fenêtres Kint apprises |
| `coeff_ext_cycles` | `ext_cycles` : échantillons Kext |
| `heating_cycles_count` | `total_cycles` |
| `model_confidence` | moyenne de `min(int_cycles / 15, 1)` et `min(ext_cycles, 50) / 50` |
| `thermal_time_constant_hours` | `1 / Kint` |
| `last_learning_status` | dernier statut |
| `learning_start_dt` | début de session |
| `calculated_coef_int` / `calculated_coef_ext` | coefficients courants |

---

## 7. Persistance et Restauration

*   `async_load_data` : charge l'état, plafonne Kint à `MAX_KINT` (3,0). Si `total_cycles == 0`, les coefficients configurés sont imposés. Hors session, `_align_with_configuration` remplace un coefficient stocké qui diffère de la config au-delà de l'arrondi d'écriture (`CONFIG_COEF_TOLERANCE`) : la config fait référence.
*   Le statut est remis à `learning_started` et le cycle en cours est abandonné (`cycle_active = False`).
*   Les fenêtres Kint et l'horodatage de consigne ne sont pas persistés : après un redémarrage, le premier `update()` est traité comme un changement de consigne.

---

## 8. Configuration

*   Étape `auto_tpi_configuration` : `heater_heating_time`, `auto_tpi_continuous_kext`.
*   Migration 2.4 → 2.5 : suppression des clés `OBSOLETE_AUTO_TPI_KEYS` (`const.py`).
*   Service `set_auto_tpi_mode` : `auto_tpi_mode`, `reinitialise`.

---

## 9. Tests

*   `tests/test_auto_tpi.py` : fenêtres Kint, stabilisation Kext, cycle de vie, persistance.
*   `tests/test_auto_tpi_continuous.py` : Kext continu.
*   `tests/test_auto_tpi_realistic.py` + `tests/auto_tpi_sim.py` : simulation en boucle fermée (pièce 1R1C, émetteur avec retard du 1er ordre, PWM, capteur périodique ou « on change », résolution et bruit). Vérifie que Kint ne s'effondre pas et que Kext reste à ±50 % de `b/a`.
*   `tests/test_auto_tpi_simulation.py` : convergence sur un modèle simple.
