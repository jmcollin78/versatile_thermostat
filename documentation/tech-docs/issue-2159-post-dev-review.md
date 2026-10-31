# Revue post-développement — PR #2161 / issue #2159

| Métadonnée        | Valeur                                                                                                                                                                                  |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Date              | 2026-10-29 ; révisé le 2026-10-30 (correction de M-1, précision sur AC-019/AC-031, preuves de E-1 complétées)                                                                           |
| Branche / commit  | `2159-infinite-loop-on-trvzb-on-startup-regression-after-2141` @ `98e5524` (« dev »), identique à la branche distante `origin/` du même nom                                             |
| Référence         | `main` @ `704424d` ; dernier commit de code : `98e5524` contre `daa54fa`                                                                                                                |
| PR                | [#2161](https://github.com/jmcollin78/versatile_thermostat/pull/2161) ouverte, 5 commits, 9 fichiers, aucune revue ; checks du dernier commit : 5/6 OK (le sixième n'est pas identifié) |
| Issue             | [#2159](https://github.com/jmcollin78/versatile_thermostat/issues/2159)                                                                                                                 |
| Décision proposée | **Corriger avant approbation** (un constat élevé reproduit)                                                                                                                             |

## 1. Périmètre et état Git vérifié

- Arbre de travail propre (`git status --short -uall` vide), rien d'indexé ni de non suivi ; `git diff --check main...HEAD` et `git diff --check HEAD` : aucun défaut.
- Production : un seul fichier modifié contre `main`, [thermostat_climate.py](../../custom_components/versatile_thermostat/thermostat_climate.py) (228 lignes modifiées), dans `ThermostatOverClimate`. Aucune modification de `BaseThermostat`, `CycleScheduler`, `underlyings.py` ni d'une autre classe : cible respectée.
- Tests : [test_issue_2159.py](../../tests/test_issue_2159.py) (nouveau), [test_issue_2159_additional.py](../../tests/test_issue_2159_additional.py) (nouveau), modifications de [test_multiple_switch.py](../../tests/test_multiple_switch.py) (2 attentes `command_cause=None` → `COMMAND_CAUSE_UNDERLYING_TRACKING`) et [test_overclimate.py](../../tests/test_overclimate.py) (préparation de l'état HA et réarmement ajoutés avant le candidat).
- Documents : spécifications FR/EN, conception v3.5 et revue #2159 (commits antérieurs de documentation ; lus pour les critères, non revus en profondeur).

## 2. Exigences et critères comparés

Référentiel : [revue #2159](issue-2159-review.md), [spécification FR](issue-2141-specification_fr.md), [spécification EN](issue-2141-specification_en.md), [conception](issue-2141-design.md) v3.5. Les critères retirés ou différés (AC-029/030/033 à 038, O-01, extensions de température Q-07 à Q-09) ne sont pas évalués comme des échecs.

| Exigence cible                                              | Constat                                                                                                                                                                                                                                                                                                                                                                  |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Production limitée à `ThermostatOverClimate`                | Conforme (diff contre `main`).                                                                                                                                                                                                                                                                                                                                           |
| Compteur unique, adoptions réelles + tentatives marquées    | Conforme en lecture : `_adopt_underlying_value` ([L877](../../custom_components/versatile_thermostat/thermostat_climate.py#L877)) ne débite que si la mutation est retenue.                                                                                                                                                                                              |
| Jamais de faux retour non adopté ; troisième débit immédiat | Conforme en lecture : `_record_underlying_tracking_command` ([L1129](../../custom_components/versatile_thermostat/thermostat_climate.py#L1129)) suspend dès 3.                                                                                                                                                                                                           |
| Mode/application avant candidate consigne + débounce        | Conforme : [L868-L875](../../custom_components/versatile_thermostat/thermostat_climate.py#L868-L875), puis candidat.                                                                                                                                                                                                                                                     |
| Source multi-TRV                                            | Corrigée (`other_under`, `under` conservé) ; testée avec permutations.                                                                                                                                                                                                                                                                                                   |
| États initiaux / reprises                                   | `old_state` absent/`unknown`/`unavailable` refusé ([L827-L834](../../custom_components/versatile_thermostat/thermostat_climate.py#L827-L834)) ; testé en appel direct.                                                                                                                                                                                                   |
| Modes valides                                               | Ensemble codé en dur identique à `VALID_HVAC_MODES` moins `unknown`/`unavailable` (voir F-1).                                                                                                                                                                                                                                                                            |
| Callback livré avec paramètre HVAC nul (AC-019/AC-031)      | **Conforme à la lettre, effet contesté** : le code adopte à partir de la paire `old_state`/`new_state` livrée, comme prescrit (AC-019, AC-031 cas « action seule changée »). Le cas « callback entièrement filtré » n'est pas livré et n'est pas recréé (voir ci-dessous). L'effet obtenu avec demande ≠ effectif est le constat E-1, qui relève d'une décision humaine. |
| Pas d'exigence OFF nouvelle, pas de borne globale `number`  | Conforme ; limites documentées (AC-039). Aucun plafond `number` introduit.                                                                                                                                                                                                                                                                                               |
| Commandes existantes non modifiées                          | Conforme (aucun changement de `underlyings.py`).                                                                                                                                                                                                                                                                                                                         |

**Distinction AC-031 (vérifiée par exécution, voir § 5)** : avec demande `HEAT`, effectif `OFF`, suivi actif et source `heat → off` :

- **Cas A, callback filtré entièrement** (consigne, action et fan inchangés) : le parent ne livre rien ; `ThermostatOverClimate.underlying_changed` n'est pas appelé ; aucune adoption, demande conservée à `HEAT`. Conforme à « l'enfant peut supprimer tout le callback » et à « ne recréer ni callback absent ».
- **Cas B, callback livré avec paramètre HVAC nul** (l'action change, ici `off → idle`) : l'appel contient `new_hvac_mode=None` mais les états `heat`/`off` ; la paire est qualifiée, la demande devient `OFF`, compteur à 1. Conforme à « appliquer AC-019 sous ses gardes », mais c'est ce comportement qui constitue E-1.

Les tests directs de #2159 (appel de `ThermostatOverClimate.underlying_changed` avec `None` partout, états sans attributs) se trouvent dans la configuration demande `HEAT` / effectif `OFF` (constaté par instrumentation) mais avec action inchangée : c'est un callback que le parent n'aurait pas livré (cas A), déduit des champs transmis. Ces tests vérifient donc la logique de l'enfant, pas le comportement d'AC-031 de bout en bout.

## 3. Constats

### E-1 — Élevé : adoption d'un OFF imposé par VTherm qui écrase la demande utilisateur `HEAT`

- **Emplacement :** [thermostat_climate.py#L827-L852](../../custom_components/versatile_thermostat/thermostat_climate.py#L827-L852), combiné à [underlyings.py#L837](../../custom_components/versatile_thermostat/underlyings.py#L837) et [underlyings.py#L843](../../custom_components/versatile_thermostat/underlyings.py#L843).
- **Mécanisme (fait vérifié) :** le parent met `new_hvac_mode=None` lorsque le mode rapporté est égal au mode **effectif** de VTherm, mais livre quand même l'événement si un autre champ (ici `hvac_action`) change. L'ancien enfant ignorait alors le mode (`if new_hvac_mode:`). Le nouvel enfant se fonde sur `old_state`/`new_state` et compare au mode **demandé** (`requested_state.hvac_mode`). Si la demande est `HEAT` et l'effectif `OFF` (fenêtre, mode central, arrêt automatique…), le retour du TRV `heat → off` accompagné d'un changement d'action est adopté comme nouvelle demande `OFF`.
- **Preuve exécutée (test temporaire hors dépôt, supprimé ensuite) :** flux réel `UnderlyingClimate._underlying_changed` ; demande `HEAT`, effectif `OFF`, TRV `heat/heating → off/off`.
  - Parent → enfant : `(new_hvac_mode=None, action='off', temp=None, fan=None)`.
  - Commit `98e5524` : `requested_state.hvac_mode == off`, compteur 1 (journal `tracking debit 1/3 … {'adoption': 'mode', …}`) → assertion « la demande reste HEAT » **en échec**.
  - Même test sur `HEAD~1` (extrait par `git archive` dans `/tmp`) : demande `heat`, compteur 0 → **réussite**. Il s'agit donc d'une régression de comportement introduite par ce commit.
- **Preuve complémentaire (révision du 2026-10-30, sonde temporaire hors dépôt, événements d'état Home Assistant réels, `update_states` neutralisé) :** demande `HEAT`, effectif `OFF`, suivi actif, TRV `heat/off → off`. Action inchangée (`off`) : aucun appel à `underlying_changed`, demande `HEAT`, compteur 0 (cas A). Action `off → idle` : appel `(None, 'idle', None, None, new=off, old=heat)`, demande `OFF`, compteur 1 (cas B). E-1 est donc reproduit par le chemin parent réel, pas seulement par un appel direct.
- **Impact (déduit statiquement, non reproduit de bout en bout) :** avec `follow_underlying_temp_change` actif, une demande `HEAT` peut être remplacée par `OFF` quand VTherm éteint lui-même le TRV ; à la réouverture de la fenêtre, la demande n'est plus `HEAT`, donc le chauffage ne reprend pas sans action de l'utilisateur. Chaque cas consomme aussi une unité du compteur partagé.
- **Lien avec les documents :** AC-031 (cas « action seule changée ») renvoie à AC-019 sous ses gardes (demande différente, suivi, alignement, budget) ; ces gardes sont satisfaites dans le cas B. L'implémentation suit donc la lettre des documents. Ceux-ci ne précisent pas si une demande `HEAT` doit être remplacée par un `OFF` que VTherm a lui-même imposé. Ce constat n'est ni une non-conformité avérée aux documents ni un comportement approuvé : une décision humaine est nécessaire.
- **Correction recommandée (non appliquée) :** ne pas adopter un mode égal au mode effectif de VTherm (même garde que le parent), par exemple exiger `new_hvac_mode is not None` en plus de la paire d'états valide, ou comparer aussi à `vtherm_hvac_mode` ; ajouter le test de non-régression via le parent réel.

### M-1 — Moyen : la couverture via le filtre parent ne couvre pas la configuration de E-1

**Correction (2026-10-30) :** la version précédente affirmait qu'aucun test #2159 n'utilisait `UnderlyingClimate._underlying_changed`. C'est faux. [test_issue_2159_additional.py](../../tests/test_issue_2159_additional.py) l'appelle dans `test_real_tagged_attempt_and_trvzb_resend` ([L681](../../tests/test_issue_2159_additional.py#L681)) et dans `test_saturating_off_publication_and_other_trv` ([L758](../../tests/test_issue_2159_additional.py#L758)). Les autres tests de [test_issue_2159.py](../../tests/test_issue_2159.py) et de ce fichier appellent directement `ThermostatOverClimate.underlying_changed(...)` ; les autres occurrences de `_underlying_changed` dans ces fichiers sont des `patch.object(..., new=AsyncMock())` qui neutralisent la méthode.

**Ce que couvrent les deux tests réels (constaté par instrumentation du paramètre transmis au parent) :**

- `test_real_tagged_attempt_and_trvzb_resend` : demande = effectif = `OFF` ; le parent transmet `new_hvac_mode=heat` (non nul).
- `test_saturating_off_publication_and_other_trv` : demande = effectif = `HEAT` ; le parent transmet `new_hvac_mode=off` (non nul).

**Lacune restante (fait vérifié) :** aucun test ne passe par le filtre parent avec demande `HEAT`, effectif `OFF`, suivi actif, paramètre HVAC nul et action modifiée (cas B d'E-1). Instrumentation de la suite complète : les appels parent→enfant avec paramètre HVAC nul, paire valide et demande ≠ effectif existent dans `test_auto_start_stop`, `test_auto_start_stop_stop_mode`, `test_bugs` (`test_bug_465`) et `test_inhibition`, mais avec `follow_underlying_temp_change` désactivé (aucune adoption, demande inchangée) ; ceux de #2159 sont des appels directs à action inchangée. C'est pourquoi E-1 n'est pas détecté par les 1076 tests.

**Sévérité réévaluée : Moyen, maintenue mais avec une portée plus étroite.** La lacune est ciblée (une configuration), non générale. Elle reste Moyen et non Faible car elle explique la non-détection d'un constat Élevé reproduit. Elle ne diminue pas E-1 et ne vaut pas approbation d'un correctif.

### M-2 — Moyen/faible : tests existants modifiés

[test_overclimate.py](../../tests/test_overclimate.py) : le test `test_underlying_action_change_keeps_pending_temperature_candidate` reçoit une préparation d'état HA, un réarmement externe et un second `async_set` juste avant l'échéance. Ces ajouts sont cohérents avec le nouveau recontrôle `closure_still_valid`, mais affaiblissent l'oracle d'origine. [test_multiple_switch.py](../../tests/test_multiple_switch.py) : changement attendu de `command_cause`. À valider explicitement.

### F-1 — Faible : maintenabilité et conventions

- [L827](../../custom_components/versatile_thermostat/thermostat_climate.py#L827) duplique `VALID_HVAC_MODES` de [vtherm_hvac_mode.py](../../custom_components/versatile_thermostat/vtherm_hvac_mode.py#L17) : risque de divergence.
- [L45](../../custom_components/versatile_thermostat/thermostat_climate.py#L45) : `pylint: disable=broad-exception-caught` posé pour toute la classe ; nombreux `except BaseException` avec relance différée (comportement cohérent) ; complexité élevée de `apply_candidate`/`closure_still_valid` ([L978](../../custom_components/versatile_thermostat/thermostat_climate.py#L978)), avec conditions de garde dupliquées.
- `_record_underlying_tracking_command` journalise chaque débit au niveau WARNING avec la représentation brute du dictionnaire.

### F-2 — Observation : changement de publication

Quand le suivi est désactivé ou l'alignement refusé, l'ancien code posait `changes = True` pour tout mode livré et republiait l'état ; le nouveau ne le fait plus. Aucun test en échec ; effet utilisateur non démontré.

## 4. Points positifs

- Périmètre de production respecté, #2141 interclasses conservé.
- Écrasement de la variable `under` corrigé ; observation et candidate restent rattachées au TRV source.
- Comptage unique par mutation réellement retenue, y compris en cas d'erreur après affectation ; nettoyage des candidats/pauses et réentrance eager couverts par plusieurs tests ciblés.
- Aucun secret, entrée externe non validée ni nouvelle surface de sécurité identifiés ; aucun nouveau service appelé.

## 5. Validations

| Vérification                                                                                                             | Statut        | Résultat                                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------------ | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.venv/bin/python -m pytest -q -x -p no:cacheprovider` (suite complète)                                                  | **Réexécuté** | `1076 passed, 2 skipped, 14 subtests passed in 113.78s` (Python 3.14.8) : confirme la valeur rapportée                                                               |
| `git diff --check main...HEAD` et `git diff --check HEAD`                                                                | **Réexécuté** | Sans défaut                                                                                                                                                          |
| Diagnostics éditeur sur les trois fichiers touchés                                                                       | **Réexécuté** | Un seul message : `TODO` préexistant en [L599](../../custom_components/versatile_thermostat/thermostat_climate.py#L599), hors diff                                   |
| Reproduction E-1 (courant puis `HEAD~1`)                                                                                 | **Exécuté**   | Échec sur `98e5524`, réussite sur `HEAD~1`                                                                                                                           |
| Sonde parent réel, demande `HEAT`/effectif `OFF`, `heat → off` avec et sans changement d'action (2026-10-30, hors dépôt) | **Exécuté**   | Sans changement d'action : aucun appel, demande `HEAT`. Avec `off → idle` : appel à paramètre nul, demande `OFF`, compteur 1                                         |
| Instrumentation des deux tests parent réel (`-k "real_tagged or saturating"`)                                            | **Exécuté**   | 4 réussis ; paramètre HVAC transmis non nul dans les deux cas, demande = effectif                                                                                    |
| Instrumentation de la suite complète (appels à paramètre nul, paire valide, demande ≠ effectif)                          | **Exécuté**   | 1076 réussis, 2 ignorés ; occurrences dans les tests #2159 (appels directs, action inchangée) et dans 4 fichiers préexistants (suivi désactivé, voir ligne suivante) |
| Rejeu ciblé `test_auto_start_stop*`, `test_bugs`, `test_inhibition` avec espion                                          | **Exécuté**   | 97 réussis, 1 ignoré ; `follow=False`, demande inchangée dans tous les appels repérés                                                                                |
| Intégration Home Assistant / matériel TRVZB                                                                              | Non effectué  | Aucun accès                                                                                                                                                          |
| Lint/format complets (pylint, black), couverture                                                                         | Non effectué  | Non lancés                                                                                                                                                           |
| Détail du 6ᵉ check GitHub                                                                                                | Non vérifié   | Page PR sans détail exploitable                                                                                                                                      |

## 6. Limites et risques résiduels

- Le compteur partagé peut saturer après des gestes légitimes ; un OFF adopté au seuil peut ne pas être transmis (AC-039, sans exigence OFF nouvelle). Aucun plafond global `climate`/`number` : non demandé.
- L'origine matérielle du premier `off` de l'issue reste inconnue ; la correction ne garantit pas la disparition de la boucle TRVZB. Aucune garantie physique n'est déduite.
- Conséquence aval de E-1 déduite du code, non reproduite avec une fenêtre réelle.
- Réentrance eager : testée localement, non comparée sur HA réel.
- Changements hors périmètre : aucun fichier de production hors périmètre ; les modifications de `test_overclimate.py` et `test_multiple_switch.py` sont des ajustements de tests existants dans le commit `98e5524` (auteur Jean-Marc Collin).

## 7. Décision proposée

**Corriger avant approbation.** E-1 est une régression de comportement reproduite par rapport à `HEAD~1` (demande `HEAT` remplacée par un `OFF` imposé par VTherm) ; elle découle de la lettre d'AC-019/AC-031 et nécessite une décision humaine. Aucun correctif n'est approuvé par cette revue. Hors E-1, l'implémentation respecte le périmètre et les décisions sur le compteur unique.

## 8. Actions de suivi

1. Décision humaine : le cas B d'AC-031 (callback livré avec paramètre HVAC nul, demande ≠ effectif) reste-t-il adopté ou est-il exclu ? Proposition : l'exclure et préciser AC-031.
2. Après autorisation, corriger E-1 dans `ThermostatOverClimate` uniquement et ajouter un test passant par `UnderlyingClimate._underlying_changed` (demande `HEAT`, effectif `OFF`, suivi actif, action changée) ; ajouter aussi le cas A (callback filtré, demande conservée).
3. Valider ou rétablir les modifications de `test_overclimate.py` (M-2).
4. Optionnel : réutiliser `VALID_HVAC_MODES` et réduire la portée de la désactivation pylint (F-1).
5. Identifier le sixième check GitHub.
6. Reproduire sur banc TRVZB réel si possible.
