# Revue de l'issue #2075 - Régressions AC sur les VTherm

- **Référence :** [jmcollin78/versatile_thermostat#2075](https://github.com/jmcollin78/versatile_thermostat/issues/2075)
- **État vérifié :** ouverte, non assignée, étiquetée `bug` et `question`, sans jalon, relation ni pull request liée.
- **Branche indiquée par GitHub :** `2075-over_valve-thermostats-lose-heating-mode-when-ac-mode-is-enabled`.
- **Date de revue :** 2026-09-30.
- **Recommandation :** **retenir** comme correction de régressions AC coordonnées.

## 1. Résumé fidèle

L'issue #2075 signale qu'en version 10.4.0, un VTherm `over_valve` avec le mode AC activé n'expose plus `heat` : seuls `cool`, `sleep` et `off` sont disponibles. Les commentaires indiquent que le comportement persiste après l'essai de la préversion 10.5.beta.

Le signal complémentaire fourni pour cette revue concerne exclusivement les VTherm `over_climate` avec `AC Mode=True`, et non les `over_valve`. Le test de reproduction distingue désormais le calcul interne du contrat public : le VTherm sélectionne correctement la consigne `COOL` à 25 °C, mais `preset_temperatures` ne publie pas `eco_cool_temp`. La VTherm UI Card retombe alors sur `eco_temp` et résout 19 °C, la consigne `HEAT`, en plus de ne pas afficher la température de refroidissement attendue.

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
- La copie locale ignorée `config/www/community/versatile-thermostat-ui-card/versatile-thermostat-ui-card.js` cherche en mode refroidissement `${preset}_cool_temp` puis `${preset}_cool_away_temp`, avant de se replier sur les clés chauffage. Ce repli reproduit 19 °C au lieu de 25 °C.
- `tests/test_switch_ac.py` couvre les bonnes consignes AC pour `over_switch`.
- `tests/test_auto_regulation.py` couvre une régulation manuelle `COOL` pour `over_climate`, mais pas les préréglages, leurs attributs publiés ni la carte.
- Le test de reproduction ajouté à `tests/test_auto_regulation.py` prouve que la cible interne vaut 25 °C mais que le contrat public utilisé par la carte résout 19 °C.

### Historique Git vérifié

- Le commit `e095f54036365fca1cd6f7e5b4733d7b7cce568c` du 2026-09-17 (`1938 feature request implement sleep mode for vtherm over valve (#2063)`) a introduit la surcharge `ThermostatOverValve.build_hvac_list()` avec la branche AC `[COOL, SLEEP, OFF]`. `git blame` attribue directement la ligne fautive à ce commit.
- Le commit `27b0b364bae9315338a715257835248cab51647d` du 2025-11-09 (`Change custom_attributes structure. Tests ok`) a introduit la structure `preset_temperatures` avec uniquement les clés chauffage et absence. Les commits `7ea0b86220e322e5e36c50d4f19f5c90a291d267` puis `0ab8aca006c1a2b10bdba2fca39c11800dc3ebcc` ont conservé ce contrat incomplet.
- L'artefact local de la carte est ignoré par Git et ne contient ni version ni source map exploitable. Son commit d'introduction ne peut donc pas être attribué à partir de ce dépôt. Le fait établi est une incompatibilité de contrat devenue observable; l'antériorité exacte du lecteur de carte reste inconnue.

## 3. Analyse de pertinence

### Faits établis

1. La surcharge `over_valve` est incompatible avec le contrat AC de la classe de base et avec le besoin de l'issue : elle supprime systématiquement `HEAT`.
2. Sur un `over_climate` avec `AC Mode=True`, le moteur interne sélectionne correctement 25 °C en `COOL` dans le scénario discriminant `HEAT=19` / `COOL=25`.
3. Le défaut fonctionnel apparaît à la frontière publique : faute de clé `eco_cool_temp`, la résolution réellement effectuée par la carte retombe sur `eco_temp` et obtient 19 °C.
4. Le défaut de consigne et le défaut d'affichage ont donc la même cause démontrée : un contrat `preset_temperatures` incomplet pour le refroidissement.

### Recommandation

**Retenir.** Trois symptômes doivent être corrigés dans le même lot AC : `HEAT` indisponible sur `over_valve`, consigne `HEAT` résolue à tort en `COOL` pour `over_climate`, et températures `COOL` absentes de la VTherm UI Card. Les deux derniers proviennent du même contrat public incomplet.

## 4. Périmètre proposé

### Inclus

- Rétablir, pour `ThermostatOverValve` avec `ac_mode`, la liste de modes `HEAT`, `COOL`, `SLEEP`, `OFF`, en préservant le mode spécifique `SLEEP` de ce type.
- Étendre l'attribut public `preset_temperatures` des VTherm `over_climate` AC avec `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp` et leurs variantes `${preset}_cool_away_temp` lorsque la présence est configurée.
- Corriger la résolution publique qui retombe actuellement sur la consigne `HEAT` faute de clé `COOL`, sans modifier le calcul interne déjà correct.
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

3. **Publier les consignes COOL dans `preset_temperatures` en conservant les clés chauffage.**
   - Avantages : correctif local et rétrocompatible; les clés `${preset}_cool_temp` et `${preset}_cool_away_temp` correspondent au lecteur vérifié de la carte locale.
   - Inconvénient : la version réellement déployée de la carte doit encore être confirmée; retenue.

## 7. Hypothèses, décisions nécessaires et questions ouvertes

### Hypothèses à valider en spécification/conception

- La copie locale de la VTherm UI Card consomme `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp` et les variantes `${preset}_cool_away_temp`. La version déployée doit être confirmée avant validation finale.
- Le test discriminant a réfuté l'hypothèse d'un défaut du chemin nominal `find_preset_temp()` : la cible interne passe bien de 19 à 25 °C.
- `frost` n'a pas de variante AC, conformément aux constantes de préréglage et aux tests existants.
- `SLEEP` doit rester disponible pour `over_valve` en plus de `HEAT`, `COOL` et `OFF`.

### Questions ouvertes bloquantes

1. Quelle version et quel schéma d'attributs la VTherm UI Card déployée par les utilisateurs attend-elle pour les consignes AC ?
2. Quel commit ou quelle version de VTherm UI Card a introduit le lecteur avec repli COOL vers HEAT ? L'artefact local ignoré ne permet pas de répondre depuis ce dépôt.

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