# Revue de l'issue #2111 et de la PR #2113

**Statut :** PR techniquement recevable, validation beta recommandee avant fusion
**Issue :** [#2111 - Valve regulation: entering or leaving sleep does not force the valve recalculation](https://github.com/jmcollin78/versatile_thermostat/issues/2111)
**PR :** [#2113 - Valve regulation: recalculate and send the valve at once when the hvac mode changes](https://github.com/jmcollin78/versatile_thermostat/pull/2113)
**Depot examine :** `jmcollin78/versatile_thermostat`, branche `main` et diff de la PR
**Date de revue :** 2026-10-13

## Resume fidele

L'issue #2111 decrit un thermostat `over_climate` avec regulation directe de vannes dont l'ouverture reste temporairement obsolete lors des transitions vers ou depuis `sleep`. Le filtre `auto_regulation_period_min` reporte alors le recalcul et l'envoi : une vanne peut rester ouverte a 100 %, publier `hvac_action: heating` et faire compter le thermostat comme actif alors que `on_percent` vaut 0.

La PR #2113 memorise le mode HVAC utilise par le dernier calcul et par le dernier envoi. Lorsqu'il change, elle contourne le filtre de periode pour le calcul et l'envoi, ainsi que le filtre de variation d'ouverture pour le calcul. Les limitations existantes restent appliquees quand le mode est inchange.

## Sources et elements verifies

- L'issue #2111 documente les transitions fautives `heat -> sleep`, `sleep -> heat` et `sleep -> off -> heat`, sur une configuration avec `auto_regulation_period_min = 5`.
- Le diff de la PR ne modifie que [thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py) et ajoute cinq tests a [test_overclimate_valve.py](../../tests/test_overclimate_valve.py).
- Dans le flux courant, un changement HVAC passe par `update_states()`, qui recalcule puis appelle `async_control_heating()` ; le correctif est donc place dans la classe qui determine et envoie effectivement l'ouverture des vannes.
- Le passage a `OFF` continue d'appeler `set_valve_open_percent()` pour chaque vanne. La PR met ensuite a jour le mode du dernier envoi : le cas `sleep -> off -> heat` ne reutilise donc pas l'ouverture stale.
- Les nouveaux tests couvrent les cinq comportements annonces : entree dans `sleep`, sortie vers `heat`, sequence `sleep -> off -> heat`, reprise a froid `off -> heat`, et conservation du throttling sans changement de mode.
- Les informations publiques de la PR indiquent un job de tests reussi. Le contributeur annonce 767 tests passes et 2 ignores ; cette execution n'a pas ete reproduite localement lors de cette revue.

## Pertinence et recommandation

### Recommandation : retenir la PR pour une beta ciblee

Le correctif traite la cause racine plutot que de remettre ponctuellement une ouverture a zero. Les deux memoires de mode distinguent correctement le calcul du debit de l'envoi physique. La lecture du flux ne revele pas de defaut bloquant.

La recommandation du mainteneur de publier une beta avant fusion est justifiee : la modification peut commander immediatement des vannes physiques sur chaque changement de mode HVAC.

## Perimetre propose

### Inclus

- Thermostats `over_climate` utilisant `auto_regulation_valve`.
- Recalcul immediat de l'ouverture lors d'un changement de mode HVAC.
- Envoi immediat de l'ouverture recalculee lors de ce changement.
- Maintien du filtrage par periode et par variation lorsque le mode ne change pas.

### Exclus

- Modification de l'algorithme TPI.
- Modification des thermostats sans regulation directe de vanne.
- Changement de la semantique de `sleep` sur les appareils sous-jacents.

## Impacts et risques

| Risque | Gravite | Probabilite | Mesure proposee |
| --- | --- | --- | --- |
| Commande immediate inattendue sur une vanne physique | Moyenne | Moyenne | Beta avec au moins un materiel Zigbee2MQTT represente par l'issue. |
| Regressions de cadence lors de changements HVAC repetes | Moyenne | Faible a moyenne | Exercicer des sequences rapides `heat/sleep/off` et verifier les appels de service. |
| Regresion sur les mises a jour de temperature sans changement HVAC | Moyenne | Faible | Le test de throttling ajoute couvre le chemin principal ; conserver ce test. |
| Surcharge de commandes lors d'une initialisation ou reprise | Faible a moyenne | Faible | Observer les logs et la frequence des commandes pendant la beta. |

## Alternatives examinees

| Alternative | Avantage | Inconvenient | Decision |
| --- | --- | --- | --- |
| Appeler `update_states(force=True)` uniquement autour de `sleep` | Correctif plus court | Couple la correction au chemin d'etat et ne dissocie pas calcul/envoi | Ecartee |
| Remettre `_valve_open_percent` a zero a `OFF` | Evite une partie du symptome | Ne force pas le recalcul immediat vers `sleep` ou `heat` | Ecartee |
| Memoriser les modes du dernier calcul et envoi | Couvre les transitions et preserve les garde-fous hors transition | Ajoute deux etats internes a verifier en beta | Retenue |

## Hypotheses, questions et criteres de passage

### Hypotheses verifiees par lecture

- La mise a jour du mode du dernier envoi intervient apres la commande des vannes, y compris lorsque le mode courant est `OFF`.
- Les tests etablissent un etat `HEAT` avant de verifier que deux mises a jour de temperature dans la periode restent filtrees.

### Questions ouvertes non bloquantes

- Le comportement sur les equipements reels lorsque plusieurs changements HVAC tres rapproches surviennent reste a observer.
- Les journaux publics ne donnent pas le detail de l'avertissement et de la notice du job CI reussi.

### Criteres de passage a la fusion

- Beta validee sur une installation utilisant des vannes directes, dont les transitions `heat -> sleep -> heat` et `sleep -> off -> heat`.
- Absence de commande parasite lors de mises a jour de temperature sans changement HVAC.
- Absence de chauffe residuelle, de `hvac_action: heating` ou de comptage actif apres le retour de `sleep` dans une piece deja chaude.

## Suite proposee

Publier une beta ciblee de la PR #2113, recueillir les traces de commandes et les etats de vanne sur les sequences ci-dessus, puis fusionner si les criteres de passage sont satisfaits. Aucun changement de code, de configuration ou d'etat Home Assistant n'a ete effectue pendant cette revue.