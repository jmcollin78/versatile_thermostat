# Revue de l’issue #1348 — contrôle complet de l’ouverture pour `over_valve`

- **Référence :** [issue #1348](https://github.com/jmcollin78/versatile_thermostat/issues/1348)
- **État constaté :** ouverte ; libellés `enhancement` et `Vote needed` ; aucun assigné, jalon, branche ou pull request associé.
- **Date de revue :** 14 septembre 2026
- **Recommandation :** **retenir**, avec un portage complet et cohérent des quatre paramètres de contrôle d’ouverture déjà disponibles en régulation directe `over_climate`.

## 1. Résumé fidèle

L’issue demande d’ajouter à un thermostat de type `over_valve` :

- un seuil d’ouverture (`opening_threshold`) sous lequel la vanne est considérée fermée ;
- une ouverture minimale (`minimum_opening_degrees`) dès qu’un besoin de chauffage dépasse ce seuil.

La revue élargit explicitement cette demande au portage complet du contrôle de vanne : `max_closing_degree` et `max_opening_degrees` rejoignent `opening_threshold_degree` et `min_opening_degrees`. Cet élargissement vise à éviter deux implémentations fonctionnellement divergentes entre les modes de commande directe de vanne.

Le cas d’usage provient de la discussion [#1339](https://github.com/jmcollin78/versatile_thermostat/discussions/1339) : une vanne Plugwise Tom ne chauffe pas sous 20 %, tandis que l’algorithme TPI peut commander 19 %. La discussion précise que l’appareil ne fournit pas d’entité `climate`, seulement une entité `number` de position de vanne ; `over_valve` est donc le type adapté.

## 2. Sources et éléments vérifiés

### Sources GitHub

- [Issue #1348](https://github.com/jmcollin78/versatile_thermostat/issues/1348) : description, état, métadonnées et éléments de développement visibles.
- [Discussion #1339](https://github.com/jmcollin78/versatile_thermostat/discussions/1339) : besoin matériel, absence d’entité `climate`, contournement proposé et clarification sémantique de l’ouverture minimale.
- Aucun commentaire dans l’issue, relation, branche ou pull request n’est visible.

### Dépôt local (`main`)

- `custom_components/versatile_thermostat/thermostat_valve.py` : `ThermostatOverValve` calcule et conserve un pourcentage TPI entier de 0 à 100, puis le planificateur le transmet aux `UnderlyingValve`. Aucun seuil ou minimum d’ouverture n’est lu, appliqué ou exposé.
- `custom_components/versatile_thermostat/underlyings.py` : `UnderlyingValve` est utilisé par `over_valve`. `UnderlyingValveRegulation`, qui applique les paramètres recherchés, est une classe distincte.
- `custom_components/versatile_thermostat/thermostat_climate_valve.py` : `ThermostatOverClimateValve` est le seul consommateur de `opening_threshold_degree`, `min_opening_degrees`, `max_opening_degrees` et `max_closing_degree`.
- `custom_components/versatile_thermostat/config_schema.py` et `config_flow.py` : le schéma et les validations associés à ces paramètres existent seulement pour la configuration de régulation directe des vannes d’un `over_climate`.
- `custom_components/versatile_thermostat/opening_degree_algorithm.py` : le calcul réutilisable réalise l’interpolation ouverture minimale / ouverture maximale et le repli sous le seuil.
- `documentation/en/over-valve.md` : confirme que `over_valve` est prévu lorsqu’aucune entité `climate` n’existe et commande directement des entités `number`.
- `documentation/en/self-regulation.md` et `documentation/en/releases.md` : documentent les paramètres pour `over_climate` avec contrôle direct de vanne, pas pour `over_valve`.
- `tests/test_overclimate_valve.py` : couvre l’algorithme de seuil et d’ouverture minimale ; aucune occurrence de ces paramètres n’a été trouvée dans les tests `over_valve`.

## 3. Analyse de pertinence

### Faits

1. Le besoin est cohérent avec l’objectif de `over_valve` : commander une vanne par son pourcentage d’ouverture lorsqu’il n’existe pas d’entité `climate`.
2. Le mécanisme demandé est déjà disponible pour une autre architecture : `over_climate` avec régulation directe de vanne.
3. Cette disponibilité ne couvre pas l’issue : le type `over_valve` ne propose pas les champs de configuration et commande actuellement directement la valeur TPI calculée.
4. Le contournement proposé dans la discussion (fausse entité `climate`, puis `over_climate` avec contrôle direct) implique une configuration artificielle et ne répond pas nativement au cas sans entité `climate`.

### Conclusion

L’issue n’est **pas déjà résolue**. Elle correspond à une évolution de `ThermostatOverValve`, dont la faisabilité est élevée car l’algorithme de conversion des commandes brutes existe déjà. Le portage des quatre paramètres est préférable à un ajout partiel : il garantit un comportement homogène des deux variantes de commande directe de vanne et limite les évolutions ultérieures incompatibles.

## 4. Périmètre proposé

### Inclus

- Ajouter à `over_valve` les quatre options de contrôle : `opening_threshold_degree`, `min_opening_degrees`, `max_closing_degree` et `max_opening_degrees`.
- Adopter les mêmes sémantiques que `over_climate` avec régulation directe de vanne :
   - `opening_threshold_degree` et `max_closing_degree` sont des réglages communs au thermostat ;
   - `min_opening_degrees` et `max_opening_degrees` sont des listes, une valeur par vanne sous-jacente, avec les mêmes valeurs par défaut et règles d’alignement que `over_climate`.
- Transformer le pourcentage TPI brut en commande de vanne effective :
   - besoin brut inférieur au seuil : ouverture égale à $100 - max\_closing\_degree$ ;
   - besoin brut supérieur ou égal au seuil et non nul : commande comprise entre l’ouverture minimale et l’ouverture maximale de la vanne concernée, avec interpolation linéaire ;
   - à 100 % de besoin brut : commande égale à l’ouverture maximale configurée.
- Mutualiser impérativement le calcul et ses règles de validation entre `over_valve` et `over_climate` : aucune copie ou variante locale de la formule ne doit être introduite. Le calcul existant doit devenir ou rester le point unique de conversion d’une demande TPI brute en commande effective.
- Préserver le comportement existant par défaut : seuil à 0, ouverture minimale à 0, fermeture maximale à 100 et ouverture maximale à 100 donnent exactement les commandes actuelles.
- Ajouter validations de configuration, attributs de diagnostic, tests unitaires/intégration et documentation utilisateur dans les langues maintenues selon les conventions du dépôt.

### Exclu

- Modifier le comportement de `over_climate` avec régulation directe de vanne.
- Rendre une entité `climate` obligatoire ou conserver le contournement par faux thermostat.
- Ajouter une prise en charge spécifique du modèle Plugwise : le comportement doit rester générique pour les entités `number` compatibles.
- Modifier dans cette issue la représentation persistée des listes : les valeurs restent stockées sous la forme compatible actuelle, séparée par des virgules.

## 5. Impacts et risques

| Domaine                    | Impact / risque                                                                                          | Gravité | Probabilité | Mesure proposée                                                                                               |
| -------------------------- | -------------------------------------------------------------------------------------------------------- | ------- | ----------- | ------------------------------------------------------------------------------------------------------------- |
| Fonctionnel                | Un seuil mal réglé peut créer une zone sans chauffage ou une surchauffe ponctuelle.                      | Moyenne | Moyenne     | Valeurs par défaut neutres, explications et tests des limites.                                                |
| Compatibilité              | Une erreur de transformation peut changer des installations `over_valve` existantes.                     | Élevée  | Faible      | Préserver strictement le résultat avec la configuration par défaut et le prouver par tests de non-régression. |
| Multi-vannes               | Une liste de minima ou maxima mal alignée peut appliquer une valeur à la mauvaise vanne.                 | Moyenne | Faible      | Réutiliser strictement les validations de cardinalité, bornes et cohérence min < max du flux `over_climate`.  |
| Exploitation               | L’attribut TPI brut peut différer de la commande réellement envoyée, ce qui peut dérouter le diagnostic. | Faible  | Élevée      | Exposer clairement valeur brute et valeur commandée / paramètres actifs.                                      |
| Sécurité / confidentialité | Aucun accès, secret ou donnée personnelle supplémentaire.                                                | Faible  | Faible      | Aucun traitement spécifique requis.                                                                           |
| Énergie / confort          | Les ouvertures minimale, maximale et la fermeture limitée modifient débit et consommation.               | Moyenne | Moyenne     | Paramètres opt-in, configuration documentée selon les contraintes physiques réellement mesurées.              |
| Maintenabilité             | Deux implémentations du calcul pourraient diverger à la prochaine évolution.                             | Élevée  | Moyenne     | Un point de calcul et de validation partagé, couvert par les mêmes tests de table.                            |

## 6. Alternatives examinées

1. **Utiliser `over_climate` avec contrôle direct de vanne et une fausse entité `climate`.**
   - Avantage : fonctionnalité disponible aujourd’hui.
   - Inconvénients : contournement complexe, entités factices et contradiction avec le cas d’usage sans entité `climate`.

2. **Régler uniquement les coefficients/seuils TPI.**
   - Avantage : aucun développement.
   - Inconvénient : ne garantit pas qu’une commande positive atteigne le seuil physique de chauffage de la vanne.

3. **Étendre `over_valve` avec les quatre paramètres déjà disponibles pour `over_climate`.**
   - Avantages : répond nativement au besoin, assure une parité fonctionnelle, réutilise un calcul éprouvé et évite une évolution ultérieure partielle.
   - Inconvénient : nécessite de définir précisément les attributs de diagnostic et la règle de répartition des listes multi-vannes.

## 7. Hypothèses, décisions et questions ouvertes

### Hypothèses

- Les quatre paramètres sont exprimés dans l’échelle normalisée 0–100, comme l’implémentation existante.
- La valeur calculée par TPI reste la valeur brute ; la commande envoyée est la valeur adaptée.
- `max_closing_degree` conserve le nom et la sémantique existants, au singulier : c’est un réglage commun, et non une liste `max_closing_degrees` par vanne.

### Décisions nécessaires

1. Entériner le portage des quatre paramètres avec les noms et sémantiques existants : `max_closing_degree` (singulier) est commun, `min_opening_degrees` et `max_opening_degrees` sont des listes par vanne.
2. Définir les attributs de diagnostic : recommandation de conserver `valve_open_percent` comme pourcentage TPI brut et d’exposer les commandes adaptées par vanne.

### Questions ouvertes non bloquantes

- Les traductions utilisateur de l’interface doivent-elles être mises à jour dans toutes les langues publiées au même changement ? La convention précise reste à vérifier lors de la spécification.
- Faut-il offrir une migration d’options ? Aucune option `over_valve` équivalente n’existe actuellement ; une migration de données ne semble donc pas nécessaire.
- Une évolution ultérieure peut remplacer la saisie textuelle séparée par des virgules par de véritables champs de liste dans l’interface. Elle est explicitement exclue de cette issue pour préserver la parité, réduire le risque de migration et éviter de mélanger amélioration d’UX et évolution fonctionnelle.

## 8. Critères de passage au développement

Le développement pourra démarrer après :

1. validation explicite de ce rapport et du périmètre par le demandeur ;
2. spécification fonctionnelle approuvée, incluant les quatre paramètres, valeurs par défaut, comportements aux seuils et multi-vannes ;
3. conception technique approuvée, imposant un calcul et des validations mutualisés, ainsi que les attributs de diagnostic ;
4. définition de tests couvrant le cas Plugwise représentatif (seuil à 20 %), les bornes 0/100, les quatre paramètres, plusieurs vannes et la non-régression par défaut ;
5. documentation de configuration validée.

## 9. Suite proposée

Sous validation de ce rapport, produire une spécification fonctionnelle puis une conception technique convergentes. Aucun code, configuration, dépendance ou environnement Home Assistant n’a été modifié pendant cette revue.
