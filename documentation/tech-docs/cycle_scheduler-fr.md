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
  Handler → cycle_scheduler.start_cycle(hvac_mode, on_time, off_time, on_percent, force)
             (le planificateur orchestre tous les sous-jacents dans un cycle maître unique)
```

### 2.2 Diagramme d'Architecture

```
+------------------------------------------+
|            ThermostatProp                |
|                                          |
|  +--------------------+                  |
|  | AlgoHandler        |                  |
|  | (TPI / SmartPI)    |                  |
|  |                    |                  |
|  | control_heating()  |                  |
|  |   → on_percent     |                  |
|  +--------+-----------+                  |
|           |                              |
|           v                              |
|  +--------+-----------+                  |
|  | CycleScheduler     |                  |
|  |                    |                  |
|  | start_cycle()      |                  |
|  |   compute_offsets()|                  |
|  |   schedule_actions()|                 |
|  |                    |                  |
|  +--+------+------+--+                   |
|     |      |      |                      |
|     v      v      v                      |
|   R1.on  R2.on  R3.on                    |
|   R1.off R2.off R3.off                   |
|                                          |
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

## 4. Algorithme de Calcul des Décalages

### 4.1 Principe

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

### 4.2 Exemples — 2 radiateurs, cycle de 600s

| on_percent | on_time | max_offset | pas  | Offsets  | Périodes ON            |
| ---------- | ------- | ---------- | ---- | -------- | ---------------------- |
| 20%        | 120s    | 480s       | 480s | [0, 480] | R1: 0-120, R2: 480-600 |
| 40%        | 240s    | 360s       | 360s | [0, 360] | R1: 0-240, R2: 360-600 |
| 50%        | 300s    | 300s       | 300s | [0, 300] | R1: 0-300, R2: 300-600 |
| 60%        | 360s    | 240s       | 240s | [0, 240] | R1: 0-360, R2: 240-600 |
| 100%       | 600s    | 0s         | —    | [0, 0]   | R1: 0-600, R2: 0-600   |

### 4.3 Exemples — 3 radiateurs, cycle de 600s

| on_percent | on_time | Offsets       | Chevauchement max |
| ---------- | ------- | ------------- | ----------------- |
| 20%        | 120s    | [0, 240, 480] | 0                 |
| 33%        | 200s    | [0, 200, 400] | 0                 |
| 40%        | 240s    | [0, 180, 360] | 60s par paire     |
| 50%        | 300s    | [0, 150, 300] | 150s par paire    |
| 100%       | 600s    | [0, 0, 0]     | Total             |

À un `on_percent` élevé, un certain chevauchement est inévitable. La distribution uniforme minimise le pic de charge simultanée.

---

## 5. Cycle de Vie du Cycle Maître

### 5.1 Diagramme de Séquence

