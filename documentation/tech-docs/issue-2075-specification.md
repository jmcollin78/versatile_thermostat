# Spécification fonctionnelle bilingue / Bilingual Functional Specification

## Version française

### 1. Titre et métadonnées

- **Nom :** Issue GitHub #2075 — cohérence du mode AC pour `over_valve`, `over_climate` et la VTherm UI Card
- **Version :** 1.1
- **Statut :** proposée pour conception et validation
- **Date :** 2026-09-30
- **Propriétaire :** à désigner
- **Rapport de référence :** [issue-2075-review.md](issue-2075-review.md)
- **Issue :** [jmcollin78/versatile_thermostat#2075](https://github.com/jmcollin78/versatile_thermostat/issues/2075)
- **Fichiers et symboles vérifiés dans le rapport :** `thermostat_valve.py` / `build_hvac_list()`, `base_thermostat.py` / comportement AC, `base_thermostat.py` / `find_preset_temp()` et attribut `preset_temperatures`, `number.py` / nombres de presets AC, `tests/test_switch_ac.py` et `tests/test_auto_regulation.py`.

### 2. Contexte et objectifs

Le rapport de revue regroupe trois symptômes liés au contrat AC des VTherm, mais qui doivent rester vérifiables séparément :

1. **`over_valve` avec AC Mode :** le mode `HEAT` disparaît de `hvac_modes`, alors que `COOL` reste disponible.
2. **`over_climate` avec AC Mode :** le moteur interne sélectionne correctement `COOL = 25,0 °C` après `HEAT = 19,0 °C`, mais l’attribut public `preset_temperatures` n’expose pas `eco_cool_temp`. La carte retombe alors sur `eco_temp` et résout publiquement 19,0 °C.
3. **VTherm UI Card :** les températures `COOL` ne sont pas exposées sous les clés attendues et ne sont donc pas affichées correctement.

L’objectif est de rétablir un contrat observable et cohérent entre le mode HVAC sélectionné, la consigne effective publiée et les données de presets exposées aux interfaces. La correction doit préserver les fonctions existantes, notamment le mode `SLEEP` propre à `over_valve`, les entités de nombres AC et la compatibilité avec les modes transitoires existants.

Les exemples de cette spécification utilisent volontairement des valeurs distinctes : `HEAT = 19,0 °C` et `COOL = 25,0 °C`. Une valeur publique résolue ou affichée de `19,0 °C` en `COOL` constitue donc un échec observable ; la cible interne de `25,0 °C` et la commande régulée restent vérifiables séparément.

La mise en œuvre de production est limitée à deux points : `ThermostatOverValve.build_hvac_list()` pour les modes `over_valve`, et `BaseThermostat.update_custom_attributes()` pour le contrat `preset_temperatures` des `over_climate` AC. Aucun changement n'est requis dans `find_preset_temp()` ni dans le moteur interne de régulation : la preuve runtime établit que la cible COOL vaut déjà `25,0 °C`. Le défaut de `over_climate` se situe dans les clés publiques manquantes et le fallback de lecture de la carte vers `eco_temp`.

### 3. Acteurs et cas d’utilisation

#### Acteurs

- **Utilisateur ou automatisation :** sélectionne un mode HVAC, un preset ou une valeur de température.
- **VTherm `over_valve` :** expose la liste des modes et accepte les transitions HVAC.
- **VTherm `over_climate` :** calcule la consigne correspondant au mode HVAC actif et expose les données publiques nécessaires à sa lecture.
- **Climat sous-jacent :** reçoit la consigne effective d’un `over_climate`.
- **Entités `number` de température :** fournissent les valeurs des presets chauffage, refroidissement et absence lorsqu’elles sont configurées.
- **VTherm UI Card :** consomme les données publiques de températures de presets et affiche les valeurs COOL.

#### Préconditions communes

- Le VTherm est configuré avec `AC Mode=True`.
- Les entités nécessaires sont disponibles, sauf dans les scénarios d’indisponibilité explicitement testés.
- Les valeurs d’exemple sont distinctes : `HEAT = 19,0 °C`, `COOL = 25,0 °C`, `HEAT absence = 16,0 °C`, `COOL absence = 29,0 °C`.

#### Cas d’utilisation UC-001 — Choisir un mode sur `over_valve`

1. L’utilisateur ouvre les modes HVAC d’un `over_valve` avec AC activé.
2. Le système expose `HEAT`, `COOL`, `SLEEP` et `OFF`.
3. L’utilisateur sélectionne `HEAT` ou `COOL` ; le VTherm accepte la transition et publie le mode sélectionné.

#### Cas d’utilisation UC-002 — Réguler un `over_climate` en `COOL`

1. Le VTherm est en `HEAT` avec une consigne effective de `19,0 °C`.
2. L’utilisateur sélectionne `COOL`.
3. Le moteur sélectionne la consigne fonctionnelle COOL correspondante, par exemple `25,0 °C`, et la régulation existante produit la commande COOL correspondante.
4. L’attribut public `preset_temperatures` expose la clé COOL attendue, afin que la carte ne retombe pas sur `eco_temp` à `19,0 °C`.

#### Cas d’utilisation UC-003 — Changer de mode et de preset

1. L’utilisateur change `HEAT` en `COOL`, sélectionne un preset, le réapplique ou modifie un nombre de température.
2. À chaque étape, la consigne effective et publiée suit le mode HVAC courant.
3. Un retour en `HEAT` sélectionne de nouveau la table chauffage, par exemple `19,0 °C`, sans conserver `25,0 °C` par erreur.

#### Cas d’utilisation UC-004 — Consulter les températures dans la carte

1. La carte lit l’état et les attributs publics du VTherm.
2. Elle reçoit les valeurs COOL attendues dans le schéma compatible avec sa version.
3. Elle affiche les températures de refroidissement distinctes des températures de chauffage, y compris les variantes d’absence lorsqu’elles sont configurées.

### 4. Exigences fonctionnelles

- **FR-001 — Modes `over_valve`.** Avec AC activé, le système doit exposer et accepter `HEAT`, `COOL`, `SLEEP` et `OFF` pour un VTherm `over_valve`.
- **FR-002 — Conservation de `SLEEP`.** La correction ne doit pas supprimer ni redéfinir le mode `SLEEP` spécifique à `over_valve`.
- **FR-003 — Sélection par mode.** Pour un `over_climate` avec AC activé, le système doit sélectionner la table de consignes correspondant au mode HVAC courant : consignes chauffage en `HEAT` et consignes refroidissement en `COOL`.
- **FR-004 — Cible fonctionnelle.** En `COOL`, la cible fonctionnelle interne doit être une consigne COOL. Avec les valeurs d’exemple, elle doit être `25,0 °C` et non `19,0 °C`.
- **FR-005 — Consigne régulée.** La commande envoyée au climat sous-jacent doit rester celle produite par la régulation existante à partir de la consigne fonctionnelle du mode HVAC courant ; la correction ne doit pas modifier cet algorithme interne.
- **FR-006 — Contrat public.** En `COOL`, l’attribut public `preset_temperatures` doit exposer les clés `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp` et, lorsqu’elles sont configurées, `${preset}_cool_away_temp`. La carte doit ainsi lire la consigne COOL au lieu de retomber sur la clé HEAT correspondante.
- **FR-007 — Changement de mode.** Après `HEAT -> COOL`, puis `COOL -> HEAT`, le système doit recalculer, publier et appliquer la table correspondant à chaque nouveau mode.
- **FR-008 — Preset.** La sélection ou la réapplication d’un preset doit utiliser la table du mode HVAC courant, sans réintroduire une consigne de l’autre mode.
- **FR-009 — Nombres de température.** La mise à jour d’un nombre de température doit mettre à jour la consigne effective, publiée et appliquée du mode courant ; une mise à jour COOL ne doit pas modifier la consigne HEAT, et inversement.
- **FR-010 — Présence et absence.** Lorsque les variantes d’absence sont configurées, le système doit sélectionner et publier la variante correspondant au mode courant et à l’état de présence. `HEAT` et `COOL` doivent rester distinguables ; par exemple `16,0 °C` et `29,0 °C` ne doivent pas être interverties.
- **FR-011 — Modes transitoires.** Pour `OFF`, `SLEEP`, `FAN_ONLY`, `DRY` ou tout autre mode transitoire déjà géré, le système doit conserver le comportement existant ; lorsqu’un mode transitoire requiert une consigne, sa source et sa réapplication doivent rester cohérentes avec les règles existantes et ne pas écraser silencieusement une consigne COOL par une consigne HEAT.
- **FR-012 — Données publiques pour la carte.** Pour un `over_climate` avec AC activé, l’interface publique doit exposer `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp` et les variantes `${preset}_cool_away_temp` lorsqu’elles existent, en plus des températures HEAT existantes.
- **FR-013 — Contrat de lecture COOL.** La publication doit utiliser les clés COOL attendues par le lecteur vérifié de la carte. Les clés proposées `*_ac_temp` ne font pas partie du contrat requis.
- **FR-014 — Indisponibilité.** Si une valeur nécessaire est indisponible, le système doit conserver le comportement d’erreur ou d’indisponibilité existant, sans substituer silencieusement une valeur de l’autre mode.
- **FR-015 — Non-régression.** Les consignes HEAT existantes, les entités `number` AC, les autres types de VTherm et les comportements non concernés doivent rester fonctionnels.

### 5. Règles métier

- **BR-001 — Modes indépendants.** La disponibilité d’un mode ne doit pas être conditionnée à l’exclusion de l’autre : AC activé signifie que `HEAT` et `COOL` sont disponibles selon le type, avec `SLEEP` et `OFF` conservés pour `over_valve`.
- **BR-002 — Source de consigne.** Le mode HVAC courant est l’autorité pour choisir la table de température. `COOL` ne peut pas utiliser par défaut une consigne HEAT.
- **BR-003 — Cohérence publication/application.** Une consigne publiée comme effective doit être la consigne fonctionnelle utilisée pour produire la commande envoyée au climat sous-jacent ; une transformation par la régulation existante est permise, mais aucune valeur de l’autre mode ne doit être utilisée.
- **BR-004 — Priorité temporelle.** Après un changement de mode, de preset, de présence ou de nombre, aucune réapplication ultérieure ne doit écraser la consigne correcte par une valeur issue de l’ancien mode.
- **BR-005 — Absence.** Une variante d’absence ne doit être utilisée que si elle est configurée et que l’état de présence courant la rend applicable ; elle doit rester indexée par le mode HVAC.
- **BR-006 — Nommage des clés.** Les clés publiques COOL doivent être distinctes des clés HEAT et respecter le contrat du lecteur : `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp` et `${preset}_cool_away_temp` lorsqu’elles existent.
- **BR-007 — Portée.** La correction de l’attribut public vise les `over_climate` avec AC activé ; elle ne demande pas de modifier le code de la VTherm UI Card dans ce dépôt.

### 6. Contraintes fonctionnelles et non fonctionnelles

#### Contraintes fonctionnelles

- La liste `over_valve` doit conserver exactement les quatre capacités fonctionnelles `HEAT`, `COOL`, `SLEEP`, `OFF` dans le périmètre AC ; leur ordre observable doit rester stable si le contrat existant l’exige.
- Les valeurs des entités `number` existantes ne doivent pas être renommées, migrées ou recalculées par cette spécification.
- La correction ne doit pas modifier les algorithmes de régulation, la communication générale avec les climatiseurs sous-jacents, ni la configuration utilisateur.
- La version déployée de la carte doit être vérifiée pour confirmer sa compatibilité avec les clés COOL requises. La spécification impose le résultat observable et le contrat public, pas une implémentation particulière.

#### Exigences non fonctionnelles

- **NFR-001 — Compatibilité Home Assistant.** Les modes et attributs restent exposés selon les contrats Home Assistant existants pour les entités climate et number.
- **NFR-002 — Compatibilité de carte.** La version de la VTherm UI Card prise en charge doit pouvoir distinguer et afficher les valeurs COOL publiées ; toute incompatibilité de version ou de schéma doit être identifiée avant livraison.
- **NFR-003 — Stabilité.** Le correctif ne doit pas introduire d’erreur récurrente, de boucle de réapplication ou de divergence entre état publié et consigne appliquée.
- **NFR-004 — Confidentialité et sécurité.** Aucun nouvel accès, secret, stockage ou flux de données n’est introduit.
- **NFR-005 — Vérifiabilité.** Les scénarios critiques doivent être reproductibles avec des valeurs HEAT et COOL distinctes et contrôlables dans l’état public et la commande sous-jacente.

### 7. Scénarios et transitions

| Scénario | État initial                                               | Action                                                | Résultat observable attendu                                                                                                               |
| -------- | ---------------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| T-001    | `over_valve`, AC, modes construits                         | Construire l’entité                                   | `hvac_modes` contient `HEAT`, `COOL`, `SLEEP`, `OFF`                                                                                      |
| T-002    | `over_valve` en `COOL`                                     | Sélectionner `HEAT`                                   | Le mode publié devient `HEAT` et reste sélectionnable                                                                                     |
| T-003    | `over_climate` en `HEAT`, consigne fonctionnelle `19,0 °C` | Sélectionner `COOL`                                   | La cible interne COOL vaut `25,0 °C` ; la commande sous-jacente reste celle de la régulation COOL existante                               |
| T-004    | `over_climate` en `COOL`, preset sélectionné               | Lire `preset_temperatures` puis réappliquer le preset | `eco_cool_temp` vaut `25,0 °C` et la carte ne retombe pas sur `eco_temp` à `19,0 °C`                                                      |
| T-005    | `over_climate` en `COOL`                                   | Modifier le nombre COOL                               | La nouvelle valeur COOL est publiée et appliquée ; la valeur HEAT reste inchangée                                                         |
| T-006    | `over_climate` en `HEAT`                                   | Modifier le nombre HEAT                               | La nouvelle valeur HEAT est publiée et appliquée ; la valeur COOL reste inchangée                                                         |
| T-007    | `COOL`, absence configurée                                 | Passer en absence                                     | La clé `${preset}_cool_away_temp` publie `29,0 °C` et la commande sous-jacente reste celle de la régulation COOL existante                |
| T-008    | `COOL` ou `HEAT`                                           | Passer par un mode transitoire existant               | Le comportement transitoire existant est conservé et aucune mauvaise table n’est réutilisée                                               |
| T-009    | Attributs publics avec presets AC                          | Ouvrir la VTherm UI Card compatible                   | Les clés `*_cool_temp` et `${preset}_cool_away_temp` sont lues ; les températures COOL sont affichées et distinctes des températures HEAT |

### 8. Critères d’acceptation

- **AC-001 — Modes `over_valve`.** Étant donné un `over_valve` avec `AC Mode=True`, `hvac_modes` contient et l’entité accepte `HEAT`, `COOL`, `SLEEP` et `OFF`. `HEAT` n’est pas supprimé par la présence de `COOL`.
- **AC-002 — Non-régression `SLEEP`.** Dans AC-001, `SLEEP` reste disponible et son comportement existant n’est pas remplacé par celui de `HEAT`, `COOL` ou `OFF`.
- **AC-003 — Passage en COOL.** Étant donné un `over_climate` en `HEAT` avec une consigne fonctionnelle de `19,0 °C`, lorsque `COOL` est sélectionné, la cible interne COOL vaut `25,0 °C` dans le scénario de test et la commande sous-jacente reste celle produite par la régulation COOL existante.
- **AC-004 — Retour en HEAT.** Dans AC-003, lorsque `HEAT` est sélectionné, la cible publique fonctionnelle revient à `19,0 °C` et la commande sous-jacente correspond à la régulation HEAT attendue ; la valeur COOL n’est pas réutilisée.
- **AC-005 — Preset en COOL.** En `COOL`, `preset_temperatures` contient notamment `eco_cool_temp = 25,0 °C` et, si configurée, `${preset}_cool_away_temp`. La carte lit ces clés ; elle ne retombe pas sur `eco_temp = 19,0 °C`.
- **AC-006 — Mise à jour des nombres.** En `COOL`, la modification du nombre de température COOL est reflétée dans la consigne effective publiée et appliquée. En `HEAT`, la modification du nombre HEAT produit le même résultat pour la table HEAT, sans modifier la table opposée.
- **AC-007 — Présence/absence.** Avec les variantes configurées, un scénario `COOL` en absence publie la clé `${preset}_cool_away_temp` à `29,0 °C` et conserve la commande issue de la régulation COOL existante, tandis que `HEAT` utilise sa valeur d’absence, par exemple `16,0 °C`.
- **AC-008 — Transitions existantes.** Les modes transitoires déjà pris en charge (`OFF`, `SLEEP`, `FAN_ONLY`, `DRY` selon les capacités réelles) ne provoquent ni sélection permanente de la table HEAT en `COOL`, ni régression de leur comportement existant.
- **AC-009 — Attribut public.** Pour un `over_climate` AC, l’attribut `preset_temperatures` contient `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp` et les variantes `${preset}_cool_away_temp` lorsqu’elles sont configurées, distinctes des entrées HEAT.
- **AC-010 — Affichage de la carte.** Avec une version compatible de la VTherm UI Card, la carte lit les clés COOL et affiche les valeurs du scénario (`25,0 °C` et, si applicable, `29,0 °C`) sans fallback vers les clés HEAT.
- **AC-011 — Indisponibilité.** Une valeur ou une entité indisponible ne conduit pas à publier ou appliquer silencieusement la température de l’autre mode ; le comportement d’indisponibilité existant est conservé et observable.
- **AC-012 — Non-régression.** Les tests de chauffage existants, les entités `number` existantes et les VTherm hors périmètre conservent leur comportement ; aucun changement de configuration utilisateur n’est requis.
- **AC-013 — Contrat observable.** La validation ne requiert pas de localiser un écrasement interne : elle vérifie la cible COOL interne déjà correcte, les clés publiques exactes et la résolution de la carte dans AC-003 à AC-010.

### 9. Fonctions non prises en compte

- Correction ou modification du code source de la VTherm UI Card dans ce dépôt.
- Déduction par la carte des consignes depuis les entités `number` à la place du contrat public de températures.
- Modification des algorithmes TPI, de l’auto-régulation, de la communication générale avec les climatiseurs ou des nombres de configuration AC.
- Migration des configurations existantes, changement de nom arbitraire des entités `number` ou modification de l’état Home Assistant pendant la définition de la solution.
- Modification générale du mode `SLEEP` de types autres que la conservation demandée pour `over_valve`.
- Garantie d’une capacité constructeur non déclarée par le climat sous-jacent.

### 10. Évolutions futures proposées

- Documenter le contrat versionné entre l’attribut `preset_temperatures` et la VTherm UI Card.
- Ajouter un diagnostic explicite lorsqu’une consigne publiée ne peut pas être appliquée au climat sous-jacent.
- Ajouter une matrice de compatibilité par version de la carte et par mode HVAC supporté.
- Étudier une stratégie de gestion explicite des modes transitoires si leurs règles actuelles diffèrent selon les climatiseurs.

### 11. Hypothèses, questions ouvertes et traçabilité

#### Faits établis par le rapport et les tests

- `over_valve` avec AC activé expose actuellement une liste qui exclut `HEAT`.
- Sur le test discriminant `over_climate` AC, le moteur interne passe correctement de `HEAT = 19,0 °C` à `COOL = 25,0 °C`.
- `preset_temperatures` n’expose pas `eco_cool_temp` ; la copie locale de la carte cherche `${preset}_cool_temp` puis `${preset}_cool_away_temp`, avant de retomber sur `eco_temp` et de résoudre 19,0 °C.
- Les nombres de presets AC existent pour les VTherm avec AC activé.
- Les clés proposées `*_ac_temp` sont incorrectes pour ce lecteur ; le contrat requis est `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp` et `${preset}_cool_away_temp`.
- Les deux tests rouges sont tracés ainsi : `RT-001` correspond à `tests/test_valve.py::test_over_valve_sleep_mode` pour la liste HVAC AC, et `RT-002` à `tests/test_auto_regulation.py::test_over_climate_ac_preset_temperatures_publish_cool_target` pour le contrat public et le fallback de carte. Le second vérifie séparément la cible interne correcte et l'échec public.

#### Hypothèses retenues

- La VTherm UI Card peut afficher les températures COOL dès lors que l’attribut public expose les clés requises par le lecteur vérifié.
- Les valeurs `19,0 °C` pour HEAT et `25,0 °C` pour COOL sont des valeurs de test discriminantes, pas des valeurs par défaut imposées aux utilisateurs.
- `frost` ne possède pas de variante AC, conformément au rapport ; aucune exigence COOL n’est ajoutée pour ce cas.

#### Questions ouvertes à résoudre en conception

1. Quelle version de la VTherm UI Card déployée doit être déclarée compatible avec les clés `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp` et `${preset}_cool_away_temp` ?
2. Quel commit ou quelle version de la carte a introduit le lecteur avec fallback COOL vers HEAT ? L’artefact local ignoré ne permet pas de l’établir.
3. Pour chaque mode transitoire existant (`OFF`, `SLEEP`, `FAN_ONLY`, `DRY`), une consigne doit-elle être publiée et réappliquée, ou le comportement actuel doit-il seulement être préservé ?

#### Traçabilité

Le [rapport de revue de l'issue #2075](issue-2075-review.md) est la source normative du périmètre et des symptômes. Les tests fournis établissent que le moteur `over_climate` calcule `COOL = 25,0 °C`, tandis que le contrat public incomplet provoque le fallback de la carte vers `HEAT = 19,0 °C`. L'historique causal vérifié est `e095f...` pour la branche AC de `build_hvac_list()` de `over_valve`, et `27b0b...` pour la structure incomplète de `preset_temperatures`. Aucun de ces commits ne peut être attribué à l'implémentation du lecteur de carte : l'artefact local est ignoré et son commit d'introduction n'est pas identifiable dans ce dépôt. L'issue GitHub est une source complémentaire pour le symptôme `over_valve` et sa reproduction. Aucun code, test, configuration, dépendance ni état Home Assistant n'est modifié par cette spécification.

| Élément du rapport                                                  | Exigences / critères                                   |
| ------------------------------------------------------------------- | ------------------------------------------------------ |
| `over_valve` perd `HEAT` avec AC                                    | FR-001, FR-002, BR-001, AC-001, AC-002                 |
| `over_climate` calcule COOL mais le contrat public retombe sur HEAT | FR-003 à FR-011, BR-002 à BR-005, AC-003 à AC-008      |
| UI Card n’expose pas correctement les températures COOL             | FR-012, FR-013, BR-006, BR-007, AC-009, AC-010, AC-013 |
| Valeurs AC et présence/absence                                      | FR-009, FR-010, AC-006, AC-007                         |
| Compatibilité et non-régression                                     | FR-014, FR-015, NFR-001 à NFR-005, AC-011, AC-012      |
| Compatibilité et historique de la carte à confirmer                 | FR-013, AC-013, questions 1 et 2                       |

## English Version

### 1. Title and metadata

- **Name:** GitHub issue #2075 — AC mode consistency for `over_valve`, `over_climate`, and the VTherm UI Card
- **Version:** 1.1
- **Status:** proposed for design and validation
- **Date:** 2026-09-30
- **Owner:** to be assigned
- **Reference report:** [issue-2075-review.md](issue-2075-review.md)
- **Issue:** [jmcollin78/versatile_thermostat#2075](https://github.com/jmcollin78/versatile_thermostat/issues/2075)
- **Verified files and symbols in the report:** `thermostat_valve.py` / `build_hvac_list()`, `base_thermostat.py` / AC behavior, `base_thermostat.py` / `find_preset_temp()` and `preset_temperatures`, `number.py` / AC preset numbers, `tests/test_switch_ac.py`, and `tests/test_auto_regulation.py`.

### 2. Context and objectives

The review report groups three symptoms related to the VTherm AC contract, but they shall remain independently verifiable:

1. **`over_valve` with AC Mode:** `HEAT` disappears from `hvac_modes`, while `COOL` remains available.
2. **`over_climate` with AC Mode:** the internal engine correctly selects `COOL = 25.0 °C` after `HEAT = 19.0 °C`, but the public `preset_temperatures` attribute does not expose `eco_cool_temp`. The card therefore falls back to `eco_temp` and publicly resolves 19.0 °C.
3. **VTherm UI Card:** `COOL` temperatures are not exposed under the expected keys and are therefore not displayed correctly.

The objective is to restore an observable, consistent contract between the selected HVAC mode, the effective published setpoint, and the preset-temperature data exposed to interfaces. Existing functions shall remain intact, especially the `SLEEP` mode specific to `over_valve`, AC number entities, and compatibility with existing transient modes.

This specification deliberately uses distinct example values: `HEAT = 19.0 °C` and `COOL = 25.0 °C`. A publicly resolved or displayed `19.0 °C` in `COOL` is therefore an observable failure; the internal `25.0 °C` target and regulated command remain separately verifiable.

The production implementation is limited to two points: `ThermostatOverValve.build_hvac_list()` for `over_valve` modes, and `BaseThermostat.update_custom_attributes()` for the `preset_temperatures` contract of AC `over_climate`. No change is required in `find_preset_temp()` or the internal regulation engine: runtime evidence establishes that the COOL target is already `25.0 °C`. The `over_climate` defect is located in the missing public keys and the card's read fallback to `eco_temp`.

### 3. Actors and use cases

#### Actors

- **User or automation:** selects an HVAC mode, preset, or temperature value.
- **`over_valve` VTherm:** exposes the mode list and accepts HVAC transitions.
- **`over_climate` VTherm:** computes the setpoint matching the active HVAC mode and exposes the public data required to read it.
- **Underlying climate:** receives the effective setpoint from an `over_climate`.
- **Temperature number entities:** provide heating, cooling, and away-preset values when configured.
- **VTherm UI Card:** consumes public preset-temperature data and displays COOL values.

#### Common preconditions

- The VTherm is configured with `AC Mode=True`.
- Required entities are available, except in explicitly tested unavailability scenarios.
- Example values are distinct: `HEAT = 19.0 °C`, `COOL = 25.0 °C`, `HEAT away = 16.0 °C`, `COOL away = 29.0 °C`.

#### Use case UC-001 — Select a mode on `over_valve`

1. The user opens HVAC modes for an `over_valve` with AC enabled.
2. The system exposes `HEAT`, `COOL`, `SLEEP`, and `OFF`.
3. The user selects `HEAT` or `COOL`; the VTherm accepts the transition and publishes the selected mode.

#### Use case UC-002 — Regulate an `over_climate` in `COOL`

1. The VTherm is in `HEAT` with an effective setpoint of `19.0 °C`.
2. The user selects `COOL`.
3. The engine selects the corresponding functional COOL setpoint, for example `25.0 °C`, and existing regulation produces the corresponding COOL command.
4. The public `preset_temperatures` attribute exposes the expected COOL key so that the card does not fall back to `eco_temp` at `19.0 °C`.

#### Use case UC-003 — Change mode and preset

1. The user changes `HEAT` to `COOL`, selects or reapplies a preset, or changes a temperature number.
2. At every step, the effective and published setpoint follows the current HVAC mode.
3. Returning to `HEAT` selects the heating table again, for example `19.0 °C`, without incorrectly retaining `25.0 °C`.

#### Use case UC-004 — View temperatures in the card

1. The card reads the VTherm state and public attributes.
2. It receives the expected COOL values in the schema compatible with its version.
3. It displays cooling temperatures distinct from heating temperatures, including away variants when configured.

### 4. Functional requirements

- **FR-001 — `over_valve` modes.** With AC enabled, the system shall expose and accept `HEAT`, `COOL`, `SLEEP`, and `OFF` for an `over_valve` VTherm.
- **FR-002 — Preserve `SLEEP`.** The correction shall not remove or redefine the `over_valve`-specific `SLEEP` mode.
- **FR-003 — Mode-based selection.** For an `over_climate` with AC enabled, the system shall select the setpoint table matching the current HVAC mode: heating setpoints in `HEAT` and cooling setpoints in `COOL`.
- **FR-004 — Functional target.** In `COOL`, the internal functional target shall be a COOL setpoint. With the example values, it shall be `25.0 °C`, not `19.0 °C`.
- **FR-005 — Regulated setpoint.** The command sent to the underlying climate shall remain the value produced by existing regulation from the functional setpoint for the current HVAC mode; the correction shall not change that internal algorithm.
- **FR-006 — Public contract.** In `COOL`, the public `preset_temperatures` attribute shall expose `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp`, and, when configured, `${preset}_cool_away_temp`. The card shall therefore read the COOL setpoint instead of falling back to the corresponding HEAT key.
- **FR-007 — Mode change.** After `HEAT -> COOL`, and then `COOL -> HEAT`, the system shall recalculate, publish, and apply the table matching each new mode.
- **FR-008 — Preset.** Selecting or reapplying a preset shall use the current HVAC-mode table and shall not reintroduce a setpoint from the other mode.
- **FR-009 — Temperature numbers.** Updating a temperature number shall update the effective, published, and applied setpoint for the current mode; a COOL update shall not change the HEAT setpoint, and vice versa.
- **FR-010 — Presence and away.** When away variants are configured, the system shall select and publish the variant matching the current mode and presence state. `HEAT` and `COOL` shall remain distinguishable; for example, `16.0 °C` and `29.0 °C` shall not be swapped.
- **FR-011 — Transient modes.** For already supported `OFF`, `SLEEP`, `FAN_ONLY`, `DRY`, or any other transient mode, the system shall preserve existing behavior; when a transient mode requires a setpoint, its source and reapplication shall remain consistent with existing rules and shall not silently overwrite a COOL setpoint with a HEAT setpoint.
- **FR-012 — Public card data.** For an `over_climate` with AC enabled, the public interface shall expose `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp`, and `${preset}_cool_away_temp` when present, in addition to existing HEAT temperatures.
- **FR-013 — COOL reading contract.** Publication shall use the COOL keys expected by the verified card reader. The proposed `*_ac_temp` keys are not part of the required contract.
- **FR-014 — Unavailability.** If a required value is unavailable, the system shall preserve existing error or unavailable behavior without silently substituting a value from the other mode.
- **FR-015 — Regression safety.** Existing HEAT setpoints, AC number entities, other VTherm types, and unrelated behavior shall remain functional.

### 5. Business rules

- **BR-001 — Independent modes.** Availability of one mode shall not require excluding the other: with AC enabled, `HEAT` and `COOL` are available according to type, while `SLEEP` and `OFF` remain available for `over_valve`.
- **BR-002 — Setpoint source.** The current HVAC mode is authoritative for selecting the temperature table. `COOL` shall not default to a HEAT setpoint.
- **BR-003 — Publication/application consistency.** A published effective setpoint shall be the functional setpoint used to produce the command sent to the underlying climate; transformation by existing regulation is allowed, but no value from the other mode shall be used.
- **BR-004 — Temporal priority.** After a mode, preset, presence, or number change, no later reapplication shall overwrite the correct setpoint with a value from the former mode.
- **BR-005 — Away state.** An away variant shall be used only when configured and applicable to the current presence state; it shall remain indexed by HVAC mode.
- **BR-006 — Key naming.** Public COOL keys shall be distinct from HEAT keys and shall follow the reader contract: `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp`, and `${preset}_cool_away_temp` when present.
- **BR-007 — Scope.** The public-attribute correction targets `over_climate` with AC enabled; it does not require changing VTherm UI Card source code in this repository.

### 6. Functional and non-functional constraints

#### Functional constraints

- The AC `over_valve` list shall preserve exactly the four functional capabilities `HEAT`, `COOL`, `SLEEP`, and `OFF`; observable ordering shall remain stable if required by the existing contract.
- Existing number-entity values shall not be renamed, migrated, or recalculated by this specification.
- The correction shall not change regulation algorithms, general communication with underlying climates, or user configuration.
- The deployed card version shall be checked for compatibility with the required COOL keys. This specification defines observable results and the public contract, not a particular implementation.

#### Non-functional requirements

- **NFR-001 — Home Assistant compatibility.** Modes and attributes shall remain exposed according to existing Home Assistant climate and number contracts.
- **NFR-002 — Card compatibility.** The supported VTherm UI Card version shall be able to distinguish and display published COOL values; any version or schema incompatibility shall be identified before delivery.
- **NFR-003 — Stability.** The correction shall not introduce recurring errors, reapplication loops, or divergence between published state and applied setpoint.
- **NFR-004 — Privacy and security.** No new access, secret, storage, or data flow is introduced.
- **NFR-005 — Verifiability.** Critical scenarios shall be reproducible with distinct HEAT and COOL values observable in public state and the underlying command.

### 7. Scenarios and transitions

| Scenario | Initial state                                           | Action                                          | Expected observable result                                                                                                 |
| -------- | ------------------------------------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| T-001    | `over_valve`, AC, modes being built                     | Build the entity                                | `hvac_modes` contains `HEAT`, `COOL`, `SLEEP`, `OFF`                                                                       |
| T-002    | `over_valve` in `COOL`                                  | Select `HEAT`                                   | Published mode becomes `HEAT` and remains selectable                                                                       |
| T-003    | `over_climate` in `HEAT`, functional setpoint `19.0 °C` | Select `COOL`                                   | Internal COOL target is `25.0 °C`; the underlying command remains the value from existing COOL regulation                  |
| T-004    | `over_climate` in `COOL`, preset selected               | Read `preset_temperatures`, then reapply preset | `eco_cool_temp` is `25.0 °C` and the card does not fall back to `eco_temp` at `19.0 °C`                                    |
| T-005    | `over_climate` in `COOL`                                | Change COOL number                              | New COOL value is published and applied; HEAT value remains unchanged                                                      |
| T-006    | `over_climate` in `HEAT`                                | Change HEAT number                              | New HEAT value is published and applied; COOL value remains unchanged                                                      |
| T-007    | `COOL`, away configured                                 | Enter away state                                | `${preset}_cool_away_temp` publishes `29.0 °C`; the underlying command remains the value from existing COOL regulation     |
| T-008    | `COOL` or `HEAT`                                        | Pass through an existing transient mode         | Existing transient behavior is preserved and no wrong table is reused                                                      |
| T-009    | Public attributes with AC presets                       | Open a compatible VTherm UI Card                | `*_cool_temp` and `${preset}_cool_away_temp` are read; COOL temperatures are displayed and distinct from HEAT temperatures |

### 8. Acceptance criteria

- **AC-001 — `over_valve` modes.** Given an `over_valve` with `AC Mode=True`, `hvac_modes` contains and the entity accepts `HEAT`, `COOL`, `SLEEP`, and `OFF`. `HEAT` is not removed by the presence of `COOL`.
- **AC-002 — `SLEEP` regression safety.** In AC-001, `SLEEP` remains available and its existing behavior is not replaced by `HEAT`, `COOL`, or `OFF` behavior.
- **AC-003 — Entering COOL.** Given an `over_climate` in `HEAT` with a functional setpoint of `19.0 °C`, when `COOL` is selected, the internal COOL target is `25.0 °C` in the test scenario and the underlying command remains the value produced by existing COOL regulation.
- **AC-004 — Returning to HEAT.** In AC-003, when `HEAT` is selected, the public functional target returns to `19.0 °C` and the underlying command matches the expected HEAT regulation; the COOL value is not reused.
- **AC-005 — COOL preset.** In `COOL`, `preset_temperatures` contains `eco_cool_temp = 25.0 °C` and, when configured, `${preset}_cool_away_temp`. The card reads these keys and does not fall back to `eco_temp = 19.0 °C`.
- **AC-006 — Number updates.** In `COOL`, changing the COOL temperature number is reflected in the published and applied effective setpoint. In `HEAT`, changing the HEAT number produces the same result for the HEAT table without changing the opposite table.
- **AC-007 — Presence/away.** With variants configured, a COOL-away scenario publishes `${preset}_cool_away_temp` as `29.0 °C` and retains the command from existing COOL regulation, while HEAT uses its away value, for example `16.0 °C`.
- **AC-008 — Existing transitions.** Already supported transient modes (`OFF`, `SLEEP`, `FAN_ONLY`, `DRY` according to actual capabilities) cause neither permanent selection of the HEAT table in `COOL` nor a regression of existing behavior.
- **AC-009 — Public attribute.** For an AC `over_climate`, `preset_temperatures` contains `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp`, and `${preset}_cool_away_temp` when configured, distinct from the HEAT entries.
- **AC-010 — Card display.** With a compatible VTherm UI Card version, the card reads the COOL keys and displays the scenario values (`25.0 °C` and, where applicable, `29.0 °C`) without falling back to HEAT keys.
- **AC-011 — Unavailability.** An unavailable value or entity does not silently cause the temperature from the other mode to be published or applied; existing unavailable behavior is preserved and observable.
- **AC-012 — Regression safety.** Existing heating tests, existing number entities, and out-of-scope VTherms retain their behavior; no user configuration change is required.
- **AC-013 — Observable contract.** Validation does not require locating an internal overwrite: it verifies the already-correct internal COOL target, the exact public keys, and card resolution in AC-003 through AC-010.

### 9. Out-of-scope functions

- Fixing or changing VTherm UI Card source code in this repository.
- Having the card derive setpoints from number entities instead of the public temperature contract.
- Changing TPI algorithms, auto-regulation, general climate communication, or AC configuration numbers.
- Migrating existing configurations, arbitrarily renaming number entities, or changing Home Assistant state during solution definition.
- General changes to `SLEEP` for types other than preserving the requested `over_valve` behavior.
- Guaranteeing an undeclared capability of an underlying climate.

### 10. Proposed future enhancements

- Document the versioned contract between the `preset_temperatures` attribute and the VTherm UI Card.
- Add an explicit diagnostic when a published setpoint cannot be applied to the underlying climate.
- Add a compatibility matrix by card version and supported HVAC mode.
- Study explicit handling for transient modes if their current rules differ across climates.

### 11. Assumptions, open questions, and traceability

#### Facts established by the report and tests

- `over_valve` with AC enabled currently exposes a list excluding `HEAT`.
- In the discriminating AC `over_climate` test, the internal engine correctly changes from `HEAT = 19.0 °C` to `COOL = 25.0 °C`.
- `preset_temperatures` does not expose `eco_cool_temp`; the local card copy looks for `${preset}_cool_temp` and then `${preset}_cool_away_temp`, before falling back to `eco_temp` and resolving 19.0 °C.
- AC preset numbers exist for VTherms with AC enabled.
- The proposed `*_ac_temp` keys are incorrect for this reader; the required contract is `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp`, and `${preset}_cool_away_temp`.
- The two red tests are traced as follows: `RT-001` is `tests/test_valve.py::test_over_valve_sleep_mode` for the AC HVAC list, and `RT-002` is `tests/test_auto_regulation.py::test_over_climate_ac_preset_temperatures_publish_cool_target` for the public contract and card fallback. The latter separately verifies the correct internal target and the public failure.

#### Assumptions retained

- The VTherm UI Card can display COOL temperatures once the public attribute exposes the keys required by the verified reader.
- `19.0 °C` for HEAT and `25.0 °C` for COOL are discriminating test values, not user defaults imposed by this specification.
- `frost` has no AC variant, according to the report; no COOL requirement is added for that case.

#### Open design questions

1. Which deployed VTherm UI Card version shall be declared compatible with `eco_cool_temp`, `comfort_cool_temp`, `boost_cool_temp`, and `${preset}_cool_away_temp`?
2. Which commit or version of the card introduced the reader with COOL-to-HEAT fallback? The ignored local artifact cannot establish this.
3. For each existing transient mode (`OFF`, `SLEEP`, `FAN_ONLY`, `DRY`), must a setpoint be published and reapplied, or should existing behavior merely be preserved?

#### Traceability

The [issue #2075 review report](issue-2075-review.md) is the normative source for scope and symptoms. The supplied tests establish that the `over_climate` engine computes `COOL = 25.0 °C`, while the incomplete public contract causes the card to fall back to `HEAT = 19.0 °C`. The verified causal history is `e095f...` for the AC branch of `over_valve`'s `build_hvac_list()`, and `27b0b...` for the incomplete `preset_temperatures` structure. Neither commit can be attributed to the card reader implementation: the local artifact is ignored and its introduction commit cannot be identified in this repository. The GitHub issue is a complementary source for the `over_valve` symptom and reproduction. No code, test, configuration, dependency, or Home Assistant state is modified by this specification.

| Report item                                                             | Requirements / criteria                                |
| ----------------------------------------------------------------------- | ------------------------------------------------------ |
| `over_valve` loses `HEAT` with AC                                       | FR-001, FR-002, BR-001, AC-001, AC-002                 |
| `over_climate` computes COOL but the public contract falls back to HEAT | FR-003 to FR-011, BR-002 to BR-005, AC-003 to AC-008   |
| UI Card does not expose COOL temperatures correctly                     | FR-012, FR-013, BR-006, BR-007, AC-009, AC-010, AC-013 |
| AC values and presence/away                                             | FR-009, FR-010, AC-006, AC-007                         |
| Card version compatibility and history to confirm                       | FR-013, AC-013, questions 1 and 2                      |