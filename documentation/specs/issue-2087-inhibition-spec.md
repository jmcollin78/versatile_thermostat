# Spécification fonctionnelle — Issue #2087 : inhibition contrôlée d’un VTherm

## Métadonnées

| Champ             | Valeur                                                                                                                                                                            |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nom               | Inhibition contrôlée d’un VTherm / Controlled VTherm inhibition                                                                                                                   |
| Issue             | [#2087 — Add an “inhibit” sensor to pause a VTherm](https://github.com/jmcollin78/versatile_thermostat/issues/2087)                                                               |
| Version           | 2.0 — décision d’architecture core/API/plugin                                                                                                                                     |
| Statut            | Spécification convergée, validation mainteneur requise                                                                                                                            |
| Date              | 2026-10-13                                                                                                                                                                        |
| Propriétaire      | Projet Versatile Thermostat                                                                                                                                                       |
| Sources analysées | [Revue de l’issue](../tech-docs/issue-2087-review.md), `base_thermostat.py`, `state_manager.py`, `underlyings.py`, `feature_repair_incorrect_state_manager.py`, `vtherm_state.py` |

## 1. Contexte et objectifs

L’inhibition permet à une autre source de chauffage ou de refroidissement, à un utilisateur ou à une automatisation de disposer temporairement du contrôle effectif des sous-jacents d’un VTherm. Le besoin couvre notamment le chauffage sur surplus photovoltaïque et la coexistence avec une climatisation.

L’inhibition ne modifie jamais l’intention durable du VTherm : HVAC demandé, preset et consigne restent conservés. Elle retire temporairement au VTherm le droit de commander ses sous-jacents, résout l’état effectif à `OFF` avec la raison `hvac_off_inhibition`, puis réconcilie l’intention courante lorsque le plugin confirme la fin de l’inhibition.

Le périmètre est réparti ainsi :

- **Core** : `BaseThermostat` et un manager core minimal de l’état opérationnel et persisté ;
- **API** : façade publique minimale pour demander `set_inhibition(stop_underlyings: bool)` et `unset_inhibition()` ;
- **Plugin** : détection, sources, configuration, délais, bypass, cycle de vie, statut, politique et persistance métier.

Sans plugin d’inhibition, le comportement historique du VTherm est inchangé.

## 2. Acteurs et responsabilités

| Acteur                                | Responsabilités                                                                                                                                                                                                                                                               |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Utilisateur ou automatisation externe | Peut commander directement les sous-jacents pendant l’inhibition ; ses commandes ne sont pas écrasées par le VTherm.                                                                                                                                                          |
| Plugin d’inhibition                   | Agrège les sources, applique configuration, délais et bypass, maintient `ACTIVE`, `INACTIVE` ou `UNKNOWN`, conserve sa politique métier et appelle l’API. Il appelle `set_inhibition` pour `ACTIVE` et `UNKNOWN`, et `unset_inhibition` uniquement après `INACTIVE` confirmé. |
| API                                   | Expose uniquement la façade qui transmet `set_inhibition(stop_underlyings: bool)` et `unset_inhibition()`. Elle ne fournit ni provider, ni factory, ni callback, ni statut ternaire.                                                                                          |
| Core — `BaseThermostat`               | Possède l’état d’inhibition, résout `OFF`, arrête le contrôle, transmet les deux opérations au manager et applique l’intercepteur unique des commandes vers les sous-jacents.                                                                                                 |
| Manager core                          | Gère l’état opérationnel/persisté minimal, l’idempotence, la raison d’arrêt et la phase de réconciliation de sortie. Il ne détecte aucune source et n’instancie aucun composant externe.                                                                                      |
| `StateManager`                        | Résout l’état HVAC effectif à partir de l’état demandé et des contraintes existantes, dont l’inhibition.                                                                                                                                                                      |
| Sous-jacents                          | Peuvent être pilotés directement pendant l’inhibition ; ils reçoivent uniquement l’arrêt d’entrée optionnel et la réconciliation de sortie autorisée.                                                                                                                         |

## 3. Cas d’utilisation

### UC-01 — Activer l’inhibition

1. Le plugin détecte une condition active ou inconnue selon sa politique et appelle `set_inhibition(stop_underlyings)`.
2. Le core marque l’inhibition active, résout le HVAC effectif à `OFF` avec `hvac_off_inhibition` et suspend contrôle et réparation.
3. L’intercepteur ferme les commandes normales vers les sous-jacents.
4. Si `stop_underlyings` vaut `true`, le core autorise une seule opération d’arrêt d’entrée. S’il vaut `false`, aucune commande d’arrêt n’est envoyée.

### UC-02 — Maintenir l’inhibition

Tant que l’inhibition est active, le VTherm ne contrôle pas le chauffage, ne répare pas l’état des sous-jacents et ne réémet pas l’arrêt d’entrée. Les changements de HVAC, de preset ou de consigne sont conservés comme intention, sans reprise des sous-jacents.

### UC-03 — Désactiver l’inhibition

1. Le plugin appelle `unset_inhibition()` seulement après avoir confirmé `INACTIVE`.
2. Le core ferme encore le garde aux commandes normales et ouvre uniquement l’opération de sortie : recalculer l’état demandé courant et l’appliquer aux sous-jacents.
3. Lorsque cette réconciliation est terminée, le core ouvre le garde et reprend le fonctionnement normal.

Une demande `OFF` effectuée pendant l’inhibition reste `OFF` après la sortie.

### UC-04 — Statut inconnu

Le plugin traite `UNKNOWN` comme une condition nécessitant le maintien de l’inhibition : il maintient ou rappelle `set_inhibition(stop_underlyings)` selon sa politique. Il n’appelle jamais `unset_inhibition()` tant que `INACTIVE` n’est pas confirmé. Le core ne reçoit pas et ne décide pas de statut ternaire.

## 4. Exigences fonctionnelles

| ID     | Exigence                                                                                                                                                                                                                        |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-001 | Le core doit être porté par `BaseThermostat` et un manager minimal d’état opérationnel/persisté.                                                                                                                                |
| FR-002 | L’API doit exposer uniquement `set_inhibition(stop_underlyings: bool)` et `unset_inhibition()`, sous forme de façade vers le core.                                                                                              |
| FR-003 | L’API ne doit déclarer ni provider, ni factory, ni callback, ni statut ternaire.                                                                                                                                                |
| FR-004 | Le manager core doit accepter des appels répétés à `set_inhibition` et `unset_inhibition` sans produire d’opération d’entrée ou de sortie supplémentaire.                                                                       |
| FR-005 | `set_inhibition(true)` doit résoudre l’état effectif à `OFF` avec la raison `hvac_off_inhibition`, suspendre contrôle et réparation, fermer l’intercepteur et autoriser un seul arrêt d’entrée.                                 |
| FR-006 | `set_inhibition(false)` doit produire les mêmes effets de retrait et de garde que `set_inhibition(true)`, mais ne doit envoyer aucun arrêt aux sous-jacents.                                                                    |
| FR-007 | Le core doit conserver HVAC demandé, preset et consigne ; l’inhibition ne doit pas les remplacer par `OFF`.                                                                                                                     |
| FR-008 | L’intercepteur core doit être l’unique point bloquant toute commande VTherm vers un sous-jacent pendant l’inhibition.                                                                                                           |
| FR-009 | Lorsque le garde est fermé, les seules commandes autorisées sont l’arrêt d’entrée optionnel et l’opération de réconciliation de sortie. Toutes les commandes normales, y compris réparation et contrôle, doivent être bloquées. |
| FR-010 | `unset_inhibition()` doit maintenir le garde fermé pendant toute la réconciliation ; le garde ne doit s’ouvrir qu’après son achèvement.                                                                                         |
| FR-011 | La réconciliation de sortie doit recalculer et appliquer l’intention demandée courante, avec les autres contraintes actives.                                                                                                    |
| FR-012 | Le plugin doit porter les sources, la configuration, les délais, le bypass, le cycle de vie, la politique métier et leur persistance.                                                                                           |
| FR-013 | Le plugin doit exposer et traiter les statuts `ACTIVE`, `INACTIVE` et `UNKNOWN`. Il doit appeler `set_inhibition` pour `ACTIVE` et `UNKNOWN`, et réserver `unset_inhibition` à `INACTIVE` confirmé.                             |
| FR-014 | Le core ne doit découvrir, créer ou instancier directement aucun provider ou composant de source. Il ne doit contenir aucun `if` dispersé de détection ou de politique plugin.                                                  |
| FR-015 | Le manager core doit persister au minimum l’inhibition opérationnelle, la phase de garde et l’accomplissement de l’arrêt d’entrée lorsque celui-ci a été demandé.                                                               |
| FR-016 | En l’absence de plugin, le système doit conserver le comportement historique, sans garde ni raison d’inhibition active.                                                                                                         |

## 5. Règles métier

| ID     | Règle                                                                                                                                           |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| BR-001 | L’inhibition est une contrainte temporaire ; elle ne modifie jamais l’intention demandée durable.                                               |
| BR-002 | Une activation est idempotente : un même état inhibé n’entraîne ni nouvel arrêt, ni contrôle, ni réparation.                                    |
| BR-003 | `stop_underlyings` ne concerne que l’arrêt d’entrée ; il ne désactive ni la résolution `OFF`, ni la suspension, ni le garde.                    |
| BR-004 | Le garde unique interdit toute commande normale VTherm vers un sous-jacent pendant l’inhibition.                                                |
| BR-005 | L’opération de sortie est une exception contrôlée au garde : elle peut uniquement réconcilier l’état demandé courant.                           |
| BR-006 | Le garde reste fermé pendant la réconciliation de sortie et s’ouvre ensuite, jamais avant.                                                      |
| BR-007 | `UNKNOWN` est traité par le plugin comme une absence de confirmation de sortie ; il maintient l’inhibition et n’appelle pas `unset_inhibition`. |
| BR-008 | Seul `INACTIVE` confirmé par le plugin autorise l’appel à `unset_inhibition`.                                                                   |
| BR-009 | Une demande `OFF` conservée pendant l’inhibition interdit toute réactivation à la sortie.                                                       |
| BR-010 | Sans plugin, aucune règle d’inhibition ne s’applique et le cycle historique est conservé.                                                       |

## 6. Transitions et persistance

| État           | Événement                                      | Effet                                                                                                                      |
| -------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Normal         | `set_inhibition(true)`                         | Résoudre `OFF`, raison dédiée, suspendre contrôle/réparation, fermer le garde, envoyer un arrêt d’entrée au plus une fois. |
| Normal         | `set_inhibition(false)`                        | Même retrait et même garde, sans arrêt d’entrée.                                                                           |
| Inhibé         | Appel répété à `set_inhibition(...)`           | Ne rien réémettre ; mettre à jour la politique seulement selon le contrat du plugin, sans rouvrir le garde.                |
| Inhibé         | HVAC/preset/consigne modifié                   | Conserver l’intention ; bloquer toute commande normale.                                                                    |
| Inhibé         | `unset_inhibition()` après `INACTIVE` confirmé | Passer en réconciliation, autoriser uniquement l’application de l’état demandé courant, puis ouvrir le garde.              |
| Réconciliation | Commande normale ou nouvel appel concurrent    | Bloquer la commande normale ; ne pas ouvrir le garde avant la fin de l’opération de sortie.                                |
| Normal         | Aucun plugin                                   | Exécuter le comportement historique.                                                                                       |

Après redémarrage, le core doit restaurer son état opérationnel sans réémettre un arrêt déjà accompli. Si l’inhibition est active, le garde et la suspension restent actifs. Si une confirmation `INACTIVE` n’est pas disponible, le plugin maintient l’inhibition. La persistance métier des sources, délais, bypass et politique appartient au plugin ; elle ne doit pas être dupliquée par le core.

## 7. Contraintes fonctionnelles et exclusions

Le core doit conserver une résolution centralisée de l’état effectif et une raison stable `hvac_off_inhibition`. Aucune donnée sensible supplémentaire n’est requise. Le contrôle direct des sous-jacents par une autre intégration doit rester possible pendant l’inhibition.

Sont exclus de cette version : configuration utilisateur d’inhibition dans le core, entité ou service core dédié, provider/factory core, callback d’événement public, statut ternaire dans l’API ou le core, modification de `requested_state`/`current_state` pour y ajouter `inhibited`, modes forcés autres que `OFF`, et refactorisation générale des contraintes HVAC.

## 8. Critères d’acceptation

| ID     | Scénario                                                                                   | Résultat attendu                                                                                                       |
| ------ | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| AC-001 | Le plugin appelle `set_inhibition(true)` alors que le VTherm chauffe.                      | HVAC effectif `OFF`, raison `hvac_off_inhibition`, contrôle/réparation suspendus, un seul arrêt envoyé et garde fermé. |
| AC-002 | Le plugin appelle `set_inhibition(false)`.                                                 | HVAC effectif `OFF`, contrôle/réparation suspendus, aucun arrêt envoyé et garde fermé.                                 |
| AC-003 | Plusieurs cycles sont exécutés pendant l’inhibition.                                       | Aucune commande normale, réparation ou répétition de l’arrêt n’est envoyée.                                            |
| AC-004 | Une autre intégration commande un sous-jacent pendant l’inhibition.                        | La commande externe n’est pas écrasée par le VTherm.                                                                   |
| AC-005 | HVAC, preset ou consigne changent pendant l’inhibition.                                    | La dernière intention est conservée et aucun sous-jacent ne reprend avant la sortie.                                   |
| AC-006 | `INACTIVE` est confirmé puis le plugin appelle `unset_inhibition()`.                       | Le core garde le garde fermé, effectue une seule réconciliation avec l’intention courante, puis ouvre le garde.        |
| AC-007 | Une commande normale arrive pendant la réconciliation.                                     | Elle est bloquée ; seule l’opération de sortie est autorisée.                                                          |
| AC-008 | `OFF` est demandé pendant l’inhibition puis celle-ci prend fin.                            | Aucun sous-jacent n’est réactivé.                                                                                      |
| AC-009 | Le plugin est `UNKNOWN` après démarrage, erreur ou rechargement.                           | Le plugin maintient/appelle `set_inhibition`; aucun `unset_inhibition` n’est appelé et aucune reprise n’a lieu.        |
| AC-010 | Home Assistant redémarre pendant l’inhibition après l’arrêt d’entrée.                      | Le garde reste fermé, le contrôle reste suspendu et aucun second arrêt inutile n’est envoyé.                           |
| AC-011 | Le VTherm fonctionne sans plugin.                                                          | Le comportement historique est inchangé.                                                                               |
| AC-012 | Deux chemins core tentent d’émettre une commande vers un sous-jacent pendant l’inhibition. | L’intercepteur unique bloque les deux, sauf l’arrêt d’entrée autorisé ou la réconciliation de sortie.                  |

## 9. Matrice de tests attendus

| Domaine         | Cas                                                                                 | Vérification minimale                                                                            |
| --------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| API             | Appels `set(true)`, `set(false)`, `unset`, répétition et ordre invalide             | Contrat de façade ; absence de provider, factory, callback et statut ternaire.                   |
| Manager core    | États normal, inhibé, réconciliation, persistance et restauration                   | Transitions idempotentes, garde et état opérationnel restauré.                                   |
| Résolution HVAC | Chauffage, refroidissement, demande `OFF`, autres contraintes                       | `OFF` effectif et raison stable sans modification de l’intention.                                |
| Intercepteur    | Contrôle, réparation, commandes multiples et appels concurrents                     | Toute commande normale bloquée pendant l’inhibition ; seules les deux exceptions sont possibles. |
| Arrêt d’entrée  | `stop_underlyings=true`, `false`, sous-jacent déjà arrêté, répétition               | Arrêt unique si demandé, jamais sinon.                                                           |
| Sortie          | `INACTIVE`, intention chauffage/refroidissement/`OFF`, réconciliation lente         | Une seule réconciliation, garde fermé jusqu’à sa fin, ouverture ensuite.                         |
| Plugin          | Sources multiples, configuration, délais, bypass, cycle de vie, persistance métier  | `ACTIVE` et `UNKNOWN` appellent/maintiennent `set`; seul `INACTIVE` confirmé appelle `unset`.    |
| Redémarrage     | Inhibition active, arrêt déjà accompli, sortie non confirmée                        | Pas de second arrêt ni de reprise prématurée.                                                    |
| Régression      | Absence de plugin, fenêtre, auto-start/auto-stop, TPI et réparation hors inhibition | Fonctionnement historique inchangé hors périmètre.                                               |

## 10. Hypothèses, questions ouvertes et traçabilité

### Hypothèses

- La raison stable retenue est `hvac_off_inhibition`.
- Le plugin agrège plusieurs sources si nécessaire ; le core ne connaît que les appels de la façade.
- `UNKNOWN` signifie que la sortie n’est pas confirmée et impose le maintien de l’inhibition.
- La persistance core et la persistance métier du plugin sont distinctes.

### Questions ouvertes

1. Confirmer le nom sérialisé de la politique plugin qui détermine `stop_underlyings`.
2. Définir le format exact des attributs d’observabilité core et plugin.
3. Définir le comportement précis du plugin lorsqu’une politique change pendant une inhibition déjà active.
4. Confirmer l’ordre de livraison API, core et plugin.

### Traçabilité

Cette spécification s’appuie sur [la revue de l’issue #2087](../tech-docs/issue-2087-review.md) et sur les fichiers techniques indiqués dans les métadonnées. Elle décrit une décision cible et ne prétend pas que ces opérations existent déjà dans le code. Aucun autre fichier n’est modifié par cette révision.

---

# Functional Specification — Issue #2087: Controlled VTherm Inhibition

## Metadata

| Field            | Value                                                                                                                                                                         |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name             | Controlled VTherm inhibition / Inhibition contrôlée d’un VTherm                                                                                                               |
| Issue            | [#2087 — Add an “inhibit” sensor to pause a VTherm](https://github.com/jmcollin78/versatile_thermostat/issues/2087)                                                           |
| Version          | 2.0 — core/API/plugin architecture decision                                                                                                                                   |
| Status           | Converged specification, maintainer approval required                                                                                                                         |
| Date             | 2026-10-13                                                                                                                                                                    |
| Owner            | Versatile Thermostat project                                                                                                                                                  |
| Analyzed sources | [Issue review](../tech-docs/issue-2087-review.md), `base_thermostat.py`, `state_manager.py`, `underlyings.py`, `feature_repair_incorrect_state_manager.py`, `vtherm_state.py` |

## 1. Context and objectives

Inhibition lets another heating or cooling source, a user, or an automation temporarily own effective control of a VTherm’s underlying devices. Use cases include photovoltaic-surplus heating and coexistence with air conditioning.

Inhibition never changes durable VTherm intent: requested HVAC mode, preset, and setpoint remain stored. It withdraws VTherm authority to command underlying devices, resolves effective state to `OFF` with reason `hvac_off_inhibition`, and reconciles current intent when the plugin confirms that inhibition has ended.

The scope is divided between the core (`BaseThermostat` and a minimal operational/persisted-state manager), the API (only `set_inhibition(stop_underlyings: bool)` and `unset_inhibition()`), and the plugin (sources, configuration, delays, bypass, lifecycle, status, policy, and business persistence). Without a plugin, historical behavior remains unchanged.

## 2. Actors and responsibilities

| Actor                       | Responsibilities                                                                                                                                                                                                                                                        |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User or external automation | May directly command underlying devices during inhibition; VTherm does not overwrite those commands.                                                                                                                                                                    |
| Inhibition plugin           | Aggregates sources, applies configuration, delays, and bypass, maintains `ACTIVE`, `INACTIVE`, or `UNKNOWN`, persists business policy, and calls the API. It calls `set_inhibition` for `ACTIVE` and `UNKNOWN`, and `unset_inhibition` only after confirmed `INACTIVE`. |
| API                         | Exposes only the façade forwarding `set_inhibition(stop_underlyings: bool)` and `unset_inhibition()`. It provides no provider, factory, callback, or ternary status.                                                                                                    |
| Core — `BaseThermostat`     | Owns inhibition state, resolves `OFF`, stops control, forwards the two operations to the manager, and applies the unique command interceptor for underlying devices.                                                                                                    |
| Core manager                | Manages minimal operational/persisted state, idempotence, stop reason, and exit reconciliation. It detects no source and instantiates no external component.                                                                                                            |
| `StateManager`              | Resolves effective HVAC from requested state and existing constraints, including inhibition.                                                                                                                                                                            |
| Underlying devices          | May be directly controlled during inhibition; they receive only the optional entry stop and authorized exit reconciliation.                                                                                                                                             |

## 3. Use cases

### UC-01 — Set inhibition

1. The plugin detects an active or policy-defined unknown condition and calls `set_inhibition(stop_underlyings)`.
2. The core marks inhibition active, resolves effective HVAC to `OFF` with `hvac_off_inhibition`, and suspends control and repair.
3. The interceptor closes normal commands to underlying devices.
4. If `stop_underlyings` is `true`, the core authorizes one entry-stop operation; if `false`, no stop is sent.

### UC-02 — Remain inhibited

While inhibition is active, VTherm does not control heating, repair underlying state, or resend the entry stop. Changes to HVAC, preset, or setpoint are retained as intent without resuming underlying devices.

### UC-03 — Unset inhibition

1. The plugin calls `unset_inhibition()` only after confirming `INACTIVE`.
2. The core keeps the guard closed to normal commands and authorizes only recalculation and application of current requested state.
3. After reconciliation completes, the core opens the guard and resumes normal operation.

An `OFF` request made during inhibition remains `OFF` after exit.

### UC-04 — Unknown status

The plugin treats `UNKNOWN` as requiring inhibition: it maintains or calls `set_inhibition(stop_underlyings)` according to policy. It never calls `unset_inhibition()` until `INACTIVE` is confirmed. The core neither receives nor decides a ternary status.

## 4. Functional requirements

| ID     | Requirement                                                                                                                                                                       |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-001 | The core shall be implemented by `BaseThermostat` and a minimal operational/persisted-state manager.                                                                              |
| FR-002 | The API shall expose only `set_inhibition(stop_underlyings: bool)` and `unset_inhibition()` as a façade to the core.                                                              |
| FR-003 | The API shall declare no provider, factory, callback, or ternary status.                                                                                                          |
| FR-004 | The core manager shall accept repeated set/unset calls without producing another entry or exit operation.                                                                         |
| FR-005 | `set_inhibition(true)` shall resolve effective state to `OFF` with reason `hvac_off_inhibition`, suspend control and repair, close the interceptor, and authorize one entry stop. |
| FR-006 | `set_inhibition(false)` shall produce the same withdrawal and guard behavior but shall send no stop to underlying devices.                                                        |
| FR-007 | The core shall preserve requested HVAC, preset, and setpoint; inhibition shall not replace them with `OFF`.                                                                       |
| FR-008 | The core interceptor shall be the unique point blocking every VTherm command to an underlying device during inhibition.                                                           |
| FR-009 | While the guard is closed, only the optional entry stop and exit reconciliation shall be allowed; all normal control and repair commands shall be blocked.                        |
| FR-010 | `unset_inhibition()` shall keep the guard closed for the whole reconciliation and open it only after completion.                                                                  |
| FR-011 | Exit reconciliation shall recalculate and apply current requested intent with other active constraints.                                                                           |
| FR-012 | The plugin shall own sources, configuration, delays, bypass, lifecycle, business policy, and their persistence.                                                                   |
| FR-013 | The plugin shall process `ACTIVE`, `INACTIVE`, and `UNKNOWN`; it shall call set for `ACTIVE`/`UNKNOWN` and unset only for confirmed `INACTIVE`.                                   |
| FR-014 | The core shall not discover, create, or instantiate a provider or source component directly, nor contain dispersed plugin-policy conditionals.                                    |
| FR-015 | The core manager shall persist operational inhibition, guard phase, and completion of the requested entry stop.                                                                   |
| FR-016 | Without a plugin, the system shall preserve historical behavior, with no active inhibition guard or reason.                                                                       |

## 5. Business rules

| ID     | Rule                                                                                                               |
| ------ | ------------------------------------------------------------------------------------------------------------------ |
| BR-001 | Inhibition is temporary; it never changes durable requested intent.                                                |
| BR-002 | Activation is idempotent: the same inhibited state causes no new stop, control, or repair.                         |
| BR-003 | `stop_underlyings` applies only to the entry stop; it does not disable `OFF` resolution, suspension, or the guard. |
| BR-004 | The unique guard forbids every normal VTherm command to an underlying device during inhibition.                    |
| BR-005 | Exit is a controlled guard exception and may only reconcile current requested state.                               |
| BR-006 | The guard remains closed throughout exit reconciliation and opens afterward, never before.                         |
| BR-007 | `UNKNOWN` is unconfirmed exit; the plugin maintains inhibition and does not call unset.                            |
| BR-008 | Only confirmed `INACTIVE` authorizes a call to `unset_inhibition`.                                                 |
| BR-009 | A requested `OFF` retained during inhibition forbids reactivation at exit.                                         |
| BR-010 | Without a plugin, no inhibition rule applies and the historical cycle is preserved.                                |

## 6. Transitions and persistence

The normal-to-inhibited transition resolves `OFF`, records the dedicated reason, suspends control and repair, closes the guard, and sends at most one requested entry stop. Repeated set calls emit nothing again. Changes to intent are retained. After confirmed `INACTIVE`, unset enters reconciliation; normal commands remain blocked until current requested state has been applied, then the guard opens.

After restart, the core restores operational state without resending a completed stop. Active inhibition keeps guard and suspension active. If `INACTIVE` is unavailable, the plugin maintains inhibition. Source, delay, bypass, and policy persistence belongs to the plugin and is not duplicated in core. Without a plugin, historical behavior applies.

## 7. Functional constraints and exclusions

The core retains centralized effective-state resolution and stable reason `hvac_off_inhibition`. Direct external control of underlying devices remains possible. Excluded are core configuration/entities/services, provider/factory/callback contracts, ternary API/core status, an `inhibited` requested/current state, modes other than `OFF`, and general HVAC refactoring.

## 8. Acceptance criteria

| ID     | Scenario                                                             | Expected result                                                                           |
| ------ | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| AC-001 | Plugin calls `set_inhibition(true)` while VTherm heats.              | Effective HVAC `OFF`, dedicated reason, control/repair suspended, one stop, guard closed. |
| AC-002 | Plugin calls `set_inhibition(false)`.                                | Effective HVAC `OFF`, control/repair suspended, no stop, guard closed.                    |
| AC-003 | Several cycles run during inhibition.                                | No normal command, repair, or repeated stop is sent.                                      |
| AC-004 | Another integration commands an underlying device.                   | VTherm does not overwrite the external command.                                           |
| AC-005 | HVAC, preset, or setpoint changes during inhibition.                 | Latest intent is retained and no underlying device resumes before exit.                   |
| AC-006 | Confirmed `INACTIVE` is followed by `unset_inhibition()`.            | Guard remains closed during one reconciliation and opens afterward.                       |
| AC-007 | A normal command arrives during reconciliation.                      | It is blocked; only exit operation is allowed.                                            |
| AC-008 | `OFF` is requested during inhibition and inhibition ends.            | No underlying device is reactivated.                                                      |
| AC-009 | Plugin is `UNKNOWN`.                                                 | Plugin maintains/calls set; unset is not called and no resumption occurs.                 |
| AC-010 | Home Assistant restarts during active inhibition after entry stop.   | Guard remains closed, control stays suspended, and no second stop is sent.                |
| AC-011 | VTherm runs without a plugin.                                        | Historical behavior is unchanged.                                                         |
| AC-012 | Multiple core paths attempt an underlying command during inhibition. | Unique interceptor blocks them, except authorized entry stop or exit reconciliation.      |

## 9. Expected test matrix

| Area            | Cases                                                              | Minimum verification                                                |
| --------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------- |
| API             | set true/false, unset, repetition, invalid order                   | Façade contract; no provider, factory, callback, or ternary status. |
| Core manager    | Normal, inhibited, reconciling, persistence, restoration           | Idempotent transitions, guard, and restored state.                  |
| HVAC resolution | Heating, cooling, requested `OFF`, other constraints               | Effective `OFF` and stable reason without changing intent.          |
| Interceptor     | Control, repair, multiple paths, concurrency                       | Every normal command blocked; only two exceptions possible.         |
| Entry stop      | Policy true/false, stopped device, repetition                      | One stop when requested, never otherwise.                           |
| Exit            | Confirmed inactive, each intent, slow reconciliation               | One reconciliation, guard closed until completion, then open.       |
| Plugin          | Sources, configuration, delays, bypass, lifecycle, persistence     | Active/unknown maintain set; only confirmed inactive calls unset.   |
| Restart         | Active inhibition, completed stop, unconfirmed exit                | No second stop or premature resumption.                             |
| Regression      | No plugin, window, auto-start/stop, TPI, repair outside inhibition | Historical behavior unchanged outside scope.                        |

## 10. Assumptions, open questions, and traceability

### Assumptions

- Stable reason is `hvac_off_inhibition`.
- The plugin aggregates sources when needed; core knows only façade calls.
- `UNKNOWN` means exit is unconfirmed and inhibition must remain active.
- Core and plugin business persistence are distinct.

### Open questions

1. Confirm the serialized plugin policy name determining `stop_underlyings`.
2. Define exact core and plugin observability attributes.
3. Define plugin behavior when policy changes during active inhibition.
4. Confirm API, core, and plugin delivery order.

### Traceability

This specification is based on [the Issue #2087 review](../tech-docs/issue-2087-review.md) and the technical files listed in the metadata. It describes a target decision and does not claim that these operations already exist in code. No other file is modified by this revision.
