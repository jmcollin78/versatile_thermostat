# CycleScheduler — Documentation Technique

## 1. Énoncé du Problème

### 1.1 Architecture Précédente

Chaque `UnderlyingSwitch` gérait indépendamment son propre cycle ON/OFF :

```
start_cycle() → _turn_on_later() → _turn_off_later() → _turn_on_later() → ...
```

Un délai initial fixe (`initial_delay_sec = idx * delta_cycle`) était appliqué au démarrage pour décaler les sous-jacents (underlyings). Après le premier cycle, chaque sous-jacent bouclait indépendamment sans aucune coordination ultérieure.

Pour les vannes, `UnderlyingValve` gérait son propre appel à `set_valve_open_percent()` directement à l'intérieur d'une méthode de cycle.

### 1.2 Problèmes

| #   | Problème                     | Description                                                                                                                                          |
| --- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Dérive temporelle**        | Les cycles de plusieurs sous-jacents se désynchronisaient progressivement du cycle maître du thermostat.                                             |
| 2   | **Incompatibilité SmartPI**  | SmartPI calcule un seul `on_percent` pour un cycle global. Des sous-cycles indépendants par sous-jacent rendaient le retour de puissance incohérent. |
| 3   | **Retour de puissance faux** | `update_realized_power` ne correspondait pas à la réalité physique car les sous-jacents n'étaient pas synchronisés sur le cycle maître.              |
| 4   | **Délai initial statique**   | `initial_delay_sec` était calculé une seule fois et ne s'adaptait jamais au `on_percent` réel de chaque cycle.                                       |
| 5   | **Logique dispersée**        | La gestion des cycles était dupliquée entre `UnderlyingSwitch`, `UnderlyingValve` et `UnderlyingValveRegulation`.                                    |

### 1.3 Illustration (2 radiateurs, cycle de 10 minutes)

**Avant** — cycles indépendants avec délai initial fixe :
```
R1: |==ON==|----OFF----|==ON==|----OFF----|==ON==|----OFF----|
R2:      |==ON==|----OFF----|==ON==|----OFF----|==ON==|----OFF----|
    ^                   ^                   ^
    Cycle maître 1      Cycle maître 2      Cycle maître 3
    (Décalage R2)       (R1 et R2 déjà      (la dérive augmente)
                        désynchronisés)
```

Après quelques cycles, R1 et R2 dérivent et ne s'alignent plus avec le cycle maître.

---

## 2. Solution : CycleScheduler Centralisé

### 2.1 Principe

Un unique `CycleScheduler` par thermostat orchestre tous les sous-jacents au sein d'une fenêtre de cycle maître partagée. Il remplace la logique de cycle par sous-jacent pour les commutateurs (switches) et les vannes.

```
AVANT :
  Handler → pour chaque sous-jacent : underlying.start_cycle(on_time, off_time)
             (chaque sous-jacent boucle indépendamment)

APRÈS :
  Handler → cycle_scheduler.start_cycle(hvac_mode, on_percent, force)
             (le planificateur calcule le timing en interne et orchestre tous les sous-jacents)
```

### 2.2 Diagramme d'Architecture

```
+------------------------------------------+
|            ThermostatProp                 |
|                                           |
|  +--------------------+                  |
|  | AlgoHandler        |                  |
|  | (TPI / SmartPI)    |                  |
|  |                    |                  |
|  | control_heating()  |                  |
|  |   → on_percent     |                  |
|  +--------+-----------+                  |
|           |                               |
|           v                               |
|  +--------+---------------------------+  |
|  | CycleScheduler                     |  |
|  |   cycle_scheduler.py               |  |
|  |   + cycle_tick_logic.py            |  |
|  |                                    |  |
|  | start_cycle(hvac_mode, on_percent) |  |
|  |   _init_cycle() → tick → tick → … |  |
|  |   _on_master_cycle_end() → e_eff  |  |
|  |                                    |  |
|  +--+------+------+------------------+  |
|     |      |      |                      |
|     v      v      v                      |
|   R1.on  R2.on  R3.on                   |
|   R1.off R2.off R3.off                   |
|                                           |
|  Sous-jacents (turn_on/turn_off uniq.)   |
+------------------------------------------+
```

### 2.3 Séparation en deux fichiers

