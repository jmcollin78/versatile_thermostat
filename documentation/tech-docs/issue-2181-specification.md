# Spécification fonctionnelle — Issue #2181 : hooks des sous-jacents pour les plugins

## Métadonnées

| Champ             | Valeur                                                                                                                                                                  |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nom               | Suivi des commandes envoyées aux sous-jacents par les feature managers externes                                                                                         |
| Version           | 1.0                                                                                                                                                                     |
| Statut            | Implémenté dans le cœur, sous réserve de la publication de `vtherm_api` 0.9.0                                                                                           |
| Date              | 2026-11-05                                                                                                                                                              |
| Propriétaire      | Projet Versatile Thermostat ; arbitrage final par le mainteneur                                                                                                         |
| Sources analysées | [Issue #2181](https://github.com/jmcollin78/versatile_thermostat/issues/2181), [discussion #2067](https://github.com/jmcollin78/versatile_thermostat/discussions/2067) |

## 1. Contexte et objectifs

Certains équipements, comme la Sonoff TRV-ZBT, ne se pilotent pas correctement en contrôle direct de la vanne avec un simple blueprint. Au passage en OFF, la vanne se place sur sa position de repos (`idle_valve_position`) et le blueprint réagit trop tard pour la fermer. Un plugin doit pouvoir suivre les commandes que le cœur envoie aux sous-jacents pour corriger ce genre de comportement propre à un modèle d'équipement.

Objectif : offrir aux feature managers de plugins trois notifications optionnelles, définies par `vtherm_api` 0.9.0. Aucune ne modifie ni n'annule la commande du cœur.

## 2. Acteurs et cas d'utilisation

| Acteur                       | Rôle                                                                                                  |
| ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| Cœur de Versatile Thermostat | Envoie les commandes aux sous-jacents et notifie les feature managers externes configurés.            |
| Plugin (feature manager)     | Implémente un ou plusieurs hooks pour suivre les commandes et corriger le comportement d'un modèle.   |
| Utilisateur                  | N'a rien à configurer dans VTherm : la fonctionnalité concerne uniquement les plugins.                |

**UC-01 — Avant un changement de mode.** Le plugin est prévenu juste avant que le cœur envoie `climate.set_hvac_mode` à un climate sous-jacent, pendant que celui-ci est encore dans son mode courant.

**UC-02 — Après une commande de vanne.** Le plugin est prévenu après l'envoi des degrés d'ouverture et de fermeture d'un `over_climate` à contrôle direct de la vanne, avec la cause de la commande.

**UC-03 — Suivi de la puissance.** Le plugin est prévenu, pour chaque sous-jacent piloté par le cycle scheduler, de la puissance demandée et de la puissance appliquée au début de cycle, à chaque mise à jour de vanne et à l'arrêt du cycle.

## 3. Exigences fonctionnelles

| ID     | Exigence                                                                                                                                                                                                    |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-001 | Le cœur appelle `async_before_underlying_hvac_mode(climate_entity_id, hvac_mode, current_hvac_mode, command_cause)` avant `climate.set_hvac_mode` sur un climate sous-jacent.                              |
| FR-002 | Le cœur appelle `async_after_valve_command(command)` après l'envoi des degrés d'un sous-jacent `valve_regulation`, avec une cause `regulation`, `turn_off`, `startup` ou `repair`.                          |
| FR-003 | Le cœur appelle `async_on_underlying_power(command)` au début de chaque cycle (`cycle_start`), à chaque mise à jour de vanne d'un cycle en cours (`update`) et à l'annulation d'un cycle en cours (`stop`). |
| FR-004 | Chaque hook est optionnel et indépendant : un manager qui n'en implémente qu'un seul ne reçoit que celui-là.                                                                                               |
| FR-005 | Seuls les managers dont `is_configured` est vrai sont appelés.                                                                                                                                             |
| FR-006 | Un hook n'est appelé que si la commande du cœur part vraiment : pas d'appel si le mode demandé est déjà en place, si l'inhibition bloque la commande ou si le délestage refuse l'allumage.                  |
| FR-007 | Une exception ou un dépassement de délai (`UNDERLYING_HOOK_TIMEOUT_SEC`, 10 s) est journalisé et n'empêche jamais la commande du cœur.                                                                     |

## 4. Règles métier

- Les modes HVAC sont transmis en chaînes de caractères.
- `command_cause` vaut `None` pour une commande normale et `"underlying_tracking"` quand le VTherm recopie un changement fait sur l'appareil.
- Le recalibrage des vannes et l'amorçage des degrés inconnus n'appellent pas le hook de vanne.
- Les bascules on/off d'un switch pendant un cycle ne déclenchent pas de notification de puissance : `on_time_sec`, `off_time_sec` et `start_offset_sec` suffisent à les déduire.
- Un redémarrage interne du cycle (nouvelle demande, redémarrage automatique) émet un `cycle_start`, jamais un `stop`.
- Le hook de puissance est distinct des reçus de commande appliquée (`AppliedCommandReceipt`) : le reçu décrit le thermostat entier et sert au plugin d'algorithme, le hook décrit chaque sous-jacent et sert aux feature managers.

## 5. Contraintes fonctionnelles

- Sans feature manager externe, aucun comportement ne change et le surcoût est négligeable : les points d'appel sortent immédiatement.
- Les hooks sont attendus par le cœur : ils doivent rendre la main vite. Un traitement long se planifie dans une tâche du plugin.
- Aucune configuration utilisateur n'est ajoutée.

## 6. Critères d'acceptation

| ID     | Scénario                                                                                                                                                  |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-001 | Passage en OFF puis en HEAT d'un `over_climate` : le hook de mode est appelé avant le service avec le mode réel du climate.                               |
| AC-002 | Mode déjà en place, inhibition active, délestage refusant l'allumage : aucun appel du hook de mode.                                                       |
| AC-003 | Suivi d'un changement fait sur l'appareil : `command_cause == "underlying_tracking"`.                                                                     |
| AC-004 | Fermeture d'une vanne régulée par `turn_off` : `set_value(0)`, puis hook de vanne (`turn_off`), puis hook de mode (`off`), puis `set_hvac_mode(off)`.     |
| AC-005 | Régulation, démarrage, réparation et arrêt par inhibition : la cause du hook de vanne est correcte ; `closing_degree` vaut `None` sans entité de fermeture. |
| AC-006 | Recalibrage et amorçage des degrés inconnus : aucun appel du hook de vanne.                                                                               |
| AC-007 | VTherm switch à deux sous-jacents : deux `cycle_start` aux `start_offset_sec` différents, puis `is_repeat=True` au cycle suivant.                         |
| AC-008 | `over_valve` et `over_climate` à contrôle de vanne : `cycle_start` puis `update` ; `stop` au passage en OFF.                                              |
| AC-009 | Manager non configuré, hook en exception, hook trop lent, manager à un seul hook : le cœur n'est jamais bloqué et chaque manager ne reçoit que ses hooks.  |

## 7. Fonctions non prises en compte

- Modification ou annulation de la commande du cœur par un hook.
- Hook synchrone de modification de consigne (`InterfaceSetpointModifier`), traité séparément.
- Notification des bascules on/off d'un switch pendant un cycle.
- Documentation utilisateur : la fonctionnalité ne se configure pas dans VTherm.

## 8. Évolutions futures proposées

- Nouveaux quirks d'équipements à puissance modulable qui exploitent `async_on_underlying_power`.
- Convergence de l'ordre des commandes au passage en OFF d'un `over_climate` à contrôle de vanne (voir la conception, section 6).

## 9. Hypothèses, questions ouvertes et traçabilité

**Hypothèse :** `vtherm_api` 0.9.0 est publié avant la fusion de la PR, sinon la CI ne trouve pas la dépendance.

**Question ouverte :** l'ordre « fermeture de la vanne, puis mode OFF » n'est obtenu que sur le chemin `UnderlyingValveRegulation.turn_off`. Le passage en OFF du VTherm envoie aujourd'hui le mode OFF aux climates avant la fermeture de la vanne (voir la conception).

**Traçabilité :** conception dans [issue-2181-design.md](issue-2181-design.md) ; tests dans `tests/test_underlying_hooks.py`.
