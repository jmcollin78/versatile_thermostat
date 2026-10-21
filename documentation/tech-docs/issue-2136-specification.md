# Issue #2136 - Specification et convergence de conception

## 1. Titre et metadonnees

| Element      | Valeur                                                                                                                                                                                                                                     |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Nom          | Cycle de vie du capteur de fenetre lors de sa suppression et recreation                                                                                                                                                                    |
| Issue        | [#2136](https://github.com/jmcollin78/versatile_thermostat/issues/2136)                                                                                                                                                                    |
| Version      | 0.2 - convergence candidate a valider                                                                                                                                                                                                      |
| Statut       | Specification et conception candidates; developpement non autorise                                                                                                                                                                         |
| Date         | 2026-10-21                                                                                                                                                                                                                                 |
| Proprietaire | Mainteneurs de Versatile Thermostat                                                                                                                                                                                                        |
| Sources      | [rapport](issue-2136-review.md), [gestionnaire](../../custom_components/versatile_thermostat/feature_window_manager.py), [tests gestionnaire](../../tests/test_window_feature_manager.py), [tests integration](../../tests/test_window.py) |

## 2. Contexte et objectifs

### Faits etablis

- `FeatureWindowManager._window_sensor_changed` lit `new_state.state` avant la garde `new_state is None`; l'exception a ete reproduite en isolation.
- Home Assistant peut emettre `new_state = None` lors d'un rechargement de template.
- `refresh_state` ignore deja l'entite absente et les etats `unknown` ou `unavailable`.
- Le callback retourne `try_window_condition`, fermeture utilisee directement par les tests locaux.
- Les evenements `old_state = None` sont actuellement ignores par la branche de planification.
- `start_listening` arrete les listeners existants avant d'enregistrer celui du capteur configure.

### Objectif et perimetre

Le systeme doit tolerer suppression et recreation sans exception, commande HVAC injustifiee, effet de timer obsolete ou listener duplique. La detection doit reprendre sans recharger VTherm. Le perimetre couvre le capteur et ses delais `on`/`off`, en preservant actions, bypass, attributs et contrat `refresh_state`.

## 3. Acteurs et cas d'utilisation

- **Moteur d'etats Home Assistant:** emet changements, suppressions et recreations.
- **Gestionnaire de fenetre:** valide observations, gere le delai et applique l'etat confirme.
- **VTherm:** recoit un changement effectif et peut ajuster HVAC.
- **Utilisateur ou automation:** peut declencher un rechargement ou activer le bypass.

Cas: suppression (`new_state = None`), recreation avec `old_state = None`, rechargements repetes et transition valide apres le delai approprie.

## 4. Exigences fonctionnelles

- **FR-001:** traiter `new_state = None` sans dereferencer `state` ni lever d'exception.
- **FR-002:** conserver le dernier etat accepte pendant l'absence dans la meme instance vivante, hors reinitialisation par `post_init`; ne pas fabriquer `on` ou `off`.
- **FR-003:** annuler ou invalider toute observation en attente lors de la suppression ou d'un nouvel etat `unknown` ou `unavailable`, sans modifier le dernier etat accepte.
- **FR-004:** traiter `old_state = None` sans transition depuis un etat HA presume connu.
- **FR-005:** une recreation identique a l'etat confirme ne produit ni changement effectif ni commande HVAC.
- **FR-006:** une recreation differente repart d'une observation valide avec le delai normal correspondant.
- **FR-007:** `on` utilise le delai d'ouverture configure; `off`, le delai de fermeture configure.
- **FR-008:** une observation valide plus recente supplante l'ancienne; son callback obsolete ne change ni etat, ni attributs, ni HVAC.
- **FR-009:** ces garanties valent avec un timer `on` ou `off` en cours, dans les deux sens.
- **FR-010:** conserver une fermeture async callable pour les chemins valides; les branches ignorees retournent une fermeture async callable sans effet, sans imposer de revision des tests existants.
- **FR-011:** le bypass conserve sa semantique: observation valide memorisable, aucune action HVAC bypasssee.
- **FR-012:** un evenement dont les anciens et nouveaux etats sont presents et egaux (attributs seuls) ne planifie pas de transition et n'invalide pas une observation en attente encore valide.
- **FR-013:** les rechargements repetes restent sans exception, accumulation de callbacks ou listener duplique.
- **FR-014:** pour une configuration deja appliquee, demarrer ou redemarrer l'ecoute laisse un seul listener pour le capteur configure, aucun si aucun capteur n'est configure; l'arret retire ce listener.
- **FR-015:** suppression, `old_state = None`, etat egal, callback obsolete et bypass ne produisent aucune commande HVAC injustifiee.
- **FR-016:** le flux evenementiel de suppression, etat inexploitable et recreation ne doit pas appeler `refresh_state` ni court-circuiter le delai d'une recreation differente; `refresh_state` doit conserver son application immediate d'un etat exploitable a l'initialisation et ignorer l'absence, `unknown` et `unavailable` comme actuellement.

## 5. Regles fonctionnelles

- **BR-001:** l'absence du capteur n'est pas une fermeture.
- **BR-002:** la reference est le dernier etat confirme, non l'evenement de suppression.
- **BR-003:** un callback differe n'est valide que pour l'observation encore courante de l'instance vivante; apres suppression, etat inexploitable, nouvelle transition, `post_init` ou arret de l'ecoute, il est sans effet, meme si son timer a deja ete annule.
- **BR-004:** `old_state = None` signifie qu'aucun ancien etat HA n'est fiable; l'etat conserve du gestionnaire est la base.
- **BR-005:** une recreation identique ne rouvre ni ne ferme et ne declenche pas de travail HVAC.
- **BR-006:** une recreation differente demarre le delai directionnel normal.
- **BR-007:** dans le seul flux evenementiel retrait/recreation, une observation recreee differente doit satisfaire son delai directionnel avant application; ce flux ne doit pas appeler `refresh_state`. Cette regle ne s'applique pas a l'application immediate existante de `refresh_state` a l'initialisation.
- **BR-008:** le bypass ne transforme pas absence, callback obsolete, `unknown` ou `unavailable` en observation valide.
- **BR-009:** `unknown` et `unavailable` invalident l'observation en attente sans changer le dernier etat accepte; un retour exploitable different repart avec son delai directionnel, un retour identique n'applique rien. Aucune politique d'indisponibilite persistante n'est creee.
- **BR-010:** dans le flux evenementiel du capteur, une action HVAC de fenetre n'est permise qu'apres observation exploitable courante, delai satisfait et regles d'action applicables; cette regle ne restreint pas le `refresh_state` immediat d'initialisation.

## 6. Contraintes fonctionnelles

- Correction limitee au cycle de vie partage du gestionnaire de fenetre, sans refonte generale.
- Aucun changement de schema, action, template, dependance, configuration ou rechargement manuel VTherm.
- `@callback` sur une coroutine est hors perimetre sauf decision distincte.
- Les attributs publics capteur, etat, delais, action et bypass restent coherents.
- Aucune nouvelle politique pour detection automatique, indisponibilite durable ou securite chauffage.

## 7. Criteres d'acceptation

| ID     | Etant donne                               | Quand                                                       | Alors                                                                                                                                               |
| ------ | ----------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-001 | Un etat confirme est conserve             | `new_state = None`                                          | Aucune exception; etat inchange; aucun HVAC; timer obsolete invalide                                                                                |
| AC-002 | Le capteur est absent                     | Recreation avec `old_state = None` et meme etat exploitable | Aucun changement effectif, HVAC ou timer obsolete                                                                                                   |
| AC-003 | Etat conserve `off`                       | Recreation `on` avant le delai `on`                         | Etat et HVAC restent inchanges                                                                                                                      |
| AC-004 | Meme scenario                             | Delai `on` ecoule avec observation valide                   | Passage a `on` et une seule mise a jour justifiee                                                                                                   |
| AC-005 | Etat conserve `on`                        | Recreation `off` avant le delai `off`                       | Etat et HVAC restent inchanges                                                                                                                      |
| AC-006 | Meme scenario                             | Delai `off` ecoule avec observation valide                  | Passage a `off` et une seule mise a jour justifiee                                                                                                  |
| AC-007 | Un timer `on` ou `off` est actif          | Suppression puis recreation, meme ou autre etat             | L'ancien callback ne peut rien appliquer; seul le courant peut aboutir                                                                              |
| AC-008 | Une observation differee existe           | Une observation valide plus recente arrive                  | L'ancien callback reste sans effet sur etat, attributs et HVAC                                                                                      |
| AC-009 | Bypass actif                              | Transition valide atteint son delai                         | Semantique preservee sans action HVAC bypasssee                                                                                                     |
| AC-010 | Ancien et nouvel etat egaux               | Evenement d'attributs seuls avec timer valide               | Aucun nouveau timer, etat, attribut ou HVAC induit; timer valide conserve                                                                           |
| AC-011 | Configuration deja appliquee              | Retrait/recreation repetes, ecoute redemarree puis arretee  | Aucune exception; un listener au plus pour le capteur configure; aucun apres arret; callbacks anterieurs inertes                                    |
| AC-012 | Flux retrait/recreation et initialisation | Evenements bus puis `refresh_state` a l'initialisation      | Flux bus sans appel a `refresh_state`, reprise differente temporisee; refresh initial exploitable immediat, absence/`unknown`/`unavailable` ignores |
| AC-013 | Chemin valide ou branche ignoree          | La fermeture retournee est appelee directement              | Fermeture async callable; branche ignoree sans effet; aucun changement impose aux tests existants                                                   |
| AC-014 | Timer `on` ou `off` actif                 | `unknown` ou `unavailable`, puis retour exploitable         | Timer annule/invalide, ancien callback inerte, dernier etat conserve; retour different temporise, identique sans effet                              |

## 8. Fonctions exclues

Exclus: refonte generale callbacks/timers/logs; nouvelle securite pour indisponibilite durable; conversion absence vers `off`; modifications de `template.reload`, templates, algorithmes, schemas, dependances, autres integrations, code, tests, configuration, environnement HA, GitHub, branches et commits. Le retrait de `@callback` est exclu sans decision separee.

## 9. Evolutions futures proposees

Pistes non actuelles: diagnostic explicite d'absence et d'invalidation de timer; politique separee d'indisponibilite prolongee; revue independante du contrat `@callback`/`async` selon les versions HA supportees.

## 10. Hypotheses, questions ouvertes et tracabilite

### Hypotheses

- Un etat recree exploitable est different de `unknown` et `unavailable`, comme dans la garde actuelle de `refresh_state`.
- Le dernier etat accepte existe dans le modele courant; aucune persistance nouvelle n'est requise. `post_init` reinitialise cet etat: la conservation ne traverse pas cette reinitialisation.
- La conception propose une generation d'observation distincte de `dearm_window_timer`: elle invalide les callbacks apres retrait, etat inexploitable, nouvelle transition, `post_init` ou arret, tout en preservant la fermeture valide volontairement appelee apres desarmement du seul handle. Cette separation est justifiee par les appels directs des tests; elle ne constitue pas une exigence de mecanisme public.

### Validation humaine requise et questions ouvertes

La proposition tranche les comportements de retrait/recreation, des etats inexploitables, du callable et de `refresh_state` dans le perimetre defini. Aucune question technique bloquante n'est identifiee dans ce perimetre. La conception lue (version 0.1) comporte encore une table de divergence sur FR-016 a actualiser; la presente revision ne la modifie pas. Les documents finaux doivent etre presentes a l'utilisateur et obtenir une nouvelle validation explicite avant tout developpement; cette validation n'est pas encore obtenue.

### Tracabilite

- Cause et reproduction: [issue-2136-review.md](issue-2136-review.md), section "Verification executee", et `FeatureWindowManager._window_sensor_changed`.
- Ecoute et timers: `start_listening`, `stop_listening`, `dearm_window_timer` dans [feature_window_manager.py](../../custom_components/versatile_thermostat/feature_window_manager.py).
- Rafraichissement et application: `refresh_state`, `_window_sensor_changed`, `update_window_state` dans [feature_window_manager.py](../../custom_components/versatile_thermostat/feature_window_manager.py).
- Fermeture retournee et appels directs: [test_window_feature_manager.py](../../tests/test_window_feature_manager.py) et [test_window.py](../../tests/test_window.py).

---

# Issue #2136 - Specification and design convergence (English)

## 1. Title and metadata

| Item    | Value                                                                                                                                                                                                                           |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name    | Window sensor removal and recreation lifecycle                                                                                                                                                                                  |
| Issue   | [#2136](https://github.com/jmcollin78/versatile_thermostat/issues/2136)                                                                                                                                                         |
| Version | 0.2 - convergence candidate for validation                                                                                                                                                                                      |
| Status  | Specification and design candidate; development not authorized                                                                                                                                                                  |
| Date    | 2026-10-21                                                                                                                                                                                                                      |
| Owner   | Versatile Thermostat maintainers                                                                                                                                                                                                |
| Sources | [review](issue-2136-review.md), [manager](../../custom_components/versatile_thermostat/feature_window_manager.py), [manager tests](../../tests/test_window_feature_manager.py), [integration tests](../../tests/test_window.py) |

## 2. Context and objectives

### Established facts

- `FeatureWindowManager._window_sensor_changed` reads `new_state.state` before the `new_state is None` guard; the exception was reproduced in isolation.
- Home Assistant may emit `new_state = None` during a template reload.
- `refresh_state` already ignores a missing entity and `unknown` or `unavailable` states.
- The callback returns `try_window_condition`, a closure directly used by local tests.
- `old_state = None` events are currently ignored by the scheduling branch.
- `start_listening` stops existing listeners before registering one for the configured sensor.

### Objective and scope

The system shall tolerate removal and recreation without an exception, unjustified HVAC command, stale timer effect, or duplicated listener. Detection shall resume without reloading VTherm. The scope covers the sensor and delayed `on`/`off` processing while preserving existing actions, bypass, attributes, and `refresh_state` behavior.

## 3. Actors and use cases

- **Home Assistant state engine:** emits state, removal, and recreation events.
- **Window feature manager:** validates observations, owns the delay, and applies the confirmed state.
- **VTherm:** receives an effective change and may adjust HVAC.
- **User or automation:** may trigger a reload or enable bypass.

Use cases are sensor removal (`new_state = None`), recreation with `old_state = None`, repeated reloads, and completion of a valid delayed transition.

## 4. Functional requirements

- **FR-001:** Handle `new_state = None` without dereferencing `state` or raising an exception.
- **FR-002:** During absence retain the last accepted state within the same living instance, excluding reinitialization by `post_init`, and do not manufacture `on` or `off`.
- **FR-003:** Removal or a new `unknown` or `unavailable` state shall cancel or invalidate any pending observation without changing the last accepted state.
- **FR-004:** Handle `old_state = None` without treating it as a transition from a known HA state.
- **FR-005:** Same-state recreation shall cause no effective change or HVAC command.
- **FR-006:** Different-state recreation shall resume from a valid observation with its normal directional delay.
- **FR-007:** `on` shall use the configured opening delay; `off`, the configured closing delay.
- **FR-008:** A newer valid observation shall supersede the older one; its obsolete callback shall not change state, attributes, or HVAC.
- **FR-009:** These guarantees shall hold with an `on` or `off` timer active, in either direction.
- **FR-010:** Valid paths shall keep returning a callable async closure; ignored branches shall return a callable no-op async closure, without requiring a revision to existing tests.
- **FR-011:** Existing bypass semantics shall remain: a valid observation may be recorded, but no bypassed HVAC action shall apply.
- **FR-012:** An event with both states present and equal (attributes only) shall not schedule a transition or invalidate a still-valid pending observation.
- **FR-013:** Repeated reloads shall remain exception-free, shall not accumulate callbacks, and shall not duplicate the listener.
- **FR-014:** With configuration already applied, starting or restarting listening shall leave exactly one listener for the configured sensor, none if no sensor is configured; stopping shall remove that listener.
- **FR-015:** Removal, `old_state = None`, equal state, obsolete callback, and bypass shall not produce an unjustified HVAC command.
- **FR-016:** The removal, unusable-state, and recreation event flow shall not call `refresh_state` or bypass the delay for a different-state recreation; `refresh_state` shall retain its immediate application of a usable state at initialization and shall continue to ignore absence, `unknown`, and `unavailable`.

## 5. Business rules

- **BR-001:** Sensor absence is not window closure.
- **BR-002:** The reference is the last confirmed state, not the removal event.
- **BR-003:** A delayed callback is valid only for the still-current observation of the living instance; after removal, an unusable state, a newer transition, `post_init`, or stopping listening it shall be a no-op, even if its timer has already been cancelled.
- **BR-004:** `old_state = None` means no previous HA state is trusted; the retained manager state is the baseline.
- **BR-005:** Same-state recreation neither opens nor closes the window and does no HVAC work.
- **BR-006:** Different-state recreation starts the normal directional delay.
- **BR-007:** Only in the removal/recreation event flow, a different-state recreated observation shall satisfy its directional delay before application; that flow shall not call `refresh_state`. This rule does not apply to the existing immediate `refresh_state` application at initialization.
- **BR-008:** Bypass does not turn absence, an obsolete callback, `unknown`, or `unavailable` into a valid observation.
- **BR-009:** `unknown` and `unavailable` shall invalidate the pending observation without changing the last accepted state; a different usable return shall restart its directional delay, while a matching return shall have no effect. No persistent-unavailability policy is created.
- **BR-010:** In the sensor event flow, a window HVAC action is permitted only when a current usable observation satisfies its delay and existing action rules require the change; this rule does not restrict immediate initialization `refresh_state`.

## 6. Functional constraints

- The change remains limited to the shared window-manager lifecycle, without a general callback or manager refactor.
- No user schema, action, template, dependency, configuration, or manual VTherm reload behavior changes.
- The `@callback` on coroutine question is out of scope unless separately decided.
- Public manager attributes for sensor, state, delays, action, and bypass remain coherent.
- No policy is inferred for automatic detection, persistent unavailability, or heating safety.

## 7. Acceptance criteria

| ID     | Given                                      | When                                                        | Then                                                                                                                                               |
| ------ | ------------------------------------------ | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-001 | A confirmed state is retained              | `new_state = None`                                          | No exception; state unchanged; no HVAC; obsolete timer invalidated                                                                                 |
| AC-002 | The sensor is absent                       | Recreation has `old_state = None` and the same usable state | No effective change, HVAC command, or stale timer                                                                                                  |
| AC-003 | Retained state is `off`                    | Recreation is `on` before the `on` delay                    | State and HVAC remain unchanged                                                                                                                    |
| AC-004 | Same scenario                              | The `on` delay elapses while valid                          | State becomes `on` with one justified update                                                                                                       |
| AC-005 | Retained state is `on`                     | Recreation is `off` before the `off` delay                  | State and HVAC remain unchanged                                                                                                                    |
| AC-006 | Same scenario                              | The `off` delay elapses while valid                         | State becomes `off` with one justified update                                                                                                      |
| AC-007 | An `on` or `off` timer is active           | Removal is followed by same- or different-state recreation  | The old callback cannot apply; only the current one can complete                                                                                   |
| AC-008 | A delayed observation exists               | A newer valid observation arrives                           | The old callback has no effect on state, attributes, or HVAC                                                                                       |
| AC-009 | Bypass is enabled                          | A valid delayed transition completes                        | Existing semantics are preserved without bypassed HVAC action                                                                                      |
| AC-010 | Old and new states are equal               | An attributes-only event arrives with a valid timer         | No new timer, state, attribute, or HVAC change; valid timer retained                                                                               |
| AC-011 | Configuration is already applied           | Removal/recreation repeat; listening restarts then stops    | No exception; at most one listener for the configured sensor; none after stop; earlier callbacks inert                                             |
| AC-012 | Removal/recreation flow and initialization | Bus events then initialization `refresh_state` occur        | No `refresh_state` call from bus flow; different-state recovery delayed; usable initial refresh immediate, absence/`unknown`/`unavailable` ignored |
| AC-013 | A valid path or an ignored branch          | The returned closure is called directly                     | Callable async closure; ignored branch has no effect; existing tests need no change                                                                |
| AC-014 | An `on` or `off` timer is active           | `unknown` or `unavailable`, then a usable return            | Timer cancelled/invalidated, old callback inert, last state retained; different return delayed, matching return has no effect                      |

## 8. Out of scope

Excluded are general callback, timer, or logging refactors; a new safety policy for persistent unavailability; converting absence to `off`; changes to `template.reload`, templates, algorithms, schemas, dependencies, other integrations, code, tests, configuration, HA environment, GitHub actions, branches, and commits. Removing `@callback` is also excluded without a separate decision.

## 9. Proposed future evolution

These are not current requirements: an explicit diagnostic for absence and timer invalidation; a separate policy for prolonged unavailability; and an independent review of the `@callback`/`async` contract for supported HA versions.

## 10. Assumptions, open questions, and traceability

### Assumptions

- A usable recreated state differs from `unknown` and `unavailable`, as in the current `refresh_state` guard.
- The last accepted state exists in the current manager model; no new persistence is required. `post_init` resets that state: retention does not survive reinitialization.
- The design proposes an observation generation separate from `dearm_window_timer`: it invalidates callbacks after removal, an unusable state, a newer transition, `post_init`, or stop, while preserving a valid closure deliberately invoked after cancelling only the handle. Direct test calls justify this separation; it is not a public mechanism requirement.

### Required human validation and open questions

The proposal resolves removal/recreation, unusable states, callable behavior, and `refresh_state` within the defined scope. No blocking technical question is identified within this scope. The design read (version 0.1) still has a FR-016 divergence table to update; this revision does not change it. The final documents must be presented to the user and receive separate explicit validation before development; that validation has **not** yet been obtained.

### Traceability

- Cause and reproduction: [issue-2136-review.md](issue-2136-review.md), section "Verification executee", and `FeatureWindowManager._window_sensor_changed`.
- Listening and timers: `start_listening`, `stop_listening`, and `dearm_window_timer` in [feature_window_manager.py](../../custom_components/versatile_thermostat/feature_window_manager.py).
- Refresh and application: `refresh_state`, `_window_sensor_changed`, and `update_window_state` in [feature_window_manager.py](../../custom_components/versatile_thermostat/feature_window_manager.py).
- Returned closure and direct calls: [test_window_feature_manager.py](../../tests/test_window_feature_manager.py) and [test_window.py](../../tests/test_window.py).
