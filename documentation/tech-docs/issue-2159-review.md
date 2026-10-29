# Revue de l’issue #2159 — Boucle infinie TRVZB au démarrage après #2141

| Métadonnée                | Valeur                                                                                                                               |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Statut                    | Analyse terminée — développement non autorisé                                                                                        |
| Issue                     | [#2159 — Infinite loop on TRVZB on startup (regression after #2141)](https://github.com/jmcollin78/versatile_thermostat/issues/2159) |
| Version affectée signalée | `10.6.3.beta3` ; manifeste du dépôt : `10.6.3`                                                                                       |
| Date de revue             | 2026-10-29                                                                                                                           |
| Composants concernés      | `over_climate` avec régulation directe de vanne, `follow_underlying_temp_change`, TRV Sonoff TRVZB                                   |
| Issue liée                | [#2141](https://github.com/jmcollin78/versatile_thermostat/issues/2141) — suivi sûr des consignes TRV                                |
| Recommandation            | **Retenir et traiter en priorité comme régression de disponibilité.**                                                                |

## Mise à jour du 2026-10-29 — demande de correction ciblée

L'utilisateur a interrompu le développement précédent et demande une solution simple concentrée sur `ThermostatOverClimate` dans [thermostat_climate.py](../../custom_components/versatile_thermostat/thermostat_climate.py), sans modification de `BaseThermostat`, de `CycleScheduler`, ni des autres modules de production communs. Les sections historiques ci-dessous restent utiles pour le diagnostic, mais leur périmètre transversal et leurs garanties physiques ne constituent plus la proposition courante. La spécification et la conception v2.0 doivent être révisées et validées pour ce nouveau périmètre avant tout développement.

### Faits et limites vérifiés

- `underlying_changed()` adopte actuellement un mode sous-jacent sans vérifier la suspension ni transmettre la cause de suivi à `update_states()` ; ce contournement reste le défaut ciblé.
- Le compteur existant borne les tentatives `climate` effectivement marquées par la cause de suivi. Les appels de vanne `number` ne portent pas cette cause jusqu'au service ; une correction limitée à `ThermostatOverClimate` ne démontre donc pas une borne globale de trois appels physiques `climate` et `number`.
- Le callback initial peut parvenir à `ThermostatOverClimate` : le retour de la méthode parente dans `UnderlyingEntity._underlying_changed()` ne termine pas la méthode enfant `UnderlyingClimate._underlying_changed()`. L'affirmation contraire dans la conception v2.0 est à corriger.
- Les états `old_state` et `new_state` permettent de reconnaître certaines premières livraisons ou reprises (`old_state` absent, `unknown` ou `unavailable`) et des transitions réelles entre deux états valides. Ils ne prouvent ni l'origine matérielle d'une observation ni toutes les restaurations possibles.
- La réconciliation directe de `check_initial_state()` reste inchangée et peut envoyer des commandes au démarrage, indépendamment du suivi. L'origine du premier `off` de l'issue et l'événement refermant la boucle matérielle demeurent inconnus.

### Proposition candidate à faire valider

1. Dans `underlying_changed()`, ne suivre un mode que pour une transition réelle du même sous-jacent entre deux états valides ; ne pas adopter le premier état identifiable ni une reprise identifiable. Ne pas ignorer aveuglément le premier callback si celui-ci décrit déjà une transition valide. Préserver l'alignement multi-sous-jacents et le traitement indépendant des autres champs, y compris une consigne présente dans le même événement.
2. Refuser toute adoption de mode lorsque la protection existante est suspendue ; pour une adoption effective, transmettre `COMMAND_CAUSE_UNDERLYING_TRACKING` à `update_states()`, sans passer par une entrée externe qui réarmerait le suivi. Conserver le debounce de cinq secondes réservé à la température, sans réintroduire le filtre global de dix secondes.
3. En complément, **proposer**, sans l'imposer avant validation, un coupe-circuit local distinct du compteur physique : au plus trois adoptions effectives de mode suivies par VTherm entre deux réarmements externes ; la troisième est admise, les suivantes refusées, et le pilotage direct reste possible. Ce compteur porte sur les adoptions de mode, non sur chaque service physique, et ne modifie pas le traitement existant des consignes. Sa réservation doit précéder la mutation et tout `await` ; la suspension et son motif doivent être distincts du compteur physique existant.
4. Ajouter des tests du callback réel : état initial/reprise identifiable, changements `heat/off` réels et événements d'attribut sans changement de mode, compteur saturé, cause transmise, événements mixtes mode/consigne, réarmement externe et régression sur la variante vanne. Mesurer séparément les services `climate` et `number`, sans affirmer qu'ils sont tous bornés par le compteur local.

### Compromis à approuver

Le coupe-circuit proposé peut suspendre le suivi après trois changements légitimes de mode, même espacés dans le temps, tant qu'aucune commande externe ne le réarme. Il borne les **nouvelles adoptions suivies de mode**, pas les commandes physiques déjà lancées, les cycles, les callbacks d'autres couches, les réconciliations directes ni une boucle réarmée par une automatisation externe. Les commandes de vanne et les suites différées peuvent être amplifiées indépendamment du nombre d'adoptions ; la suppression complète de la boucle matérielle reste à vérifier. Un seuil différent ou une politique de reprise différente nécessiterait une décision fonctionnelle explicite.

La proposition précédente de `TrackingChain` propagée jusqu'aux vannes et du plafond global de trois appels physiques `climate`/`number` exigeait des changements transversaux exclus par la nouvelle demande. Elle ne doit pas être présentée comme satisfaite par ce correctif local.

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

1. Définir explicitement la politique de suivi des modes HVAC pour `follow_underlying_temp_change` : conservation, suppression, filtrage ou suivi avec cause explicite.
2. Si le suivi des modes est maintenu, transporter une cause interne immuable de l’observation sous-jacente jusqu’à chaque commande physique induite, y compris les callbacks différés.
3. Faire respecter le plafond commun de trois tentatives, la suspension et l’absence de réarmement interne sur ce chemin.
4. Étendre cette traçabilité aux commandes de régulation de vanne lorsque celles-ci sont causées par une observation suivie.
5. Ajouter des tests de régression sur `ThermostatOverClimateValve`, incluant une alternance `heat/off`, un budget saturé, la régulation à 0 % / 100 % et les callbacks différés TRVZB.
6. Ajouter des diagnostics permettant d’identifier la cause d’une transition de mode et la consommation effective du budget.
7. Mettre à jour la documentation utilisateur si la sémantique du commutateur ou son périmètre change.

### Exclus

- Attribuer avec certitude le premier `off` à l’intégration TRVZB, au matériel ou à un autre composant sans journal complémentaire.
- Modifier la politique fonctionnelle des consignes, presets, fenêtres, sécurité, ventilation ou régulation hors du chemin causal concerné.
- Garantir une attribution parfaite de l’origine d’un événement matériel lorsque Home Assistant ne l’expose pas.
- Modifier la configuration de l’installation affectée pendant l’analyse.

## 6. Impacts et risques

| Risque ou impact                                                     | Gravité  | Probabilité                                                        | Éléments établis / précaution                                                         |
| -------------------------------------------------------------------- | -------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| Oscillation répétée 0 % / 100 % au démarrage                         | Critique | Établie sur l’installation signalée ; mécanisme logiciel plausible | Traiter le suivi HVAC hors budget ; tester le chemin vanne complet.                   |
| Charge répétée Zigbee / Home Assistant / TRV                         | Haute    | Plausible                                                          | Borner toutes les commandes physiques dérivées et journaliser la cause.               |
| Régression fonctionnelle si le suivi HVAC est supprimé sans décision | Moyenne  | Certaine si des utilisateurs comptent sur ce comportement          | Décider explicitement la sémantique du commutateur avant développement.               |
| Contournement persistant par callbacks ou commandes de vanne         | Haute    | Plausible                                                          | Audit exhaustif de propagation de cause jusqu’aux services `climate` et `number`.     |
| Faux diagnostic de l’origine matérielle                              | Moyenne  | Élevée avec le seul extrait disponible                             | Demander un journal étendu si l’analyse requiert la source initiale du premier `off`. |
| Régression de #2141 sur les gestes rapides de température            | Haute    | Possible                                                           | Préserver le debounce et les protections de température existants par tests dédiés.   |

## 7. Alternatives examinées

| Alternative                                                                      | Avantages                                                                                  | Limites / recommandation                                                                                                                                    |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Désactiver le suivi sous-jacent                                                  | Contournement confirmé : l’oscillation signalée cesse                                      | Perd le suivi des gestes sur le TRV ; acceptable seulement comme mesure temporaire.                                                                         |
| Réintroduire le filtre global de 10 s                                            | Bloque vraisemblablement le `off` observé moins d’une seconde après une commande VTherm    | Réintroduit le défaut de #2141 : les gestes rapides de consigne sont perdus. À écarter.                                                                     |
| Ne plus suivre les modes HVAC avec ce commutateur                                | Sépare strictement le suivi des consignes de celui des modes et supprime le chemin observé | Changement de comportement à documenter ; vérifier les usages légitimes du suivi de mode. Alternative préférable si le suivi de mode n’est pas contractuel. |
| Conserver le suivi HVAC, avec la même cause et le même budget que la température | Préserve la fonctionnalité existante tout en bornant la boucle                             | Nécessite un audit complet des callbacks et des commandes de vanne ; ne résout pas la provenance matérielle du premier état.                                |
| Spécialiser le comportement TRVZB                                                | Peut réduire un problème matériel particulier                                              | Risque de masquer une faille générique et de multiplier les exceptions matériel. À considérer seulement après correction générique.                         |

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
3. Le suivi des modes HVAC est-il une fonctionnalité documentée et attendue de ce commutateur, ou un effet historique non intentionnel ?
4. Quelles commandes `number.set_value` doivent être considérées comme physiquement induites par un suivi et débitées dans le budget commun ?

Ces inconnues ne bloquent pas la correction du contournement déjà démontré, mais elles bloquent une affirmation selon laquelle toute boucle TRVZB est reproduite et éliminée sans journal/test complémentaire.

## 9. Proposition de suite et critères de passage au développement

### Recommandation de processus

1. Valider ce rapport et retenir l’issue comme régression prioritaire.
2. Décider explicitement si le commutateur continue à suivre les modes HVAC ou devient strictement un suivi de consigne.
3. Produire une spécification ciblée de la politique retenue et une conception décrivant la propagation de cause jusqu’aux commandes `climate` et `number`.
4. Ne démarrer le développement qu’après convergence et autorisation explicite.

### Critères minimaux à spécifier avant développement

- Un événement `heat → off` du climate sous-jacent, sans nouvelle commande externe, ne peut pas contourner le plafond/suspension retenu.
- Une alternance de retours `off/heat` avec budget déjà saturé n’émet plus de commandes physiques non bornées et ne force plus de transition VTherm non autorisée.
- Les retours normaux de `hvac_action`, de température et de consigne continuent à être traités selon #2141 sans être confondus avec un changement de mode.
- Le chemin `over_climate` avec régulation de vanne est testé : 100 % puis 0 %, état de climate, services `climate` et `number`, callbacks différés et ordre de réception.
- Les deux tests existants de #2141 restent valides, complétés par un test end-to-end du chemin qui échappait au marquage de cause.
- Le résultat différencie clairement les commandes externes qui réarment et les suites internes qui ne doivent jamais réarmer.

## 10. Décision de revue

**Recommandation : retenir l’issue #2159 et ouvrir la phase de spécification/conception.**

La cause exacte du premier état `off` du TRV reste inconnue. Le contournement logiciel des protections de #2141 par le suivi de mode est démontré ; son rôle exact dans l’amorçage de cette boucle matérielle reste une hypothèse fortement étayée à reproduire. La correction doit être conçue comme une régression de sécurité/disponibilité et non comme un contournement spécifique au matériel.

Aucun développement n’est autorisé par ce rapport.
