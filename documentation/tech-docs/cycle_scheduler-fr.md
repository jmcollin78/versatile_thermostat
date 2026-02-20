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
|  |                                    |  |
|  | start_cycle(hvac_mode, on_percent) |  |
|  |   calculate_cycle_times()          |  |
|  |   compute_offsets()                |  |
|  |   schedule_actions()               |  |
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

---

## 3. Modes de Fonctionnement

### 3.1 Mode Switch (Planification PWM)

Pour les entités `UnderlyingSwitch`, le planificateur utilise une approche PWM (MLI) :
- Calcule des décalages (offsets) d'allumage pour minimiser l'activation simultanée des radiateurs.
- Planifie les appels `turn_on()` et `turn_off()` via `async_call_later`.
- Planifie `_on_master_cycle_end` à `t = cycle_duration_sec`.
- À la fin du cycle, incrémente l'énergie, efface les minuteurs et redémarre avec les mêmes paramètres.

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

## 5. Algorithme de Calcul des Décalages

### 5.1 Principe

Pour le mode switch, le planificateur répartit les heures de début d'allumage (ON) uniformément sur la fenêtre disponible `[0, cycle_duration - on_time]`. C'est la stratégie de **distribution uniforme**.

```python
max_offset = cycle_duration_sec - on_time_sec
step = max_offset / (n - 1)
offsets = [i * step for i in range(n)]
```

Cas particuliers :
- `n <= 1` : retourne `[0.0]`
- `on_time_sec <= 0` : retourne `[0.0] * n` (rien à planifier)
- `on_time_sec >= cycle_duration_sec` (puissance 100%) : retourne `[0.0] * n` (tous démarrent ensemble)

### 5.2 Exemples — 2 radiateurs, cycle de 600s

| on_percent | on_time | max_offset | pas  | Offsets  | Périodes ON            |
| ---------- | ------- | ---------- | ---- | -------- | ---------------------- |
| 20%        | 120s    | 480s       | 480s | [0, 480] | R1: 0-120, R2: 480-600 |
| 40%        | 240s    | 360s       | 360s | [0, 360] | R1: 0-240, R2: 360-600 |
| 50%        | 300s    | 300s       | 300s | [0, 300] | R1: 0-300, R2: 300-600 |
| 60%        | 360s    | 240s       | 240s | [0, 240] | R1: 0-360, R2: 240-600 |
| 100%       | 600s    | 0s         | —    | [0, 0]   | R1: 0-600, R2: 0-600   |

### 5.3 Exemples — 3 radiateurs, cycle de 600s

| on_percent | on_time | Offsets       | Chevauchement max |
| ---------- | ------- | ------------- | ----------------- |
| 20%        | 120s    | [0, 240, 480] | 0                 |
| 33%        | 200s    | [0, 200, 400] | 0                 |
| 40%        | 240s    | [0, 180, 360] | 60s par paire     |
| 50%        | 300s    | [0, 150, 300] | 150s par paire    |
| 100%       | 600s    | [0, 0, 0]     | Total             |

À un `on_percent` élevé, un certain chevauchement est inévitable. La distribution uniforme minimise le pic de charge simultanée.

---

## 6. Cycle de Vie du Cycle Maître

### 6.1 Diagramme de Séquence

```
t=0          t=offset[1]  t=offset[2]  t=off[1]     t=off[2]    t=cycle_end
 |                |             |             |             |             |
 | start_cycle()  |             |             |             |             |
 | R1.turn_on()   |             |             |             |             |
 |                | R2.turn_on  |             |             |             |
 |                |             | R3.turn_on  |             |             |
 |                |             |             | R1.turn_off |             |
 |                |             |             |             | R2.turn_off |
 |                |             |             |             |             | R3.turn_off
 |                |             |             |             |             |
 |                |             |             |             |             | _on_master_
 |                |             |             |             |             | cycle_end()
 |                |             |             |             |             |  → energy
 |                |             |             |             |             | → restart
```

R1 (offset=0) est allumé immédiatement avec `await under.turn_on()`.
Tous les autres sont planifiés via `async_call_later`.

