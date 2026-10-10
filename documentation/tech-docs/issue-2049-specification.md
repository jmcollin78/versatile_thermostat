# Spécification fonctionnelle bilingue — Issue GitHub #2049

## Métadonnées / Metadata

| Élément                              | Valeur / Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nom / Name                           | Amorçage ciblé des degrés de régulation de vanne / Targeted valve-regulation degree bootstrap                                                                                                                                                                                                                                                                                                                                                                                             |
| Issue                                | [#2049](https://github.com/jmcollin78/versatile_thermostat/issues/2049)                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Version                              | 2.0 — seed one-shot minimal                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Statut / Status                      | À valider avant développement / Pending validation before development                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Date                                 | 2026-10-10                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Propriétaire / Owner                 | Équipe versatile_thermostat                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Sources analysées / Sources reviewed | [issue-2049-review.md](issue-2049-review.md), [underlying_state_manager.py](../../custom_components/versatile_thermostat/underlying_state_manager.py), [underlyings.py](../../custom_components/versatile_thermostat/underlyings.py), [thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py), [test_check_initial_state.py](../../tests/test_check_initial_state.py), [test_overclimate_valve.py](../../tests/test_overclimate_valve.py) |

---

# Version française

## 1. Contexte et objectifs

L’issue #2049 décrit un blocage durable après redémarrage de Home Assistant pour des thermostats `over_climate` utilisant `auto_regulation_valve`. Les entités `number` configurées comme `opening_degree` et `closing_degree` peuvent rester `STATE_UNKNOWN` lorsqu’elles représentent une consigne d’écriture sans retour de position fiable. Le thermostat attend alors leur initialisation et n’émet pas la commande qui pourrait leur attribuer une valeur.

Le système doit permettre un amorçage ciblé, sûr, borné et traçable de ces deux nombres afin d’éviter l’attente infinie, sans affaiblir la règle générale d’initialisation pour les autres sous-jacents. L’objectif n’est pas de déclarer silencieusement sain un appareil défaillant, mais de traiter explicitement le cas fonctionnel des consignes de régulation de vanne sans retour exploitable.

**Risque majeur :** une exception d’initialisation trop large peut masquer une panne réelle et provoquer des régressions dans les cas nominaux. Les cas de non-régression sont donc obligatoires et prioritaires.

## 2. Acteurs et cas d’utilisation

### Acteurs

- **Utilisateur final :** attend que le chauffage récupère après un redémarrage ou un rechargement.
- **Intégration VTherm :** surveille l’état des sous-jacents et pilote les degrés d’ouverture/fermeture.
- **Mainteneur/testeur :** vérifie la sécurité, les limites d’écriture et la non-régression.

### UC-001 — Démarrage ou rechargement avec nombres disponibles
1. VTherm observe les nombres de régulation.
2. Si les valeurs sont numériques et valides, le flux nominal est conservé.
3. Le thermostat termine son initialisation selon les règles existantes.

### UC-002 — Amorçage d’un nombre ciblé en `STATE_UNKNOWN`
1. VTherm identifie un `opening_degree` ou `closing_degree` configuré pour `auto_regulation_valve` dont l’état est exactement `STATE_UNKNOWN`.
2. Il applique au plus une valeur d’amorçage approuvée, dans les limites configurées.
3. Il n’impose jamais la readiness et attend le retour numérique via `UnderlyingStateManager`.

### UC-003 — Sous-jacent réellement indisponible

Un capteur, une entité `climate`, une cible de la paire à `STATE_UNAVAILABLE` ou tout autre sous-jacent non couvert par le seed reste soumis à la règle générale. Aucune écriture n’est émise sur la paire lorsqu’une cible configurée est indisponible, absente ou invalide.

### UC-004 — Commande de régulation courante
Après l’amorçage, les commandes usuelles continuent de calculer et d’envoyer les degrés d’ouverture et de fermeture selon les seuils et limites configurés.

## 3. Exigences fonctionnelles

- **FR-001** — Le système doit cibler uniquement les entités `number` configurées comme `opening_degree` ou `closing_degree` d’une régulation `auto_regulation_valve`.
- **FR-002** — Le système doit autoriser une seed uniquement lorsque l’état courant est exactement `STATE_UNKNOWN` et ne doit jamais modifier directement `_is_initialized` ni fournir de mécanisme parallèle de finalisation.
- **FR-003** — Le système doit calculer la valeur d’amorçage comme la paire de fermeture produite par l’algorithme existant avec une demande `d=0`, jamais avec la demande courante, avant toute écriture.
- **FR-004** — La valeur écrite doit respecter les bornes et seuils configurés; aucune valeur hors plage ne doit être envoyée.
- **FR-005** — L’amorçage doit être limité à une écriture au maximum par cible et par instance.
- **FR-005a** — Si une cible configurée est `STATE_UNAVAILABLE`, absente/`None`, non numérique, invalide ou possède des bornes invalides, aucune cible de la paire ne doit être écrite.
- **FR-005b** — Si toutes les cibles sont numériques ou exactement `STATE_UNKNOWN` et que les préconditions communes sont valides, une seule fois uniquement chaque cible `STATE_UNKNOWN` doit être écrite avec sa composante calculée à `d=0`; les cibles numériques ne doivent pas être réécrites.
- **FR-006a** — L’acceptation du service ne constitue jamais une readiness ; l’initialisation doit exiger un état numérique pour chaque cible requise et le retour doit être observé par `UnderlyingStateManager`.
- **FR-007** — En cas d’échec, le système doit conserver un diagnostic explicite d’état non initialisé/en erreur et ne doit pas présenter silencieusement l’appareil comme sain.
- **FR-008** — Une fois les états numériques présents, l’initialisation doit suivre uniquement le chemin historique `manager → check_initial_state → parent`, sans modifier l’algorithme TPI ni la formule de calcul des degrés.
- **FR-009** — La règle générale des autres sous-jacents `unknown`/`unavailable` doit rester inchangée.
- **FR-010** — `check_and_repair` doit rester postérieur à l’initialisation et ne doit pas être dupliqué dans la seed.
- **FR-011** — Le comportement doit être observable par les diagnostics sans exposer de données supplémentaires inutiles.

## 4. Règles métier

- **BR-001** — L’exception de seed s’applique à l’entité configurée, non à sa marque, son modèle, son firmware ou son intégration radio.
- **BR-002** — Une valeur numérique disponible suit toujours le chemin nominal et ne doit pas être réécrite uniquement parce que le seed existe.
- **BR-003** — Une cible indisponible, absente ou invalide reste bloquante et interdit toute écriture de la paire ; les autres sous-jacents conservent la règle générale.
- **BR-004** — Le seed ne doit jamais contourner les limites `opening_threshold`, `min_opening_degree`, `max_opening_degree` ou `max_closing_degree` applicables.
- **BR-005** — Une configuration incohérente ou une limite absente ne doit pas être compensée par une valeur arbitraire; le système doit signaler l’erreur et ne pas émettre une consigne non sûre.
- **BR-006** — La fin d’amorçage ne prouve pas l’existence d’un retour physique de position; elle autorise seulement la progression du flux défini pour les consignes d’écriture.
- **BR-007** — `UnderlyingStateManager` reste seul responsable de la readiness ; sans retour numérique, l’underlying reste non prêt, sans timeout, retry ni fallback.
## 6. Contraintes fonctionnelles

- La sécurité du chauffage et la détection des pannes priment sur la récupération automatique.

## 7. Critères d’acceptation

- **AC-001** — Avec des degrés d’ouverture et de fermeture numériques au démarrage, aucun seed supplémentaire n’a lieu et le thermostat démarre comme auparavant.
- **AC-002** — Une cible exactement `STATE_UNKNOWN` reçoit au plus une écriture sûre et bornée.
- **AC-003** — L’acceptation du service ne permet pas à elle seule de quitter l’état non initialisé.
- **AC-003a** — Un état numérique pour chaque cible requise autorise la progression uniquement par le flux historique du gestionnaire.
- **AC-004** — Si l’écriture échoue, le thermostat ne boucle pas, ne publie pas une fausse disponibilité et expose l’erreur.
- **AC-004a** — Une cible `STATE_UNAVAILABLE`, absente, invalide, à bornes invalides ou sans retour numérique n’entraîne aucune nouvelle écriture ni retry dans l’instance.
- **AC-005** — Tout état autre que `STATE_UNKNOWN` sur une cible de seed, notamment `STATE_UNAVAILABLE`, `None`, absent, numérique ou invalide, reste sans écriture; les autres sous-jacents restent régis par la règle générale.
- **AC-006** — Une commande chauffage, arrêt et changement de mode après amorçage conserve les valeurs calculées attendues.
- **AC-007** — Les seuils et limites configurés sont respectés pour l’amorçage et les commandes usuelles, y compris les valeurs minimales et maximales.
- **AC-008** — Un appareil avec retour de position conserve son comportement nominal et n’est pas forcé à une valeur uniquement par la présence de la nouvelle logique.
- **AC-009** — Un rechargement répété ne provoque pas d’écritures non bornées.
- **AC-010** — Les diagnostics permettent d’identifier l’entité ciblée et le résultat sans masquer une indisponibilité réelle.
- **AC-011** — `check_and_repair` est appelé uniquement après l’initialisation et n’est pas dupliqué par la seed.

## 8. Matrice de tests obligatoire

| ID    | Scénario                                         | Résultat attendu                                                 |
| ----- | ------------------------------------------------ | ---------------------------------------------------------------- |
| T-001 | Deux nombres disponibles et valides              | Démarrage nominal; aucune régression.                            |
| T-002 | `opening_degree` `STATE_UNKNOWN` au démarrage    | Amorçage ciblé borné, une écriture au maximum.                   |
| T-003 | `closing_degree` `STATE_UNKNOWN` au démarrage    | Même traitement ciblé, une écriture au maximum.                  |
| T-004 | Cible `STATE_UNAVAILABLE`                        | Aucune écriture ; thermostat non prêt.                           |
| T-005 | Cible absente                                    | Aucune écriture ; diagnostic.                                    |
| T-006 | Bornes invalides                                 | Aucune écriture ; diagnostic.                                    |
| T-007 | Écriture refusée/exception                       | Non prêt, diagnostic, aucun retry.                               |
| T-008 | Service accepté, état `STATE_UNKNOWN` persistant | Non prêt ; l’acceptation n’est pas la readiness.                 |
| T-009 | Commande de chauffage usuelle                    | Degrés calculés et envoyés comme avant.                          |
| T-010 | Commande d’arrêt / HVAC OFF                      | Seuil minimal et fermeture attendus respectés.                   |
| T-011 | Valeur au seuil minimal                          | Aucun dépassement ni valeur négative.                            |
| T-012 | Valeur au seuil maximal                          | Aucun dépassement des maxima configurés.                         |
| T-013 | Appareil avec retour de position                 | Flux nominal inchangé ; aucune réécriture parasite.              |
| T-014 | Deux cibles `STATE_UNKNOWN`                      | Au plus une commande par cible ; aucune double commande.         |
| T-015 | État numérique après seed                        | Reprise uniquement par `manager → check_initial_state → parent`. |
## 9. Fonctions non prises en compte

- Modification générale de `UnderlyingStateManager` pour ignorer les états inconnus ou indisponibles.
- Déclaration d’un appareil sain sans preuve d’écriture ou de préconditions satisfaites.

## 10. Évolutions futures proposées

- Étendre la liste des profils vérifiés dans la documentation de compatibilité et de dépannage livrée avec la correction.

## 11. Faits, hypothèses, décisions et questions ouvertes

- Le gestionnaire évalue l’initialisation à partir des états des sous-jacents; la présente exception de seed est strictement limitée à `STATE_UNKNOWN`.
- `UnderlyingValveRegulation` surveille explicitement les nombres d’ouverture et de fermeture et envoie ces valeurs lors des commandes.
- Le thermostat `over_climate_valve` exige l’initialisation de ses sous-jacents de régulation.

- Le cas #2049 concerne des consignes d’écriture dont le retour peut rester absent après redémarrage.
- Une valeur sûre peut être calculée ou restaurée à partir de la configuration et du contexte de régulation.
- L’exception doit être déterminée par la configuration de l’entité, non par la marque de l’appareil.

### Décisions normatives intégrées

- **DEC-001 — Valeur :** la seed est la paire de fermeture calculée avec une demande `d=0` par l’algorithme existant, jamais la demande courante.
- **DEC-002 — Responsabilité :** `UnderlyingStateManager` est seul responsable de la readiness ; sans retour numérique, aucun timeout, retry ou fallback n’est ajouté.
- **DEC-003 — Atomicité :** une cible invalide, indisponible, absente/`None` ou à bornes invalides interdit toute écriture de la paire ; sinon seules les cibles exactement `STATE_UNKNOWN` sont écrites une fois.
- **DEC-004 — Documentation :** la documentation de compatibilité et de dépannage est un livrable obligatoire.

Aucune décision bloquante ne reste ouverte sur ces points.

Les versions précises de Home Assistant, Zigbee2MQTT et firmware du cas réel, ainsi que les journaux de reproduction, restent utiles mais ne bloquent pas la présente spécification.

---

# English version

## 1. Context and objectives

Issue #2049 reports a permanent post-restart deadlock for `over_climate` thermostats using `auto_regulation_valve`. The `number` entities configured as `opening_degree` and `closing_degree` may remain `unknown` when they are write-only setpoints without a reliable position state. The thermostat waits for their initialization and therefore does not issue the command that could assign them a value.

The system shall provide only a minimal one-shot seed for these two numbers, without changing initialization authority or weakening the general rule for other underlyings.

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

### UC-002 — Bootstrap of a targeted number in `STATE_UNKNOWN`
1. After normal listener installation, VTherm identifies a configured target whose state is exactly `unknown`.
2. It sends at most one safe value through existing write mechanisms and valid bounds.
3. Readiness is reevaluated only by `UnderlyingStateManager` through the historical flow.
4. `unavailable`, absent state, invalid bounds, write failure, or missing numeric feedback cause no further attempt during the instance.

### UC-003 — Actually unavailable underlying
A sensor, climate entity, or any other underlying not covered by the targeted exception remains subject to the general rule. Its `unknown`/`unavailable` state shall not be ignored by this specification.

### UC-004 — Normal regulation command
After bootstrap, normal commands continue calculating and sending opening and closing degrees according to configured thresholds and limits.

## 3. Functional requirements

- **FR-001** — The system shall target only `number` entities configured as `opening_degree` or `closing_degree` for an `auto_regulation_valve` regulation.
- **FR-002** — The system shall never directly set `_is_initialized` or provide a parallel finalization override.
- **FR-003** — The seed shall be the closing pair calculated by the existing algorithm with demand `d=0`, never current demand, before any write.
- **FR-004** — The written value shall respect configured bounds and thresholds; no out-of-range value shall be sent.
- **FR-005** — The system shall write at most once per target and instance through existing write mechanisms.
- **FR-005a** — If a configured target is `unavailable`, absent/`None`, non-numeric, invalid, or has invalid bounds, no target in the pair shall be written.
- **FR-005b** — If all targets are numeric or exactly `unknown` and common preconditions are valid, only each `unknown` target shall be written once with its `d=0` component; numeric targets shall not be rewritten.
- **FR-006a** — Service acceptance shall never mean readiness; initialization shall require a numeric state for every required target.
- **FR-007** — On failure, the system shall retain an explicit uninitialized/error diagnostic state and shall not silently present the device as healthy.
- **FR-008** — Once numeric states are present, initialization shall follow only `manager → check_initial_state → parent`, without changing the TPI algorithm or degree calculation formula.
- **FR-009** — The general rule for other `unknown`/`unavailable` underlyings shall remain unchanged.
- **FR-010** — `check_and_repair` shall remain post-initialization and shall not be duplicated in the seed.
- **FR-011** — The behavior shall be observable through diagnostics without exposing unnecessary additional data.

## 4. Business rules

- **BR-001** — The bootstrap exception applies to the configured entity, not to its brand, model, firmware, or radio integration.
- **BR-002** — An available numeric value always follows the nominal path; it shall not be rewritten solely because bootstrap exists.
- **BR-003** — An `unavailable`, absent, or invalid target remains blocking and forbids writing; other underlyings retain the general rule.
- **BR-004** — Bootstrap shall never bypass applicable `opening_threshold`, `min_opening_degree`, `max_opening_degree`, or `max_closing_degree` limits.
- **BR-005** — An inconsistent configuration or missing limit shall not be compensated by an arbitrary value; the system shall report the error and avoid an unsafe command.
- **BR-006** — Service acceptance does not prove numeric feedback, physical movement, or readiness; one successful target is insufficient when another required target is not numeric.
- **BR-007** — `UnderlyingStateManager` shall remain solely responsible for readiness; without numeric feedback, the underlying shall remain not ready, with no timeout, retry, or fallback.

## 5. Expected states and errors

| State                          | Condition                                                 | Expected behavior                                            |
| ------------------------------ | --------------------------------------------------------- | ------------------------------------------------------------ |
| `AVAILABLE_NOMINAL`            | Valid numeric value at start                              | No additional bootstrap; nominal path.                       |
| `TARGET_NEEDS_SEED`            | Targeted degree is exactly `unknown`, safe bounds hold    | One approved write at most.                                  |
| `SEED_ATTEMPTED`               | Existing write mechanism accepted or rejected the request | Readiness is not implied; manager remains authoritative.     |
| `SEED_FAILED`                  | Service rejected or raised an error                       | Explicit not-ready diagnostic; no retry during the instance. |
| `TARGET_STILL_UNKNOWN`         | No numeric state follows the seed                         | Not ready; explicit diagnostic; no retry.                    |
| `OTHER_UNDERLYING_UNAVAILABLE` | Other underlying unavailable                              | General rule unchanged; targeted bootstrap forbidden.        |
| `INVALID_CONFIGURATION`        | Inconsistent bounds or thresholds                         | No unsafe write; diagnostic error.                           |

## 6. Functional constraints

- Heating safety and failure detection take precedence over automatic recovery.
- Writes shall remain limited to the two explicitly targeted entity categories.
- The behavior shall support devices with position feedback and devices without it.
- No change shall be required in Zigbee2MQTT, firmware, radio cache, or Home Assistant state outside VTherm.
- Logs shall distinguish bootstrap, success, failure, and persistent absence of feedback.
- Compatibility and troubleshooting documentation shall be delivered with the feature and shall identify verified profiles, known limits, timeout/partial-failure symptoms, and recovery actions.

## 7. Acceptance criteria

- **AC-001** — With numeric opening and closing degrees at startup, no additional bootstrap occurs and the thermostat starts as before.
- **AC-002** — An exact `unknown` target receives at most one safe, bounded write.
- **AC-003** — Service acceptance alone does not leave the uninitialized state.
- **AC-003a** — A numeric state for every required target permits progress only through the historical manager flow.
- **AC-004** — If writing fails, the thermostat does not loop, does not report false health, and exposes the error.
- **AC-004a** — `unavailable`, absent state, invalid bounds, or missing numeric feedback causes no write or retry during the instance.
- **AC-005** — An `unknown`/`unavailable` sensor, climate entity, or other underlying remains blocking under the general rule.
- **AC-006** — Heating, stop, and mode-change commands after bootstrap retain their expected calculated values.
- **AC-007** — Configured thresholds and limits are respected for bootstrap and normal commands, including minimum and maximum values.
- **AC-008** — A device with position feedback retains nominal behavior and is not forced to a value solely because the new logic exists.
- **AC-009** — Repeated reloads do not cause unbounded writes.
- **AC-010** — Diagnostics identify the targeted entity and result without hiding a real unavailable state.
- **AC-011** — `check_and_repair` is called only post-initialization and is not duplicated by the seed.

## 8. Mandatory test matrix

| ID    | Scenario                                  | Expected result                                             |
| ----- | ----------------------------------------- | ----------------------------------------------------------- |
| T-001 | Both numbers available and valid          | Nominal startup; no regression.                             |
| T-002 | `opening_degree` `unknown` at startup     | One safe, bounded write at most once.                       |
| T-003 | `closing_degree` `unknown` at startup     | Same targeted handling.                                     |
| T-004 | Target `unavailable`                      | No write; thermostat remains not ready.                     |
| T-005 | Target absent                             | No write; diagnostic.                                       |
| T-006 | Invalid bounds                            | No write; diagnostic.                                       |
| T-007 | Write rejected/exception                  | Not ready, diagnostic, no retry.                            |
| T-008 | Service accepted, state remains `unknown` | Not ready; acceptance is not readiness.                     |
| T-009 | Normal heating command                    | Degrees calculated and sent as before.                      |
| T-010 | Stop / HVAC OFF command                   | Minimum threshold and closing behavior preserved.           |
| T-011 | Minimum threshold value                   | No underflow or negative value.                             |
| T-012 | Maximum threshold value                   | No configured maximum exceeded.                             |
| T-013 | Device with position feedback             | Nominal flow unchanged; no spurious rewrite.                |
| T-014 | Two targets `unknown`                     | At most one command per target; no double command.          |
| T-015 | Numeric state after seed                  | Resume only through manager → check_initial_state → parent. |

**Release gate:** T-001, T-004, T-005, T-006, T-007, T-008, T-011, T-012, T-013, T-014, and T-015 are mandatory non-regression tests. Any extra command, premature readiness, or change to historical flow blocks release.

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

### Integrated normative decisions

- **DEC-001 — Value:** the seed is the closing pair calculated with demand `d=0` by the existing algorithm, never current demand.
- **DEC-002 — Responsibility:** `UnderlyingStateManager` is solely responsible for readiness; no timeout, retry, or fallback is added without numeric feedback.
- **DEC-003 — Atomicity:** an invalid, unavailable, absent/`None`, or invalid-bounds target forbids any pair write; otherwise only exact `unknown` targets are written once.
- **DEC-004 — Documentation:** compatibility and troubleshooting documentation is a mandatory deliverable.

No blocking decision remains open on these points.

Removing the parallel machine, retries, finalization timeouts, and service-based readiness is mandatory and is not an open question.

The precise Home Assistant, Zigbee2MQTT, and device-firmware versions, plus reproduction logs, remain useful but are not blockers for this specification.
