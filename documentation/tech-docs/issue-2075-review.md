# Revue de l'issue #2075 - Régressions AC sur les VTherm

- **Référence :** [jmcollin78/versatile_thermostat#2075](https://github.com/jmcollin78/versatile_thermostat/issues/2075)
- **État vérifié :** ouverte, non assignée, étiquetée `bug` et `question`, sans jalon, relation ni pull request liée.
- **Branche indiquée par GitHub :** `2075-over_valve-thermostats-lose-heating-mode-when-ac-mode-is-enabled`.
- **Date de revue :** 2026-09-30.
- **Recommandation :** **retenir** comme correction de régressions AC coordonnées.

## 1. Résumé fidèle

L'issue #2075 signale qu'en version 10.4.0, un VTherm `over_valve` avec le mode AC activé n'expose plus `heat` : seuls `cool`, `sleep` et `off` sont disponibles. Les commentaires indiquent que le comportement persiste après l'essai de la préversion 10.5.beta.

Le signal complémentaire fourni pour cette revue concerne exclusivement les VTherm `over_climate` avec `AC Mode=True`, et non les `over_valve`. Il comporte deux symptômes : en mode `COOL`, le VTherm applique réellement la consigne du mode `HEAT` au lieu de la consigne de refroidissement; en outre, la VTherm UI Card n'affiche plus les températures de refroidissement. Le premier symptôme est donc une régression fonctionnelle du thermostat, indépendante du seul affichage.

## 2. Sources et éléments vérifiés

### Sources GitHub

- Issue #2075 : description, configuration, diagnostic proposé, commentaires et métadonnées consultés le 2026-09-30.
- Les utilisateurs concernés signalent que `heat` reste indisponible après la préversion proposée.
- Signal complémentaire du mainteneur : sur un VTherm `over_climate` avec `AC Mode=True`, la consigne effective en `COOL` est celle de `HEAT`; la VTherm UI Card omet également les températures `COOL`.

### Dépôt local

- `custom_components/versatile_thermostat/thermostat_valve.py` surcharge `build_hvac_list()` et retourne `COOL`, `SLEEP`, `OFF` lorsque `ac_mode` est actif. Cette liste exclut directement `HEAT`.
- `custom_components/versatile_thermostat/base_thermostat.py` définit le comportement commun AC attendu : `HEAT`, `COOL`, `OFF`.
- `custom_components/versatile_thermostat/base_thermostat.py` sélectionne les préréglages suffixés `_ac` lorsque le mode courant ou demandé est `COOL`. Le moteur de calcul de consigne possède donc la distinction chauffage/refroidissement nécessaire.
- `custom_components/versatile_thermostat/number.py` crée bien les entités `number` de préréglages AC pour tout VTherm avec `ac_mode`.
- `custom_components/versatile_thermostat/base_thermostat.py` publie l'attribut `preset_temperatures` consommable par les interfaces, mais ne contient que les clés chauffage (`frost_temp`, `eco_temp`, `comfort_temp`, `boost_temp`) et absence. Les clés `_ac` et `_ac_away` sont absentes.
- `tests/test_switch_ac.py` couvre les bonnes consignes AC pour `over_switch`.
- `tests/test_auto_regulation.py` couvre une régulation manuelle `COOL` pour `over_climate`, mais pas les préréglages, leurs attributs publiés ni la carte.
- Aucun test ne couvre les températures AC publiées dans `preset_temperatures`.

## 3. Analyse de pertinence

### Faits établis

1. La surcharge `over_valve` est incompatible avec le contrat AC de la classe de base et avec le besoin de l'issue : elle supprime systématiquement `HEAT`.
2. Sur un `over_climate` avec `AC Mode=True`, le comportement observé en `COOL` applique la consigne `HEAT` au lieu de la consigne AC. Il s'agit d'un défaut fonctionnel, pas seulement d'une erreur de présentation.
3. Le code de `find_preset_temp()` contient une branche destinée à sélectionner les préréglages suffixés `_ac` en `COOL`. Le comportement observé indique que cette branche n'est pas atteinte au bon moment, que l'état HVAC utilisé est incohérent, ou que la consigne est recalculée/écrasée ensuite. La cause exacte reste à établir par un test de reproduction ciblé.
4. Les valeurs AC ne sont pas exposées dans l'attribut `preset_temperatures`. Une UI qui s'appuie sur cet attribut ne peut ni les afficher ni les distinguer des consignes chauffage; ce défaut d'interface est distinct de la mauvaise consigne effective.

### Recommandation

**Retenir.** Trois symptômes doivent être corrigés dans le même lot AC : `HEAT` indisponible sur `over_valve`, consigne `HEAT` appliquée à tort en `COOL` sur `over_climate`, et températures `COOL` absentes de la VTherm UI Card. Les deux derniers concernent le même type de VTherm mais deux contrats différents : le fonctionnement du thermostat et les données publiées à l'interface.

## 4. Périmètre proposé

### Inclus

- Rétablir, pour `ThermostatOverValve` avec `ac_mode`, la liste de modes `HEAT`, `COOL`, `SLEEP`, `OFF`, en préservant le mode spécifique `SLEEP` de ce type.
- Étendre l'attribut public `preset_temperatures` avec les températures `eco_ac`, `comfort_ac`, `boost_ac`, ainsi que leurs variantes absence lorsque la présence est configurée, pour les VTherm `over_climate`. Les clés et leur convention de nommage devront être compatibles avec la VTherm UI Card.
- Identifier et corriger, pour `over_climate`, le chemin qui applique actuellement une consigne `HEAT` lors du passage en `COOL` ou de la sélection d'un préréglage en `COOL`.
- Vérifier que le passage `COOL ->` préréglage et le retour `HEAT ->` même préréglage sélectionnent chacun la bonne table de consignes, sans écrasement ultérieur.
- Ajouter les tests ciblés : modes HVAC `over_valve` AC, consignes et attributs AC `over_climate`, contenu de `preset_temperatures` et cas présence si l'attribut l'expose.
- Mettre à jour la documentation de contrat de l'UI Card uniquement si le nom des clés AC doit être documenté ou si une incompatibilité de version est identifiée.

### Exclus

- Modification des algorithmes de régulation, de la communication avec les climatiseurs sous-jacents ou des nombres de configuration AC.
- Modification de la logique `SLEEP` au-delà de la conservation du mode déjà prévu pour `over_valve`.
- Changement de la configuration existante des utilisateurs ou migration de config entries.
- Correction du code de la VTherm UI Card dans ce dépôt : son code source n'a pas été fourni ni trouvé dans l'espace de travail.

## 5. Impacts et risques

| Domaine       | Risque                                                                                                | Gravité | Probabilité | Mesure proposée                                                                              |
| ------------- | ----------------------------------------------------------------------------------------------------- | ------- | ----------- | -------------------------------------------------------------------------------------------- |
| Fonctionnel   | `over_valve` AC reste incapable de chauffer.                                                          | Élevée  | Élevée      | Vérifier la liste ordonnée des quatre modes et l'acceptation de `HEAT`.                      |
| Fonctionnel   | Un `over_climate` en `COOL` applique la consigne `HEAT`, entraînant une régulation incorrecte.        | Élevée  | Élevée      | Reproduire la transition avec des valeurs distinctes et vérifier la consigne effective.      |
| Interface     | La carte continue d'afficher une valeur chauffage ou aucune valeur en `COOL`.                         | Élevée  | Élevée      | Tester les attributs exacts attendus par la carte avec valeurs chaleur/froid distinctes.     |
| Compatibilité | Un changement de nom de clé AC ne serait pas lu par la version déployée de la carte.                  | Moyenne | Moyenne     | Confirmer le contrat de clé de la carte avant implémentation; conserver les clés existantes. |
| Régression    | La présence ou les modes transitoires (`OFF`, `FAN_ONLY`, `DRY`) sélectionnent une mauvaise table AC. | Moyenne | Faible      | Couvrir au minimum `COOL`, puis conserver les règles existantes pour les modes transitoires. |
| Exploitation  | Les utilisateurs peuvent appliquer une préversion sans correction complète.                           | Moyenne | Élevée      | Associer les tests de non-régression au correctif et communiquer la version corrigée.        |

**Sécurité et confidentialité :** aucun nouvel accès, secret, stockage ou flux de données n'est impliqué.

## 6. Alternatives examinées

1. **Supprimer la surcharge `build_hvac_list()` de `over_valve`.**
   - Avantage : réutilise le comportement AC commun.
   - Inconvénient : supprimerait aussi le mode `SLEEP` propre à `over_valve`; écartée au profit d'une liste explicite complète.

2. **Faire déduire à la carte les consignes AC depuis les entités `number`.**
   - Avantage : les valeurs existent déjà.
   - Inconvénient : rompt le contrat d'attributs centralisé, augmente les lectures côté interface et ne corrige pas les autres consommateurs; écartée.

3. **Publier les consignes AC dans `preset_temperatures` en conservant les clés chauffage.**
   - Avantages : correctif local, rétrocompatible et cohérent avec les noms des entités `number` (`eco_ac`, `comfort_ac`, `boost_ac`).
   - Inconvénient : exige de confirmer le schéma exact attendu par la carte; retenue sous cette condition.

## 7. Hypothèses, décisions nécessaires et questions ouvertes

### Hypothèses à valider en spécification/conception

- La VTherm UI Card attend ou peut consommer des clés nommées `eco_ac_temp`, `comfort_ac_temp`, `boost_ac_temp` et, si applicable, `eco_ac_away_temp`, `comfort_ac_away_temp`, `boost_ac_away_temp`. Cette convention doit être vérifiée dans le dépôt de la carte ou auprès de son mainteneur avant de figer l'interface.
- La mauvaise consigne effective peut provenir de l'ordre de mise à jour entre mode HVAC, préréglage et température, ou d'un écrasement après `find_preset_temp()`; cette hypothèse doit être départagée par un test reproduisant une transition `HEAT -> COOL` avec des consignes volontairement distinctes.
- `frost` n'a pas de variante AC, conformément aux constantes de préréglage et aux tests existants.
- `SLEEP` doit rester disponible pour `over_valve` en plus de `HEAT`, `COOL` et `OFF`.

### Questions ouvertes bloquantes

1. Quelle version et quel schéma d'attributs la VTherm UI Card déployée par les utilisateurs attend-elle pour les consignes AC ?
2. À quelle transition précise la consigne `COOL` est-elle remplacée par celle de `HEAT` : changement de mode HVAC, sélection/réapplication du préréglage, restauration au démarrage ou rafraîchissement des entités `number` ? Cette question concerne la cause technique, le défaut fonctionnel étant confirmé.

## 8. Suite proposée et critères de passage au développement

1. Obtenir l'approbation explicite de ce rapport et la décision sur les deux questions ouvertes, en particulier le contrat de la carte.
2. Rédiger la spécification fonctionnelle décrivant les modes `over_valve` AC et le schéma complet des consignes publiées.
3. Produire une conception technique localisant les changements et les tests, sans modifier les algorithmes de régulation.
4. Faire converger spécification et conception, puis obtenir l'autorisation explicite de développement.
5. Le développement devra satisfaire au minimum les critères d'acceptation suivants :
   - un `over_valve` avec `ac_mode=True` expose et accepte `HEAT`, `COOL`, `SLEEP` et `OFF`;
   - un `over_climate` avec `ac_mode=True` expose et applique effectivement les consignes `_ac` en `COOL`, puis les consignes sans suffixe en `HEAT`, avec des valeurs de test distinctes;
   - la consigne correcte reste appliquée après changement de mode, sélection ou réapplication d'un préréglage et mise à jour des nombres de température;
   - l'attribut public de températures expose les consignes AC et, lorsque configurées, les consignes AC d'absence avec des valeurs distinctes vérifiables;
   - la VTherm UI Card affiche les consignes de refroidissement attendues avec sa version compatible;
   - les scénarios chauffage existants et les entités `number` existantes restent inchangés.

Aucun code, configuration, dépendance ou état Home Assistant n'a été modifié durant cette revue.