### 6.2 Nombre de minuteurs par cycle

```
Total minuteurs = 2 * N + 1
  N  × minuteurs turn_on  (offset[1..N-1]; R1 à offset=0 est immédiat)
  N  × minuteurs turn_off (sauf si le sous-jacent reste allumé jusqu'à la fin)
  1  × minuteur fin de cycle maître
```

Pour les configurations typiques (N = 2–4), cela représente 5–9 minuteurs par cycle — négligeable pour Home Assistant.

### 6.3 À `_on_master_cycle_end`

1. Éteindre tout sous-jacent encore allumé (sauf si `on_time >= cycle_duration`).
2. Déclencher tous les `_on_cycle_end_callbacks` enregistrés.
3. Appeler `thermostat.incremente_energy()`.
4. Appeler `start_cycle(hvac_mode, on_percent, force=True)` — `cancel_cycle()` est appelé atomiquement à l'intérieur.

---

## 7. Logique de `start_cycle()`

```
start_cycle(hvac_mode, on_percent, force=False)
│
├── calculate_cycle_times(on_percent, cycle_min,
│       min_activation_delay, min_deactivation_delay)
│     → on_time_sec, off_time_sec
│
├── mettre à jour thermostat._on_time_sec / _off_time_sec   ← toujours, avant le retour anticipé
│
├── si _scheduled_actions n'est pas vide ET force=False
│   ├── si on_time actuel > 0  → mettre à jour les params stockés, retour (maj non disruptive)
│   └── si on_time actuel == 0 → annuler le cycle inactif, continuer
│
├── cancel_cycle()          ← annule toujours avant de (re)démarrer
├── stocker params actuels
├── déclencher callbacks cycle_start
│
├── si mode valve → _start_cycle_valve()
└── si mode switch → _start_cycle_switch()
```

**Comportement clé :** `thermostat._on_time_sec` et `thermostat._off_time_sec` sont mis à jour **avant** la vérification de retour anticipé. Cela garantit que les valeurs affichées par les capteurs reflètent toujours les dernières valeurs calculées, même lorsque le cycle en cours n'est pas interrompu — préservant la compatibilité ascendante avec l'ancienne assignation côté gestionnaire.

