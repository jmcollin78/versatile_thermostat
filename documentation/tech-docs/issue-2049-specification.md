# Spécification fonctionnelle bilingue — Issue GitHub #2049

## Métadonnées / Metadata

| Élément                              | Valeur / Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nom / Name                           | Amorçage ciblé des degrés de régulation de vanne / Targeted valve-regulation degree bootstrap                                                                                                                                                                                                                                                                                                                                                                                             |
| Issue                                | [#2049](https://github.com/jmcollin78/versatile_thermostat/issues/2049)                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Version                              | 1.0 — proposition approuvée pour conception                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Statut / Status                      | À valider avant développement / Pending validation before development                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Date                                 | 2026-10-10                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Propriétaire / Owner                 | Équipe versatile_thermostat                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Sources analysées / Sources reviewed | [issue-2049-review.md](issue-2049-review.md), [underlying_state_manager.py](../../custom_components/versatile_thermostat/underlying_state_manager.py), [underlyings.py](../../custom_components/versatile_thermostat/underlyings.py), [thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py), [test_check_initial_state.py](../../tests/test_check_initial_state.py), [test_overclimate_valve.py](../../tests/test_overclimate_valve.py) |

---

# Version française

## 1. Contexte et objectifs

L’issue #2049 décrit un blocage durable après redémarrage de Home Assistant pour des thermostats `over_climate` utilisant `auto_regulation_valve`. Les entités `number` configurées comme `opening_degree` et `closing_degree` peuvent rester `unknown` ou `unavailable` lorsqu’elles représentent une consigne d’écriture sans retour de position fiable. Le thermostat attend alors leur initialisation et n’émet pas la commande qui pourrait leur attribuer une valeur.

Le système doit permettre un amorçage ciblé, sûr, borné et traçable de ces deux nombres afin d’éviter l’attente infinie, sans affaiblir la règle générale d’initialisation pour les autres sous-jacents. L’objectif n’est pas de déclarer silencieusement sain un appareil défaillant, mais de traiter explicitement le cas fonctionnel des consignes de régulation de vanne sans retour exploitable.

**Risque majeur :** une exception d’initialisation trop large peut masquer une panne réelle et provoquer des régressions dans les cas nominaux. Les cas de non-régression sont donc obligatoires et prioritaires.

## 2. Acteurs et cas d’utilisation

### Acteurs

- **Utilisateur final :** attend que le chauffage récupère après un redémarrage ou un rechargement.
- **Intégration VTherm :** surveille l’état des sous-jacents et pilote les degrés d’ouverture/fermeture.
- **Appareil de chauffage :** reçoit les consignes `number`; il peut fournir ou non un retour d’état.
- **Mainteneur/testeur :** vérifie la sécurité, les limites d’écriture et la non-régression.

### UC-001 — Démarrage ou rechargement avec nombres disponibles
1. VTherm observe les nombres de régulation.
2. Si les valeurs sont numériques et valides, le flux nominal est conservé.
3. Le thermostat termine son initialisation selon les règles existantes.

### UC-002 — Amorçage d’un nombre ciblé non disponible
1. VTherm identifie un `opening_degree` ou `closing_degree` configuré pour `auto_regulation_valve` dont l’état est `unknown` ou `unavailable`.
2. Il applique la valeur d’amorçage approuvée, dans les limites configurées.
3. Il réévalue l’initialisation sans boucle d’écriture infinie.
4. Si l’écriture échoue ou si les préconditions de sécurité ne sont pas satisfaites, il conserve un état non initialisé explicite et expose une indication diagnostique.

### UC-003 — Sous-jacent réellement indisponible
Un capteur, une entité climate, ou tout autre sous-jacent non couvert par l’exception ciblée reste soumis à la règle générale. Son état `unknown`/`unavailable` ne doit pas être ignoré par cette spécification.

### UC-004 — Commande de régulation courante
Après l’amorçage, les commandes usuelles continuent de calculer et d’envoyer les degrés d’ouverture et de fermeture selon les seuils et limites configurés.

## 3. Exigences fonctionnelles

- **FR-001** — Le système doit cibler uniquement les entités `number` configurées comme `opening_degree` ou `closing_degree` d’une régulation `auto_regulation_valve`.
- **FR-002** — Le système doit considérer `unknown` et `unavailable` comme des états nécessitant un traitement d’amorçage uniquement dans le périmètre FR-001.
- **FR-003** — Le système doit choisir une valeur d’amorçage déterministe et sûre, validée par la décision DEC-001, avant toute écriture.
- **FR-004** — La valeur écrite doit respecter les bornes et seuils configurés; aucune valeur hors plage ne doit être envoyée.
- **FR-005** — L’amorçage doit être idempotent et limité : un même cycle de démarrage/rechargement ne doit pas produire une répétition illimitée d’écritures.
- **FR-006** — Le système doit distinguer une écriture réussie, une valeur toujours non disponible, une erreur d’écriture et une configuration invalide.
- **FR-007** — En cas d’échec, le système doit conserver un état diagnostique non initialisé ou en erreur; il ne doit pas présenter silencieusement l’appareil comme sain.
- **FR-008** — Une fois les préconditions remplies, le système doit reprendre l’initialisation et les commandes usuelles sans modifier l’algorithme TPI ni la formule de calcul des degrés.
- **FR-009** — La règle générale des autres sous-jacents `unknown`/`unavailable` doit rester inchangée.
- **FR-010** — Le comportement doit être observable au moyen de journaux ou attributs diagnostiques ne divulguant pas de données supplémentaires non nécessaires.

## 4. Règles métier

- **BR-001** — L’exception d’amorçage s’applique à l’entité configurée, pas à sa marque, son modèle, son firmware ou son intégration radio.
- **BR-002** — Une valeur disponible et numérique suit toujours le chemin nominal; elle ne doit pas être réécrite uniquement parce que l’amorçage existe.
- **BR-003** — Un état `unknown`/`unavailable` d’un sous-jacent qui n’est pas un degré ciblé reste bloquant conformément à la règle générale.
- **BR-004** — L’amorçage ne doit jamais contourner les seuils `opening_threshold`, `min_opening_degree`, `max_opening_degree` ou `max_closing_degree` applicables.
- **BR-005** — Une configuration incohérente ou une limite absente ne doit pas être compensée par une valeur arbitraire; le système doit signaler l’erreur et ne pas émettre une consigne non sûre.
- **BR-006** — La fin d’amorçage ne prouve pas l’existence d’un retour physique de position; elle autorise seulement la progression du flux défini pour les consignes d’écriture.
- **BR-007** — La récupération automatique ne doit pas dépendre d’une attente illimitée d’un événement externe.

## 5. États et erreurs attendus

| État                           | Condition                                                | Comportement attendu                                                                         |
| ------------------------------ | -------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `AVAILABLE_NOMINAL`            | Valeur numérique valide au démarrage                     | Aucun amorçage additionnel; chemin nominal.                                                  |
| `TARGET_NEEDS_BOOTSTRAP`       | Degré ciblé `unknown`/`unavailable`, préconditions sûres | Écriture de la valeur approuvée, au plus dans la limite définie.                             |
| `BOOTSTRAP_APPLIED`            | Écriture acceptée ou valeur devenue exploitable          | Réévaluation de l’initialisation et reprise contrôlée.                                       |
| `BOOTSTRAP_FAILED`             | Service refusé, exception ou timeout                     | État non initialisé/erreur explicite; pas de boucle infinie.                                 |
| `TARGET_STILL_UNAVAILABLE`     | Cible toujours non exploitable après la limite           | Diagnostic explicite et comportement de sécurité validé; aucune prétention de disponibilité. |
| `OTHER_UNDERLYING_UNAVAILABLE` | Autre sous-jacent indisponible                           | Règle générale inchangée; amorçage ciblé interdit.                                           |
| `INVALID_CONFIGURATION`        | Bornes ou relation de seuil incohérentes                 | Aucune écriture non sûre; erreur diagnostiquée.                                              |

## 6. Contraintes fonctionnelles

- La sécurité du chauffage et la détection des pannes priment sur la récupération automatique.
- L’écriture doit rester limitée aux deux catégories d’entités explicitement visées.
- Le comportement doit être compatible avec les appareils qui fournissent un retour de position et avec ceux qui n’en fournissent pas.
- Aucun changement ne doit être requis dans Zigbee2MQTT, le firmware, le cache radio ou l’état Home Assistant hors VTherm.
- Les journaux doivent être suffisamment explicites pour distinguer amorçage, succès, échec et absence persistante de retour.

## 7. Critères d’acceptation

- **AC-001** — Avec `opening_degree` et `closing_degree` numériques au démarrage, aucun amorçage supplémentaire n’est effectué et le thermostat démarre comme avant.
- **AC-002** — Avec un degré ciblé `unknown`/`unavailable`, une valeur conforme aux bornes est proposée selon DEC-001; l’écriture est limitée selon DEC-002.
- **AC-003** — Si l’écriture réussit, le thermostat peut sortir de l’état non initialisé et reprendre les commandes prévues.
- **AC-004** — Si l’écriture échoue, le thermostat ne boucle pas, n’annonce pas à tort un état sain et expose l’erreur.
- **AC-005** — Un `unknown`/`unavailable` sur un capteur, une entité climate ou un autre sous-jacent reste bloquant selon la règle générale.
- **AC-006** — Une commande chauffage, arrêt et changement de mode après amorçage conserve les valeurs calculées attendues.
- **AC-007** — Les seuils et limites configurés sont respectés pour l’amorçage et les commandes usuelles, y compris les valeurs minimales et maximales.
- **AC-008** — Un appareil avec retour de position conserve son comportement nominal et n’est pas forcé à une valeur uniquement par la présence de la nouvelle logique.
- **AC-009** — Un rechargement répété ne provoque pas d’écritures non bornées.
- **AC-010** — Les diagnostics permettent d’identifier l’entité ciblée et le résultat sans masquer une indisponibilité réelle.

## 8. Matrice de tests obligatoire

| ID    | Scénario                                       | Résultat attendu                                                                                       |
| ----- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| T-001 | Deux nombres disponibles et valides            | Démarrage nominal; aucune régression.                                                                  |
| T-002 | `opening_degree` `unknown` au démarrage        | Amorçage ciblé borné et valeur conforme.                                                               |
| T-003 | `closing_degree` `unavailable` au démarrage    | Même traitement ciblé, sans impact global.                                                             |
| T-004 | Les deux nombres non disponibles               | Traitement déterministe, limite respectée, pas de boucle.                                              |
| T-005 | Écriture refusée/exception                     | `BOOTSTRAP_FAILED`, diagnostic, pas de faux succès.                                                    |
| T-006 | Valeur toujours non disponible après tentative | `TARGET_STILL_UNAVAILABLE`, comportement de sécurité validé.                                           |
| T-007 | Autre sous-jacent `unknown`                    | Règle générale conservée; amorçage interdit.                                                           |
| T-008 | Autre sous-jacent `unavailable`                | Règle générale conservée; amorçage interdit.                                                           |
| T-009 | Commande de chauffage usuelle                  | Degrés calculés et envoyés comme avant.                                                                |
| T-010 | Commande d’arrêt / HVAC OFF                    | Seuil minimal et fermeture attendus respectés.                                                         |
| T-011 | Valeur au seuil minimal                        | Aucun dépassement ni valeur négative.                                                                  |
| T-012 | Valeur au seuil maximal                        | Aucun dépassement des maxima configurés.                                                               |
| T-013 | Appareil avec retour de position               | Flux nominal inchangé; pas de réécriture parasite.                                                     |
| T-014 | Rechargements successifs                       | Nombre d’écritures borné et comportement idempotent.                                                   |
| T-015 | Configuration de limites incohérente           | Erreur explicite, aucune commande non sûre.                                                            |
| T-016 | Documentation compatibilité/dépannage          | Compatibilité, limites et procédures couvrent rejet, réussite partielle, timeout et absence de retour. |

**Exigence de passage :** T-001, T-005, T-007, T-008, T-009, T-010, T-011, T-012 et T-013 sont des tests de non-régression obligatoires. Toute régression d’un cas nominal ou d’un garde-fou existant bloque la livraison, même si T-002 et T-003 réussissent.

## 9. Fonctions non prises en compte

- Modification générale de `UnderlyingStateManager` pour ignorer les états inconnus ou indisponibles.
- Détection générique de fabricant, modèle ou firmware.
- Modification de Zigbee2MQTT, du firmware, du cache ou des entités Home Assistant externes.
- Refonte du TPI, des seuils, de la recalibration ou des commandes manuelles.
- Déclaration d’un appareil sain sans preuve d’écriture ou de préconditions satisfaites.

## 10. Évolutions futures proposées

- Ajouter une procédure de diagnostic utilisateur pour les appareils sans retour.
- Étudier une télémétrie agrégée du nombre d’amorçages et d’échecs.
- Documenter les versions d’intégrations connues pour produire des consignes sans retour.
- Envisager une configuration explicite de stratégie d’amorçage si plusieurs appareils présentent des besoins différents.

## 11. Faits, hypothèses, décisions et questions ouvertes

### Faits vérifiés

- Le gestionnaire considère `None`, `unknown` et `unavailable` comme non initialisés.
- `UnderlyingValveRegulation` surveille explicitement les nombres d’ouverture et de fermeture et envoie ces valeurs lors des commandes.
- Le thermostat `over_climate_valve` exige l’initialisation de ses sous-jacents de régulation.
- Les tests existants couvrent les états inconnus/indisponibles, mais pas le cas durable décrit par l’issue.

### Hypothèses retenues pour la spécification

- Le cas #2049 concerne des consignes d’écriture dont le retour peut rester absent après redémarrage.
- Une valeur sûre peut être calculée ou restaurée à partir de la configuration et du contexte de régulation.
- L’exception doit être déterminée par la configuration de l’entité, non par la marque de l’appareil.

### Décisions à confirmer avant développement

- **DEC-001 — Valeur :** dernière valeur restaurée, valeur calculée par TPI, ou repli explicite dérivé des seuils.
- **DEC-002 — Limite :** nombre maximal de tentatives, fenêtre temporelle et déclencheurs exacts au démarrage/rechargement.
- **DEC-003 — Échec :** comportement de sécurité après échec ou persistance de `unknown`/`unavailable`.
- **DEC-004 — Diagnostic :** contenu exact des journaux/attributs et niveau de visibilité utilisateur.
- **DEC-005 — Timeout :** la conception propose un délai technique de **10 s par cible et par tentative**, mesuré sur l’appel de service. Un dépassement est un échec terminal (`BOOTSTRAP_FAILED`/`TIMED_OUT`), sans reprise ni seconde écriture dans le même cycle; le diagnostic et la récupération doivent exposer cette situation. Cette valeur est proposée pour validation par les tests T-005, T-006, T-014 et T-016, et reste à confirmer avant développement.
- **DEC-006 — Documentation :** profils et versions pouvant être déclarés vérifiés, emplacement et versionnement de la documentation de compatibilité/dépannage.

Les versions précises de Home Assistant, Zigbee2MQTT et firmware du cas réel, ainsi que les journaux de reproduction, restent utiles mais ne bloquent pas la présente spécification.

---

# English version

## 1. Context and objectives

Issue #2049 reports a permanent post-restart deadlock for `over_climate` thermostats using `auto_regulation_valve`. The `number` entities configured as `opening_degree` and `closing_degree` may remain `unknown` or `unavailable` when they are write-only setpoints without a reliable position state. The thermostat waits for their initialization and therefore does not issue the command that could assign them a value.

The system shall provide a targeted, safe, bounded, and observable bootstrap for these two numbers to prevent indefinite waiting, without weakening the general initialization rule for other underlyings. The goal is not to silently declare a faulty device healthy, but to explicitly handle write-only valve-regulation setpoints.

The scope also includes compatibility and troubleshooting documentation: covered profiles, known limits, the distinction between service acceptance and actual state, failure causes, and recovery actions.
**Major risk:** an overly broad initialization exception may hide a real failure and cause regressions in nominal cases. Non-regression cases are therefore mandatory and take priority.

## 2. Actors and use cases
### Actors

- **End user:** expects heating to recover after a restart or reload.
- **Heating device:** receives `number` setpoints and may or may not provide state feedback.
- **Maintainer/tester:** verifies safety, write limits, and non-regression.

### UC-001 — Start or reload with available numbers
1. VTherm observes the valve-regulation numbers.
2. If the values are numeric and valid, the nominal flow is preserved.
3. The thermostat completes initialization under the existing rules.

### UC-002 — Bootstrap of an unavailable targeted number
1. VTherm identifies a configured `opening_degree` or `closing_degree` whose state is `unknown` or `unavailable`.
2. It applies the approved bootstrap value within configured limits.
3. It reevaluates initialization without an unbounded write loop.
4. If writing fails or safety preconditions are not met, it retains an explicit uninitialized/error state and exposes diagnostics.

### UC-003 — Actually unavailable underlying
A sensor, climate entity, or any other underlying not covered by the targeted exception remains subject to the general rule. Its `unknown`/`unavailable` state shall not be ignored by this specification.

### UC-004 — Normal regulation command
After bootstrap, normal commands continue calculating and sending opening and closing degrees according to configured thresholds and limits.

## 3. Functional requirements

- **FR-001** — The system shall target only `number` entities configured as `opening_degree` or `closing_degree` for an `auto_regulation_valve` regulation.
- **FR-002** — The system shall treat `unknown` and `unavailable` as requiring bootstrap only within FR-001.
- **FR-003** — The system shall select a deterministic and safe bootstrap value approved by DEC-001 before writing.
- **FR-004** — The written value shall respect configured bounds and thresholds; no out-of-range value shall be sent.
- **FR-005** — Bootstrap shall be idempotent and bounded: one start/reload cycle shall not produce unlimited writes.
- **FR-006** — The system shall distinguish successful writing, still-unavailable state, write error, and invalid configuration.
- **FR-006a** — `BOOTSTRAP_APPLIED` shall mean only that Home Assistant accepted the service for the target; it shall not mean that the entity became available, the command was executed, or physical movement was confirmed.
- **FR-006b** — Resumption shall require every required target to succeed. Partial success shall remain not ready, retain per-target results, and expose the remaining failure.
- **FR-006c** — Any bootstrap timeout shall be treated as failure, never acceptance. The detailed timeout, status, diagnostic, and recovery contract shall be designed before development.
- **FR-007** — On failure, the system shall retain an explicit uninitialized/error diagnostic state and shall not silently present the device as healthy.
- **FR-008** — Once preconditions are met, the system shall resume initialization and normal commands without changing the TPI algorithm or degree calculation formula.
- **FR-009** — The general rule for other `unknown`/`unavailable` underlyings shall remain unchanged.
- **FR-010** — The behavior shall be observable through logs or diagnostic attributes without exposing unnecessary additional data.

## 4. Business rules

- **BR-001** — The bootstrap exception applies to the configured entity, not to its brand, model, firmware, or radio integration.
- **BR-002** — An available numeric value always follows the nominal path; it shall not be rewritten solely because bootstrap exists.
- **BR-003** — An `unknown`/`unavailable` state for an underlying that is not a targeted degree remains blocking under the general rule.
- **BR-004** — Bootstrap shall never bypass applicable `opening_threshold`, `min_opening_degree`, `max_opening_degree`, or `max_closing_degree` limits.
- **BR-005** — An inconsistent configuration or missing limit shall not be compensated by an arbitrary value; the system shall report the error and avoid an unsafe command.
- **BR-006** — Completing bootstrap does not prove physical position feedback exists; it only permits the defined write-only setpoint flow to progress.
- **BR-006a** — `BOOTSTRAP_APPLIED` is limited to Home Assistant service acceptance; the raw state may remain `unknown`/`unavailable` and physical movement may remain unconfirmed.
- **BR-006b** — One successful target is insufficient when multiple targets are required; any unsuccessful target keeps the underlying not ready.
- **BR-006c** — A timeout cannot imply success; its recovery contract remains subject to approval.
- **BR-007** — Automatic recovery shall not depend on waiting indefinitely for an external event.

## 5. Expected states and errors

| State                          | Condition                                                           | Expected behavior                                                            |
| ------------------------------ | ------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `AVAILABLE_NOMINAL`            | Valid numeric value at start                                        | No additional bootstrap; nominal path.                                       |
| `TARGET_NEEDS_BOOTSTRAP`       | Targeted degree is `unknown`/`unavailable`, safe preconditions hold | Write approved value, within the defined limit.                              |
| `BOOTSTRAP_APPLIED`            | Write accepted or value became usable                               | Controlled initialization reevaluation and resume.                           |
| `BOOTSTRAP_PARTIAL_FAILURE`    | One target succeeds and one required target fails                   | No resumption; retain per-target results and diagnose the remaining failure. |
| `BOOTSTRAP_FAILED`             | Service rejected, exception, or timeout                             | Explicit uninitialized/error state; no infinite loop.                        |
| `TARGET_STILL_UNAVAILABLE`     | Target remains unusable after the limit                             | Explicit diagnostic and approved safety behavior; no false availability.     |
| `OTHER_UNDERLYING_UNAVAILABLE` | Other underlying unavailable                                        | General rule unchanged; targeted bootstrap forbidden.                        |
| `INVALID_CONFIGURATION`        | Inconsistent bounds or thresholds                                   | No unsafe write; diagnostic error.                                           |

## 6. Functional constraints

- Heating safety and failure detection take precedence over automatic recovery.
- Writes shall remain limited to the two explicitly targeted entity categories.
- The behavior shall support devices with position feedback and devices without it.
- No change shall be required in Zigbee2MQTT, firmware, radio cache, or Home Assistant state outside VTherm.
- Logs shall distinguish bootstrap, success, failure, and persistent absence of feedback.
- Compatibility and troubleshooting documentation shall be delivered with the feature and shall identify verified profiles, known limits, timeout/partial-failure symptoms, and recovery actions.

## 7. Acceptance criteria

- **AC-001** — With numeric opening and closing degrees at startup, no additional bootstrap occurs and the thermostat starts as before.
- **AC-002** — With a targeted degree `unknown`/`unavailable`, a value complying with the limits is proposed according to DEC-001; writing is bounded according to DEC-002.
- **AC-003** — If writing succeeds, the thermostat can leave the uninitialized state and resume expected commands.
- **AC-003a** — A service accepted by Home Assistant produces `BOOTSTRAP_APPLIED` for that target only; diagnostics shall not claim availability or physical movement.
- **AC-003b** — If one required target succeeds while another fails or times out, the underlying and thermostat remain not ready and expose the partial failure.
- **AC-004** — If writing fails, the thermostat does not loop, does not report false health, and exposes the error.
- **AC-004a** — A bootstrap timeout is classified as failure, causes no resumption, and exposes the target and terminal status defined by the timeout contract.
- **AC-005** — An `unknown`/`unavailable` sensor, climate entity, or other underlying remains blocking under the general rule.
- **AC-006** — Heating, stop, and mode-change commands after bootstrap retain their expected calculated values.
- **AC-007** — Configured thresholds and limits are respected for bootstrap and normal commands, including minimum and maximum values.
- **AC-008** — A device with position feedback retains nominal behavior and is not forced to a value solely because the new logic exists.
- **AC-009** — Repeated reloads do not cause unbounded writes.
- **AC-010** — Diagnostics identify the targeted entity and result without hiding a real unavailable state.
- **AC-011** — Compatibility and troubleshooting documentation identifies covered configurations, known limits, exact `BOOTSTRAP_APPLIED` semantics, partial-failure/timeout symptoms, and recovery steps; unverified items are marked as such.

## 8. Mandatory test matrix

| ID    | Scenario                                  | Expected result                                       |
| ----- | ----------------------------------------- | ----------------------------------------------------- |
| T-001 | Both numbers available and valid          | Nominal startup; no regression.                       |
| T-002 | `opening_degree` `unknown` at startup     | Bounded targeted bootstrap and compliant value.       |
| T-003 | `closing_degree` `unavailable` at startup | Same targeted handling, no global impact.             |
| T-004 | Both numbers unavailable                  | Deterministic handling, bounded attempts, no loop.    |
| T-005 | Write rejected/exception                  | `BOOTSTRAP_FAILED`, diagnostic, no false success.     |
| T-006 | Target remains unavailable after attempt  | `TARGET_STILL_UNAVAILABLE`, approved safety behavior. |
| T-007 | Other underlying `unknown`                | General rule preserved; bootstrap forbidden.          |
| T-008 | Other underlying `unavailable`            | General rule preserved; bootstrap forbidden.          |
| T-009 | Normal heating command                    | Degrees calculated and sent as before.                |
| T-010 | Stop / HVAC OFF command                   | Minimum threshold and closing behavior preserved.     |
| T-011 | Minimum threshold value                   | No underflow or negative value.                       |
| T-012 | Maximum threshold value                   | No configured maximum exceeded.                       |
| T-013 | Device with position feedback             | Nominal flow unchanged; no spurious rewrite.          |
| T-014 | Successive reloads                        | Bounded write count and idempotent behavior.          |
| T-015 | Inconsistent limits configuration         | Explicit error; no unsafe command.                    |

**Release gate:** T-001, T-005, T-007, T-008, T-009, T-010, T-011, T-012, and T-013 are mandatory non-regression tests. Any regression in a nominal case or existing guardrail blocks release, even if T-002 and T-003 pass.

## 9. Out of scope

- General changes to `UnderlyingStateManager` to ignore unknown or unavailable states.
- Generic manufacturer, model, or firmware detection.
- Changes to Zigbee2MQTT, firmware, cache, or external Home Assistant entities.
- TPI, threshold, recalibration, or manual-command redesign.
- Declaring a device healthy without evidence of writing or satisfied preconditions.

## 10. Proposed future enhancements

- Add user-facing diagnosis for devices without feedback.
- Study aggregate telemetry for bootstrap attempts and failures.
- Document integration versions known to expose write-only setpoints.
- Consider an explicit bootstrap strategy setting if devices require different behavior.

## 11. Facts, assumptions, decisions, and open questions

### Verified facts

- The state manager treats `None`, `unknown`, and `unavailable` as uninitialized.
- `UnderlyingValveRegulation` explicitly monitors opening and closing numbers and sends those values during commands.
- The `over_climate_valve` thermostat requires its regulation underlyings to be initialized.
- Existing tests cover unknown/unavailable states, but not the persistent post-restart case described by the issue.

### Assumptions used by this specification

- The #2049 case concerns write-only setpoints whose feedback may remain absent after restart.
- A safe value can be calculated or restored from configuration and regulation context.
- The exception shall be determined by entity configuration, not device brand.

### Decisions to confirm before development

- **DEC-001 — Value:** last restored value, TPI-calculated value, or explicit threshold-derived fallback.
- **DEC-002 — Limit:** maximum attempts, time window, and exact startup/reload triggers.
- **DEC-003 — Failure:** safety behavior after a failed write or persistent `unknown`/`unavailable` state.
- **DEC-004 — Diagnostics:** exact log/attribute content and user visibility.
- **DEC-005 — Timeout:** the design proposes a technical timeout of **10 seconds per target and per attempt**, measured on the service call. Expiration is a terminal failure (`BOOTSTRAP_FAILED`/`TIMED_OUT`), with no retry or second write in the same cycle; diagnostics and recovery shall expose this condition. This value is proposed for validation by tests T-005, T-006, T-014, and T-016, and remains subject to confirmation before development.
- **DEC-006 — Documentation:** verified profiles/versions and documentation location/versioning.

The precise Home Assistant, Zigbee2MQTT, and device-firmware versions, plus reproduction logs, remain useful but are not blockers for this specification.
