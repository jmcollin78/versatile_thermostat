# Revue de l’issue #2091 — erreurs de placeholders de traduction polonaise

**Statut :** à valider avant spécification et conception
**Issue :** [#2091 — Translation error](https://github.com/jmcollin78/versatile_thermostat/issues/2091)
**Dépôt examiné :** `jmcollin78/versatile_thermostat`, branche `main`
**Date de revue :** 2026-10-10

## 1. Résumé fidèle de l’issue

Avec VTherm 10.5.0, Home Assistant signale depuis plusieurs mois deux erreurs de validation dans la traduction polonaise (`pl`) :

- `options.step.auto_tpi_configuration.data.auto_tpi_heating_rate` ne contient pas le placeholder attendu `{unit}` ;
- `options.step.heating_failure_detection.title` ne contient pas le placeholder attendu `{name}`.

L’issue est ouverte, sans étiquette, assignation, projet, branche ou pull request associés. Le mainteneur a demandé si l’auteur pouvait proposer une pull request.

## 2. Sources et éléments vérifiés

- Description, journal, commentaire et métadonnées de [#2091](https://github.com/jmcollin78/versatile_thermostat/issues/2091).
- La traduction polonaise contient un libellé Auto TPI avec l’unité écrite en dur `°C/h`, sans `{unit}`, et un titre de détection de panne sans `{name}` : [custom_components/versatile_thermostat/translations/pl.json](../../custom_components/versatile_thermostat/translations/pl.json#L685-L749).
- La référence anglaise contient bien `Heating Rate ({unit}/h)` et `Heating failure detection - {name}` : [custom_components/versatile_thermostat/strings.json](../../custom_components/versatile_thermostat/strings.json#L795-L810) et [custom_components/versatile_thermostat/translations/en.json](../../custom_components/versatile_thermostat/translations/en.json#L740-L764).
- Le flux d’options initialise `name`, puis affecte la température de Home Assistant à `unit` dans les étapes concernées : [custom_components/versatile_thermostat/config_flow.py](../../custom_components/versatile_thermostat/config_flow.py#L1362-L1370) et [custom_components/versatile_thermostat/config_flow.py](../../custom_components/versatile_thermostat/config_flow.py#L910-L911).
- Audit statique complémentaire de la structure, des clés et des placeholders de `strings.json` contre les dix locales : `cs`, `de`, `el`, `en`, `fr`, `it`, `pl`, `ru`, `sk` et `zh-Hans`. Les résultats détaillés figurent en section 6.
- La CI de pull request exécute Hassfest, qui validera les traductions : [.github/workflows/pull.yml](../../.github/workflows/pull.yml#L1-L18).

Aucun test ni outil de validation n’a été exécuté, et aucun état Home Assistant n’a été modifié pendant cette revue.

## 3. Analyse de pertinence et recommandation

### Recommandation : retenir un correctif de traduction circonscrit

Le défaut est confirmé statiquement et correspond exactement aux deux erreurs du journal. Il empêche la validation correcte de l’intégration par Home Assistant et donne une information erronée aux utilisateurs utilisant une unité de température autre que Celsius.

Le correctif attendu est limité à la restauration des placeholders contractuels dans les deux chaînes polonaises :

1. employer `{unit}` dans le libellé de vitesse de chauffe Auto TPI plutôt que l’unité `°C` codée en dur ;
2. employer `{name}` dans le titre de configuration de détection de panne de chauffage.

Cette modification ne doit pas toucher la logique de régulation, les données utilisateur, le flux de configuration ni les autres traductions, sauf erreur supplémentaire objectivement détectée par la validation de traduction.

## 4. Périmètre proposé

### Inclus

- Correction des deux valeurs concernées dans la traduction polonaise.
- Conservation stricte des clés JSON et de la structure existantes.
- Validation JSON et validation Hassfest des placeholders de traduction.
- Contrôle de non-régression ciblé pour confirmer que les deux chaînes polonaises contiennent respectivement `{unit}` et `{name}`.

### Exclus

- Refonte ou harmonisation linguistique générale des traductions polonaises.
- Modification de `strings.json`, du code Python du flux d’options ou des placeholders runtime.
- Audit exhaustif des placeholders de toutes les locales, hors erreurs que Hassfest révélerait pendant la validation.
- Modification des réglages ou données d’une instance Home Assistant.

## 5. Impacts et risques

| Risque                                                                       | Gravité | Probabilité           | Mesure proposée                                               |
| ---------------------------------------------------------------------------- | ------- | --------------------- | ------------------------------------------------------------- |
| Les erreurs de validation polonaises persistent                              | Moyenne | Élevée sans correctif | Restaurer les placeholders contractuels et exécuter Hassfest. |
| L’interface affiche une unité incorrecte pour les utilisateurs non métriques | Moyenne | Moyenne               | Utiliser `{unit}` au lieu de `°C` écrit en dur.               |
| Erreur de syntaxe JSON ou de placeholder dans le correctif                   | Faible  | Faible                | Valider le JSON et Hassfest avant intégration.                |
| Régression de la logique du thermostat                                       | Faible  | Très faible           | Limiter la modification aux deux chaînes de traduction.       |
| Sécurité ou confidentialité                                                  | Faible  | Faible                | Aucune donnée, service ou permission n’est modifié.           |

## 6. Audit complémentaire des autres traductions

L’audit a comparé les placeholders de `strings.json` avec les dix fichiers du dossier `translations`. Il porte sur les chaînes et la structure JSON ; il ne valide ni la qualité linguistique ni le rendu de l’interface.

| Locale    | `options.step.auto_tpi_configuration.data.auto_tpi_heating_rate` | `options.step.heating_failure_detection.title` | Conclusion                                   |
| --------- | ---------------------------------------------------------------- | ---------------------------------------------- | -------------------------------------------- |
| `cs`      | `{unit}` présent                                                 | `{name}` présent                               | Conforme sur les deux clés                   |
| `de`      | `{unit}` présent                                                 | `{name}` présent                               | Conforme sur les deux clés                   |
| `el`      | Clé absente                                                      | `{name}` absent                                | Traduction incomplète / écart de placeholder |
| `en`      | `{unit}` présent                                                 | `{name}` présent                               | Conforme sur les deux clés                   |
| `fr`      | `{unit}` présent                                                 | `{name}` présent                               | Conforme sur les deux clés                   |
| `it`      | `{unit}` présent                                                 | `{name}` présent                               | Conforme sur les deux clés                   |
| `pl`      | `{unit}` absent                                                  | `{name}` absent                                | Écarts signalés par l’issue #2091            |
| `ru`      | Clé absente                                                      | `{name}` absent                                | Traduction incomplète / écart de placeholder |
| `sk`      | Clé absente                                                      | `{name}` absent                                | Traduction incomplète / écart de placeholder |
| `zh-Hans` | `{unit}` présent                                                 | `{name}` présent                               | Conforme sur les deux clés                   |

Les autres placeholders standard contrôlés (`{humidity_detected}`, `{plugins_link}`, `{reason}`, `{unit}` et `{name}`) sont cohérents dans les chaînes présentes des locales examinées. Une première synthèse ayant conclu à tort à l’absence d’écart a été invalidée par une seconde vérification précise ; le tableau ci-dessus reflète le résultat retenu.

Les écarts dans `el`, `ru` et `sk` ne sont pas cités par l’issue. Ils constituent un constat connexe : les inclure au correctif étendrait le périmètre au-delà de #2091 et nécessite une décision explicite.

## 7. Alternatives examinées

| Alternative                                                                    | Avantages                                                | Inconvénients                                                        | Décision |
| ------------------------------------------------------------------------------ | -------------------------------------------------------- | -------------------------------------------------------------------- | -------- |
| Restaurer uniquement les deux placeholders manquants                           | Correctif minimal, conforme à la référence et au journal | Ne réalise pas un audit complet des locales                          | Retenue  |
| Remplacer intégralement `pl.json` par une génération ou une copie de l’anglais | Peut éliminer d’autres divergences                       | Détruit la traduction polonaise et dépasse l’issue                   | Écartée  |
| Modifier le flux d’options pour rendre les placeholders optionnels             | Pourrait masquer le message de validation                | Viole le contrat de traduction et risque une régression multi-locale | Écartée  |
| Auditer toutes les traductions dans cette issue                                | Renforce la prévention globale                           | Périmètre et coût non justifiés par les deux erreurs confirmées      | Différée |

## 8. Hypothèses, décisions nécessaires et questions ouvertes

### Faits établis

- Les deux chaînes signalées par Home Assistant sont présentes dans `pl.json` sans les placeholders attendus.
- Les chaînes de référence anglaise contiennent ces placeholders.
- La CI dispose d’une validation Hassfest.

### Hypothèses

- L’ajout des placeholders dans les deux chaînes suffit à faire disparaître les deux erreurs signalées.
- Les valeurs injectées par le flux d’options restent disponibles dans les étapes concernées.

### Questions ouvertes non bloquantes

- Une formulation polonaise particulière est-elle souhaitée pour les deux libellés, au-delà de la conservation des placeholders ? Aucune préférence n’est fournie par l’issue ; la correction doit préserver le texte polonais existant autant que possible.

### Décision nécessaire

- Valider le périmètre limité aux deux chaînes polonaises et la stratégie de validation par JSON + Hassfest.
- Indiquer si les écarts connexes relevés dans `el`, `ru` et `sk` doivent être intégrés à ce correctif ou traités dans une issue séparée.

## 9. Proposition de suite et critères de passage

### Suite proposée

Après approbation de ce rapport, produire une spécification fonctionnelle et une conception technique légères et convergentes, définissant exactement les deux clés, les placeholders attendus et les vérifications. Le développement ne sera demandé qu’après une seconde autorisation explicite.

### Critères de passage à la spécification et à la conception

- Le présent rapport est approuvé explicitement.
- Le périmètre limité aux deux chaînes et aux validations associées est accepté.
- Les questions ouvertes non bloquantes sont acceptées comme hors périmètre de cette correction.

### Critères de passage au développement

- Les spécifications et la conception confirment les mêmes deux clés, les placeholders `{unit}` et `{name}`, ainsi que les validations JSON et Hassfest.
- Aucun désaccord bloquant ne subsiste entre spécification et conception.
- L’utilisateur autorise explicitement le développement après présentation des résultats de convergence.