```
t=0          t=offset[1]  t=offset[2]  t=off[1]     t=off[2]     t=cycle_end
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

### 5.2 Nombre de minuteurs par cycle

```
Total minuteurs = 2 * N + 1
  N  × minuteurs turn_on  (offset[1..N-1]; R1 à offset=0 est immédiat)
  N  × minuteurs turn_off (sauf si le sous-jacent reste allumé jusqu'à la fin)
  1  × minuteur fin de cycle maître
```

Pour les configurations typiques (N = 2–4), cela représente 5–9 minuteurs par cycle — négligeable pour Home Assistant.

### 5.3 À `_on_master_cycle_end`

1. Éteindre tout sous-jacent encore allumé (sauf si `on_time >= cycle_duration`).
2. Déclencher tous les `_on_cycle_end_callbacks` enregistrés.
3. Appeler `thermostat.incremente_energy()`.
4. Effacer `_scheduled_actions`.
5. Appeler `start_cycle(..., force=True)` pour redémarrer avec les mêmes paramètres.

---

## 6. Logique de `start_cycle()`

```
start_cycle(hvac_mode, on_time, off_time, on_percent, force=False)
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

La mise à jour non disruptive (quand `force=False` et qu'un cycle réel est en cours) permet au gestionnaire de soumettre de nouvelles valeurs `on_percent` sans casser le timing du cycle en cours. Les nouveaux paramètres prennent effet à la prochaine répétition automatique.

---

## 7. Callbacks (Rappels)

### 7.1 Enregistrement

```python
cycle_scheduler.register_cycle_start_callback(callback)
cycle_scheduler.register_cycle_end_callback(callback)
```

### 7.2 Signature du callback de début de cycle

```python
async def callback(
    on_time_sec: float,
    off_time_sec: float,
    on_percent: float,
    hvac_mode: VThermHvacMode,
) -> None: ...
```

Appelé une fois au début de chaque cycle maître (avant tout `turn_on`).
Utilisé par SmartPI pour l'apprentissage et le calcul du retour de puissance.

### 7.3 Signature du callback de fin de cycle

```python
async def callback() -> None: ...
```

Appelé une fois à `_on_master_cycle_end`, avant `incremente_energy()` et avant le redémarrage du cycle.

---

## 8. Cas Particuliers

| Cas                   | Comportement                                                                                                                                                |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `on_percent = 0`      | Tous les sous-jacents éteints. Cycle inactif planifié pour `cycle_duration_sec` (maintient le rythme maître).                                               |
| `on_percent = 100`    | Tous les sous-jacents allumés à offset=0. Pas de `turn_off` planifié. Tous éteints à `_on_master_cycle_end` puis immédiatement réactivés.                   |
| Redémarrage forcé     | `force=True` annule tous les minuteurs actuels via `cancel_cycle()` puis redémarre immédiatement.                                                           |
| HVAC_MODE_OFF         | Le gestionnaire appelle `async_underlying_entity_turn_off()` qui appelle `cancel_cycle()` + `turn_off()` sur chaque sous-jacent.                            |
| Sous-jacent unique    | `compute_offsets` retourne `[0.0]`. Comportement identique à l'implémentation précédente.                                                                   |
| Keep-alive            | Reste dans `UnderlyingSwitch`. Lit `_should_be_on` (mis à jour par le planificateur) pour renvoyer l'état actuel périodiquement.                            |
| Contraintes pré-cycle | `calculate_cycle_times()` dans `timing_utils.py` borne `on_time_sec`/`off_time_sec` avant que le planificateur ne les reçoive. Aucun changement nécessaire. |

---

## 9. Impact sur le Code Existant

### 9.1 Supprimé de `underlyings.py`

| Classe                      | Supprimé                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| `UnderlyingEntity`          | `start_cycle()`, `_cancel_cycle()`, `turn_off_and_cancel_cycle()`                                |
| `UnderlyingSwitch`          | `start_cycle()`, `_turn_on_later()`, `_turn_off_later()`, `_cancel_cycle()`, `initial_delay_sec` |
| `UnderlyingValve`           | `start_cycle()`, `_async_cancel_cycle`, appel `_cancel_cycle()` dans `remove_entity()`           |
| `UnderlyingValveRegulation` | `start_cycle()`                                                                                  |

`UnderlyingSwitch` conserve : `turn_on()`, `turn_off()`, `_should_be_on`, `_on_time_sec`, `_off_time_sec`, logique keep-alive.

### 9.2 Fichiers modifiés

| Fichier                   | Changement                                                                                                                                                                                                                       |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `thermostat_switch.py`    | Crée `CycleScheduler` dans `post_init()` après la construction de la liste des sous-jacents.                                                                                                                                     |
| `thermostat_valve.py`     | Crée `CycleScheduler` dans `post_init()` après la construction de la liste des sous-jacents.                                                                                                                                     |
| `base_thermostat.py`      | `_cycle_scheduler = None` dans `__init__`; propriété `cycle_scheduler`; `async_underlying_entity_turn_off()` appelle `cancel_cycle()`; `register_cycle_callback()` route vers `cycle_scheduler.register_cycle_start_callback()`. |
| `prop_handler_tpi.py`     | Appelle `t.cycle_scheduler.start_cycle(...)` directement.                                                                                                                                                                        |
| `prop_handler_smartpi.py` | Appelle `t.cycle_scheduler.start_cycle(...)` directement.                                                                                                                                                                        |

### 9.3 Fichiers non affectés

- `prop_algo_tpi.py` (algorithmes purs)
- Flux de configuration, services, gestionnaires de fonctionnalités
- `timing_utils.py`

---

## 10. Propriétés

| Propriété          | Type   | Description                                   |
| ------------------ | ------ | --------------------------------------------- |
| `is_cycle_running` | `bool` | True si `_scheduled_actions` n'est pas vide   |
| `is_valve_mode`    | `bool` | True si gestion de sous-jacents de type vanne |