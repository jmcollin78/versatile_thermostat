# Revue de l'issue #2127

**Statut :** correction realisee et validee par tests cibles
**Issue :** [#2127 - Restored off state always becomes hvac_off_manual](https://github.com/jmcollin78/versatile_thermostat/issues/2127)
**Depot examine :** `jmcollin78/versatile_thermostat`, copie locale du depot
**Date de revue :** 2026-10-18

## Resume fidele

L'issue signalee par @rekinet constate qu'un VTherm restaure a l'etat `off` recoit systematiquement `hvac_off_reason: hvac_off_manual`, meme lorsque l'arret venait d'une fonctionnalite automatique. Le cas rapporte concerne des VTherm `over_climate` pilotant des vannes Netatmo exposees via HomeKit, dont les entites sous-jacentes ne proposent que `heat`.

Lorsqu'une vanne est indisponible pendant le demarrage ou le rechargement de l'integration, le VTherm peut ne jamais devenir pret. Son instantane `off`, sans raison d'arret, est alors persiste. Au demarrage suivant, la restauration le transforme en arret manuel. Une piece precedemment en chauffe peut donc rester arretee jusqu'a une action manuelle, sans que cet etat puisse etre distingue d'un veritable arret utilisateur.

L'auteur propose de restaurer la raison depuis `specific_states` en priorite, avec repli sur la racine pour les anciens etats persistes.

## Sources et elements verifies

- L'issue est ouverte, sans commentaire, etiquette, assignation, jalon, branche ni pull request associee au moment de la revue.
- L'issue indique la version 10.5.1 et precise que le meme code etait present sur `main` au commit `e625ae5` cite par le rapporteur. L'execution du cas materiel n'a pas ete reproduite dans cette revue.
- [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) restaure actuellement `_hvac_off_reason` depuis la racine des attributs dans `get_my_previous_state()`.
- La meme methode lit ensuite `specific_states` pour `hvac_mode_reason` et `total_energy`, et utilise deja un repli a la racine pour l'energie legacy.
- Si le VTherm est eteint et qu'aucune raison n'a ete restauree, cette methode definit ensuite la raison `hvac_off_manual`.
- [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) publie `hvac_off_reason` dans `specific_states`, ce qui confirme l'incoherence entre ecriture et lecture.
- [test_state_manager.py](../../tests/test_state_manager.py) couvre la restauration de `total_energy` depuis `specific_states` et depuis la racine, mais ne couvre pas la restauration de `hvac_off_reason` depuis ces deux formats.

## Pertinence et recommandation

### Recommandation : retenir et corriger

La cause racine est localisee et reproductible par construction : un attribut ecrit dans `specific_states` est lu a la racine. Le mecanisme de valeur par defaut transforme ensuite cette absence de lecture en une information metier fausse.

Le correctif est de faible ampleur, cible un unique chemin de restauration et suit le modele de retrocompatibilite deja applique a l'energie. Il preserve les anciens etats qui auraient stocke la raison a la racine tout en restaurant correctement les etats actuellement publies.

## Perimetre propose

### Inclus

- Restaurer `hvac_off_reason` depuis `specific_states` lorsqu'il y est present.
- Utiliser la valeur racine uniquement comme repli pour les etats legacy.
- Conserver la regle actuelle qui attribue `hvac_off_manual` seulement lorsqu'un VTherm restaure eteint ne possede reellement aucune raison.
- Ajouter des tests de restauration pour la valeur dans `specific_states`, pour le format legacy a la racine, et pour l'absence de valeur qui doit conserver le comportement manuel actuel.

### Exclus

- Changer la creation ou la persistance de l'instantane d'un VTherm jamais pret.
- Requalifier l'etat `off` produit pendant l'indisponibilite d'une entite sous-jacente.
- Modifier les regles de disponibilite, d'initialisation ou de reprise des vannes Netatmo/HomeKit.
- Modifier les autres raisons d'arret ou la priorite fonctionnelle entre les managers.

## Impacts et risques

| Risque                                                                         | Gravite | Probabilite                                                       | Mesure proposee                                                                                                 |
| ------------------------------------------------------------------------------ | ------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Un motif automatique est perdu et transforme en arret manuel apres redemarrage | Haute   | Moyenne sur les VTherm subissant une indisponibilite au demarrage | Restaurer en priorite `specific_states` et ajouter un test de non-regression.                                   |
| Un ancien etat persiste a la racine n'est plus relu                            | Moyenne | Faible                                                            | Conserver explicitement le repli a la racine et le couvrir par un test.                                         |
| L'absence reelle de raison ne produit plus l'arret manuel attendu              | Moyenne | Faible                                                            | Conserver la valeur par defaut existante et tester ce cas.                                                      |
| L'instantane d'un VTherm non initialise reste ambigu                           | Moyenne | Moyenne                                                           | Hors perimetre de ce correctif ; traiter dans une issue distincte si une semantique supplementaire est requise. |

## Alternatives examinees

| Alternative                                    | Avantage                                                            | Inconvenient                                                                                 | Decision |
| ---------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | -------- |
| Lire `specific_states` puis la racine          | Corrige la cause et preserve la compatibilite avec les etats legacy | Necessite des tests de priorite et de repli                                                  | Retenue  |
| Ecrire aussi la raison a la racine             | Peut satisfaire le lecteur actuel                                   | Duplique le schema publie et ne corrige pas les etats deja persistes                         | Ecartee  |
| Ne plus attribuer `hvac_off_manual` par defaut | Evite le faux motif manuel                                          | Change la semantique des vrais arrets sans motif et ne restaure pas l'information disponible | Ecartee  |
| Traiter aussi les instantanes non initialises  | Pourrait eviter le scenario initial complet                         | Elargit le besoin vers les etats de disponibilite et demande une decision metier             | Reportee |

## Hypotheses, decisions et questions ouvertes

### Hypotheses verifiees

- `specific_states` est le format courant de publication de `hvac_off_reason`.
- Le repli legacy a la racine est un patron deja employe dans le meme bloc de restauration pour `total_energy`.
- Le defaut `hvac_off_manual` est applique apres la restauration, donc il masque directement toute absence de lecture de la raison.

### Decisions necessaires

- Valider que le correctif reste limite a la restauration de `hvac_off_reason` et ne tente pas de donner une nouvelle semantique aux instantanes non initialises.

### Questions ouvertes non bloquantes

- Aucun exemple d'etat legacy contenant reellement `hvac_off_reason` a la racine n'est fourni dans l'issue ; le repli conserve cette compatibilite par precaution.
- L'issue ne precise pas si d'autres attributs de `specific_states` presentent une incoherence comparable. Une inspection plus large n'est pas necessaire pour cette correction ciblee, mais peut etre menee separement.

## Criteres de passage au developpement

- Un test demontre qu'un VTherm `off` restaure avec une raison dans `specific_states` conserve exactement cette raison et ne devient pas manuel.
- Un test demontre qu'un etat legacy avec la raison a la racine reste restaure.
- Un test demontre qu'un VTherm `off` sans raison continue de recevoir `hvac_off_manual`.
- Les tests existants de restauration d'etat continuent de passer.
- Aucun changement de schema de publication ni de logique d'initialisation des entites sous-jacentes n'est introduit.

## Realisation et validation

La restauration lit maintenant `hvac_off_reason` depuis `specific_states` avant de se replier sur la racine legacy. Un test parametre couvre la priorite du format courant, le repli legacy et l'absence reelle de raison qui doit conserver `hvac_off_manual`.

La commande `pytest tests/test_state_manager.py -k test_vtherm_restore_hvac_off_reason` a reussi : 3 tests passes. Aucun changement de configuration, de dependance ou d'etat Home Assistant n'a ete effectue.