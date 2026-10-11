# Spécification fonctionnelle — Issue #2087 : mise en retrait contrôlée d’un VTherm

## Métadonnées

| Champ                        | Valeur                                                                                                                                                                                                                                                                                                           |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nom                          | Mécanisme d’inhibition extensible / Extensible inhibition mechanism                                                                                                                                                                                                                                              |
| Issue                        | [#2087 — Add an “inhibit” sensor to pause a VTherm](https://github.com/jmcollin78/versatile_thermostat/issues/2087)                                                                                                                                                                                              |
| Version                      | 1.2 — politique d’arrêt physique configurable par VTherm, spécification convergée avec la conception                                                                                                                                                                                                             |
| Statut                       | Convergée avec la conception ; validation mainteneur requise avant développement                                                                                                                                                                                                                                 |
| Date                         | 2026-10-11                                                                                                                                                                                                                                                                                                       |
| Propriétaire fonctionnel     | Projet Versatile Thermostat — décision mainteneur à confirmer                                                                                                                                                                                                                                                    |
| Source principale            | [Revue validée de l’issue](../tech-docs/issue-2087-review.md)                                                                                                                                                                                                                                                    |
| Sources techniques analysées | `custom_components/versatile_thermostat/state_manager.py`, `base_thermostat.py`, `prop_handler_tpi.py`, `feature_repair_incorrect_state_manager.py`, `underlyings.py`, `vtherm_state.py`, ainsi que `custom_components/vtherm_api/src/vtherm_api/interfaces.py` et `vtherm_api.py`, tels que cités dans la revue |

## 1. Contexte et objectif

L’issue #2087 demande qu’un VTherm cesse temporairement de commander ses sous-jacents lorsqu’une autre source de chauffage ou de refroidissement est active. Les cas d’usage identifiés sont notamment un chauffage alimenté par un surplus photovoltaïque et une climatisation qui refroidit déjà la pièce.

L’objectif V1 est de permettre une **mise en retrait contrôlée** : à l’entrée, le core retire le contrôle VTherm, suspend le contrôle et la réparation, et résout le HVAC effectif à `OFF`. Le plugin fournit, pour chaque VTherm, une politique demandant au core d’émettre ou non l’arrêt physique des sous-jacents ; sa valeur par défaut est **« éteindre »**, afin de préserver le comportement V1 déjà spécifié. Seule cette émission physique unique est conditionnelle : le retrait, les suspensions et la résolution `OFF` s’appliquent toujours. L’inhibition ne doit pas modifier l’intention durable de l’utilisateur, c’est-à-dire le HVAC, la consigne ou le preset demandés.

La fonction métier de détection, de configuration et de diagnostic spécifique est portée par un plugin. Le core et l’API fournissent uniquement le point d’extension et la politique commune de mise en retrait.

## 2. Acteurs et responsabilités

| Acteur / composant                    | Responsabilités fonctionnelles                                                                                                                                                                                                                                     |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Utilisateur ou automatisation externe | Peut commander directement les sous-jacents pendant la mise en retrait, sans être écrasé par le VTherm.                                                                                                                                                            |
| Plugin d’inhibition                   | Détecte la condition externe, applique ses délais, configure et expose par VTherm la politique d’arrêt physique (`éteindre` par défaut), expose le bypass éventuel et signale les transitions confirmées. Il ne commande ni le HVAC du VTherm ni ses sous-jacents. |
| `InhibitionProvider`                  | Contrat d’extension exposant le statut ternaire `ACTIVE`/`INACTIVE`/`UNKNOWN` et le cycle de vie nécessaires au core. Un seul provider est autorisé par VTherm éligible en V1.                                                                                     |
| API                                   | Fournit l’enregistrement d’une factory dédiée et le contrat public du provider. Elle doit rendre explicite tout conflit d’enregistrement.                                                                                                                          |
| Core / `BaseThermostat`               | Détient l’état de mise en retrait, applique les transitions, résout `OFF`, suspend contrôle et réparation, et émet l’arrêt physique unique seulement selon la politique fournie. Le core ne possède aucune configuration utilisateur d’inhibition.                 |
| `StateManager`                        | Résout exclusivement l’état HVAC effectif à partir de l’état demandé et des contraintes, avec l’inhibition comme contrainte prioritaire après l’arrêt central et la sécurité.                                                                                      |
| Sous-jacents                          | Reçoivent l’arrêt initial et la reprise normale ; ils restent pilotables directement pendant l’inhibition.                                                                                                                                                         |

## 3. Cas d’utilisation

### UC-01 — Entrer en inhibition

1. Le provider confirme que la condition d’inhibition est active.
2. Le core recalcule l’état effectif.
3. Si le HVAC demandé n’est pas `OFF`, l’état effectif devient `OFF` avec une raison d’arrêt dédiée.
4. Si la politique effective est « éteindre », le core envoie l’arrêt physique aux sous-jacents une seule fois ; sinon il ne leur envoie pas `turn_off`, y compris si le statut est `UNKNOWN`. Dans les deux cas, il mémorise que le contrôle leur a été retiré et que la transition d’entrée est accomplie.
5. Le core suspend la boucle de chauffage et la réparation automatique d’état.

### UC-02 — Rester inhibé

Tant que l’inhibition est active, le VTherm ne doit ni réémettre l’arrêt, ni lancer le contrôle de chauffage, ni réparer l’état des sous-jacents. Les commandes directes envoyées par l’utilisateur ou une autre intégration ne doivent pas être annulées par le VTherm.

### UC-03 — Modifier l’intention pendant l’inhibition

Une modification du HVAC, du preset ou de la consigne demandés doit être conservée comme intention courante. Elle ne doit pas provoquer de reprise des sous-jacents tant que l’inhibition reste active.

### UC-04 — Sortir d’inhibition

1. Le provider confirme que la condition est inactive.
2. Le core abandonne l’état de mise en retrait.
3. Le `StateManager` recalcule l’état effectif à partir de l’état demandé courant et des autres contraintes actives.
4. Le VTherm reprend son fonctionnement normal et applique cet état aux sous-jacents.

### UC-05 — Arrêt manuel pendant l’inhibition

Si l’utilisateur demande `OFF` pendant l’inhibition, cette demande doit rester `OFF` après la sortie. Le VTherm ne doit pas réactiver le chauffage uniquement parce que l’inhibition est levée.

## 4. Exigences fonctionnelles V1

| ID     | Exigence                                                                                                                                                                                                                                                            |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-001 | Le système doit fournir dans l’API une factory dédiée permettant d’enregistrer un `InhibitionProvider`.                                                                                                                                                             |
| FR-002 | Le système doit instancier au plus un provider par VTherm éligible.                                                                                                                                                                                                 |
| FR-003 | Le système doit signaler explicitement toute tentative d’enregistrer un second provider en conflit.                                                                                                                                                                 |
| FR-004 | Le provider doit exposer exactement l’un des statuts `ACTIVE`, `INACTIVE` ou `UNKNOWN` et signaler au core les transitions confirmées après ses éventuels délais. `UNKNOWN` ne doit être converti silencieusement en aucun autre statut.                            |
| FR-005 | Le provider ne doit pas modifier l’état HVAC, le preset ou la consigne demandés.                                                                                                                                                                                    |
| FR-006 | À l’entrée en inhibition, le système doit toujours résoudre le HVAC effectif vers `OFF`, y compris lorsque le HVAC demandé est déjà `OFF`.                                                                                                                          |
| FR-007 | Le plugin doit fournir par VTherm une politique effective `éteindre` ou `ne pas éteindre`; sa valeur par défaut et son repli sûr sont `éteindre`. Le core ne doit pas fournir de configuration utilisateur d’inhibition.                                            |
| FR-008 | À l’entrée, le système doit émettre au plus une fois `turn_off` vers les sous-jacents si, et seulement si, la politique effective est `éteindre`; cette émission est interdite si la politique est désactivée, y compris en `UNKNOWN`.                              |
| FR-009 | Dans tous les cas, l’entrée doit retirer le contrôle VTherm, suspendre le contrôle de chauffage et la réparation automatique des sous-jacents.                                                                                                                      |
| FR-010 | Pendant l’inhibition, le système ne doit pas réémettre `turn_off` ni écraser les commandes directes externes.                                                                                                                                                       |
| FR-011 | À la sortie, le système doit recalculer et appliquer l’état demandé courant, y compris les changements intervenus pendant l’inhibition.                                                                                                                             |
| FR-012 | Le système doit conserver la sémantique d’une demande `OFF` effectuée pendant l’inhibition.                                                                                                                                                                         |
| FR-013 | Le core doit persister, dans une mémoire runtime distincte de `VThermState`, la politique effective et l’accomplissement de la transition d’entrée. Cet accomplissement est distinct de l’arrêt physique : la garde de retrait peut être accomplie sans `turn_off`. |
| FR-014 | Le système doit fournir une raison d’arrêt stable et distincte pour l’inhibition, proposée sous le nom `hvac_off_inhibition`.                                                                                                                                       |
| FR-015 | Le système doit rendre observable l’état de mise en retrait, la politique effective, l’accomplissement de l’entrée et sa raison sans exposer de données sensibles supplémentaires.                                                                                  |
| FR-016 | Les délais, la détection des sources, la configuration de la politique, les traductions, les entités de diagnostic et le bypass spécifique doivent rester dans le plugin.                                                                                           |

## 5. Règles métier

| ID     | Règle                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BR-001 | L’inhibition est une contrainte externe temporaire ; elle ne remplace jamais l’état demandé durable.                                                                                                                                                                                                                                                                                                                                              |
| BR-002 | L’état effectif doit respecter la relation `current_state = f(requested_state, contraintes_actives)`.                                                                                                                                                                                                                                                                                                                                             |
| BR-003 | La priorité de résolution V1 est : arrêt central et sécurité, inhibition, fenêtre, puis auto-start/auto-stop ; les autres priorités doivent rester inchangées si elles ne sont pas précisées par la conception.                                                                                                                                                                                                                                   |
| BR-004 | Une transition `inactive → active` constitue le seul déclencheur de l’arrêt initial.                                                                                                                                                                                                                                                                                                                                                              |
| BR-005 | Une transition `active → active` est idempotente : aucun nouvel arrêt et aucune réparation des sous-jacents ne sont autorisés.                                                                                                                                                                                                                                                                                                                    |
| BR-006 | Une transition `active → inactive` déclenche une seule réconciliation avec l’état demandé courant.                                                                                                                                                                                                                                                                                                                                                |
| BR-007 | Si l’état demandé courant est `OFF` à la sortie, aucun sous-jacent ne doit être réactivé.                                                                                                                                                                                                                                                                                                                                                         |
| BR-008 | L’inhibition ne doit pas être représentée comme une modification de `requested_state` ou de `current_state` persisté ; elle doit être observable comme contrainte et raison de fonctionnement.                                                                                                                                                                                                                                                    |
| BR-009 | Un provider unique peut agréger plusieurs sources ; la V1 ne définit pas plusieurs providers indépendants par VTherm.                                                                                                                                                                                                                                                                                                                             |
| BR-010 | `UNKNOWN` est un statut observable distinct : aucune reprise n’est autorisée avant `INACTIVE` confirmé. La politique effective reste celle persistée ; en repli sans provider exploitable ou sans politique connue, elle vaut « éteindre ». Si elle vaut « éteindre », une seule coupure de précaution est exécutée ; si elle est désactivée, aucun `turn_off` n’est envoyé, même en `UNKNOWN`. La garde de retrait s’applique dans les deux cas. |

## 6. Transitions d’état

| État avant | Événement                            | État après             | Effet obligatoire                                                                                                                                        |
| ---------- | ------------------------------------ | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Inactif    | Détection confirmée                  | Actif, contrôle retiré | Résoudre `OFF`, accomplir la garde d’entrée, suspendre contrôle et réparation ; envoyer `turn_off` une fois seulement si la politique vaut « éteindre ». |
| Actif      | Nouveau cycle sans changement        | Actif, contrôle retiré | Ne rien réémettre et laisser les commandes externes inchangées.                                                                                          |
| Actif      | HVAC/preset/consigne demandé modifié | Actif, contrôle retiré | Mémoriser l’intention courante sans reprendre les sous-jacents.                                                                                          |
| Actif      | Arrêt manuel demandé                 | Actif, contrôle retiré | Conserver `OFF` comme intention courante.                                                                                                                |
| Actif      | Fin d’inhibition confirmée           | Inactif                | Recalculer puis appliquer l’état demandé courant.                                                                                                        |
| Inactif    | Cycle normal                         | Inactif                | Conserver le fonctionnement VTherm existant.                                                                                                             |

## 7. Redémarrage, rechargement et persistance

- Le core doit persister au minimum, dans un état runtime distinct de `VThermState`, l’état de mise en retrait, le statut provider, la politique effective et l’accomplissement de la transition d’entrée. Cet accomplissement de garde est distinct de l’arrêt physique effectivement émis.
- Après redémarrage de Home Assistant, le core doit réconcilier cet état avec le provider avant de reprendre le contrôle normal.
- Un redémarrage ne doit pas générer un second arrêt uniquement parce que l’état persistant indique que l’arrêt initial a déjà été exécuté.
- Si l’inhibition est toujours active après redémarrage, le contrôle des sous-jacents doit rester suspendu.
- Si l’inhibition est inactive après redémarrage, la reprise doit utiliser l’état demandé courant, et non une valeur reconstruite à partir de l’ancien état effectif.
- Lors d’un chargement tardif, le provider passe par `UNKNOWN` ; aucune reprise n’est autorisée avant `INACTIVE` confirmé. Sans politique connue ou provider exploitable, le repli sûr est « éteindre » et une coupure de précaution unique est appliquée ; une politique désactivée interdit `turn_off`, y compris dans ce cas.
- Une garantie exactly-once physique de bout en bout n’est pas exigée : l’arrêt est exactement-once logique par activation en processus sain, avec une limite documentée en cas de panne entre l’appel de service et la persistance.

## 8. Périmètre V1 et exclusions

### Inclus

- Contrat `InhibitionProvider` et factory dédiée dans `vtherm_api`.
- Unicité du provider, cycle de vie, écoute des transitions et recalcul demandé par le provider.
- Politique core d’arrêt unique, retrait du contrôle, suspension et réconciliation.
- Contrainte HVAC `OFF` et raison d’arrêt dédiée.
- Persistance minimale et observabilité core.
- Détection, délais, bypass, configuration, diagnostics et documentation spécifiques dans un plugin.
- Tests unitaires et d’intégration correspondant aux exigences et critères ci-dessous.

### Exclus

- Fonctionnalité complète `inhibit` dans le core avec parcours de configuration, entités et services utilisateur.
- Ajout d’un état `inhibited` dans `requested_state` ou `current_state`.
- Forçage vers `eco`, `frost`, `fan_only` ou un autre mode que `OFF`.
- Plusieurs providers indépendants par VTherm.
- Migration ou remplacement de la fonctionnalité fenêtre.
- Refactorisation générale de toutes les contraintes HVAC.
- Correction du code, de la configuration, des dépendances ou des tests dans le cadre de cette spécification.

## 9. Priorités et conflits de provider

- L’inhibition doit être appliquée après l’arrêt central et les mécanismes de sécurité, et avant la fenêtre et l’auto-start/auto-stop.
- La priorité entre inhibition et des contraintes futures non citées ici n’est pas définie par cette spécification.
- Le premier provider enregistré pour un VTherm éligible est retenu comme unique provider actif en V1 ; chaque candidat suivant est rejeté pour ce VTherm.
- Toute seconde factory ou tout second provider incompatible doit produire un conflit explicite, traçable et non silencieux, en indiquant le provider retenu et le provider rejeté.
- Le provider ne doit pas contourner la résolution centralisée du `StateManager` en émettant lui-même des commandes HVAC.
- En cas de statut `UNKNOWN`, le retrait conservateur observable s’applique : aucune reprise avant `INACTIVE` confirmé ; une seule coupure de précaution est exécutée si aucune coupure connue n’existe. En l’absence de factory éligible (`ABSENT`), le comportement historique est conservé. D-2087-06 couvre cette décision et elle n’est plus bloquante.

## 10. Observabilité

Le système doit rendre vérifiables au minimum :

- l’état de détection fourni par le provider ;
- l’état de mise en retrait core ;
- la raison effective `hvac_off_inhibition` lorsqu’elle s’applique ;
- l’entrée et la sortie d’inhibition ;
- l’exécution unique de l’arrêt initial ;
- la suspension du contrôle et de la réparation ;
- la réconciliation effectuée à la sortie ;
- les conflits ou erreurs de provider.

Les diagnostics spécifiques à la source, aux délais et au bypass appartiennent au plugin. Aucun nouveau traitement de données sensibles n’est requis par le périmètre défini.

## 11. Critères d’acceptation

| ID      | Scénario observable                                                                                                             | Résultat attendu                                                                                                                                                                                                                                                               |
| ------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| AC-001  | Un provider confirme l’activation alors que le VTherm demande du chauffage ou du refroidissement, avec la politique par défaut. | Le HVAC effectif passe à `OFF`, la raison d’arrêt est dédiée, le contrôle et la réparation sont suspendus, et les sous-jacents reçoivent un seul `turn_off`.                                                                                                                   |
| AC-001b | Le plugin désactive la politique d’arrêt physique avant l’entrée.                                                               | Le HVAC effectif passe à `OFF`, le contrôle et la réparation sont suspendus, la garde de retrait est accomplie, et aucun `turn_off` n’est envoyé.                                                                                                                              |
| AC-002  | Plusieurs cycles s’exécutent sans changement de détection.                                                                      | Aucun nouvel arrêt, ordre HVAC, contrôle de chauffage ou repair n’est émis par le VTherm.                                                                                                                                                                                      |
| AC-003  | Un sous-jacent est commandé directement par l’utilisateur pendant l’inhibition.                                                 | Le VTherm ne réémet pas d’ordre pour écraser cette commande.                                                                                                                                                                                                                   |
| AC-004  | Le preset, la consigne ou le HVAC demandé change pendant l’inhibition.                                                          | La dernière intention demandée est conservée et aucun sous-jacent n’est repris avant la sortie.                                                                                                                                                                                |
| AC-005  | L’utilisateur demande `OFF` pendant l’inhibition puis le provider devient inactif.                                              | La sortie ne réactive pas le chauffage ; l’état `OFF` demandé est respecté.                                                                                                                                                                                                    |
| AC-006  | Le provider devient inactif après une inhibition ayant laissé une intention de chauffage.                                       | Le core recalcule et applique cette intention courante selon les autres contraintes actives.                                                                                                                                                                                   |
| AC-007  | Home Assistant redémarre pendant une inhibition active après l’arrêt initial.                                                   | L’inhibition reste active, aucun second arrêt inutile n’est envoyé et le contrôle reste suspendu.                                                                                                                                                                              |
| AC-008  | Home Assistant redémarre alors que l’inhibition est inactive.                                                                   | Le VTherm reprend son fonctionnement normal avec l’état demandé courant.                                                                                                                                                                                                       |
| AC-009  | Deux providers veulent s’enregistrer pour le même VTherm.                                                                       | Un conflit explicite est signalé et un seul provider reste autorisé.                                                                                                                                                                                                           |
| AC-010  | Le provider est `UNKNOWN` au chargement, après une erreur ou durant un reload.                                                  | Le statut est observable, aucune reprise n’a lieu avant `INACTIVE` confirmé ; le repli sans politique connue est « éteindre » et envoie une seule coupure de précaution, tandis qu’une politique désactivée n’envoie jamais `turn_off`. La garde s’applique dans les deux cas. |
| AC-011  | L’état HVAC effectif est déjà `OFF` mais un sous-jacent est actif à l’entrée.                                                   | L’arrêt initial est tout de même envoyé une fois.                                                                                                                                                                                                                              |
| AC-012  | Une contrainte fenêtre ou auto-start/auto-stop est active en plus de l’inhibition.                                              | L’inhibition respecte la priorité V1 et ne dégrade pas les autres contraintes non modifiées.                                                                                                                                                                                   |
| AC-013  | Deux factories sont éligibles pour le même VTherm.                                                                              | La première enregistrée est retenue, la seconde est rejetée et le conflit mentionne les deux providers.                                                                                                                                                                        |
| AC-014  | Une panne survient entre l’arrêt physique et la persistance de la garde.                                                        | La limite d’exactly-once physique est documentée ; aucune reprise automatique n’est autorisée sans statut `INACTIVE`.                                                                                                                                                          |

## 12. Matrice de tests attendus

| Domaine         | Cas attendus                                                                                               | Couverture minimale                                                                                       |
| --------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| API / factory   | Enregistrement valide, unicité, conflit, cycle de vie, provider absent                                     | Tests unitaires du contrat et des erreurs explicites.                                                     |
| Détection       | Transitions inactive/active, délais confirmés, répétition d’état, état non confirmé                        | Tests unitaires du provider ou de son adaptateur plugin.                                                  |
| Résolution HVAC | HVAC demandé chauffage, refroidissement et `OFF` ; raison dédiée ; priorité sur fenêtre et auto-start/stop | Tests unitaires du `StateManager`.                                                                        |
| Entrée          | Sous-jacent actif, sous-jacent déjà arrêté, plusieurs sous-jacents, arrêt unique                           | Tests unitaires et d’intégration des ordres produits.                                                     |
| Maintien        | Cycles normaux, commande externe, repair et contrôle de chauffage                                          | Tests d’intégration garantissant l’absence d’ordres du VTherm.                                            |
| Intention       | Changement de HVAC, preset, consigne et arrêt manuel pendant inhibition                                    | Tests unitaires de conservation puis de réconciliation de l’intention.                                    |
| Sortie          | Inhibition levée vers chaque état demandé, contraintes concurrentes                                        | Tests d’intégration de reprise et de priorité.                                                            |
| Persistance     | Redémarrage actif, redémarrage inactif, arrêt déjà effectué, restauration du provider tardive              | Tests de persistance et de cycle de vie.                                                                  |
| Exactly-once    | Politique activée/désactivée, `UNKNOWN`, coupure connue/inconnue, panne entre service et persistance       | Tests de garde logique, absence de `turn_off` désactivé et documentation explicite de la limite physique. |
| Politique       | Valeur par défaut, configuration plugin par VTherm, politique persistée, repli sans provider/politique     | Tests de configuration plugin et de restauration ; aucun parcours de configuration core.                  |
| Observabilité   | Attributs, raison, transitions, conflits et erreurs                                                        | Tests de présence et de stabilité des diagnostics.                                                        |
| Régression      | Fonctionnement sans provider, fenêtre, auto-start/stop, contrôle TPI et réparation existants               | Suite de non-régression du core et intégration.                                                           |

## 13. Hypothèses, questions ouvertes et traçabilité

### Hypothèses retenues

- Le provider fournit un état fiable après les délais qui lui sont propres.
- La V1 force uniquement `OFF`.
- Un provider peut agréger plusieurs sources ; l’agrégation est une responsabilité du plugin.
- Le core doit gérer l’ordre de chargement du provider sans reprise prématurée ; `UNKNOWN` applique D-2087-06 jusqu’à `INACTIVE` confirmé.
- La persistance runtime core est distincte de `VThermState`.
- La garantie exactly-once concerne la transition d’entrée et la garde logique, pas nécessairement l’arrêt physique ; elle est logique par activation dans un processus sain, et non physique de bout en bout après panne.

### Questions ouvertes et décisions à prendre

1. Valider le nom stable de la raison `hvac_off_inhibition`.
2. Définir le format exact des attributs et de la mémoire persistée, notamment les champs de politique effective et d’accomplissement de la transition d’entrée, distincts de l’arrêt physique.
3. Définir le nom et les valeurs sérialisées de l’option plugin (« éteindre » / « ne pas éteindre ») ainsi que la migration des configurations existantes vers le défaut sûr.
4. Le repli `UNKNOWN` est couvert par D-2087-06 ; il n’est plus bloquant pour la convergence documentaire.
5. Décider si le bypass doit être livré avec le plugin V1 ou reporté ; question non bloquante, sans impact sur le core.
6. Définir les critères d’éligibilité d’un VTherm à un provider.
7. Confirmer le découpage et l’ordre de livraison des changements API/core puis plugin.

### Traçabilité

Cette spécification reprend les faits établis et la recommandation de [documentation/tech-docs/issue-2087-review.md](../tech-docs/issue-2087-review.md). Les comportements explicitement marqués comme proposés, hypothèses ou questions ouvertes ne constituent pas des comportements existants. Aucun code, fichier de configuration, dépendance ou test n’a été modifié pour produire ce document.

---

# Functional Specification — Issue #2087: Controlled VTherm Withdrawal

## Metadata

| Field                      | Value                                                                                                                                                                                                                                                                                                 |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name                       | Extensible inhibition mechanism / Mécanisme d’inhibition extensible                                                                                                                                                                                                                                   |
| Issue                      | [#2087 — Add an “inhibit” sensor to pause a VTherm](https://github.com/jmcollin78/versatile_thermostat/issues/2087)                                                                                                                                                                                   |
| Version                    | 1.2 — per-VTherm configurable physical-stop policy, specification converged with the design                                                                                                                                                                                                           |
| Status                     | Converged with the design; maintainer approval required before development                                                                                                                                                                                                                            |
| Date                       | 2026-10-11                                                                                                                                                                                                                                                                                            |
| Functional owner           | Versatile Thermostat project — maintainer decision to be confirmed                                                                                                                                                                                                                                    |
| Main source                | [Validated issue review](../tech-docs/issue-2087-review.md)                                                                                                                                                                                                                                           |
| Technical sources analyzed | `custom_components/versatile_thermostat/state_manager.py`, `base_thermostat.py`, `prop_handler_tpi.py`, `feature_repair_incorrect_state_manager.py`, `underlyings.py`, `vtherm_state.py`, and `custom_components/vtherm_api/src/vtherm_api/interfaces.py` and `vtherm_api.py`, as cited in the review |

## 1. Context and objective

Issue #2087 requests that a VTherm temporarily stop commanding its underlying devices when another heating or cooling source is active. Identified use cases include heating powered by photovoltaic surplus and air conditioning that is already cooling the room.

The V1 objective is to provide a **controlled withdrawal**: on entry, the core withdraws VTherm control, suspends control and repair, and resolves effective HVAC to `OFF`. The plugin provides, per VTherm, a policy telling the core whether to emit the physical stop to underlying devices; its default is **“turn off”**, preserving the already-specified V1 behavior. Only this single physical stop emission is conditional: withdrawal, suspension, and `OFF` resolution always apply. Inhibition must not change the user’s durable intent, namely the requested HVAC mode, setpoint, or preset.

The plugin owns the source-specific detection, configuration, and diagnostics. The core and API provide only the extension point and the common withdrawal policy.

## 2. Actors and responsibilities

| Actor / component           | Functional responsibilities                                                                                                                                                                                                                                   |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User or external automation | May directly command underlying devices during withdrawal without being overwritten by the VTherm.                                                                                                                                                            |
| Inhibition plugin           | Detects the external condition, applies its delays, configures and exposes the per-VTherm physical-stop policy (`turn off` by default), exposes any bypass, and signals confirmed transitions. It does not command the VTherm HVAC or its underlying devices. |
| `InhibitionProvider`        | Extension contract exposing the ternary `ACTIVE`/`INACTIVE`/`UNKNOWN` status and the lifecycle required by the core. Only one provider is allowed per eligible VTherm in V1.                                                                                  |
| API                         | Provides registration of a dedicated factory and the public provider contract. It must make any registration conflict explicit.                                                                                                                               |
| Core / `BaseThermostat`     | Owns withdrawal state, applies transitions, resolves `OFF`, suspends control and repair, and emits the single physical stop only according to the supplied policy. The core has no user inhibition configuration.                                             |
| `StateManager`              | Exclusively resolves effective HVAC from requested state and constraints, with inhibition as a priority constraint after central stop and safety.                                                                                                             |
| Underlying devices          | Receive the initial stop and normal resumption; they remain directly controllable during inhibition.                                                                                                                                                          |

## 3. Use cases

### UC-01 — Enter inhibition

1. The provider confirms that the inhibition condition is active.
2. The core recalculates the effective state.
3. If the requested HVAC mode is not `OFF`, the effective mode becomes `OFF` with a dedicated stop reason.
4. If the effective policy is “turn off”, the core sends one physical stop to underlying devices; otherwise it sends no `turn_off`, including when status is `UNKNOWN`. In both cases it records that control has been withdrawn and that the entry transition is complete.
5. The core suspends the heating-control loop and automatic state repair.

### UC-02 — Remain inhibited

While inhibition is active, the VTherm shall neither resend the stop, run heating control, nor repair underlying state. Direct commands sent by the user or another integration shall not be cancelled by the VTherm.

### UC-03 — Change intent during inhibition

A change to the requested HVAC mode, preset, or setpoint shall be retained as the current intent. It shall not resume underlying devices while inhibition remains active.

### UC-04 — Exit inhibition

1. The provider confirms that the condition is inactive.
2. The core leaves withdrawal state.
3. The `StateManager` recalculates effective state from the current requested state and other active constraints.
4. The VTherm resumes normal operation and applies that state to the underlying devices.

### UC-05 — Manual stop during inhibition

If the user requests `OFF` during inhibition, that request shall remain `OFF` after exit. The VTherm shall not reactivate heating solely because inhibition was cleared.

## 4. V1 functional requirements

| ID     | Requirement                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| FR-001 | The system shall provide a dedicated API factory for registering an `InhibitionProvider`.                                                                                                                                                        |
| FR-002 | The system shall instantiate at most one provider per eligible VTherm.                                                                                                                                                                           |
| FR-003 | The system shall explicitly report any attempt to register a conflicting second provider.                                                                                                                                                        |
| FR-004 | The provider shall expose exactly one of `ACTIVE`, `INACTIVE`, or `UNKNOWN` and notify the core of confirmed transitions after provider-specific delays. `UNKNOWN` shall not be silently converted to another status.                            |
| FR-005 | The provider shall not modify requested HVAC mode, preset, or setpoint.                                                                                                                                                                          |
| FR-006 | On inhibition entry, the system shall always resolve effective HVAC to `OFF`, including when requested HVAC is already `OFF`.                                                                                                                    |
| FR-007 | The plugin shall provide an effective per-VTherm policy of `turn off` or `do not turn off`; its default and safe fallback are `turn off`. The core shall not provide user inhibition configuration.                                              |
| FR-008 | On entry, the system shall emit `turn_off` to underlying devices at most once if and only if the effective policy is `turn off`; emission is forbidden when disabled, including in `UNKNOWN`.                                                    |
| FR-009 | In all cases, entry shall withdraw VTherm control and suspend heating control and automatic underlying-state repair.                                                                                                                             |
| FR-010 | During inhibition, the system shall not resend `turn_off` or overwrite direct external commands.                                                                                                                                                 |
| FR-011 | On exit, the system shall recalculate and apply the current requested state, including changes made during inhibition.                                                                                                                           |
| FR-012 | The system shall preserve the semantics of an `OFF` request made during inhibition.                                                                                                                                                              |
| FR-013 | The core shall persist, in runtime memory distinct from `VThermState`, the effective policy and completion of the entry transition. This completion is distinct from physical stopping: the withdrawal guard may be complete without `turn_off`. |
| FR-014 | The system shall provide a stable stop reason distinct for inhibition, proposed as `hvac_off_inhibition`.                                                                                                                                        |
| FR-015 | The system shall expose withdrawal state, effective policy, entry completion, and reason without introducing additional sensitive data.                                                                                                          |
| FR-016 | Source detection, delays, policy configuration, translations, diagnostic entities, and source-specific bypass shall remain in the plugin.                                                                                                        |

## 5. Business rules

| ID     | Rule                                                                                                                                                                                                                                                                                                                                                                                |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BR-001 | Inhibition is a temporary external constraint; it never replaces durable requested state.                                                                                                                                                                                                                                                                                           |
| BR-002 | Effective state shall follow `current_state = f(requested_state, active_constraints)`.                                                                                                                                                                                                                                                                                              |
| BR-003 | V1 resolution priority is: central stop and safety, inhibition, window, then auto-start/auto-stop; other priorities shall remain unchanged unless specified by design.                                                                                                                                                                                                              |
| BR-004 | An `inactive → active` transition is the only trigger for the initial stop.                                                                                                                                                                                                                                                                                                         |
| BR-005 | An `active → active` transition is idempotent: no new stop and no underlying repair are allowed.                                                                                                                                                                                                                                                                                    |
| BR-006 | An `active → inactive` transition shall trigger exactly one reconciliation with the current requested state.                                                                                                                                                                                                                                                                        |
| BR-007 | If current requested state is `OFF` on exit, no underlying device shall be reactivated.                                                                                                                                                                                                                                                                                             |
| BR-008 | Inhibition shall not be represented as a modification of persisted `requested_state` or `current_state`; it shall be observable as a constraint and operating reason.                                                                                                                                                                                                               |
| BR-009 | One provider may aggregate multiple sources; V1 does not define multiple independent providers per VTherm.                                                                                                                                                                                                                                                                          |
| BR-010 | `UNKNOWN` is a distinct observable status: no resumption is allowed before confirmed `INACTIVE`. The effective policy remains the persisted policy; without an usable provider or known policy, the safe fallback is `turn off`. If enabled, one precautionary stop is executed; if disabled, no `turn_off` is sent, even in `UNKNOWN`. The withdrawal guard applies in both cases. |

## 6. State transitions

| State before | Event                                  | State after               | Mandatory effect                                                                                                         |
| ------------ | -------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Inactive     | Confirmed detection                    | Active, control withdrawn | Resolve `OFF`, complete the entry guard, suspend control and repair; send one `turn_off` only when policy is `turn off`. |
| Active       | New cycle with no change               | Active, control withdrawn | Emit nothing new and leave external commands unchanged.                                                                  |
| Active       | Requested HVAC/preset/setpoint changed | Active, control withdrawn | Record current intent without resuming underlying devices.                                                               |
| Active       | Manual stop requested                  | Active, control withdrawn | Preserve `OFF` as current intent.                                                                                        |
| Active       | Confirmed inhibition end               | Inactive                  | Recalculate and apply current requested state.                                                                           |
| Inactive     | Normal cycle                           | Inactive                  | Preserve existing VTherm operation.                                                                                      |

## 7. Restart, reload, and persistence

- The core shall persist at least withdrawal state, provider status, effective policy, and completion of the entry transition, in runtime state distinct from `VThermState`. Guard completion is distinct from whether a physical stop was emitted.
- After Home Assistant restarts, the core shall reconcile this state with the provider before resuming normal control.
- A restart shall not generate a second stop merely because persistent state says that the initial stop was already executed.
- If inhibition remains active after restart, control of underlying devices shall remain suspended.
- If inhibition is inactive after restart, resumption shall use current requested state, not a value reconstructed from former effective state.
- When loaded late, the provider enters `UNKNOWN`; resumption is forbidden until confirmed `INACTIVE`. Without a known policy or usable provider, the safe fallback is `turn off` and one precautionary stop is sent; a disabled policy forbids `turn_off`, including in this case.
- End-to-end physical exactly-once is not guaranteed: the stop is logically exactly-once per activation in a healthy process, with a documented failure boundary between service call and persistence.

## 8. V1 scope and exclusions

### Included

- `InhibitionProvider` contract and dedicated factory in `vtherm_api`.
- Provider uniqueness, lifecycle, transition listening, and provider-requested recalculation.
- Core policy for one-time stop, control withdrawal, suspension, and reconciliation.
- `OFF` HVAC constraint and dedicated stop reason.
- Minimum persistence and core observability.
- Source detection, delays, bypass, configuration, diagnostics, and specific documentation in a plugin.
- Unit and integration tests corresponding to the requirements and acceptance criteria below.

### Excluded

- A complete core `inhibit` feature with user configuration flow, entities, and services.
- Adding an `inhibited` state to `requested_state` or `current_state`.
- Forcing `eco`, `frost`, `fan_only`, or any mode other than `OFF`.
- Multiple independent providers per VTherm.
- Migration or replacement of the window feature.
- General refactoring of all HVAC constraints.
- Correction of code, configuration, dependencies, or tests as part of this specification.

## 9. Priorities and provider conflicts

- Inhibition shall be applied after central stop and safety mechanisms, and before window and auto-start/auto-stop.
- Priority between inhibition and future constraints not listed here is not defined by this specification.
- The first provider registered for an eligible VTherm is retained as the only active provider in V1; each later candidate is rejected for that VTherm.
- Any second incompatible factory or provider shall produce an explicit, traceable, non-silent conflict identifying the retained and rejected providers.
- The provider shall not bypass centralized `StateManager` resolution by issuing HVAC commands itself.
- For `UNKNOWN`, observable conservative withdrawal applies: no resumption before confirmed `INACTIVE`, and one precautionary stop if no stop is known. With no eligible factory (`ABSENT`), historical behavior is preserved. D-2087-06 covers this decision; it is no longer blocking for documentary convergence.

## 10. Observability

The system shall make at least the following verifiable:

- provider detection state;
- core withdrawal state;
- effective `hvac_off_inhibition` reason when applicable;
- inhibition entry and exit;
- execution of the one-time initial stop;
- suspension of control and repair;
- reconciliation performed on exit;
- provider conflicts or errors.

Source-, delay-, and bypass-specific diagnostics belong to the plugin. No new processing of sensitive data is required by the defined scope.

## 11. Acceptance criteria

| ID      | Observable scenario                                                                               | Expected result                                                                                                                                                                                                                 |
| ------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-001  | A provider confirms activation while VTherm requests heating or cooling, with the default policy. | Effective HVAC becomes `OFF`, the dedicated reason applies, control and repair are suspended, and underlying devices receive one `turn_off`.                                                                                    |
| AC-001b | The plugin disables the physical-stop policy before entry.                                        | Effective HVAC becomes `OFF`, control and repair are suspended, the withdrawal guard completes, and no `turn_off` is sent.                                                                                                      |
| AC-002  | Several cycles run with no detection change.                                                      | No new stop, HVAC command, heating control, or repair is emitted by VTherm.                                                                                                                                                     |
| AC-003  | An underlying device is directly commanded by the user during inhibition.                         | VTherm does not issue an order to overwrite that command.                                                                                                                                                                       |
| AC-004  | Requested HVAC, preset, or setpoint changes during inhibition.                                    | The latest requested intent is retained and no underlying device resumes before exit.                                                                                                                                           |
| AC-005  | User requests `OFF` during inhibition and provider becomes inactive.                              | Exit does not reactivate heating; requested `OFF` is respected.                                                                                                                                                                 |
| AC-006  | Provider becomes inactive after inhibition while heating intent remains.                          | Core recalculates and applies current intent subject to other active constraints.                                                                                                                                               |
| AC-007  | Home Assistant restarts during active inhibition after initial stop.                              | Inhibition remains active, no unnecessary second stop is sent, and control remains suspended.                                                                                                                                   |
| AC-008  | Home Assistant restarts while inhibition is inactive.                                             | VTherm resumes normal operation with current requested state.                                                                                                                                                                   |
| AC-009  | Two providers attempt to register for the same VTherm.                                            | An explicit conflict is reported and only one provider remains allowed.                                                                                                                                                         |
| AC-010  | Provider is `UNKNOWN` at loading, after an error, or during reload.                               | Status is observable, no resumption occurs before confirmed `INACTIVE`; the no-policy fallback is `turn off` and sends one precautionary stop, while a disabled policy never sends `turn_off`. The guard applies in both cases. |
| AC-011  | Effective HVAC is already `OFF` but an underlying device is active on entry.                      | Initial stop is still sent once.                                                                                                                                                                                                |
| AC-012  | Window or auto-start/auto-stop constraint is active together with inhibition.                     | Inhibition follows V1 priority and does not degrade other unchanged constraints.                                                                                                                                                |
| AC-013  | Two factories are eligible for the same VTherm.                                                   | The first registered is retained, the second is rejected, and the conflict names both providers.                                                                                                                                |
| AC-014  | A failure occurs between physical stop and guard persistence.                                     | The physical exactly-once limitation is documented; no automatic resumption occurs without `INACTIVE`.                                                                                                                          |

## 12. Expected test matrix

| Area            | Expected cases                                                                                          | Minimum coverage                                                                                                   |
| --------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| API / factory   | Valid registration, uniqueness, conflict, lifecycle, absent provider                                    | Unit tests for contract and explicit errors.                                                                       |
| Detection       | Inactive/active transitions, confirmed delays, repeated state, unconfirmed state                        | Unit tests for provider or plugin adapter.                                                                         |
| HVAC resolution | Requested heating, cooling, and `OFF`; dedicated reason; priority over window and auto-start/stop       | `StateManager` unit tests.                                                                                         |
| Entry           | Active underlying device, already-stopped underlying device, multiple underlying devices, one-time stop | Unit and integration tests for produced commands.                                                                  |
| Holding         | Normal cycles, external command, repair, and heating control                                            | Integration tests ensuring no VTherm orders.                                                                       |
| Intent          | HVAC, preset, setpoint, and manual stop changes during inhibition                                       | Unit tests for retaining and reconciling intent.                                                                   |
| Exit            | Inhibition cleared for each requested state, concurrent constraints                                     | Integration tests for resumption and priority.                                                                     |
| Persistence     | Active restart, inactive restart, stop already performed, late provider restoration                     | Persistence and lifecycle tests.                                                                                   |
| Exactly-once    | Enabled/disabled policy, `UNKNOWN`, known/unknown stop, failure between service call and persistence    | Logical guard tests, disabled-policy absence of `turn_off`, and explicit documentation of the physical limitation. |
| Policy          | Default, per-VTherm plugin configuration, persisted policy, no-provider/no-policy fallback              | Plugin configuration and restoration tests; no core configuration flow.                                            |
| Observability   | Attributes, reason, transitions, conflicts, and errors                                                  | Tests for diagnostic presence and stability.                                                                       |
| Regression      | Operation without provider, window, auto-start/stop, TPI control, and existing repair                   | Core and integration regression suite.                                                                             |

## 13. Assumptions, open questions, and traceability

### Assumptions retained

- Provider supplies a reliable state after its own delays.
- V1 forces only `OFF`.
- A provider may aggregate multiple sources; aggregation is the plugin’s responsibility.
- Core must handle provider load order without premature resumption; `UNKNOWN` applies D-2087-06 until confirmed `INACTIVE`.
- Core runtime persistence is distinct from `VThermState`.
- Exactly-once applies to the entry transition and logical guard, not necessarily to physical stopping; it is logical per activation in a healthy process, not physical end-to-end after a failure.

### Open questions and decisions required

1. Approve the stable reason name `hvac_off_inhibition`.
2. Define the exact format of persisted attributes and memory, including effective policy and entry-transition completion, distinct from physical stopping.
3. Define the plugin option name and serialized values (`turn off` / `do not turn off`) and migration of existing configurations to the safe default.
4. `UNKNOWN` fallback is covered by D-2087-06; it is no longer blocking for documentary convergence.
5. Decide whether bypass is delivered with the V1 plugin or deferred; this is non-blocking and has no core impact.
6. Define VTherm eligibility criteria for a provider.
7. Confirm split and delivery order for API/core changes and plugin changes.

### Traceability

This specification restates the established facts and recommendation from [documentation/tech-docs/issue-2087-review.md](../tech-docs/issue-2087-review.md). Behaviors explicitly marked as proposed, assumptions, or open questions are not existing behaviors. No code, configuration file, dependency, or test was modified to produce this document.
