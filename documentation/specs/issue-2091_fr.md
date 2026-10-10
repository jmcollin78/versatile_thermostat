# Spécification fonctionnelle — Issue #2091

## 1. Titre et métadonnées

- **Nom :** Correction des placeholders de traduction polonaise
- **Version :** 2.1
- **Statut :** Proposée
- **Date :** 2026-10-10
- **Propriétaire :** Projet Versatile Thermostat
- **Issue :** [#2091 — Translation error](https://github.com/jmcollin78/versatile_thermostat/issues/2091)
- **Rapport analysé :** [issue-2091-review.md](../tech-docs/issue-2091-review.md)
- **Sources :** [strings.json](../../custom_components/versatile_thermostat/strings.json), [pl.json](../../custom_components/versatile_thermostat/translations/pl.json), [config_flow.py](../../custom_components/versatile_thermostat/config_flow.py)

## 2. Contexte et objectifs

Home Assistant signale deux incohérences de placeholders dans la traduction polonaise de l’interface d’options. Ces incohérences peuvent produire des erreurs de validation et empêcher l’affichage dynamique attendu.

L’objectif est de rendre les deux chaînes polonaises conformes aux placeholders de référence, sans modifier le comportement du thermostat ni les autres locales.

## 3. Acteurs et cas d’utilisation

### Acteurs

- **Utilisateur polonais :** consulte ou modifie les options du thermostat.
- **Home Assistant :** charge les traductions et valide leurs placeholders.
- **Mainteneur :** vérifie le correctif avant intégration.

### Cas nominal

1. Home Assistant charge la traduction polonaise.
2. L’interface d’options fournit les valeurs dynamiques `unit` et `name`.
3. Les chaînes polonaises utilisent ces placeholders.
4. La validation des traductions s’exécute sans les deux erreurs de l’issue.

## 4. Exigences fonctionnelles

- **FR-001 — Placeholder d’unité :** Le système doit conserver, dans `pl.json`, le placeholder `{unit}` dans `options.step.auto_tpi_configuration.data.auto_tpi_heating_rate`.
- **FR-002 — Placeholder de nom :** Le système doit conserver, dans `pl.json`, le placeholder `{name}` dans `options.step.heating_failure_detection.title`.
- **FR-003 — Préservation du texte :** Le correctif doit préserver autant que possible le texte polonais existant et ne modifier que les placeholders nécessaires.
- **FR-004 — Périmètre des fichiers :** Le correctif doit être limité à la traduction polonaise concernée, sauf modification documentaire ou de test explicitement nécessaire à la validation.
- **FR-005 — Absence de régression :** Le correctif ne doit modifier ni la logique de régulation, ni le flux de configuration, ni les valeurs de configuration utilisateur.

## 5. Règles métier

- **BR-001 — Contrat de placeholder :** Chaque traduction doit conserver les placeholders attendus par la chaîne de référence correspondante.
- **BR-002 — Valeur dynamique :** L’unité affichée doit provenir de `{unit}` et ne doit pas être imposée par une valeur textuelle fixe dans cette chaîne.
- **BR-003 — Nom de configuration :** Le titre de détection de panne doit pouvoir afficher le nom fourni par `{name}`.
- **BR-004 — Locales connexes :** Les écarts constatés dans `el`, `ru` et `sk` ne font pas partie de l’issue #2091 et ne doivent pas être corrigés dans ce périmètre.

## 6. Contraintes fonctionnelles

- La structure JSON existante doit rester valide.
- Les clés de traduction doivent rester inchangées.
- Le correctif doit être compatible avec les unités et noms injectés par Home Assistant.
- La validation Hassfest de la CI doit pouvoir contrôler les placeholders.
- Aucune donnée personnelle, permission ou service Home Assistant ne doit être ajouté ou modifié.

## 7. Critères d’acceptation

- **AC-001 :** La chaîne polonaise `auto_tpi_heating_rate` contient exactement le placeholder `{unit}` attendu par la référence.
- **AC-002 :** La chaîne polonaise `heating_failure_detection.title` contient exactement le placeholder `{name}` attendu par la référence.
- **AC-003 :** `pl.json` reste un JSON valide et conserve ses clés et sa structure.
- **AC-004 :** Les deux messages de validation de l’issue ne sont plus produits par Hassfest.
- **AC-005 :** Les valeurs des placeholders ne sont pas codées en dur dans les chaînes corrigées.
- **AC-006 :** Aucun fichier de code, aucune autre locale et aucune configuration utilisateur ne sont modifiés par le correctif fonctionnel.

## 8. Fonctions non prises en compte

- Correction linguistique générale de la traduction polonaise.
- Correction des écarts `el`, `ru` et `sk` relevés dans le rapport.
- Audit ou harmonisation complète de toutes les traductions.
- Modification de `strings.json`, de `config_flow.py` ou de la logique métier.
- Modification des traductions de configuration initiale hors des deux chemins `options` concernés.

## 9. Évolutions futures proposées

- Ajouter un contrôle automatisé des placeholders de toutes les locales avant soumission.
- Ouvrir une issue distincte pour les traductions incomplètes `el`, `ru` et `sk`.
- Documenter la procédure de validation locale des fichiers JSON et de Hassfest.

## 10. Hypothèses, questions ouvertes et traçabilité

### Hypothèses

- Les valeurs `unit` et `name` sont disponibles au moment où Home Assistant rend les étapes d’options concernées, conformément au rapport.
- La correction des deux chaînes suffit à résoudre les deux erreurs signalées.

### Questions ouvertes

- La formulation polonaise exacte souhaitée pour les deux chaînes n’est pas précisée ; le texte existant sera conservé autant que possible.
- La validation Hassfest n’a pas encore été exécutée dans cette spécification.

### Traçabilité

- **Issue :** #2091.
- **Rapport :** [issue-2091-review.md](../tech-docs/issue-2091-review.md).
- **Référence des placeholders :** [strings.json](../../custom_components/versatile_thermostat/strings.json).
- **Traduction concernée :** [pl.json](../../custom_components/versatile_thermostat/translations/pl.json).

## Extension 2.0 — `auto_tpi_cooling_rate`

### Périmètre et constat vérifié

L’extension doit ajouter `auto_tpi_cooling_rate` à la référence `strings.json` et aux dix fichiers `translations/*.json`, sous `config.step.auto_tpi_configuration` et `options.step.auto_tpi_configuration`, à la fois dans `data` et `data_description`. Le périmètre d’implémentation est strictement limité à cette clé, à ses quatre feuilles de référence et à ses quatre feuilles par locale ; aucun autre chemin ne doit être modifié.

Le constat vérifié dans les fichiers réels est le suivant : `strings.json` ne définit pas cette clé ; `cs.json` ne contient que les deux feuilles `config` (libellé et description), tandis que `fr.json` ne contient que les deux feuilles `options` ; `pl.json` ne contient que `options.data` ; `de.json`, `en.json`, `it.json` et `zh-Hans.json` possèdent les sections mais non la clé ; `el.json`, `ru.json` et `sk.json` n’ont pas la section `auto_tpi_configuration`. L’audit précédent était donc erroné pour `cs` et `fr` : elles sont partielles, et non complètes. Les occurrences déjà présentes doivent rester inchangées.

### Exigences fonctionnelles

- **FR-006 :** Chaque locale présente doit contenir la clé aux quatre chemins exacts : `config...data`, `config...data_description`, `options...data` et `options...data_description`.
- **FR-007 :** Toute occurrence déjà présente doit conserver exactement sa valeur, sa ponctuation et ses placeholders.
- **FR-008 :** Chaque valeur de `data` doit être un libellé localisé contenant `{unit}` ; chaque valeur de `data_description` doit être une description localisée contenant `{unit}` et décrivant la valeur nulle si cette information est retenue par la référence.
- **FR-009 :** Aucune formulation ne doit être inventée lorsqu’elle n’est pas déterminable. Elle doit être marquée « à définir par la conception » avant implémentation.
- **FR-010 :** L’implémentation doit modifier `strings.json` pour définir les quatre références de `auto_tpi_cooling_rate`, et ne doit modifier aucun code, aucune configuration, aucune dépendance ni aucune autre clé de `strings.json`.

### Règles métier et contraintes

- **BR-006 :** Les quatre chemins sont obligatoires ; une clé dans un seul contexte ne suffit pas.
- **BR-007 :** Le placeholder dynamique doit être exactement `{unit}` ; une unité codée en dur ne le remplace pas.
- **BR-008 :** L’absence de la clé dans `strings.json` doit être résolue par la définition explicite des quatre références canoniques ; elle n’autorise pas l’invention silencieuse des traductions.
- **BR-009 :** Les autres écarts de `el`, `ru`, `sk` et `pl` restent hors périmètre sauf décision explicite.

Les dix fichiers actuellement recensés (`cs`, `de`, `el`, `en`, `fr`, `it`, `pl`, `ru`, `sk`, `zh-Hans`) sont concernés. Chaque fichier doit rester un JSON valide ; la validité JSON ne constitue pas une validation linguistique.

### Valeurs localisées et critères d’acceptation

Les formulations déjà présentes de `cs` (côté `config`) et de `fr` (côté `options`) constituent les valeurs localisées directement déterminables dans les sources consultées ; elles doivent être préservées. Les valeurs manquantes de `cs`, `fr`, `de`, `en`, `it`, `pl`, `zh-Hans`, `el`, `ru` et `sk` sont **à définir par la conception/traduction** ; aucune valeur supposée ne doit être spécifiée. Les quatre références anglaises doivent être définies dans `strings.json` conformément à la conception validée.

- **AC-007 :** Tous les fichiers présents sont recensés et contiennent les quatre chemins.
- **AC-008 :** Chaque valeur `data.auto_tpi_cooling_rate` contient `{unit}` exactement une fois, sauf décision documentée.
- **AC-009 :** Chaque valeur `data_description.auto_tpi_cooling_rate` contient `{unit}` exactement une fois, sauf décision documentée.
- **AC-010 :** Une comparaison avant/après démontre qu’aucune occurrence existante, notamment les deux feuilles `config` de `cs`, les deux feuilles `options` de `fr` et `options.data` de `pl`, n’a changé.
- **AC-011 :** Un parseur JSON et Hassfest valident les fichiers et les placeholders.
- **AC-012 :** Une relecture linguistique compétente est recommandée pour chaque nouvelle traduction, mais elle est non bloquante ; les valeurs localisées proposées par la conception constituent la base autorisée de l’implémentation.

### Exclusions, évolutions, questions et risques

Sont exclus : toute modification de `strings.json` autre que les quatre feuilles de `auto_tpi_cooling_rate`, la réécriture des traductions existantes, la correction automatique des autres écarts et la modification du flux Auto TPI. Évolutions possibles : automatiser la parité des chemins et traiter les traductions partielles dans une issue dédiée.

Question non bloquante : une relecture linguistique complémentaire des formulations proposées est-elle souhaitée ? Les autres écarts doivent-ils être traités séparément ?

Une traduction partielle peut rendre configuration et options incohérentes, déclencher Hassfest ou afficher une unité incorrecte. Une formulation peut encore être améliorée linguistiquement ; la relecture est donc recommandée comme mesure de risque, tandis que les validations JSON, structurelle, du placeholder `{unit}` et Hassfest restent obligatoires. Les valeurs proposées par la conception sont autorisées pour l’implémentation.

### Convergence avec la conception

La présente version converge avec la conception 2.1 : `strings.json` est explicitement inclus pour les quatre références, les dix locales et les quatre chemins par locale sont conservés, `cs` et `fr` sont décrites comme partielles selon l’audit réel, et les occurrences existantes — notamment `pl.options.data` — restent préservées. Les validations JSON, structurelles, des placeholders et Hassfest restent obligatoires. La relecture linguistique est recommandée mais non bloquante ; les valeurs localisées proposées par la conception constituent la base autorisée de l’implémentation. Aucune divergence bloquante ne subsiste.
