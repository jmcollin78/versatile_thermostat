# Revue de l'issue #2109 - Energie et gestionnaire de puissance

## Reference et resume fidele

- Issue : [#2109 - Capteur d'energie et gestionnaire de puissance](https://github.com/jmcollin78/versatile_thermostat/issues/2109), ouverte le 12 octobre 2026.
- Cette revue couvre uniquement le point 1.1 : le compteur d'energie d'un thermostat `over_switch` a plusieurs relais sous-estime l'energie d'un facteur egal au nombre de relais.
- Cas rapporte : `device_power = 5 000 W`, trois relais, puissance moyenne de cycle de `4 300 W`, cycle de cinq minutes. L'increment observe est `0,1194 kWh` au lieu de `0,3583 kWh`.

## Sources et elements verifies

- L'issue #2109 et l'issue historique [#877](https://github.com/jmcollin78/versatile_thermostat/issues/877).
- `custom_components/versatile_thermostat/thermostat_switch.py` : `incremente_energy()` divise la puissance moyenne par `nb_underlying_entities`.
- `custom_components/versatile_thermostat/cycle_scheduler.py` : `_on_master_cycle_end()` appelle `incremente_energy()` une unique fois par fin de cycle.
- `custom_components/versatile_thermostat/feature_power_manager.py` : `mean_cycle_power` est `device_power * on_percent` ; elle est donc deja la puissance moyenne totale du thermostat.
- `documentation/fr/base-attributes.md` : `device_power` doit etre la puissance totale lorsque plusieurs equipements sont controles.
- `tests/test_power.py` : le test existant encode la division par deux, mais appelle directement `incremente_energy()` ; il ne couvre pas l'integration ordonnanceur + plusieurs relais.
- La correction de #877 (commit `bcf570e`) ajoutait cette division pour un ancien modele dans lequel l'increment etait effectue par chaque relais.

## Analyse de pertinence et recommandation

**Recommandation : retenir le point 1.1 comme regression fonctionnelle, et supprimer la division par `nb_underlying_entities` dans `ThermostatOverSwitch.incremente_energy()`.**

La formule attendue pour un increment de cycle est :

`energie_ajoutee = mean_cycle_power * cycle_min / 60`

`mean_cycle_power` incorpore deja le total de `device_power`. Puisque l'ordonnanceur appelle l'increment une seule fois par cycle, toute nouvelle division par le nombre de relais produit necessairement un sous-comptage de ce facteur. Le calcul reproduit le cas signale : `4 300 * 5 / 60 / 3 = 119,4 Wh`, contre `358,3 Wh` sans division.

## Perimetre propose

Inclus :

- Supprimer la division dans le calcul d'energie `over_switch`.
- Mettre a jour les attentes du test existant d'energie multi-relais.
- Ajouter un test d'integration couvrant plusieurs relais, une puissance totale et un appel unique par fin de cycle.

Exclus :

- Le point 1.2 (rafale d'increments) et le point 2 (reservations du gestionnaire de puissance) de l'issue #2109.
- Toute correction retrospective des statistiques Home Assistant deja enregistrees.

## Impacts et risques

| Impact ou risque                                                         | Gravite | Probabilite | Traitement                                                           |
| ------------------------------------------------------------------------ | ------- | ----------- | -------------------------------------------------------------------- |
| Hausse du compteur d'energie pour les thermostats ayant plusieurs relais | Moyenne | Certaine    | C'est la correction attendue ; ne pas migrer les historiques.        |
| Regression future vers des increments par relais                         | Moyenne | Faible      | Test d'integration qui affirme un unique increment par cycle.        |
| Confusion sur la puissance configuree                                    | Moyenne | Moyenne     | Conserver la documentation : `device_power` est le total des relais. |
| Securite et confidentialite                                              | Nulle   | Nulle       | Aucun impact identifie.                                              |

## Alternatives examinees

| Alternative                             | Avantage                                                                                 | Inconvenient                                                            | Decision |
| --------------------------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------- |
| Retirer la division                     | Respecte le contrat actuel de l'ordonnanceur et la documentation de `device_power` total | Modifie les nouvelles valeurs exposees                                  | Retenue. |
| Appeler l'increment une fois par relais | Reproduit le modele historique de #877                                                   | Duplique des ecritures d'etat et complique l'ordonnanceur sans benefice | Ecartee. |
| Ajouter une option de compatibilite     | Preserverait le sous-comptage actuel                                                     | Valide un calcul incorrect et augmente la complexite                    | Ecartee. |

## Hypotheses, decisions et questions ouvertes

- Fait : l'ordonnanceur actuel ne fait qu'un appel d'increment par cycle.
- Fait : la division introduite pour #877 supposait un appel par entite sous-jacente, qui n'existe plus dans le chemin actuel.
- Hypothese a valider par test : aucune autre voie active ne declenche `incremente_energy()` une fois par relais pour `over_switch`.
- Decision requise : accepter le perimetre restreint au point 1.1 avant de specifier et concevoir la correction.

## Suite proposee et criteres de passage au developpement

Apres validation de ce rapport, produire une specification et une conception alignees couvrant les criteres suivants :

1. Avec deux ou plusieurs relais et une puissance totale configuree, l'increment vaut la puissance moyenne totale multipliee par la duree du cycle.
2. Avec un seul relais, le comportement reste inchange.
3. Le test passe par la fin de cycle de l'ordonnanceur et confirme un seul increment.
4. Les unites W/Wh et kW/kWh restent coherentes.

Le developpement ne doit commencer qu'apres validation explicite de la specification et de la conception.