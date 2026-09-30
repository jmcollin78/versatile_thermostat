# Revue PR 2080 - Auto TPI

## Reference et resume

- PR : https://github.com/jmcollin78/versatile_thermostat/pull/2080
- Titre : `fix: stop Auto TPI failure notifications when learning is disabled`
- Objet : ne plus executer la detection de pannes Auto TPI une fois que l'apprentissage est desactive, afin d'eviter des notifications repetitives apres un arret automatique.

## Sources verifiees

- Description, diff et commentaires de la PR (un commit, deux fichiers, +55 / -0).
- `custom_components/versatile_thermostat/auto_tpi_manager.py` : `_detect_failures`, `on_cycle_completed`, `start_learning` et `stop_learning`.
- `tests/test_auto_tpi.py` : nouveaux tests de regression et tests du cycle de vie de l'apprentissage.

## Constat et pertinence

Le probleme est reel : `on_cycle_completed` appelle `_detect_failures` meme lorsque `autolearn_enabled` est faux. Le garde ajoute par la PR supprime correctement les notifications repetitives pendant que l'apprentissage reste desactive.

Toutefois, la PR conserve aussi `consecutive_failures` lorsque l'apprentissage est desactive. Elle l'affirme dans le test de regression. Or une reprise avec `start_learning(reset_data=False)` ne remet pas ce compteur a zero. Apres un arret automatique a trois echecs, une reprise peut donc rester bloquee par `_should_learn()` ou se desactiver et notifier des le prochain cycle en echec.

## Recommandation

Demander une correction avant fusion : le garde doit empecher la detection et la notification lorsque l'apprentissage est inactif, sans rendre une reprise de session impossible. La solution la plus locale est de reinitialiser `consecutive_failures` lors du redemarrage de l'apprentissage, ou de clarifier et tester explicitement une autre semantique de reprise.

## Perimetre propose

Inclus : detection de pannes Auto TPI, compteur `consecutive_failures`, arret et reprise de l'apprentissage, notifications persistantes.

Exclus : algorithmes de calcul Kint/Kext, regulation des vannes, migrations et configuration Home Assistant.

## Impacts et risques

| Risque                                                | Gravite | Probabilite            | Detail                                                                                               |
| ----------------------------------------------------- | ------- | ---------------------- | ---------------------------------------------------------------------------------------------------- |
| Reprise Auto TPI inutilisable apres arret automatique | Moyenne | Moyenne                | Le compteur persiste a 3 avec `reset_data=False`; `_should_learn()` refuse alors tout apprentissage. |
| Nouvelle notification immediate apres reprise         | Moyenne | Moyenne                | Un cycle en echec incremente le compteur deja a 3 et desactive de nouveau l'apprentissage.           |
| Notifications repetitives pendant l'arret             | Corrige | Elevee avant correctif | Le retour anticipe couvre ce comportement.                                                           |

## Questions et criteres de passage

- La reprise sans remise a zero des donnees doit-elle conserver les echecs consecutifs ? Le comportement actuel de `_should_learn()` indique que non, car trois echecs bloquent l'apprentissage.
- Ajouter un test de reprise apres arret automatique : demarrer avec trois echecs, appeler `start_learning(reset_data=False)`, puis verifier qu'un cycle sain peut apprendre et qu'un unique nouvel echec ne redonne pas lieu a un arret immediat.
- Executer au minimum les tests Auto TPI cibles apres correction.