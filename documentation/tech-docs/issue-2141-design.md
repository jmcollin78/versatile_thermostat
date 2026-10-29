# Issue #2141 — Conception détaillée v2.0 du suivi sûr des TRV

| Métadonnée             | Valeur                                                                                                                                                                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Statut                 | Conception à valider ; développement non autorisé                                                                                                                                                                                                      |
| Version / date         | 2.0 / 2026-10-29                                                                                                                                                                                                                                       |
| Propriétaire           | Mainteneurs de Versatile Thermostat                                                                                                                                                                                                                    |
| Périmètre              | VTherm `over_climate`, y compris la régulation directe de vanne                                                                                                                                                                                        |
| Sources fonctionnelles | [Spécification FR v2.0](issue-2141-specification_fr.md), [Specification EN v2.0](issue-2141-specification_en.md)                                                                                                                                       |
| Régression source      | [Revue #2159](issue-2159-review.md) ; [#2141](https://github.com/jmcollin78/versatile_thermostat/issues/2141)                                                                                                                                          |
| Code et tests relus    | `thermostat_climate.py`, `underlyings.py`, `thermostat_climate_valve.py`, `base_thermostat.py`, `cycle_scheduler.py`, `valve_command.py`, `underlying_state_manager.py`, `test_overclimate.py`, `test_overclimate_valve.py`, `test_cycle_scheduler.py` |
| Vérification           | Relecture statique uniquement. Aucun code, test, configuration ou état Home Assistant n'a été exécuté ou modifié.                                                                                                                                      |

> **Normativité.** Les sections 1 à 10 ci-dessous constituent l'intégralité de la conception v2.0 applicable. L'historique des versions antérieures relève exclusivement de Git et ne doit pas servir de référence de développement.

## 1. Objectif et décisions confirmées

Le commutateur `follow_underlying_temp_change` suit les changements sous-jacents de **consigne et de `hvac_mode`** pour un VTherm `over_climate`. La conception remplace donc définitivement l'ancien périmètre « consignes seulement ». Elle ne transforme jamais `hvac_action` ni fan en changement de mode.

- L'alternative A (« aucun suivi avant le premier envoi VTherm ») est rejetée afin de préserver Q-03.
- L'alternative B est retenue : le premier état de découverte ou de restauration de chaque underlying est une référence inerte ; un changement distinct postérieur peut être suivi sans ordre VTherm antérieur.
- Le mode ne reçoit pas le debounce de cinq secondes, réservé à la consigne. Il reste soumis à la même cause, au même plafond global et à la même suspension.
- Toute commande physique induite par une observation suivie porte l'immuable `COMMAND_CAUSE_UNDERLYING_TRACKING`, y compris la régulation/TPI, les callbacks, le renvoi TRVZB, les services `climate` et `number`.
- Trois tentatives physiques induites sont autorisées par VTherm entre deux nouvelles commandes externes valides : la troisième est débitée puis envoyée, la quatrième est refusée avant appel. Le pilotage direct ne consomme pas ce budget.
- Seule une commande externe valide reçue à la frontière du VTherm réarme. Un timer, un callback, une régulation, un écho, une bascule d'option ou un appel interne ne réarme jamais.

Le plafond ne borne pas une automatisation Home Assistant externe qui renvoie une commande VTherm à chaque tour : chaque nouvelle livraison externe la réarme volontairement. Il ne prouve pas non plus une provenance humaine ou matérielle d'une observation.

## 2. Constats vérifiés et écart de l'implémentation actuelle

1. `UnderlyingStateManager.add_underlying_entities()` programme l'état déjà en cache avec `old_state=None`. `UnderlyingEntity._underlying_changed()` utilise ce premier passage pour initialiser et appeler `check_initial_state()`, puis retourne : ce premier callback n'est actuellement pas transmis à `ThermostatOverClimate.underlying_changed()`.
2. Après initialisation, `UnderlyingClimate._underlying_changed()` dérive mode, action, fan et consigne puis appelle `ThermostatOverClimate.underlying_changed()`.
3. Cette dernière méthode adopte actuellement un `new_hvac_mode` lorsque le commutateur est actif, mais appelle `update_states()` sans `COMMAND_CAUSE_UNDERLYING_TRACKING`. La revue #2159 a démontré qu'avec budget saturé et suivi suspendu, cette branche continue à adopter `heat/off` et peut donc provoquer une régulation de vanne 0 % / 100 %.
4. Les consignes candidates possèdent un délai de cinq secondes et transmettent déjà la cause dans leur adoption. Le classement actuel dépend néanmoins de `last_sent_temperature` ; il ne peut pas être utilisé pour décider si un état est initial en toute sécurité.
5. `BaseThermostat.update_states()` propage déjà une cause vers `set_hvac_mode()` et `async_control_heating()`. `UnderlyingClimate.set_hvac_mode()` conserve la cause dans le renvoi TRVZB de deux secondes, mais la branche mode ne fournit actuellement aucune cause.
6. La régulation à vanne casse encore cette chaîne : `ThermostatOverClimateValve`, `CycleScheduler`, `UnderlyingValveRegulation` et `send_value_to_number()` ne transportent pas de cause jusqu'à `number.set_value`. Le plafond n'y est donc pas démontrable.

## 3. Modèle de données sans cause globale mutable

Chaque adoption crée un contexte immuable ; aucune variable « cause courante » partagée entre tâches ne doit exister.

```text
TrackingChain(
    cause=COMMAND_CAUSE_UNDERLYING_TRACKING,
    chain_id=<compteur ou UUID VTherm>,
    tracking_epoch=<entier>,
    source_entity_id=<climate.xxx>,
    observation_rank=<entier local>,
    kind=<temperature | hvac_mode>
)
```

La même instance est passée à `update_states`, aux transitions HVAC, à la régulation, au scheduler et à chaque underlying. Une fermeture de callback capture la chaîne et son époque ; elle ne relit pas un état global mutable pour savoir quelle cause appliquer.

| État VTherm en mémoire                     | Règle                                                                                                  |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `tracking_epoch`                           | Invalide les callbacks issus d'une commande externe, d'une désactivation, d'un retrait ou d'un reload. |
| `tracking_attempts` / `tracking_suspended` | Budget commun 0..3, partagé entre tous les TRV et les domaines `climate` et `number`. Non persistant.  |
| `intent_generation`                        | Invalide les candidates après une intention/priorité plus récente ; distinct de l'époque causale.      |
| `tracking_chain_seq`                       | Corrélation et diagnostics uniquement.                                                                 |

| État par underlying              | Règle                                                                                                              |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `baseline_pending`, `baseline`   | Référence initiale `{mode, consigne, rang, type_de_livraison}` ; elle ne dépend jamais de `last_sent_temperature`. |
| `last_observed` et `event_rank`  | Dernier état livré et ordre local strict, pas horodatage matériel.                                                 |
| `last_physical_temperature_send` | Dernière tentative réellement lancée `{valeur limitée, issue}` ; ni acquittement ni historique d'ordres remplacés. |
| `candidate`                      | Une seule candidate avec rang, version, génération, époque, échéance monotone et handle d'annulation.              |

Après redémarrage, le budget repart à zéro et le suivi est armé, mais chaque underlying doit refaire sa baseline. Ce redémarrage n'est pas une commande externe.

## 4. Classification de l'état initial et limite prouvable

L'API actuelle permet d'identifier le callback programmé depuis l'état HA déjà en cache, mais ne fournit pas une provenance matérielle du changement. Elle ne distingue pas non plus aujourd'hui explicitement une restauration d'une livraison ordinaire après indisponibilité. Il serait donc faux d'affirmer que le premier `heat` ou `off` est matériellement un état de démarrage.

La mise en œuvre doit enrichir le contrat du gestionnaire d'états avec un type de livraison explicite :

1. `INITIAL_CACHED_STATE` pour le callback créé par `add_underlying_entities()` ;
2. `RECOVERY_FIRST_VALID_STATE` lorsqu'un `unknown`, `unavailable` ou retrait a été effectivement observé, puis que le premier état valide arrive ;
3. `STATE_CHANGED` pour les changements normaux postérieurs.

`baseline_pending` est vrai à la création et après une indisponibilité observée. Pour les deux premiers types, la couche de suivi mémorise mode et consigne, annule une candidate, diagnostique `initial_baseline_ignored` ou `recovery_baseline_ignored`, puis s'arrête : aucune adoption, aucune propagation de mode, aucun calcul déclenché par le suivi et aucune commande suivie. Un changement post-baseline est comparé à la dernière observation **du même underlying**, non au seul mode VTherm ; il peut donc être suivi sans `last_physical_temperature_send` préalable.

Cette stratégie est fail-closed et testable, mais sa limite demeure exacte : un geste humain réellement livré comme première valeur est ignoré ; une restauration dont HA n'a pas vu l'indisponibilité peut rester indiscernable d'un changement normal. Ce n'est pas une provenance matérielle inventée et ce risque est la contrepartie documentée de l'alternative B.

`check_initial_state()` peut déjà envoyer une réconciliation directe afin d'aligner le sous-jacent avec le VTherm. AC-017/AC-018 l'autorisent explicitement, à condition qu'elle reste distincte du suivi, hors budget et identifiable dans les diagnostics comme réconciliation directe. La présente conception garantit qu'aucune commande n'est **causée par le suivi de la baseline**.

## 5. Contrats d'appel et passerelle unique de débit

### Frontière externe

Après validation et avant modification de l'intention, les méthodes publiques correspondant à `climate.set_hvac_mode`, `climate.set_temperature`, `climate.set_preset_mode` et aux services VTherm équivalents appellent atomiquement `receive_external_command()` : incrémenter l'époque, invalider callbacks/candidates suivis, remettre le compteur à zéro, lever la suspension, puis exécuter la commande directe. Une valeur identique réarme si l'appel externe est valide ; l'origine première d'une automatisation n'est pas examinée.

Les suites internes ne doivent pas appeler une méthode publique sans contexte. Prévoir des voies privées explicites, par exemple `apply_tracked_temperature(chain, value)` et `apply_tracked_hvac_mode(chain, mode)`. Elles appliquent Q-01 ou le mode suivi, puis appellent `update_states(chain=chain)` ; elles ne réarment jamais. Cette séparation est nécessaire car `async_set_temperature()` est actuellement partagé avec la commande directe et peut démarrer un override.

### Propagation obligatoire

| Route                                          | Contrat                                                                                                                                                         |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| observation -> adoption                        | La baseline est traitée avant toute qualification ; une suspension refuse le suivi de consigne et de mode.                                                      |
| adoption -> `update_states` -> transition HVAC | La même `TrackingChain` est transmise, y compris au `set_hvac_mode` de chaque climate sous-jacent.                                                              |
| `async_control_heating` -> régulation/TPI      | Une régulation dérivée reçoit la chaîne ; une régulation périodique autonome utilise `None` et ne réarme pas.                                                   |
| `set_hvac_mode` -> renvoi TRVZB                | Le callback de deux secondes capture chaîne + époque et les revalide avant `set_temperature`.                                                                   |
| `CycleScheduler` -> valve                      | `start_cycle`, `apply_valve_update`, répétition et callback conservent la chaîne jusqu'à `set_valve_open_percent`, `send_percent_open`, `send_value_to_number`. |

### Passerelle physique

Toutes les émissions `climate.set_hvac_mode`, `climate.set_temperature` et `number.set_value` passent par une même opération conceptuelle `try_physical_attempt(chain, endpoint, payload)` :

1. calculer la valeur effective et coalescer les no-op ; un no-op ne compte pas ;
2. vérifier indisponibilité, inhibition, capacité et validité de l'époque ; si aucun appel ne peut partir, ne pas débiter ;
3. sans chaîne, envoyer directement sans toucher au budget ;
4. avec chaîne, refuser si suspendu, obsolète ou déjà à trois ;
5. sinon débiter immédiatement avant l'appel ; dès la troisième tentative, suspendre avant l'appel tout en envoyant cette troisième tentative ;
6. conserver le débit après exception, timeout ou résultat incertain.

Une paire ouverture/fermeture de vanne contient deux appels `number.set_value` et donc deux tentatives physiques lorsqu'ils partent réellement. Une commande 0 % ou 100 % ne peut ainsi pas contourner le plafond via le domaine `number`.

## 6. Flux nominaux et gestion des erreurs

### Consigne

Une consigne post-baseline est enregistrée comme observation. Si elle est égale ou compatible avec la dernière tentative vérifiée, elle est `echo_possible`; si elle est trop proche sans capacité vérifiée, elle est `ambiguous`. Ces cas n'adoptent pas et annulent une candidate physiquement remplacée. Une valeur distincte, y compris sans ordre VTherm préalable, devient candidate avec une échéance monotone de cinq secondes. Duplicata, `hvac_action`, fan ou mode ne prolongent pas cette échéance.

Au timer, relire l'état HA et revalider valeur, rang/version, génération, époque, suivi actif, suspension et priorités. En cas d'admission, créer une chaîne `kind=temperature`, appliquer Q-01 — demande mise à jour, preset `NONE`, override annulé sans restauration — puis propager cette chaîne. Pendant OFF, la demande est sauvegardée sans lever l'OFF forcé ni le OFF manuel.

### Mode

Un mode post-baseline distinct est évalué immédiatement, sans debounce. Les règles existantes d'alignement multi-underlyings restent applicables ; un refus d'alignement ne doit pas supprimer une consigne présente dans le même événement. Si le suivi est actif et non suspendu, créer une chaîne `kind=hvac_mode`, écrire le mode demandé et appeler `update_states(chain=...)`. Si le suivi est suspendu, n'adopter ni `heat` ni `off`, et ne lancer ni calcul ni commande issue de cette observation. `hvac_action` et fan restent indépendants.

### TRVZB, scheduler et reprise

Le renvoi TRVZB capture `(chain, epoch, mode attendu, température effective)` ; il est annulé par un nouveau mode et devient inerte après changement d'époque. Les callbacks `do_send_regulated_temp_later`, `do_recalculate_later`, TPI et scheduler suivent le même protocole : transmettre la chaîne capturée ou s'arrêter fail-closed. Une répétition de cycle issue d'une chaîne ne peut pas effacer son contexte pour retrouver un comportement direct après saturation.

Désactivation, indisponibilité, retrait, reload et suppression annulent handles/candidates avant leur échéance. Une nouvelle intention invalide les candidates avant tout `await`, mais ne réarme que si elle est une commande externe valide. Les erreurs avant service ne sont pas débitées ; celles après débit restent comptées.

## 7. Observabilité et sécurité opérationnelle

Les diagnostics bornés doivent présenter : type de livraison, rang et baseline ; observation/mode/consigne ; dernière tentative physique et issue ; candidate, génération et échéance ; `chain_id`, époque et route de callback ; domaine/service/entité de chaque tentative ; compteur avant/après, suspension et refus ; réarmement externe. Ils ne doivent jamais affirmer qu'un service réussi est un acquittement ou qu'un état initial identifie un acteur humain.

La documentation et les journaux doivent signaler que le plafond est par VTherm entre commandes externes, que les gestes ambigus peuvent être ignorés, qu'un ancien écho distinct peut être adopté, et qu'une automatisation externe réactive n'est pas globalement bornée.

## 8. Stratégie de tests et critères AC-017 à AC-024

Les tests futurs emploient horloge contrôlée, callbacks capturés et compteurs de services par entité/domaine.

| Critère         | Preuve de test ciblée                                                                                                                                                                                                                |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| AC-017 / AC-018 | Premier `heat`, puis premier `off` : baseline mémorisée, aucune adoption, aucune chaîne, aucun service suivi `climate` ou `number`; réconciliation directe éventuelle explicitement distinguée.                                      |
| AC-019          | Après baseline, `off -> heat` et `heat -> off` avant tout envoi VTherm : suivi immédiat de mode. Évolutions `hvac_action` et fan seules : aucune adoption de mode.                                                                   |
| AC-020          | Vérifier le même `chain_id` de la réception au mode climate, au TPI et à la vanne 0 % / 100 %, dans les deux sens.                                                                                                                   |
| AC-021          | Renvoyer la température TRVZB après deux secondes : même chaîne, débit si et seulement si service réel ; callback de baseline absent, callback annulé/périmé inerte.                                                                 |
| AC-022          | Budget à trois/suspendu, séquence `heat -> off -> heat` : aucune modification suivie de `requested_state`, aucun service `climate` ou `number`. Une commande externe valide réarme ; un callback interne non.                        |
| AC-023          | UI, service et automatisation réarment chacun après validation. Simuler une automatisation réactive et attester l'absence de promesse de borne globale.                                                                              |
| AC-024          | `ThermostatOverClimateValve`: `update_states -> recalculate -> CycleScheduler -> UnderlyingValveRegulation -> number.set_value`, positions 0/100, ouverture et fermeture comptées séparément, troisième admise et quatrième refusée. |

Compléter avec redémarrage, premier changement post-baseline sans premier send, quantification `25.6 -> 25.5`, rafale `26 -> 26.5 -> 27`, retour tardif `7 -> 21`, Q-01 sous OFF, alignement multi-TRV et persistance de la cause pendant répétition de scheduler.

## 9. Risques, limites et bloqueurs

| Sujet                        | État                                                                                                                                           |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Premier `off` TRVZB          | Sa provenance exacte reste inconnue ; #2159 démontre le contournement de sécurité, pas l'origine matérielle de l'amorçage.                     |
| Baseline parfaite            | Impossible sans provenance intégration. La classification de cycle de vie est testable, mais peut perdre un geste livré comme première valeur. |
| Gestionnaire d'états         | Le type de livraison explicite est requis ; inférer depuis `old_state` seul n'est pas une garantie suffisante.                                 |
| Services `number`            | Propagation de chaîne et passerelle jusqu'à `send_value_to_number` sont un bloqueur de sécurité.                                               |
| Méthodes publiques partagées | Une voie interne explicite est un bloqueur de traçabilité, sinon un appel suivi peut réarmer indûment.                                         |
| Callbacks                    | Chaîne + époque doivent être capturées et revalidées partout ; sinon TRVZB/régulation peut contourner la suspension.                           |
| Réconciliation de démarrage  | Autorisée explicitement par AC-017/AC-018 si elle demeure distincte du suivi, hors plafond et diagnostiquée comme réconciliation directe.      |

## 10. Conclusion et faisabilité

La conception est réalisable et testable à condition d'introduire : (1) un type de livraison initiale/reprise explicite, (2) une voie interne qui ne réarme pas, et (3) une passerelle commune qui couvre réellement les services `climate` et `number`. Sans ces trois mécanismes, la garantie des trois tentatives et l'alternative B ne sont pas démontrables.

Il n'y a pas de divergence avec les décisions v2.0 sur le maintien du suivi `hvac_mode`, Q-03, l'immuabilité de cause, le plafond, le réarmement externe ou la réconciliation directe de démarrage. La limite consignée reste l'absence de provenance matérielle prouvable. Aucun développement n'est autorisé par cette conception.