La mise à jour non disruptive (quand `force=False` et qu'un cycle réel est en cours) permet au gestionnaire de soumettre de nouvelles valeurs `on_percent` sans casser le timing du cycle en cours. Les nouveaux paramètres prennent effet à la prochaine répétition automatique.

---

## 8. Callbacks et Intégration des Gestionnaires

### 8.1 Enregistrement

```python
cycle_scheduler.register_cycle_start_callback(callback)
cycle_scheduler.register_cycle_end_callback(callback)
```

### 8.2 Signature du callback de début de cycle

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

### 8.3 Signature du callback de fin de cycle

```python
async def callback() -> None: ...
```

Appelé une fois à `_on_master_cycle_end`, avant `incremente_energy()` et avant le redémarrage du cycle.

### 8.4 Intégration des gestionnaires via `on_scheduler_ready()`

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
- `on_cycle_completed()` se déclenche → l'algo relit les paramètres stockés, exécute l'apprentissage

### 8.5 Suppression de `CycleManager`

`CycleManager` — une classe abstraite basée sur le polling avec `process_cycle(timestamp, data_provider, event_sender, force)` — a été supprimée. Les classes d'algorithme qui en héritaient (`AutoTpiManager`, `SmartPI`) :

- Implémentent directement les callbacks `on_cycle_started()` / `on_cycle_completed()`
- N'héritent plus de `CycleManager`
- Ne sont plus pilotées par des appels à `process_cycle()` depuis les gestionnaires

Les gestionnaires ne contiennent plus de bloc `_data_provider` / `process_cycle()` dans `control_heating()`.

### 8.6 `update_realized_power()` — Exigence de Pulsation

`AutoTpiManager.update_realized_power(realized_percent)` doit être appelé **à chaque invocation de `control_heating()`**, pas seulement aux frontières de cycle. Cela garantit que `last_power` reste à jour lorsque `max_on_percent` ou d'autres facteurs limitants changent en milieu de cycle.

Le gestionnaire TPI appelle ceci de manière inconditionnelle :

```python
if self._auto_tpi_manager:
    self._auto_tpi_manager.update_realized_power(realized_percent)
```

Cet appel est indépendant du callback `on_cycle_started` (qui se déclenche uniquement aux frontières de cycle via le minuteur du planificateur).

---

## 9. Cas Particuliers

| Cas                        | Comportement                                                                                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `on_percent = 0`           | Tous les sous-jacents éteints. Cycle inactif planifié pour `cycle_duration_sec` (maintient le rythme maître).                                                                  |
| `on_percent = 1.0` (100%)  | Tous les sous-jacents allumés à offset=0. Pas de `turn_off` planifié. Tous éteints à `_on_master_cycle_end` puis immédiatement réactivés.                                      |
| Redémarrage forcé          | `force=True` annule tous les minuteurs actuels via `cancel_cycle()` puis redémarre immédiatement.                                                                              |
| HVAC_MODE_OFF              | Le gestionnaire positionne `t._on_time_sec=0`, `t._off_time_sec=cycle_sec` directement, puis appelle `async_underlying_entity_turn_off()` (→ `cancel_cycle()` + `turn_off()`). `start_cycle()` n'est pas appelé. |
| Sous-jacent unique         | `compute_offsets` retourne `[0.0]`. Comportement identique à l'implémentation précédente.                                                                                      |
| Keep-alive                 | Reste dans `UnderlyingSwitch`. Lit `_should_be_on` (mis à jour par le planificateur) pour renvoyer l'état actuel périodiquement.                                               |
| Contraintes temporelles    | `calculate_cycle_times()` est appelé **en interne** par `start_cycle()`. Les gestionnaires l'appellent aussi directement pour le retour `realized_percent` uniquement.         |

---

## 10. Impact sur le Code Existant

### 10.1 Supprimé de `underlyings.py`

| Classe                      | Supprimé                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| `UnderlyingEntity`          | `start_cycle()`, `_cancel_cycle()`, `turn_off_and_cancel_cycle()`                                |
| `UnderlyingSwitch`          | `start_cycle()`, `_turn_on_later()`, `_turn_off_later()`, `_cancel_cycle()`, `initial_delay_sec` |
| `UnderlyingValve`           | `start_cycle()`, `_async_cancel_cycle`, appel `_cancel_cycle()` dans `remove_entity()`           |
| `UnderlyingValveRegulation` | `start_cycle()`                                                                                  |

`UnderlyingSwitch` conserve : `turn_on()`, `turn_off()`, `_should_be_on`, `_on_time_sec`, `_off_time_sec`, logique keep-alive.

### 10.2 Fichiers supprimés

| Fichier            | Raison                                                                                        |
| ------------------ | --------------------------------------------------------------------------------------------- |
| `timing_utils.py`  | `calculate_cycle_times()` déplacé au niveau module de `cycle_scheduler.py`                    |
| `cycle_manager.py` | Détection de cycle basée sur le polling ; remplacée par les callbacks dans `CycleScheduler`   |

### 10.3 Fichiers modifiés

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

### 10.4 Fichiers non affectés

- `prop_algo_tpi.py` (algorithme TPI pur)
- Flux de configuration, services, gestionnaires de fonctionnalités

---

## 11. Constructeur et Propriétés

### 11.1 Constructeur

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

### 11.2 Propriétés

| Propriété               | Type   | Description                                           |
| ----------------------- | ------ | ----------------------------------------------------- |
| `is_cycle_running`      | `bool` | True si `_scheduled_actions` n'est pas vide           |
| `is_valve_mode`         | `bool` | True si gestion de sous-jacents de type vanne         |
| `min_activation_delay`  | `int`  | Durée minimale ON en secondes (protection matériel)   |
| `min_deactivation_delay`| `int`  | Durée minimale OFF en secondes (protection matériel)  |
