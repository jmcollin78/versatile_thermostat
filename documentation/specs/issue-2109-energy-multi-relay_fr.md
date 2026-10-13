# Spécification fonctionnelle — Issue #2109, point 1.1

## 1. Titre et métadonnées

- **Nom :** Sous-comptage du capteur d’énergie `over_switch` avec plusieurs relais
- **Issue :** [#2109 — Capteur d’énergie et gestionnaire de puissance](https://github.com/jmcollin78/versatile_thermostat/issues/2109)
- **Point couvert :** 1.1 uniquement
- **Version :** 1.0
- **Statut :** Proposée pour validation avant développement
- **Date :** 2026-10-13
- **Propriétaire :** Projet Versatile Thermostat
- **Rapport validé :** [issue-2109-review.md](../tech-docs/issue-2109-review.md)
- **Sources vérifiées :** [thermostat_switch.py](../../custom_components/versatile_thermostat/thermostat_switch.py), [cycle_scheduler.py](../../custom_components/versatile_thermostat/cycle_scheduler.py), [feature_power_manager.py](../../custom_components/versatile_thermostat/feature_power_manager.py), [base-attributes.md](../fr/base-attributes.md), [test_power.py](../../tests/test_power.py)

## 2. But et contexte

Pour un thermostat `over_switch` commandant plusieurs relais, le capteur d’énergie sous-estime actuellement l’énergie ajoutée à chaque cycle d’un facteur égal au nombre de relais. Le rapport validé attribue ce sous-comptage à une division par `nb_underlying_entities` alors que la fin de cycle appelle `incremente_energy()` une seule fois et que `mean_cycle_power` représente déjà la puissance moyenne totale du thermostat.

Le but est de définir le comportement attendu pour que chaque incrément de cycle reflète la puissance totale configurée, tout en conservant le comportement d’un thermostat à un seul relais et les contrats d’unités existants.

## 3. Périmètre inclus et exclusions

### Inclus

- Le calcul de l’énergie ajoutée par cycle pour `over_switch` lorsque le thermostat possède deux relais ou plus.
- La suppression de la division par le nombre de relais dans ce calcul.
- La mise à jour des attentes du test d’énergie existant.
- Un test d’intégration passant par la fin de cycle de l’ordonnanceur, vérifiant plusieurs relais et un appel unique par cycle.
- La conservation de `device_power` comme puissance totale lorsque plusieurs équipements sont contrôlés.

### Exclus

- Le point 1.2 de l’issue #2109, relatif à une éventuelle rafale d’incréments.
- Le point 2, relatif aux réservations du gestionnaire de puissance.
- Toute correction rétrospective des statistiques ou historiques Home Assistant déjà enregistrés.
- L’alternative consistant à appeler l’incrément une fois par relais.
- L’ajout d’une option de compatibilité conservant le calcul sous-compté.
- Toute modification du code, de la configuration, des dépendances ou de l’état Home Assistant dans le cadre de cette spécification.

## 4. Acteurs et cas d’utilisation

### Acteurs

- **Utilisateur ou administrateur :** configure la puissance totale de l’équipement et consulte le capteur d’énergie.
- **Thermostat `over_switch` :** maintient le compteur d’énergie selon sa puissance moyenne de cycle.
- **Ordonnanceur de cycles :** déclenche l’incrément à la fin du cycle maître.
- **Home Assistant :** expose l’énergie et ses unités aux utilisateurs et aux statistiques.
- **Mainteneur :** valide la spécification et les tests avant développement.

### Cas nominal — Incrément d’un cycle multi-relais

1. L’utilisateur a configuré `device_power` comme puissance totale des relais contrôlés.
2. Le thermostat calcule `mean_cycle_power` à partir de cette puissance totale et du pourcentage d’allumage du cycle.
3. L’ordonnanceur atteint la fin du cycle maître et déclenche un seul incrément.
4. Le thermostat ajoute l’énergie correspondant à la puissance moyenne totale pendant la durée du cycle.
5. Le compteur expose une valeur dans l’unité d’énergie correspondant à l’unité de puissance configurée.

## 5. Terminologie et unités

- **Relais / entité sous-jacente :** équipement commandé par le thermostat `over_switch`.
- **`nb_underlying_entities` :** nombre d’entités sous-jacentes contrôlées.
- **`device_power` :** puissance totale configurée pour l’ensemble des équipements contrôlés lorsqu’il y en a plusieurs.
- **`mean_cycle_power` :** puissance moyenne du thermostat pendant le cycle ; elle est calculée à partir de `device_power` et du pourcentage d’allumage.
- **Durée du cycle (`cycle_min`) :** durée du cycle en minutes.
- **Puissance :** W ou kW selon l’unité configurée ; le calcul interne est normalisé en W selon le code vérifié.
- **Énergie ajoutée :** Wh lorsque la puissance utilisée est en W, ou kWh lorsque la puissance affichée/configurée est en kW.

La conversion attendue est :

`énergie_ajoutée = mean_cycle_power × cycle_min / 60`

La formule ne doit pas contenir de division supplémentaire par `nb_underlying_entities`. Exemple du rapport : pour 4 300 W, cinq minutes et trois relais, l’incrément attendu est environ 358,3 Wh, contre 119,4 Wh avec la division erronée.

## 6. Exigences fonctionnelles

- **FR-001 — Puissance totale :** Le système doit interpréter `device_power` comme la puissance totale de l’ensemble des relais lorsque plusieurs équipements sont contrôlés.
- **FR-002 — Calcul multi-relais :** Pour un `over_switch` ayant au moins deux relais, le système doit calculer chaque incrément avec `mean_cycle_power × cycle_min / 60`, sans division par `nb_underlying_entities`.
- **FR-003 — Un appel par cycle :** Le système doit produire un seul incrément d’énergie à la fin de chaque cycle maître de l’ordonnanceur.
- **FR-004 — Puissance moyenne :** Le système doit utiliser `mean_cycle_power` comme puissance moyenne totale du thermostat, et non comme puissance d’un seul relais.
- **FR-005 — Cas mono-relais :** Avec un seul relais, le comportement fonctionnel attendu doit rester inchangé.
- **FR-006 — Unités :** Le système doit conserver la cohérence entre W et Wh, ainsi qu’entre kW et kWh, lors de l’exposition du calcul.
- **FR-007 — Historique :** Le système ne doit pas recalculer ni modifier rétroactivement les valeurs d’énergie déjà enregistrées par Home Assistant.
- **FR-008 — Non-régression de périmètre :** Le changement ne doit pas modifier les réservations du gestionnaire de puissance ni traiter les points 1.2 et 2 de l’issue.

## 7. Règles métier et règles de calcul

- **BR-001 — Total configuré :** Lorsque plusieurs relais sont contrôlés, `device_power` est la puissance totale et ne doit pas être répartie une seconde fois lors du comptage de l’énergie.
- **BR-002 — Formule de cycle :** Pour un cycle actif, l’énergie ajoutée est la puissance moyenne totale multipliée par la durée du cycle exprimée en heures.
- **BR-003 — Appel unique :** La fin du cycle maître est le point de déclenchement de l’incrément ; un cycle ne doit pas être compté une fois par relais.
- **BR-004 — Unités homogènes :** La puissance et l’énergie doivent rester dans des unités correspondantes ; la durée en minutes est divisée par 60 pour obtenir des heures.
- **BR-005 — Arrêt :** Si le thermostat est à l’arrêt ou si aucune puissance moyenne de cycle n’est disponible, aucun nouvel incrément positif ne doit être déduit de cette spécification.
- **BR-006 — Historiques :** Les valeurs passées restent inchangées ; la correction s’applique uniquement aux nouveaux incréments.

## 8. Compatibilité, non-régression et données

- Le comportement d’un `over_switch` mono-relais doit rester compatible avec le comportement attendu avant cette correction.
- Les attributs et unités existants doivent rester utilisables par Home Assistant.
- Le test direct existant qui encode la division par deux doit être aligné sur la formule corrigée ; il ne constitue pas à lui seul la preuve de l’appel unique par cycle.
- Un test d’intégration doit traverser `_on_master_cycle_end()` et vérifier qu’un seul incrément est réalisé pour plusieurs relais.
- Aucune migration de données, de configuration ou d’historique n’est requise.
- Les statistiques déjà enregistrées ne doivent pas être corrigées rétroactivement.

## 9. Critères d’acceptation

- **AC-001 :** Avec deux relais ou plus et une puissance totale configurée, un cycle ajoute `mean_cycle_power × cycle_min / 60` dans l’unité d’énergie correspondante.
- **AC-002 :** Avec 4 300 W, trois relais et un cycle de cinq minutes, l’incrément est environ 358,3 Wh et non 119,4 Wh.
- **AC-003 :** Un scénario traversant la fin de cycle de l’ordonnanceur confirme qu’un seul appel d’incrément est effectué par cycle maître.
- **AC-004 :** Le calcul ne divise jamais l’énergie de cycle par `nb_underlying_entities`.
- **AC-005 :** Avec un seul relais, les résultats fonctionnels et les unités restent inchangés.
- **AC-006 :** Les valeurs en W produisent des valeurs en Wh et les valeurs en kW produisent des valeurs en kWh, sans facteur 1 000 incorrect.
- **AC-007 :** Un cycle sans puissance moyenne disponible ou avec le thermostat à l’arrêt n’ajoute pas d’énergie positive au compteur.
- **AC-008 :** Les valeurs historiques Home Assistant ne sont ni recalculées ni modifiées.
- **AC-009 :** Les tests de réservation du gestionnaire de puissance et les comportements hors point 1.1 ne sont pas modifiés par cette correction.

## 10. Comportements explicitement hors-scope

- La gestion d’une rafale ou de plusieurs appels d’incrément dans le point 1.2.
- La correction des réservations ou de la logique de délestage du point 2.
- Le changement de modèle d’appel pour déclencher un incrément par relais.
- La reconstruction des historiques et statistiques Home Assistant.
- La modification de la puissance configurée par l’utilisateur ou sa réinterprétation comme puissance unitaire par relais.
- La modification des thermostats `over_climate` ou des autres modes non concernés par le point 1.1.

## 11. Risques et traitements

| Risque                                                                   | Gravité / probabilité          | Traitement prévu                                                                  |
| ------------------------------------------------------------------------ | ------------------------------ | --------------------------------------------------------------------------------- |
| Hausse des nouvelles valeurs d’énergie pour les thermostats multi-relais | Moyenne / certaine             | L’assumer comme résultat attendu et ne pas migrer les historiques.                |
| Régression vers un incrément par relais                                  | Moyenne / faible               | Ajouter le test d’intégration qui vérifie un appel unique par cycle.              |
| Confusion sur la puissance totale configurée                             | Moyenne / moyenne              | Conserver et vérifier la documentation indiquant que `device_power` est le total. |
| Incohérence W/Wh ou kW/kWh                                               | Moyenne / faible               | Vérifier les unités dans les tests et les critères d’acceptation.                 |
| Sécurité ou confidentialité                                              | Nulle / nulle selon le rapport | Aucun impact identifié ; aucun traitement supplémentaire.                         |

## 12. Évolutions futures proposées

- Traiter séparément le point 1.2 après décision et spécification dédiées.
- Traiter séparément le point 2 sur les réservations du gestionnaire de puissance.
- Renforcer les tests de cycle si d’autres chemins d’appel apparaissent.

## 13. Hypothèses, questions ouvertes et traçabilité

### Hypothèses

- Aucune autre voie active ne déclenche `incremente_energy()` une fois par relais pour `over_switch` ; cette hypothèse doit être confirmée par le test d’intégration.
- `mean_cycle_power` reste la puissance moyenne totale du thermostat dans le chemin concerné.

### Questions ouvertes

- La spécification et la conception doivent-elles être explicitement validées par le mainteneur avant tout développement, conformément au rapport ?
- Le test d’intégration doit-il couvrir uniquement le chauffage ou également les autres états `over_switch` déjà pris en charge ?

### Traçabilité

Cette spécification est strictement alignée sur le rapport validé [issue-2109-review.md](../tech-docs/issue-2109-review.md) et couvre uniquement son point 1.1. Le rapport est la source de la décision de supprimer la division, de la formule, de l’exemple numérique, des exclusions et des risques. Les fichiers de code et de documentation listés dans les métadonnées ont été consultés pour vérifier les symboles et contrats existants. Aucun développement n’est inclus dans ce document.