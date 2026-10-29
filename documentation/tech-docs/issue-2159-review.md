# Revue de l’issue #2159 — Boucle infinie TRVZB au démarrage après #2141

| Métadonnée                | Valeur                                                                                                                               |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Statut                    | Documents v3.5 convergents sur le plan statique — validation finale avant développement                                              |
| Issue                     | [#2159 — Infinite loop on TRVZB on startup (regression after #2141)](https://github.com/jmcollin78/versatile_thermostat/issues/2159) |
| Version affectée signalée | `10.6.3.beta3` ; manifeste du dépôt : `10.6.3`                                                                                       |
| Date de revue             | 2026-10-29                                                                                                                           |
| Composants concernés      | `over_climate` avec régulation directe de vanne, `follow_underlying_temp_change`, TRV Sonoff TRVZB                                   |
| Issue liée                | [#2141](https://github.com/jmcollin78/versatile_thermostat/issues/2141) — suivi sûr des consignes TRV                                |
| Recommandation            | **Retenir et traiter en priorité comme régression de disponibilité.**                                                                |

## Mise à jour du 2026-10-29 — demande de correction ciblée

L'utilisateur a interrompu le développement précédent et demande une solution simple concentrée sur `ThermostatOverClimate` dans [thermostat_climate.py](../../custom_components/versatile_thermostat/thermostat_climate.py), sans nouvelle modification de `BaseThermostat`, de `CycleScheduler`, ni des autres classes de production. Les mécanismes interclasses déjà développés pour #2141 restent en place et peuvent être réutilisés ; ils ne sont ni rapatriés ni réécrits. Les anciennes propositions transversales et garanties physiques ne constituent plus le périmètre courant. Les documents v3.5 restent candidats ; les relectures confirment leur convergence statique, sans preuve applicative ni reproduction matérielle. Une validation finale est demandée avant développement.

### Faits et limites vérifiés

- `underlying_changed()` adopte actuellement un mode sous-jacent sans vérifier la suspension ni transmettre la cause de suivi à `update_states()` ; ce contournement reste le défaut ciblé.
- Le compteur existant borne les tentatives `climate` effectivement marquées par la cause de suivi. Les appels de vanne `number` ne portent pas cette cause jusqu'au service ; une correction limitée à `ThermostatOverClimate` ne démontre donc pas une borne globale de trois appels physiques `climate` et `number`.
- Le callback initial peut parvenir à `ThermostatOverClimate` : le retour de la méthode parente dans `UnderlyingEntity._underlying_changed()` ne termine pas la méthode enfant `UnderlyingClimate._underlying_changed()`. L'affirmation contraire dans la conception v2.0 est à corriger.
- Les états `old_state` et `new_state` permettent de reconnaître certaines premières livraisons ou reprises (`old_state` absent, `unknown` ou `unavailable`) et des transitions réelles entre deux états valides. Ils ne prouvent ni l'origine matérielle d'une observation ni toutes les restaurations possibles.
- La réconciliation directe de `check_initial_state()` reste inchangée et peut envoyer des commandes au démarrage, indépendamment du suivi. L'origine du premier `off` de l'issue et l'événement refermant la boucle matérielle demeurent inconnus.

### Proposition candidate à faire valider

1. Dans `underlying_changed()`, ne suivre un mode que pour une transition réelle du même sous-jacent entre deux états valides ; ne pas adopter le premier état identifiable ni une reprise identifiable. Ne pas ignorer aveuglément le premier callback si celui-ci décrit déjà une transition valide. Préserver l'alignement multi-sous-jacents et le traitement indépendant des autres champs, y compris une consigne présente dans le même événement.
2. Refuser toute adoption de mode lorsque la protection existante est suspendue ; pour une adoption effective, transmettre `COMMAND_CAUSE_UNDERLYING_TRACKING` à `update_states()`, sans passer par une entrée externe qui réarmerait le suivi. Conserver le debounce de cinq secondes réservé à la température, sans réintroduire le filtre global de dix secondes.
3. Selon la décision utilisateur, **un seul compteur existant** doit compter à la fois les changements de mode ou de consigne effectivement adoptés et les tentatives `climate` marquées déjà comptées. Un retour non adopté ne débite pas d'adoption ; une interaction peut débiter plusieurs unités. Aucun second compteur n'est proposé.
4. Prévoir des tests du callback réel : état initial/reprise identifiable, changements `heat/off` réels et événements d'attribut sans changement de mode, budget saturé, cause transmise, événements mixtes, réarmement externe et régression sur la variante vanne. Mesurer séparément adoptions, tentatives `climate` et services `number` ; tester le seuil et la réentrance.

### Conséquences et limites

Le compteur partagé peut saturer après des gestes légitimes espacés, voire avant trois adoptions si des tentatives sont aussi débitées. Un `OFF` adopté qui porte le total à trois peut rester demandé ou publié sans être transmis à un autre TRV ; aucun rattrapage n'est garanti. L'utilisateur a confirmé qu'aucune exigence supplémentaire de transmission forcée de `OFF` n'était demandée ; ce constat ne lui attribue pas une acceptation générale du danger. Le compteur ne borne ni les commandes déjà lancées, ni les services `number`, cycles, réconciliations ou automatisations externes réarmantes. La suppression complète de la boucle matérielle reste à vérifier.

La proposition précédente de `TrackingChain` propagée jusqu'aux vannes et du plafond global de trois appels physiques `climate`/`number` exigeait des changements transversaux exclus par la nouvelle demande. Elle ne doit pas être présentée comme satisfaite par ce correctif local.

### Convergence documentaire v3.5 et risques résiduels

Les [spécifications FR](issue-2141-specification_fr.md) et [EN](issue-2141-specification_en.md) et la [conception](issue-2141-design.md) sont candidates en v3.5. Deux relectures indépendantes confirment le même périmètre, la couverture documentaire des critères, l'absence de nouvelle contradiction bloquante et la faisabilité/testabilité statiques. Elles ne certifient ni conformité complète ni exécution réussie.

Les décisions et limites sont les suivantes :

- **Compteur partagé :** choisi par l'utilisateur pour les adoptions réelles de mode/consigne et les tentatives marquées existantes. L'ancienne option de compteur séparé est retirée.
- **Extensions de température Q-07 à Q-09 :** retirées du périmètre #2159, sans arbitrage nécessaire pour le socle HVAC. Les divergences historiques de référence, de pas et de déduplication restent documentées, sans prétendre qu'elles sont résolues.
- **Seuil et séquencement Q-11/Q-12 :** pas d'exigence de transmission forcée de `OFF` ; mode et application avant l'examen de la consigne. Les limites du compteur demeurent documentées.
- **Réentrance :** une reprise d'expiration de preset peut démarrer une tâche immédiatement dans la version HA inspectée et déclencher une application imbriquée non marquée. La conception propose de conserver la reprise immédiate et de finaliser sur l'état courant ; la non-régression reste à tester. Aucun double débit ni envoi systématique n'est prouvé.

Le refus HVAC des paires mal identifiées, les limites des événements filtrés en amont et le comportement en cas d'erreur sont précisés dans les documents candidats, sans nouveau filtre général de température. L'origine du premier `off` et l'élimination de l'oscillation matérielle demeurent non établies. Les résultats restent à valider avant développement.

## 1. Résumé fidèle de l’issue

Après l’installation de la version `10.6.3.beta3` qui contient l’implémentation de #2141, un VTherm `over_climate` configuré pour la régulation par contrôle direct de vanne sur un Sonoff TRVZB alterne entre une ouverture de vanne de 0 % et 100 % au démarrage.

Le phénomène est signalé uniquement lorsque le commutateur `follow_underlying_temp_change` est activé. Le désactiver arrête l’oscillation, tout en supprimant le suivi des changements émis par l’équipement sous-jacent.

L’extrait de journal fourni établit notamment la séquence suivante :

1. VTherm est en `heat`, à une consigne de 25 °C ; le TPI calcule 100 % avec une température ambiante de 19,5 °C.
2. Le TRV publie la consigne 25 °C, sans qu’elle soit différente de l’intention VTherm.
3. Le TRV publie une activité `heating`.
4. Le TRV publie ensuite `hvac_mode=off`, sans changement de consigne.
5. VTherm adopte ce `off` avec le journal « Follow is 'on'. Changing hvac_mode for all underlying to 'off' ».
6. Le recalcul TPI avec VTherm arrêté donne 0 % et annule le cycle.

Les journaux fournis ne contiennent ni le premier événement qui a conduit le TRV à produire `off`, ni le retour à `heat` qui ferme effectivement une itération complète de la boucle observée.

## 2. Sources et éléments vérifiés

### Sources externes

- Issue [#2159](https://github.com/jmcollin78/versatile_thermostat/issues/2159), consultée le 2026-10-29 : description, journal de reproduction, absence de commentaire, d’étiquette, d’assignation, de jalon, de branche ou de pull request associés à la consultation.
- Issue [#2141](https://github.com/jmcollin78/versatile_thermostat/issues/2141) et ses documents de revue, spécification et conception présents dans le dépôt.

### Sources du dépôt

- [thermostat_climate.py](../../custom_components/versatile_thermostat/thermostat_climate.py) : réception des changements du climate sous-jacent, suivi du mode HVAC et arbitrage des températures candidates.
- [underlyings.py](../../custom_components/versatile_thermostat/underlyings.py) : envois `set_hvac_mode`, renvoi différé de température pour TRVZB, commandes de vannes et degré d’ouverture/fermeture.
- [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) : application de l’état demandé, propagation du mode et déclenchement du recalcul/contrôle de chauffe.
- [thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py) et [valve_command.py](../../custom_components/versatile_thermostat/valve_command.py) : conversion de la puissance TPI en commande de vanne.
- [cycle_scheduler.py](../../custom_components/versatile_thermostat/cycle_scheduler.py) et [prop_handler_tpi.py](../../custom_components/versatile_thermostat/prop_handler_tpi.py) : cycle TPI et son annulation.
- [tests/test_overclimate.py](../../tests/test_overclimate.py) : tests existants du plafond de commandes du suivi.
- [rapport #2141](issue-2141-review.md), [spécification FR #2141](issue-2141-specification_fr.md) et [conception #2141](issue-2141-design.md).

### Vérifications effectuées

- Revue statique des chemins listés ci-dessus.
- Inspection du commit `358b070` qui implémente #2141 : il supprime le filtre global historique de dix secondes appliqué aux événements du climate sous-jacent.
- Exécution avec l’environnement virtuel du projet des deux tests existants de plafond de suivi : **2 réussis**.
- Exécution isolée du corps du callback réel `ThermostatOverClimate.underlying_changed` avec un budget déjà épuisé et le suivi suspendu : des alternances `off`/`heat` sont toujours adoptées lorsqu’elles arrivent sur la branche de suivi du mode. Cette vérification prouve le contournement du garde-fou, mais n’est pas une reproduction Home Assistant ou matérielle complète.

Aucune modification de code, de configuration ni d’état Home Assistant n’a été effectuée pendant cette revue.

## 3. Constat technique principal

### 3.1 Le commutateur suit aussi le mode HVAC

Malgré son nom, `follow_underlying_temp_change` ne traite pas uniquement la consigne. Lorsqu’un changement `new_hvac_mode` arrive depuis le climate sous-jacent et que le commutateur est actif, `ThermostatOverClimate.underlying_changed` appelle directement :

```text
requested_state.set_hvac_mode(new_hvac_mode)
update_states(...)
```

Cette transition est immédiate ; elle ne passe ni par le debounce de cinq secondes, ni par la qualification des échos de température.

Cela correspond exactement à l’événement observé dans l’issue : `heat → off`, avec une consigne encore fixée à 25 °C.

### 3.2 Le plafond de trois tentatives de #2141 ne couvre pas cette branche

Les protections introduites par #2141 sont déclenchées uniquement quand une commande porte explicitement la cause interne `COMMAND_CAUSE_UNDERLYING_TRACKING` :

- la température candidate acceptée transmet cette cause à `update_states` ;
- `UnderlyingClimate.set_temperature` et `UnderlyingClimate.set_hvac_mode` ne débitent le budget de trois tentatives que lorsque cette cause est présente ;
- la suspension est testée dans l’arbitre de **température**.

Le suivi du mode HVAC appelle `update_states` sans cause `underlying_tracking`. La commande qui résulte de ce suivi est donc traitée comme une commande normale : elle n’est ni comptée, ni refusée lorsque le budget est saturé, ni bloquée par la suspension du suivi des températures.

**Fait vérifié :** avec `_underlying_tracking_attempts = 3` et `_underlying_tracking_suspended = True`, des événements alternant `off` et `heat` sont toujours adoptés par la branche de suivi du mode ; chaque application reçoit une cause absente. Cela démontre le contournement du garde-fou, sans démontrer que ce chemin est à lui seul l’origine du premier `off` matériel rapporté par l’issue.

### 3.3 La transition de mode force le recalcul de vanne

L’application d’un nouveau mode dans `BaseThermostat.update_states` entraîne un recalcul forcé pour un `over_climate` avec régulation de vanne. Ainsi :

- `heat` avec l’écart de température observé conduit à 100 % ;
- `off` force l’algorithme TPI à 0 % ;
- les commandes de degrés d’ouverture/de fermeture sont envoyées via les underlyings de vanne.

Une alternance d’états HVAC rapportés par le TRV peut donc se matérialiser en alternance 100 % / 0 %, même lorsque la consigne reste inchangée.

### 3.4 Autres chemins de retour à surveiller

Le code contient un renvoi différé de température, deux secondes après le passage à `heat` ou `cool`, explicitement documenté pour les Sonoff TRVZB. Son callback appelle `set_temperature(..., command_cause=command_cause)` : il conserve la cause lorsqu’elle est fournie, mais le chemin de suivi du **mode** ne lui fournit pas cette cause. Ce renvoi est donc un second mécanisme de commandes non bornées possible après une transition de mode non marquée ; son intervention dans la boucle matérielle signalée reste à prouver.

Les commandes de vanne ne transportent pas non plus de cause de suivi jusqu’au point d’envoi du `number`. Une correction limitée au marquage de `set_hvac_mode` ne démontrera donc pas encore que l’ensemble des commandes physiques induites est borné.

## 4. Analyse de pertinence

### Décision : retenir

L’issue est cohérente avec une régression introduite par #2141 : la suppression du filtre global de dix secondes était nécessaire pour améliorer le suivi des consignes rapides, mais ce filtre protégeait aussi les changements de mode HVAC. La nouvelle logique de sécurité couvre les consignes candidates, pas le suivi immédiat des modes.

Le problème affecte la disponibilité et peut entraîner une sollicitation répétée du TRV, du réseau Zigbee et de Home Assistant. Il est donc prioritaire, même si la source première du premier `off` matériel n’est pas encore prouvée.

### Conformité aux documents de #2141

La spécification de #2141 exclut une refonte implicite des modes HVAC et exige que les changements de mode restent indépendants du traitement des seules consignes. Cependant, son objectif de prévention des boucles, son plafond de trois tentatives et la conservation de la cause interne ne sont pas atteints pour le chemin de suivi HVAC actuellement exécuté.

La régression n’invalide pas le besoin fonctionnel de #2141 ; elle révèle une frontière d’implémentation non couverte entre le suivi de consigne et le suivi de mode.

## 5. Périmètre proposé

### Inclus

1. Conserver le suivi des modes HVAC avec qualification locale des transitions, source, alignement, garde existante et cause de suivi.
2. Réutiliser sans modification les mécanismes interclasses #2141, limités aux points déjà couverts ; ne pas promettre la propagation jusqu'à chaque commande physique.
3. Tester le callback et la variante vanne, notamment les alternances `heat/off`, le budget existant saturé et les callbacks différés, en mesurant séparément les services `climate` et `number`.
4. Prévoir des diagnostics locaux adaptés et préserver les traitements existants de température et des autres champs ; les tests peuvent être modifiés hors de la classe.
5. Ajouter le comptage des adoptions réelles au compteur partagé existant, en conservant le comptage des tentatives et l'ordre mode puis consigne.

### Exclus

- Attribuer avec certitude le premier `off` à l’intégration TRVZB, au matériel ou à un autre composant sans journal complémentaire.
- Modifier la politique fonctionnelle des consignes, presets, fenêtres, sécurité, ventilation ou régulation hors du chemin causal concerné.
- Garantir une attribution parfaite de l’origine d’un événement matériel lorsque Home Assistant ne l’expose pas.
- Modifier la configuration de l’installation affectée pendant l’analyse.
- Modifier ou rapatrier les mécanismes #2141 dans les autres classes, ajouter une borne globale des services physiques ou refaire les politiques de température sous #2159.

## 6. Impacts et risques

| Risque ou impact                                                     | Gravité  | Probabilité                                                        | Éléments établis / précaution                                                            |
| -------------------------------------------------------------------- | -------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Oscillation répétée 0 % / 100 % au démarrage                         | Critique | Établie sur l’installation signalée ; mécanisme logiciel plausible | Traiter le suivi HVAC hors budget ; tester le chemin vanne complet.                      |
| Charge répétée Zigbee / Home Assistant / TRV                         | Haute    | Plausible                                                          | Mesurer séparément les commandes et reconnaître l'absence de borne globale.              |
| Régression fonctionnelle si le suivi HVAC est supprimé sans décision | Moyenne  | Certaine si des utilisateurs comptent sur ce comportement          | Le socle candidat conserve ce suivi ; soumettre cette proposition à validation.          |
| Contournement persistant par callbacks ou commandes de vanne         | Haute    | Plausible                                                          | Caractériser les services non couverts ; une protection transversale est hors périmètre. |
| Faux diagnostic de l’origine matérielle                              | Moyenne  | Élevée avec le seul extrait disponible                             | Demander un journal étendu si l’analyse requiert la source initiale du premier `off`.    |
| Régression de #2141 sur les gestes rapides de température            | Haute    | Possible                                                           | Préserver le debounce et les protections de température existants par tests dédiés.      |

## 7. Alternatives examinées

| Alternative                                                                  | Avantages                                                                                  | Limites / recommandation                                                                                                              |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Désactiver le suivi sous-jacent                                              | Contournement confirmé : l’oscillation signalée cesse                                      | Perd le suivi des gestes sur le TRV ; acceptable seulement comme mesure temporaire.                                                   |
| Réintroduire le filtre global de 10 s                                        | Bloque vraisemblablement le `off` observé moins d’une seconde après une commande VTherm    | Réintroduit le défaut de #2141 : les gestes rapides de consigne sont perdus. À écarter.                                               |
| Ne plus suivre les modes HVAC avec ce commutateur                            | Sépare strictement le suivi des consignes de celui des modes et supprime le chemin observé | Alternative examinée mais non retenue dans le socle candidat ; changerait le comportement actuel et exigerait une décision distincte. |
| Conserver le suivi HVAC et étendre le compteur partagé aux adoptions réelles | Préserve le suivi et compte aussi les adoptions sans tentative `climate`                   | Peut saturer avant diffusion, notamment d'un `OFF` ; ne borne pas les commandes de vanne ni la provenance du premier état.            |
| Spécialiser le comportement TRVZB                                            | Peut réduire un problème matériel particulier                                              | Risque de masquer une faille générique et de multiplier les exceptions matériel. À considérer seulement après correction générique.   |

## 8. Hypothèses, inconnues et questions ouvertes

### Faits établis

- Le commutateur actif fait suivre un changement de `hvac_mode` sous-jacent.
- L’événement `heat → off` de l’issue est immédiatement adopté par VTherm.
- Cette adoption entraîne un recalcul TPI à 0 %.
- Le chemin de suivi HVAC n’est pas marqué `COMMAND_CAUSE_UNDERLYING_TRACKING`.
- Le budget/suspension introduit par #2141 ne s’applique donc pas à cette branche.
- Les tests actuels vérifient le plafond lorsque la cause est fournie explicitement, y compris pour un appel HVAC marqué. Ils ne reproduisent pas l’enchaînement réel `retour HVAC → suivi sans cause → régulation de vanne → renvoi différé TRVZB`.

### Hypothèses plausibles, non démontrées

- Les retours `off/heat` successifs du TRV, ou les interactions de démarrage/cycles/renvoi différé TRVZB, alimentent l’oscillation observée.
- Le comportement peut concerner d’autres climats/valves, et non uniquement Sonoff TRVZB.

### Inconnues bloquantes pour une garantie complète

1. Quelle commande, quel état initial ou quel comportement de l’intégration produit le premier `off` après le démarrage ?
2. Quel événement précis produit le retour ultérieur à `heat` qui complète l’alternance observée ?
3. Le suivi des modes HVAC est-il une fonctionnalité documentée et attendue de ce commutateur, ou un effet historique non intentionnel ? Le socle candidat le conserve, sans trancher cette question historique.
4. Quelles commandes `number.set_value` seraient physiquement induites par un suivi ? Leur éventuelle inclusion dans un budget transversal est hors du correctif local proposé.

Ces inconnues ne bloquent pas la correction du contournement déjà démontré, mais elles bloquent une affirmation selon laquelle toute boucle TRVZB est reproduite et éliminée sans journal/test complémentaire.

## 9. Proposition de suite et critères de passage au développement

### Recommandation de processus

1. Valider ce rapport et retenir l’issue comme régression prioritaire.
2. Soumettre les spécifications et la conception v3.5 convergentes à validation finale.
3. Tester le seuil, les événements mixtes et la non-régression face à la réentrance pendant le développement autorisé.
4. Ne démarrer le développement qu'après validation et autorisation explicite.

### Critères minimaux à spécifier avant développement

- Un événement `heat → off` du climate sous-jacent, sans nouvelle commande externe, ne peut pas contourner le plafond/suspension retenu.
- Une alternance de retours `off/heat` avec budget existant déjà saturé ne provoque plus d'adoption HVAC par suivi ; les autres commandes, notamment `number`, sont observées séparément sans garantie d'arrêt global.
- Les retours normaux de `hvac_action`, de température et de consigne continuent à être traités selon #2141 sans être confondus avec un changement de mode.
- Le chemin `over_climate` avec régulation de vanne est testé : 100 % puis 0 %, état de climate, services `climate` et `number`, callbacks différés et ordre de réception.
- Les deux tests existants de #2141 restent valides, complétés par un test end-to-end du chemin qui échappait au marquage de cause.
- Le résultat différencie clairement les commandes externes qui réarment et les suites internes qui ne doivent jamais réarmer.

## 10. Décision de revue

**Recommandation : retenir l’issue #2159 et soumettre les documents candidats v3.5 à validation finale.**

La cause exacte du premier état `off` du TRV reste inconnue. Le contournement logiciel des protections de #2141 par le suivi de mode est démontré ; son rôle exact dans l’amorçage de cette boucle matérielle reste une hypothèse fortement étayée à reproduire. La correction doit être conçue comme une régression de sécurité/disponibilité et non comme un contournement spécifique au matériel.

La convergence statique ne remplace ni la validation finale ni les tests applicatifs ; ce rapport ne vaut pas autorisation de développer.