| Fichier               | Rôle                                                                                         |
| --------------------- | -------------------------------------------------------------------------------------------- |
| `cycle_scheduler.py`  | Orchestration (timers HA, callbacks, gestion du cycle maître, intégration thermostat)         |
| `cycle_tick_logic.py` | Logique pure (calculs d'offsets, état cible, need_on/need_off, e_eff) — sans dépendance HA   |

---

## 3. Modes de Fonctionnement

### 3.1 Mode Switch (Planification par ticks)

Pour les entités `UnderlyingSwitch`, le planificateur utilise une approche par **ticks événementiels** :
- Calcule des décalages circulaires (offsets) pour répartir les activations des sous-jacents.
- À chaque tick, évalue l'état théorique de chaque sous-jacent et applique les contraintes de durée minimale.
- Planifie le prochain tick via `async_call_later` au moment du prochain changement d'état attendu.
- Planifie `_on_master_cycle_end` à `t = cycle_duration_sec`.
- À la fin du cycle, calcule `e_eff`, incrémente l'énergie, et redémarre avec les mêmes paramètres.

### 3.2 Mode Valve (Transmission directe)

Pour les entités `UnderlyingValve` et `UnderlyingValveRegulation`, aucune planification de minuteur n'est nécessaire :
- `_start_cycle_valve()` appelle directement `set_valve_open_percent()` sur chaque sous-jacent.
- Aucune répétition du cycle maître n'est planifiée — c'est le `async_track_time_interval` du thermostat qui pilote la réévaluation périodique.
- Cela unifie la gestion des cycles de vannes sous la même API `start_cycle()`.

La détection du mode est automatique lors de la construction via `_detect_valve_mode()`, qui inspecte le `entity_type` du premier sous-jacent.

---

## 4. `calculate_cycle_times()` — Fonction de Contraintes Temporelles

Cette fonction au niveau module (définie dans `cycle_scheduler.py`) convertit `on_percent` en `on_time_sec` / `off_time_sec` tout en appliquant les contraintes de protection du matériel.

```python
def calculate_cycle_times(
    on_percent: float,           # fraction 0.0–1.0
    cycle_min: int,              # durée du cycle en minutes
    minimal_activation_delay: int = 0,    # durée minimale ON (secondes)
    minimal_deactivation_delay: int = 0,  # durée minimale OFF (secondes)
) -> tuple[int, int, bool]:
    # retourne (on_time_sec, off_time_sec, forced_by_timing)
```

**Règles de contrainte :**

| Condition                              | Effet                                                  |
| -------------------------------------- | ------------------------------------------------------ |
| `0 < on_time < min_activation_delay`  | `on_time` forcé à 0 (trop court pour être utile)       |
| `off_time < min_deactivation_delay`   | `on_time` forcé à `cycle_sec` (reste en ON permanent)  |
| `forced_by_timing = True`             | Les gestionnaires l'utilisent pour mettre à jour `realized_power` |

Cette fonction est également appelée directement par les gestionnaires (TPI, SmartPI) pour calculer `realized_percent` en retour d'algorithme — indépendamment du calcul interne du planificateur.

---

## 5. Algorithme de Calcul des Décalages Circulaires

### 5.1 Principe

Pour le mode switch, le planificateur répartit les débuts de cycle de chaque sous-jacent uniformément sur la durée du cycle en utilisant des **offsets circulaires**. L'offset détermine le décalage du début de cycle pour chaque sous-jacent.

```python
offset = (cycle_duration / n) * index
```

Cas particulier :
- `n <= 1` : retourne `[0.0]`

### 5.2 Exemples

**5 sous-jacents, cycle de 5 minutes (300s) :**

| Sous-jacent | Index | Offset                |
| ----------- | ----- | --------------------- |
| R1          | 0     | (300 / 5) × 0 = 0s   |
| R2          | 1     | (300 / 5) × 1 = 60s  |
| R3          | 2     | (300 / 5) × 2 = 120s |
| R4          | 3     | (300 / 5) × 3 = 180s |
| R5          | 4     | (300 / 5) × 4 = 240s |

**2 sous-jacents, cycle de 600s :**

| Sous-jacent | Index | Offset                 |
| ----------- | ----- | ---------------------- |
| R1          | 0     | (600 / 2) × 0 = 0s    |
| R2          | 1     | (600 / 2) × 1 = 300s  |

Les offsets sont indépendants du `on_percent`. La répartition est fixe et circulaire — chaque sous-jacent démarre son activation à un point régulièrement espacé dans le cycle, avec un retour au début du cycle (wrap-around) si `on_t + on_time` dépasse la durée du cycle.

---

## 6. Initialisation d'un Cycle (`_init_cycle`)

### 6.1 Principe

Cette étape se produit une fois par cycle, au démarrage. Elle réinitialise les états de chaque sous-jacent et la pénalité globale.

### 6.2 Variables initialisées

**Globale :**
- `penalty = 0.0` — compteur du temps de chauffe ajouté ou retiré pour le calcul de `e_eff` en fin de cycle.

**Par sous-jacent (`UnderlyingCycleState`) :**

| Variable  | Formule                                        | Description                                        |
| --------- | ---------------------------------------------- | -------------------------------------------------- |
| `on_t`    | `offset`                                       | Temps auquel le sous-jacent doit être allumé       |
| `on_time` | `cycle_duration × on_percent`                  | Durée de fonctionnement du sous-jacent             |
| `off_t`   | `(on_t + on_time) % cycle_duration`            | Temps auquel le sous-jacent doit être éteint       |

```python
on_t = offset
on_time = cycle_duration_sec * on_percent
off_t = (on_t + on_time) % cycle_duration_sec
```

### 6.3 Wrap-around circulaire

Quand `on_t + on_time > cycle_duration`, `off_t` revient au début du cycle grâce au modulo. Cela crée une activation qui « enveloppe » la fin et le début du cycle.

**Exemple** — 2 sous-jacents, cycle 600s, on_percent = 60% (on_time = 360s) :

| Sous-jacent | offset | on_t | on_time | off_t             | Période ON         |
| ----------- | ------ | ---- | ------- | ----------------- | ------------------ |
| R1          | 0s     | 0s   | 360s    | 360s              | 0–360s             |
| R2          | 300s   | 300s | 360s    | (300+360)%600=60s | 300–600s puis 0–60s |

### 6.4 Enchaînement

Après l'initialisation, le premier tick est exécuté immédiatement (`_is_initial=True`). L'initialisation est réexécutée après `cycle_duration` secondes ou après un changement de puissance avec `force=True`.

---

## 7. Le Tick — Méthode Principale de Calcul d'État

### 7.1 Principe

Le tick est la méthode qui détermine dans quel état doit être chacun des sous-jacents. Il s'exécute :
- À `t = 0` du cycle (premier tick, `_is_initial=True`).
- À chaque `on_t` ou `off_t` d'un sous-jacent.
- À d'autres moments si l'algorithme de racollage reporte un changement d'état.

Le tick n'a pas besoin de s'exécuter de façon régulière : on peut déterminer les prochains changements d'état des sous-jacents et planifier le prochain tick exactement à ce moment-là.

`current_t` désigne le temps écoulé depuis le début du cycle au moment du tick.

### 7.2 Détermination de l'état théorique (`compute_target_state`)

Pour chaque sous-jacent, la fonction `compute_target_state(on_t, off_t, current_t, cycle_duration)` détermine l'état souhaité (ON ou OFF), le prochain tick et la durée dans l'état courant.

Les conditions sont évaluées en cascade (if / elif). Dès qu'un état est déterminé, les tests suivants ne sont pas effectués.

#### Cas 1 : `off_t > on_t` — ON confiné dans `[on_t, off_t)`

```
|----OFF----|====ON====|----OFF----|
0          on_t       off_t       cycle_end
```

| Condition            | État | Prochain tick  | Durée dans l'état    |
| -------------------- | ---- | -------------- | -------------------- |
| `current_t < on_t`   | OFF  | `on_t`         | `on_t - current_t`   |
| `current_t < off_t`  | ON   | `off_t`        | `off_t - current_t`  |
| `current_t >= off_t` | OFF  | `cycle_end`    | `cycle_end - current_t` |

#### Cas 2 : `off_t <= on_t` — ON enveloppe la fin et le début du cycle `[0, off_t) ∪ [on_t, cycle_end)`

```
|====ON====|----OFF----|====ON====|
0          off_t       on_t       cycle_end
```

| Condition            | État | Prochain tick  | Durée dans l'état    |
| -------------------- | ---- | -------------- | -------------------- |
| `current_t < off_t`  | ON   | `off_t`        | `off_t - current_t`  |
| `current_t < on_t`   | OFF  | `on_t`         | `on_t - current_t`   |
| `current_t >= on_t`  | ON   | `cycle_end`    | `cycle_end - current_t` |

### 7.3 Application de l'état — Need ON / Need OFF

Une fois l'état théorique déterminé, le tick vérifie s'il y a lieu de changer effectivement l'état du sous-jacent, en tenant compte des contraintes de durée minimale d'activation et de désactivation.

---

## 8. Need ON — Logique d'Activation

### 8.1 Cas nominal

Si le sous-jacent est déjà ON, aucune action n'est nécessaire.

On détermine `under_dt` : le temps écoulé depuis le dernier changement d'état du sous-jacent.

On connaît `state_duration` : le temps entre `current_t` et le prochain changement d'état prévu (calculé par `compute_target_state`).

Si les deux conditions suivantes sont remplies :
- `under_dt >= minimal_deactivation_delay` (le sous-jacent est resté OFF assez longtemps)
- `state_duration > minimal_activation_delay` (la durée d'activation prévue est suffisante)

Alors l'action est `turn_on`.

### 8.2 Cas de racollage (skip + décalage de `on_t`)

Si l'activation ne peut pas avoir lieu (conditions non remplies), on procède à un **racollage** : le temps d'activation manqué est reporté sur la prochaine fenêtre d'activation.

1. On calcule un nouveau `on_t = on_t - state_duration` pour incorporer le temps d'activation manqué en amont de la prochaine activation.

2. On vérifie que ce nouveau `on_t` respecte la désactivation minimale restante :
   - Temps restant avant la prochaine activation : `on_t - current_t`
   - Temps nécessaire pour respecter la désactivation minimale : `minimal_deactivation_delay - under_dt`
   - Si `on_t - current_t < minimal_deactivation_delay - under_dt`, alors on force `on_t = current_t + (minimal_deactivation_delay - under_dt)`.

3. Le temps de chauffe non réalisé est ajouté à `penalty` (valeur positive = temps de chauffe perdu).

Un nouveau tick est planifié au moment du nouveau `on_t`.

---

## 9. Need OFF — Logique de Désactivation

La logique est symétrique à Need ON, avec inversion des rôles :

### 9.1 Cas nominal

Si le sous-jacent est déjà OFF, aucune action n'est nécessaire.

Si les deux conditions suivantes sont remplies :
- `under_dt >= minimal_activation_delay` (le sous-jacent est resté ON assez longtemps)
- `state_duration > minimal_deactivation_delay` (la durée de désactivation prévue est suffisante)

Alors l'action est `turn_off`.

### 9.2 Cas de racollage (skip + décalage de `off_t`)

1. On calcule un nouveau `off_t = off_t - state_duration`.
2. On vérifie que ce nouveau `off_t` respecte l'activation minimale restante.
3. Le temps de chauffe supplémentaire (le sous-jacent reste ON plus longtemps que prévu) est **retiré** de `penalty` (valeur négative = temps de chauffe excédentaire).

---

## 10. Calcul de la Puissance Effective (`e_eff`)

### 10.1 Principe

La puissance effective est calculée et notifiée par `CycleScheduler` via la méthode interne `_calculate_realized_e_eff(elapsed_sec)`.
Elle représente la puissance réellement produite en intégrant exactement le temps de chauffe des sous-jacents sur le temps écoulé, en tenant compte des ajustements de racollage.

### 10.2 Formule d'intégration exacte

Plutôt que d'estimer en fin de cycle, l'algorithme calcule le temps physique exact `t_on_actual` d'activation projeté de chaque sous-jacent sur une fenêtre de temps absolue `elapsed_sec` :

```python
e_eff = max(0.0, t_on_actual - penalty) / (elapsed_sec * n_underlyings)
```

Où :
- `t_on_actual` est la somme des fractions temporelles d'activation absolues découpées sur `elapsed_sec` (gérant le *wrap-around* du scheduler).
- `penalty` est le cumul des temps de chauffe ajoutés (+) ou retirés (−) par les racollages pendant le cycle.
- `e_eff` est borné entre 0.0 et 1.0.

### 10.3 Fin de cycle et Interruptions

La méthode s'applique dans deux contextes cruciaux :
1. **Fin normale (`_on_master_cycle_end`)** : Appelée avec `nominal_cycle_duration`.
2. **Interruption (`cancel_cycle`)** : Si un cycle en cours de roulement (> 1.0s) est annulé (ex. la consigne change à mi-cycle), un `e_eff` partiel est calculé sur le vrai temps écoulé (`elapsed_sec`). Le scheduler déclenche alors une notification (callback `on_cycle_completed(e_eff_partiel)`), ce qui permet notamment aux algorithmes de régulation (comme Smart-PI) d'intégrer proprement ce fragment d'historique thermique.

---

## 11. Planification des Ticks

### 11.1 Algorithme de planification

À chaque tick, le planificateur détermine le prochain tick global comme le minimum parmi :
- Le temps restant avant la fin du cycle.
- Le prochain `on_t` ou `off_t` de chaque sous-jacent.
- Les éventuels nouveaux `on_t` ou `off_t` issus du racollage.

Un délai minimum de 0.1s est imposé pour éviter les boucles trop rapides.

### 11.2 Nombre de timers

À tout instant, il y a au maximum **2 timers** actifs :
- 1 timer pour le prochain tick (`_tick_unsub`)
- 1 timer pour la fin du cycle maître (`_cycle_end_unsub`)

C'est significativement moins que l'ancienne approche (2 × N + 1 timers).

### 11.3 Diagramme de séquence

```
t=0                t=off_t[R1]    t=on_t[R2]    t=off_t[R2]         t=cycle_end
 |                      |              |              |                    |
 | _init_cycle()        |              |              |                    |
 | _tick(initial=True)  |              |              |                    |
 |   R1 → ON            |              |              |                    |
 |   R2 → OFF           |              |              |                    |
 |   next_tick=off_t[1] |              |              |                    |
 |                      |              |              |                    |
 |                      | _tick()      |              |                    |
 |                      |  R1 → OFF    |              |                    |
 |                      |  next=on_t[2]|              |                    |
 |                      |              |              |                    |
 |                      |              | _tick()      |                    |
 |                      |              |  R2 → ON     |                    |
 |                      |              |  next=off[2] |                    |
 |                      |              |              |                    |
 |                      |              |              | _tick()            |
 |                      |              |              |  R2 → OFF          |
 |                      |              |              |  next=cycle_end    |
 |                      |              |              |                    |
 |                      |              |              |     _on_master_    |
 |                      |              |              |     cycle_end()    |
 |                      |              |              |      → e_eff       |
 |                      |              |              |      → energy      |
 |                      |              |              |      → restart     |
```

---

## 12. Logique de `start_cycle()`

```
start_cycle(hvac_mode, on_percent, force=False)
│
├── calculate_cycle_times(on_percent, cycle_min,
│       min_activation_delay, min_deactivation_delay)
│     → on_time_sec, off_time_sec
│
├── mettre à jour thermostat._on_time_sec / _off_time_sec   ← toujours, avant le retour anticipé
│
├── si cycle en cours ET force=False
│   ├── si on_time actuel > 0  → mettre à jour les params stockés, retour (maj non disruptive)
│   └── si on_time actuel == 0 → annuler le cycle inactif, continuer
│
├── cancel_cycle()          ← annule toujours avant de (re)démarrer
├── stocker params actuels
├── déclencher callbacks cycle_start
│
├── si mode valve → _start_cycle_valve()
└── si mode switch → _start_cycle_switch()
      ├── si HVAC_OFF ou on_time=0 → éteindre tout, planifier fin de cycle
      ├── si on_time >= cycle_duration → allumer tout, planifier fin de cycle
      └── sinon → _init_cycle() → _tick(initial=True) + planifier fin de cycle
```

**Comportement clé :** `thermostat._on_time_sec` et `thermostat._off_time_sec` sont mis à jour **avant** la vérification de retour anticipé. Cela garantit que les valeurs affichées par les capteurs reflètent toujours les dernières valeurs calculées.

La mise à jour non disruptive (quand `force=False` et qu'un cycle réel est en cours) permet au gestionnaire de soumettre de nouvelles valeurs `on_percent` sans casser le timing du cycle en cours. Les nouveaux paramètres prennent effet à la prochaine répétition automatique.

---

## 13. Callbacks et Intégration des Gestionnaires

### 13.1 Enregistrement

```python
cycle_scheduler.register_cycle_start_callback(callback)
cycle_scheduler.register_cycle_end_callback(callback)
```

### 13.2 Signature du callback de début de cycle

```python
async def callback(
    on_time_sec: float,
    off_time_sec: float,
    on_percent: float,   # fraction réalisée 0.0–1.0 (contrainte par le timing)
    hvac_mode: VThermHvacMode,
) -> None: ...
```

Appelé une fois au début de chaque cycle maître (avant tout `turn_on`).

> **Note :** `on_percent` est la fraction **réalisée** après application des contraintes `min_activation_delay` / `min_deactivation_delay` — ce n'est pas la valeur brute passée à `start_cycle()`. Utiliser cette valeur pour le retour de puissance (ex. `update_realized_power()`), pas la sortie brute de l'algorithme.

### 13.3 Signature du callback de fin de cycle

```python
async def callback(e_eff: float) -> None: ...
```

Appelé une fois à `_on_master_cycle_end`, avant `incremente_energy()` et avant le redémarrage du cycle. `e_eff` est la puissance effective calculée sur le cycle qui vient de se terminer.

### 13.4 Intégration des gestionnaires via `on_scheduler_ready()`

Au lieu d'assigner directement `self._cycle_scheduler = CycleScheduler(...)`, les sous-classes de thermostat appellent `_bind_scheduler()` :

```python
# Dans thermostat_switch.py / thermostat_valve.py / thermostat_climate_valve.py :
self._bind_scheduler(CycleScheduler(
    hass=self._hass,
    thermostat=self,
    underlyings=self._underlyings,
    cycle_duration_sec=self._cycle_min * 60,
    min_activation_delay=self.minimal_activation_delay,
    min_deactivation_delay=self.minimal_deactivation_delay,
))
```

`ThermostatProp._bind_scheduler()` stocke le planificateur et notifie le gestionnaire actif :

```python
def _bind_scheduler(self, scheduler) -> None:
    self._cycle_scheduler = scheduler
    if self._algo_handler and hasattr(self._algo_handler, "on_scheduler_ready"):
        self._algo_handler.on_scheduler_ready(scheduler)
```

Chaque gestionnaire implémente `on_scheduler_ready(scheduler)` pour s'auto-enregistrer :

**Gestionnaire TPI :**
```python
def on_scheduler_ready(self, scheduler) -> None:
    if self._auto_tpi_manager:
        scheduler.register_cycle_start_callback(self._auto_tpi_manager.on_cycle_started)
        scheduler.register_cycle_end_callback(self._auto_tpi_manager.on_cycle_completed)
```

**Gestionnaire SmartPI :**
```python
def on_scheduler_ready(self, scheduler) -> None:
    algo = self._thermostat.prop_algorithm
    if algo:
        scheduler.register_cycle_start_callback(algo.on_cycle_started)
        scheduler.register_cycle_end_callback(algo.on_cycle_completed)
```

Cycle de vie :
```
ThermostatProp.post_init()
  └─ _bind_scheduler(CycleScheduler(...))
       ├─ self._cycle_scheduler = scheduler
       └─ algo_handler.on_scheduler_ready(scheduler)
            ├─ scheduler.register_cycle_start_callback(algo.on_cycle_started)
            └─ scheduler.register_cycle_end_callback(algo.on_cycle_completed)
```

À chaque frontière de cycle maître :
- `on_cycle_started(on_time_sec, off_time_sec, realized_on_percent, hvac_mode)` se déclenche → l'algo stocke les paramètres, met à jour le retour de puissance
- `on_cycle_completed(e_eff)` se déclenche → l'algo relit les paramètres stockés, exécute l'apprentissage

### 13.5 Suppression de `CycleManager`

`CycleManager` — une classe abstraite basée sur le polling avec `process_cycle(timestamp, data_provider, event_sender, force)` — a été supprimée. Les classes d'algorithme qui en héritaient (`AutoTpiManager`, `SmartPI`) :

- Implémentent directement les callbacks `on_cycle_started()` / `on_cycle_completed()`
- N'héritent plus de `CycleManager`
- Ne sont plus pilotées par des appels à `process_cycle()` depuis les gestionnaires

Les gestionnaires ne contiennent plus de bloc `_data_provider` / `process_cycle()` dans `control_heating()`.

### 13.6 `update_realized_power()` — Exigence de Pulsation

`AutoTpiManager.update_realized_power(realized_percent)` doit être appelé **à chaque invocation de `control_heating()`**, pas seulement aux frontières de cycle. Cela garantit que `last_power` reste à jour lorsque `max_on_percent` ou d'autres facteurs limitants changent en milieu de cycle.

Le gestionnaire TPI appelle ceci de manière inconditionnelle :

```python
if self._auto_tpi_manager:
    self._auto_tpi_manager.update_realized_power(realized_percent)
```

Cet appel est indépendant du callback `on_cycle_started` (qui se déclenche uniquement aux frontières de cycle via le minuteur du planificateur).

---

## 14. Cas Particuliers

| Cas                        | Comportement                                                                                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `on_percent = 0`           | Tous les sous-jacents éteints. Cycle inactif planifié pour `cycle_duration_sec` (maintient le rythme maître). Pas d'appel à `_init_cycle`.                                     |
| `on_percent = 1.0` (100%)  | Tous les sous-jacents allumés inconditionnellement. Pas de tick scheduling. Fin de cycle planifiée pour la prochaine itération.                                                 |
| Redémarrage forcé          | `force=True` annule tous les minuteurs actuels via `cancel_cycle()` puis redémarre immédiatement.                                                                              |
| HVAC_MODE_OFF              | Le gestionnaire positionne `t._on_time_sec=0`, `t._off_time_sec=cycle_sec` directement, puis appelle `async_underlying_entity_turn_off()` (→ `cancel_cycle()` + `turn_off()`). |
| Sous-jacent unique         | `compute_circular_offsets` retourne `[0.0]`. Comportement identique : un seul sous-jacent avec offset 0.                                                                      |
| Keep-alive                 | Reste dans `UnderlyingSwitch`. Lit `_should_be_on` (mis à jour par le planificateur) pour renvoyer l'état actuel périodiquement.                                               |
| Contraintes temporelles    | `calculate_cycle_times()` est appelé **en interne** par `start_cycle()`. Les gestionnaires l'appellent aussi directement pour le retour `realized_percent` uniquement.         |

---

## 15. Impact sur le Code Existant

### 15.1 Supprimé de `underlyings.py`

| Classe                      | Supprimé                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| `UnderlyingEntity`          | `start_cycle()`, `_cancel_cycle()`, `turn_off_and_cancel_cycle()`                                |
| `UnderlyingSwitch`          | `start_cycle()`, `_turn_on_later()`, `_turn_off_later()`, `_cancel_cycle()`, `initial_delay_sec` |
| `UnderlyingValve`           | `start_cycle()`, `_async_cancel_cycle`, appel `_cancel_cycle()` dans `remove_entity()`           |
| `UnderlyingValveRegulation` | `start_cycle()`                                                                                  |

`UnderlyingSwitch` conserve : `turn_on()`, `turn_off()`, `_should_be_on`, `_on_time_sec`, `_off_time_sec`, logique keep-alive.

### 15.2 Fichiers supprimés

| Fichier            | Raison                                                                                        |
| ------------------ | --------------------------------------------------------------------------------------------- |
| `timing_utils.py`  | `calculate_cycle_times()` déplacé au niveau module de `cycle_scheduler.py`                    |
| `cycle_manager.py` | Détection de cycle basée sur le polling ; remplacée par les callbacks dans `CycleScheduler`   |

### 15.3 Fichiers ajoutés

| Fichier              | Rôle                                                                                         |
| -------------------- | -------------------------------------------------------------------------------------------- |
| `cycle_tick_logic.py` | Logique pure du tick scheduler : `UnderlyingCycleState`, `compute_circular_offsets`, `compute_target_state`, `evaluate_need_on`, `evaluate_need_off` |

### 15.4 Fichiers modifiés

| Fichier                        | Changement                                                                                                                                                                                                                                                                 |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `thermostat_switch.py`         | Appelle `_bind_scheduler(CycleScheduler(...))` dans `post_init()` en passant les attributs de délai (définis par `init_algorithm()` plus tôt dans la chaîne d'appel)                                                                                                      |
| `thermostat_valve.py`          | Identique à ci-dessus                                                                                                                                                                                                                                                      |
| `thermostat_climate_valve.py`  | Identique à ci-dessus                                                                                                                                                                                                                                                      |
| `thermostat_prop.py`           | Ajout de `_bind_scheduler()` pour stocker le planificateur et notifier le gestionnaire via `on_scheduler_ready()` ; suppression de `_on_prop_cycle_start()` (code mort)                                                                                                    |
| `base_thermostat.py`           | `_cycle_scheduler = None` dans `__init__` ; propriété `cycle_scheduler` ; `async_underlying_entity_turn_off()` appelle `cancel_cycle()` ; suppression de `_fire_cycle_start_callbacks()` (code mort) ; suppression de l'import `asyncio` inutilisé                        |
| `prop_handler_tpi.py`          | Importe `calculate_cycle_times` depuis `cycle_scheduler` ; appelle `start_cycle(hvac_mode, on_percent, force)` ; implémente `on_scheduler_ready()` pour enregistrer les callbacks `AutoTpiManager` ; appelle `update_realized_power()` à chaque pulsation                  |
| `prop_handler_smartpi.py`      | Même schéma que le gestionnaire TPI ; implémente `on_scheduler_ready()` pour enregistrer les callbacks de l'algo `SmartPI`                                                                                                                                                 |
| `auto_tpi_manager.py`          | Suppression de l'héritage `CycleManager` ; implémente les callbacks `on_cycle_started()` / `on_cycle_completed()` ; stocke les paramètres de cycle dans `state.current_cycle_params`                                                                                       |
| `prop_algo_smartpi.py`         | Suppression de l'héritage `CycleManager` ; ajout de la propriété `cycle_min` ; simplification de `on_cycle_completed()` ; ajout de la méthode `reset_cycle_state()`                                                                                                       |

### 15.5 Fichiers non affectés

- `prop_algo_tpi.py` (algorithme TPI pur)
- Flux de configuration, services, gestionnaires de fonctionnalités

---

## 16. Constructeur et Propriétés

### 16.1 Constructeur

```python
CycleScheduler(
    hass: HomeAssistant,
    thermostat: Any,
    underlyings: list,
    cycle_duration_sec: float,
    min_activation_delay: int = 0,    # durée minimale ON en secondes
    min_deactivation_delay: int = 0,  # durée minimale OFF en secondes
)
```

`min_activation_delay` et `min_deactivation_delay` sont des attributs permanents accessibles via `scheduler.min_activation_delay` et `scheduler.min_deactivation_delay`. Ils sont mis à jour par les appels de service (ex. `service_set_tpi_parameters`) lorsque l'utilisateur modifie ces valeurs à l'exécution.

### 16.2 Propriétés

| Propriété               | Type   | Description                                           |
| ----------------------- | ------ | ----------------------------------------------------- |
| `is_cycle_running`      | `bool` | True si un tick ou une fin de cycle est planifié      |
| `is_valve_mode`         | `bool` | True si gestion de sous-jacents de type vanne         |
| `min_activation_delay`  | `int`  | Durée minimale ON en secondes (protection matériel)   |
| `min_deactivation_delay`| `int`  | Durée minimale OFF en secondes (protection matériel)  |

### 16.3 État interne du cycle

| Attribut              | Type                       | Description                                                    |
| --------------------- | -------------------------- | -------------------------------------------------------------- |
| `_states`             | `list[UnderlyingCycleState]` | État par sous-jacent (on_t, off_t, on_time, offset)          |
| `_penalty`            | `float`                    | Cumul des ajustements de racollage (secondes)                  |
| `_cycle_start_time`   | `float`                    | Timestamp du début du cycle (pour calcul de la durée réelle)   |
| `_tick_unsub`         | `CALLBACK_TYPE | None`     | Annulation du prochain tick planifié                           |
| `_cycle_end_unsub`    | `CALLBACK_TYPE | None`     | Annulation de la fin du cycle maître                           |

### 16.4 `UnderlyingCycleState`

Défini dans `cycle_tick_logic.py` :

```python
class UnderlyingCycleState:
    underlying     # référence vers l'entité sous-jacente
    offset: float  # décalage circulaire fixe (secondes)
    on_t: float    # temps d'activation dans le cycle (peut être modifié par racollage)
    off_t: float   # temps de désactivation dans le cycle (peut être modifié par racollage)
    on_time: float # durée de fonctionnement prévue (secondes)
```
