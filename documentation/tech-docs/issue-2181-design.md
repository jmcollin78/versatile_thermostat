# Conception technique — Issue #2181 : hooks des sous-jacents pour les plugins

| Champ          | Valeur                                                                                                                                                      |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Statut         | Implémentée, alignée sur la [spécification](issue-2181-specification.md) 1.0                                                                                |
| Version / date | 1.0 / 2026-11-05                                                                                                                                            |
| Propriétaire   | Projet Versatile Thermostat ; arbitrage final par le mainteneur                                                                                             |
| Sources        | [Issue #2181](https://github.com/jmcollin78/versatile_thermostat/issues/2181), [spécification fonctionnelle](issue-2181-specification.md), `vtherm_api` 0.9.0 |

## 1. Objectif et limites

Appeler, depuis le cœur, les trois hooks optionnels que `vtherm_api` 0.9.0 définit sur les feature managers externes (`BaseThermostat._external_managers`). Les trois sont des notifications : ils ne modifient ni n'annulent la commande du cœur. Les dataclasses et enums (`ValveCommand`, `ValveCommandCause`, `UnderlyingPowerCommand`, `PowerCommandKind`) et la constante `UNDERLYING_HOOK_TIMEOUT_SEC` sont importés depuis `vtherm_api`. La dépendance passe à `vtherm_api>=0.9.0`.

## 2. Répartition dans `BaseThermostat`

`_async_call_external_hook(method_name, *args)` parcourt les managers externes, ignore ceux qui n'ont pas la méthode (`getattr`) ou qui ne sont pas configurés (`is_configured`), et attend chaque appel sous `asyncio.timeout(UNDERLYING_HOOK_TIMEOUT_SEC)`. Un `TimeoutError` est journalisé en avertissement et une exception en erreur, sans être propagés. Le délai couvre chaque appel : un plugin lent ne retarde pas les autres de plus de 10 s chacun.

Trois méthodes publiques s'appuient sur ce helper : `async_before_underlying_hvac_mode`, `async_after_valve_command` et `async_on_underlying_power`. Elles sortent immédiatement si `_external_managers` est vide, sans construire d'objet. Les modes sont convertis en `str` avant l'appel.

## 3. Points d'appel

| Hook                                | Fichier et méthode                                               | Moment                                                                                                                                                                                                                                                                                                                  |
| ----------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `async_before_underlying_hvac_mode` | `underlyings.py`, `UnderlyingClimate.set_hvac_mode`              | Juste avant `climate.set_hvac_mode`, donc après le court-circuit « déjà dans ce mode », le contrôle de délestage, l'annulation du renvoi différé et les contrôles du suivi. Protégé par `is_command_blocked(CLIMATE_DOMAIN, SERVICE_SET_HVAC_MODE)`. `current_hvac_mode` est l'état réel du climate (`state.state`).      |
| `async_after_valve_command`         | `underlyings.py`, `UnderlyingValveRegulation.send_percent_open`  | Après l'envoi de l'ouverture et, s'il y a lieu, de la fermeture. Pas d'appel si `is_command_blocked` est vrai sur le domaine réel de l'entité d'ouverture (`number` ou `input_number`).                                                                                                                                  |
| `async_on_underlying_power`         | `cycle_scheduler.py`, `_fire_underlying_power`                   | Voir la section 5.                                                                                                                                                                                                                                                                                                      |

### 3.1 Causes des commandes de vanne

`send_percent_open(fixed_value=None, cause=ValveCommandCause.REGULATION)`. `UnderlyingValve.send_percent_open` accepte `cause` et l'ignore, pour garder la même signature dans la hiérarchie : le hook ne concerne pas `over_valve`.

| Appelant                                                        | Cause                     |
| --------------------------------------------------------------- | ------------------------- |
| `set_valve_open_percent` (cycle, `_send_regulated_temperature`) | `REGULATION` (par défaut) |
| `UnderlyingValveRegulation.turn_off` et `UnderlyingValve.turn_off` | `TURN_OFF`             |
| `async_inhibition_stop`                                         | `TURN_OFF`                |
| `check_initial_state` (vanne et vanne régulée)                  | `STARTUP`                 |
| `check_and_repair`                                              | `REPAIR`                  |

Le recalibrage (`service_recalibrate_valves`) et l'amorçage des degrés inconnus (`_seed_unknown_degrees_once`) appellent `send_value_to_number` directement : ils ne déclenchent pas le hook. Un accesseur public `climate_entity_id` est ajouté sur `UnderlyingValveRegulation`.

## 4. Correction annexe de `UnderlyingValve`

`UnderlyingValve.__init__` ignorait son paramètre `entity_type` et transmettait toujours `VALVE` : une vanne régulée se déclarait donc `valve`. Le paramètre est désormais transmis, ce qui permet à `UnderlyingPowerCommand.underlying_type` de valoir `valve_regulation`. Le cycle scheduler traite déjà `VALVE` et `VALVE_REGULATION` de la même manière.

## 5. Hook de puissance dans `CycleScheduler`

`_fire_underlying_power(kind, hvac_mode, requested_on_percent, applied_on_percent, on_time_sec, off_time_sec, is_repeat, offsets)` construit un `UnderlyingPowerCommand` par sous-jacent. Elle sort tout de suite sans feature manager externe, si le thermostat n'expose pas de coroutine `async_on_underlying_power` (doubles de test) ou s'il est inhibé (comme pour les reçus de commande).

| Type                 | Endroit                                               | Détail                                                                                                                                                                                                  |
| -------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CYCLE_START` switch | `start_cycle`, après `_start_cycle_switch`            | `start_offset_sec` lu dans `self._states` (rempli par `_init_cycle`) ; `None` pour les branches 0 % et 100 %, où il n'y a pas d'état                                                                    |
| `CYCLE_START` vanne  | `start_cycle`, après `_start_cycle_valve`             | `start_offset_sec=None`                                                                                                                                                                                 |
| `UPDATE` vanne       | `_update_running_valve_cycle` et `apply_valve_update` | Après `_apply_valve_command`                                                                                                                                                                            |
| `STOP`               | `_cancel_cycle_impl`                                  | Seulement si un cycle tournait, avec `applied_on_percent=0` ; pas lors de l'annulation interne de `start_cycle` (paramètre `_restarting`), car le `CYCLE_START` suit                                   |

`requested_on_percent` et `is_repeat` sont ceux déjà utilisés pour `_fire_command_receipt`, pour garder les deux notifications cohérentes.

`cycle_start_monotonic` reprend `self._cycle_start_monotonic`, la valeur des reçus, et `monotonic` vaut `time.monotonic()` à la construction de la commande. `cycle_start_monotonic` vaut `None` hors cycle : pour `STOP`, le début de cycle est effacé par `_cancel_cycle_impl` avant la notification, et pour un `UPDATE` émis hors cycle (`apply_valve_update` sans cycle en cours).

Un switch s'allume à `cycle_start_monotonic + start_offset_sec` et s'éteint `on_time_sec` plus tard, modulo la durée du cycle (`_init_cycle` et `_tick`). Ces instants sont nominaux : les délais minimaux d'activation et de désactivation peuvent décaler une bascule. Comme les managers sont attendus l'un après l'autre, la notification peut arriver après l'actionnement : un manager doit se fier à ces horodatages, pas à son heure de réception.

## 6. Ordre des commandes au passage en OFF

Sur le chemin `UnderlyingValveRegulation.turn_off`, l'ordre est : vanne à 0, hook de vanne (`TURN_OFF`), hook de mode, `climate.set_hvac_mode(off)`. Ce chemin est couvert par un test.

Le passage en OFF du VTherm n'emprunte pas ce chemin. `BaseThermostat` envoie d'abord le mode OFF aux climates sous-jacents (`UnderlyingClimate.set_hvac_mode`, donc le hook de mode puis le service), puis la fermeture de la vanne part à la régulation suivante (`_send_regulated_temperature`), avec la cause `REGULATION` et le mode `off`. Un plugin qui doit agir avant le mode OFF reçoit donc le hook de mode, mais pas encore la fermeture de la vanne. Dans le hook de mode, le mode cible est le paramètre `hvac_mode` du hook (il n'y a pas d'objet commande). Dans le hook de vanne, il doit lire `command.hvac_mode` de la `ValveCommand`. Dans les deux cas, il ne doit pas se fier à l'état HA du climate pour savoir que le thermostat est éteint, car cet état peut encore afficher l'ancien mode.

Cet ordre est conservé volontairement. L'inverser demanderait de fermer les vannes régulées avant de déléguer le mode aux climates, ce qui changerait le comportement de tous les VTherm `over_climate` à contrôle de vanne.

## 7. Sécurité, observabilité et exploitation

Un délai dépassé est journalisé en avertissement et une exception en erreur, avec le nom du manager et du hook. Le coût sans plugin est un test de liste vide par point d'appel ; seule la commande de vanne construit sa donnée avant de constater l'absence de manager.

## 8. Tests

`tests/test_underlying_hooks.py` : hook de mode (ordre, mode réel, mode déjà en place, inhibition, délestage, `underlying_tracking`), hook de vanne (ordre au `turn_off`, causes, valeurs envoyées, `closing_degree=None`, absence d'appel pour le recalibrage et l'amorçage, porte d'inhibition), hook de puissance (deux switches avec offsets et `is_repeat`, `over_valve`, `over_climate` à contrôle de vanne, `STOP`), robustesse (manager non configuré, exception, délai, un seul hook, sans plugin). La suite complète sert de contrôle de non-régression.

## 9. Hypothèses, risques, décisions et convergence

- La PR vers `jmcollin78/versatile_thermostat` suit la publication de `vtherm_api` 0.9.0.
- `InterfaceSetpointModifier` n'est appelé nulle part aujourd'hui. Une PR qui l'intègre toucherait aussi `UnderlyingClimate` et la boucle des managers externes ; elle devra réutiliser `_async_call_external_hook` (la version synchrone du modificateur demandera une variante).
- Risque : un hook qui dépasse 10 s retarde la commande du cœur de 10 s au plus.
- Décision : l'ordre du cœur au passage en OFF reste « mode OFF, puis fermeture de la vanne » (section 6).
