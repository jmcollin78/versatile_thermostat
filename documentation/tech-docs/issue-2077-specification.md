# Spécification fonctionnelle bilingue / Bilingual Functional Specification

## Version française

### 1. Titre et métadonnées

- **Nom :** Issue GitHub #2077 — sommeil / mode maintenance de `ThermostatOverClimateValve`
- **Version :** 1.0
- **Statut :** proposée pour validation fonctionnelle
- **Date :** 2026-09-29
- **Propriétaire :** à désigner
- **Périmètre :** `ThermostatOverClimateValve` uniquement
- **Source de vérité approuvée :** [rapport de revue de l'issue #2077](issue-2077-review.md)
- **Sources analysées :** [thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py), [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py), [underlyings.py](../../custom_components/versatile_thermostat/underlyings.py), [vtherm_hvac_mode.py](../../custom_components/versatile_thermostat/vtherm_hvac_mode.py), [test_overclimate_valve.py](../../tests/test_overclimate_valve.py), [documentation utilisateur over-climate](../fr/over-climate.md)

### 2. Contexte et objectifs

Une TRV utilisée comme climat sous-jacent d'un VTherm `over_climate` peut fermer physiquement sa vanne lorsqu'elle reçoit `hvac_mode: off`. Le VTherm affiche alors correctement le sommeil comme un état public `OFF` et publie déjà une ouverture demandée de 100 % / une fermeture de 0 %, mais la commande `OFF` de la TRV empêche l'ouverture physique.

L'objectif est de réaliser le mode sommeil comme un mode de maintenance : maintenir la vanne physique totalement ouverte sans demander de chauffage à la chaudière. La correction doit concerner la commande adressée au climat sous-jacent de `ThermostatOverClimateValve`, sans modifier la représentation publique du VTherm ni le comportement des autres types de thermostat.

### 3. Acteurs et cas d'utilisation

#### Acteurs

- **Utilisateur ou automatisation :** demande l'entrée ou la sortie du mode sommeil.
- **VTherm `ThermostatOverClimateValve` :** expose l'état public, calcule l'ouverture et applique les règles de non-demande.
- **Climat sous-jacent / TRV :** reçoit le mode HVAC physique et les degrés d'ouverture/fermeture.
- **Chaudière centrale :** consomme l'état d'activité du VTherm ; elle ne doit pas être sollicitée par le sommeil.

#### Cas d'utilisation nominal : entrée en sommeil

1. Le VTherm est en `HEAT` ou `COOL` et régule normalement.
2. L'utilisateur ou une automatisation demande `SLEEP`.
3. Le VTherm conserve le mode interne `SLEEP` et expose `OFF` dans Home Assistant.
4. Le climat sous-jacent reçoit son mode physique actif : `HEAT` hors `ac_mode`, `COOL` avec `ac_mode`.
5. Les entités de degré reçoivent 100 % en ouverture et 0 % en fermeture.
6. Le VTherm reste inactif du point de vue de la régulation et de la chaudière.

#### Cas d'utilisation nominal : sortie du sommeil

1. Le VTherm est en `SLEEP`.
2. L'utilisateur ou une automatisation demande le mode de fonctionnement précédent ou un nouveau mode autorisé.
3. Le climat sous-jacent reçoit le mode correspondant au mode demandé.
4. La consigne et le préréglage conservés sont réutilisés selon le comportement normal.
5. La régulation reprend et l'ouverture n'est plus forcée à 100 %.

#### Cas d'utilisation : reprise ou redémarrage en sommeil

Au démarrage ou après restauration d'un VTherm dont le mode interne restauré est `SLEEP`, le système doit rétablir le contrat de sommeil : état public `OFF`, mode physique actif adapté à `ac_mode`, réémission inconditionnelle des deux degrés à 100 % / 0 % et absence de demande chaudière. Cette réémission doit avoir lieu après l'initialisation nécessaire des entités sous-jacentes.

### 4. Exigences fonctionnelles

- **FR-001 — Périmètre.** Le système doit appliquer ces règles uniquement à `ThermostatOverClimateValve` et à son climat sous-jacent utilisé pour la régulation directe de vanne.
- **FR-002 — État public.** Lorsque le mode interne du VTherm est `SLEEP`, le système doit conserver `hvac_mode: OFF` dans l'état public Home Assistant.
- **FR-003 — État interne.** Lorsque le sommeil est demandé, le système doit conserver le mode interne `SLEEP` et signaler `is_sleeping: true`.
- **FR-004 — Commande physique en chauffage.** En `SLEEP`, lorsque `ac_mode` est désactivé, le système doit commander le climat sous-jacent en `HEAT`.
- **FR-005 — Commande physique en climatisation.** En `SLEEP`, lorsque `ac_mode` est activé, le système doit commander le climat sous-jacent en `COOL`.
- **FR-006 — Ouverture de vanne.** En `SLEEP`, le système doit commander une ouverture de vanne de 100 % et une fermeture de 0 %, dans les limites d'entités configurées qui permettent ces valeurs.
- **FR-007 — Non-demande fonctionnelle.** En `SLEEP`, le système doit maintenir `hvac_action: OFF`, `is_device_active: false` et une liste `device_actives` vide pour le VTherm.
- **FR-008 — Non-demande chaudière.** En `SLEEP`, le système ne doit pas compter le VTherm comme appareil actif ni produire de demande de chauffage pour la chaudière centrale.
- **FR-009 — Sortie du sommeil.** À la sortie de `SLEEP`, le système doit commander le mode demandé, restaurer la régulation normale et cesser de forcer l'ouverture à 100 %.
- **FR-010 — Conservation utilisateur.** La sortie de sommeil doit conserver la consigne et le préréglage existants, sauf modification explicite demandée par l'utilisateur ou impossibilité signalée par une contrainte du sous-jacent.
- **FR-011 — Reprise.** Après démarrage ou restauration en `SLEEP`, le système doit rétablir les comportements FR-002 à FR-008 une fois les entités nécessaires initialisées, en réémettant inconditionnellement les deux degrés de vanne correspondant à 100 % d'ouverture et 0 % de fermeture.
- **FR-012 — Isolation du mapping public.** Le mapping public `SLEEP` vers `OFF` ne doit pas imposer `OFF` à la commande physique du climat sous-jacent dans le périmètre FR-001.
- **FR-013 — Erreur d'application.** Si le climat sous-jacent ou une entité de degré est indisponible, le système doit conserver les invariants publics et de non-demande chaudière applicables, et l'échec de commande doit être observable dans les diagnostics ou journaux existants. Le comportement de reprise de la commande doit rester celui du mécanisme existant.

### 5. Règles métier

- **BR-001 — Dissociation des états.** `SLEEP` est le mode fonctionnel interne du VTherm ; `OFF` est sa représentation publique ; le mode actif `HEAT` ou `COOL` est la commande physique de la TRV. Ces trois notions ne doivent pas être confondues.
- **BR-002 — Choix du mode physique.** Le mode physique de sommeil est `HEAT` si `ac_mode` est faux et `COOL` si `ac_mode` est vrai.
- **BR-003 — Priorité de l'ouverture.** En sommeil, l'objectif de vanne est 100 % ouverte et 0 % fermée, indépendamment de la dernière demande TPI.
- **BR-004 — Invariant chaudière.** L'activation physique du mode HVAC de la TRV ne constitue pas une demande de chauffage du VTherm. Les indicateurs d'activité du VTherm et de la chaudière restent à l'arrêt.
- **BR-005 — Transition entrante.** L'entrée en sommeil doit appliquer le mode physique actif et les degrés de sommeil dans le même changement fonctionnel, sans exposer temporairement le sommeil comme une demande de régulation.
- **BR-006 — Transition sortante.** La sortie du sommeil doit réappliquer le mode demandé et les valeurs calculées par la régulation ; le contrat 100 % / 0 % cesse alors de s'appliquer.
- **BR-007 — Portée.** Les comportements `SLEEP` d'autres types, notamment `over_valve` sans climat sous-jacent, ne sont pas déduits de cette spécification.

### 6. Contraintes fonctionnelles

- La commande doit rester compatible avec les TRV qui ferment leur vanne lorsque leur mode HVAC est `OFF`, notamment le cas Sonoff TRVZB décrit dans la revue.
- Le mode `COOL` ne doit être utilisé pour la TRV que lorsque `ac_mode` est activé ; envoyer `HEAT` dans ce cas est incohérent avec le contrat défini.
- La consigne régulée ou la consigne déjà envoyée doit rester disponible pour les équipements qui exigent une consigne après le passage en `HEAT` ou `COOL`. Le mécanisme précis de disponibilité et de renvoi est une contrainte à confirmer en conception.
- Les limites configurées des entités de degré doivent être respectées. Si 100 % / 0 % ne peuvent pas être acceptés, le système doit signaler l'écart plutôt que prétendre que la vanne est ouverte.
- Aucun nouvel accès, secret, flux de données ou exigence de confidentialité n'est introduit.

### 7. Critères d'acceptation

- **AC-001 — Chauffage, entrée en sommeil.** Étant donné un `ThermostatOverClimateValve` en `HEAT`, quand `SLEEP` est demandé, alors le VTherm expose `OFF`, conserve `SLEEP` en interne, et le climat sous-jacent est en `HEAT`.
- **AC-002 — Vanne ouverte.** Dans le scénario AC-001, les entités de degré indiquent respectivement 100 % en ouverture et 0 % en fermeture.
- **AC-003 — Invariants d'activité.** Dans le scénario AC-001, `hvac_action` vaut `OFF`, `is_device_active` vaut `false`, `should_device_be_active` vaut `false` pour le VTherm et `nb_device_actives` vaut 0 ; aucune demande chaudière n'est produite.
- **AC-004 — Climatisation.** Étant donné `ac_mode: true`, quand `SLEEP` est demandé, le VTherm expose `OFF` mais le climat sous-jacent reçoit `COOL`, avec les mêmes valeurs 100 % / 0 % et les mêmes invariants d'inactivité.
- **AC-005 — Sortie de sommeil.** Étant donné le scénario AC-001, quand `HEAT` est demandé, le climat sous-jacent revient en `HEAT`, la consigne et le préréglage sont conservés, et la valeur de vanne redevient celle calculée par la régulation, par exemple inférieure à 100 % lorsque la demande n'est pas maximale.
- **AC-006 — Redémarrage/restauration.** Étant donné un VTherm restauré en `SLEEP`, après initialisation des sous-jacents, le système réémet inconditionnellement les deux degrés et les états publics, le mode physique, les valeurs 100 % / 0 % et les invariants de chaudière correspondent à AC-001 à AC-004 selon `ac_mode`, même si les valeurs restaurées des degrés étaient différentes.
- **AC-007 — Erreur ou indisponibilité.** Si le climat ou une entité de degré est indisponible au moment de la transition, le VTherm ne devient pas une demande chaudière par effet de cette erreur et l'échec est observable selon le mécanisme de diagnostic existant.
- **AC-008 — Non-régression.** Les scénarios hors sommeil, notamment fonctionnement normal en `HEAT` ou `COOL` et arrêt réel en `OFF`, conservent leur comportement existant.
- **AC-009 — Limitation de portée.** Aucun test de cette correction ne doit exiger une modification du comportement d'un thermostat `over_valve` sans climat sous-jacent.

### 8. Fonctions non prises en compte

- Modification du comportement `SLEEP` de `over_valve`.
- Paramètre par fabricant, contournement Sonoff ou nouveau réglage utilisateur.
- Modification des algorithmes TPI, du pourcentage de sommeil, des limites de vanne ou de la configuration existante.
- Modification générale du mapping `SLEEP` vers `OFF` pour les autres thermostats.
- Garantie d'un comportement constructeur pour une TRV qui expose des entités de degré mais refuse `HEAT` ou `COOL` ; ce cas doit être signalé comme incompatibilité et reste une question ouverte.
- Modification de l'état Home Assistant ou de la configuration pendant la définition de la solution.

### 9. Évolutions futures proposées

- Documenter explicitement les capacités requises d'un climat sous-jacent pour le mode maintenance.
- Ajouter un diagnostic dédié lorsque le mode physique demandé, la consigne ou les degrés ne peuvent pas être appliqués.
- Étudier une stratégie déclarative pour les appareils dont le mode actif de maintien diffère de `HEAT` / `COOL`.
- Ajouter une couverture de compatibilité par famille de TRV si des comportements constructeurs divergents sont identifiés.

### 10. Hypothèses, questions ouvertes et traçabilité

#### Faits établis

- Le calcul de sommeil produit déjà 100 % d'ouverture et 0 % de fermeture.
- Le chemin générique transmet actuellement `OFF` au climat sous-jacent lorsque le mode interne vaut `SLEEP`.
- Le VTherm expose `OFF` pour `SLEEP` et possède des indicateurs d'activité séparés de l'état HVAC du climat sous-jacent.
- Le test existant couvre `HEAT -> SLEEP -> HEAT`, mais attend actuellement `OFF` pour le climat sous-jacent pendant le sommeil.
- La documentation utilisateur promet une vanne totalement ouverte en sommeil.

#### Hypothèses retenues pour cette spécification

- `HEAT` est le mode physique de maintien hors `ac_mode` et `COOL` est le mode physique de maintien avec `ac_mode`.
- La consigne régulée peut être réutilisée ou renvoyée par le mécanisme existant lorsque le climat est activé.
- Le contrat concerne la commande fonctionnelle ; l'ouverture physique effective dépend aussi de la capacité et de l'état de la TRV.

#### Questions ouvertes et ambiguïtés

- Que doit faire précisément le système si la TRV accepte les degrés mais refuse `HEAT` ou `COOL` ?
- La garantie de restauration doit-elle être vérifiée dès l'initialisation du VTherm ou seulement après l'initialisation complète des entités de degrés ?
- Quel comportement diagnostique exact est attendu lorsqu'une commande de mode ou de degré échoue ?
- Une précision doit-elle être ajoutée à la documentation utilisateur concernant la nécessité, pour certaines TRV, d'un mode physique actif pendant `SLEEP` ?

#### Traçabilité

La revue approuvée [issue-2077-review.md](issue-2077-review.md) constitue la source normative du périmètre et des décisions. Les symboles vérifiés sont `ThermostatOverClimateValve.recalculate`, `BaseThermostat.update_states`, `BaseThermostat.is_sleeping`, `UnderlyingClimate.set_hvac_mode`, `UnderlyingValveRegulation.check_initial_state`, `UnderlyingValveRegulation.send_percent_open` et le test `test_over_climate_valve_vtherm_hvac_mode_sleep`. Cette spécification est cohérente avec le rapport : elle reprend son périmètre, sa recommandation, ses invariants, ses transitions, ses exclusions et ses critères de passage au développement, sans introduire de correction de code.

## English Version

### 1. Title and metadata

- **Name:** GitHub issue #2077 — sleep / maintenance mode for `ThermostatOverClimateValve`
- **Version:** 1.0
- **Status:** proposed for functional validation
- **Date:** 2026-09-29
- **Owner:** to be assigned
- **Scope:** `ThermostatOverClimateValve` only
- **Approved source of truth:** [issue #2077 review](issue-2077-review.md)
- **Analyzed sources:** [thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py), [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py), [underlyings.py](../../custom_components/versatile_thermostat/underlyings.py), [vtherm_hvac_mode.py](../../custom_components/versatile_thermostat/vtherm_hvac_mode.py), [test_overclimate_valve.py](../../tests/test_overclimate_valve.py), [over-climate user documentation](../en/over-climate.md)

### 2. Context and objectives

A TRV used as the underlying climate of an `over_climate` VTherm may physically close its valve when it receives `hvac_mode: off`. The VTherm then correctly exposes sleep as public `OFF` and already publishes a requested opening of 100% / closing of 0%, but the TRV's `OFF` command prevents the physical opening.

The objective is to implement sleep as a maintenance mode: keep the physical valve fully open without requesting heat from the boiler. The correction shall apply to the command sent to the underlying climate of `ThermostatOverClimateValve`, without changing the public VTherm representation or the behavior of other thermostat types.

### 3. Actors and use cases

#### Actors

- **User or automation:** requests entry to or exit from sleep.
- **`ThermostatOverClimateValve` VTherm:** exposes public state, calculates opening, and applies no-request rules.
- **Underlying climate / TRV:** receives the physical HVAC mode and opening/closing degrees.
- **Central boiler:** consumes VTherm activity state; it shall not be requested by sleep.

#### Nominal use case: entering sleep

1. The VTherm is in `HEAT` or `COOL` and regulates normally.
2. The user or an automation requests `SLEEP`.
3. The VTherm keeps internal mode `SLEEP` and exposes `OFF` in Home Assistant.
4. The underlying climate receives its active physical mode: `HEAT` without `ac_mode`, `COOL` with `ac_mode`.
5. The degree entities receive 100% opening and 0% closing.
6. The VTherm remains inactive for regulation and boiler purposes.

#### Nominal use case: exiting sleep

1. The VTherm is in `SLEEP`.
2. The user or an automation requests the previous operating mode or another allowed mode.
3. The underlying climate receives the mode matching the request.
4. The retained target temperature and preset are reused according to normal behavior.
5. Regulation resumes and the opening is no longer forced to 100%.

#### Use case: resume or restart while sleeping

At startup or after restoring a VTherm whose restored internal mode is `SLEEP`, the system shall restore the sleep contract: public `OFF`, a physical mode matching `ac_mode`, unconditional re-emission of both degree commands at 100% / 0%, and no boiler request. This re-emission shall occur after the required underlying entities have been initialized.

### 4. Functional requirements

- **FR-001 — Scope.** The system shall apply these rules only to `ThermostatOverClimateValve` and its underlying climate used for direct valve regulation.
- **FR-002 — Public state.** When the VTherm internal mode is `SLEEP`, the system shall keep `hvac_mode: OFF` in the Home Assistant public state.
- **FR-003 — Internal state.** When sleep is requested, the system shall keep internal mode `SLEEP` and report `is_sleeping: true`.
- **FR-004 — Physical heating mode.** In `SLEEP`, when `ac_mode` is disabled, the system shall command the underlying climate to `HEAT`.
- **FR-005 — Physical cooling mode.** In `SLEEP`, when `ac_mode` is enabled, the system shall command the underlying climate to `COOL`.
- **FR-006 — Valve opening.** In `SLEEP`, the system shall command 100% valve opening and 0% closing, within the limits of configured entities that support those values.
- **FR-007 — Functional no-request state.** In `SLEEP`, the system shall keep `hvac_action: OFF`, `is_device_active: false`, and an empty `device_actives` list for the VTherm.
- **FR-008 — No boiler request.** In `SLEEP`, the system shall not count the VTherm as active or produce a heating request for the central boiler.
- **FR-009 — Exit from sleep.** On exit from `SLEEP`, the system shall command the requested mode, restore normal regulation, and stop forcing the opening to 100%.
- **FR-010 — User-state retention.** Exiting sleep shall retain the existing target temperature and preset, unless explicitly changed by the user or prevented by an underlying-device constraint.
- **FR-011 — Resume.** After startup or restoration in `SLEEP`, the system shall restore FR-002 through FR-008 once the required entities are initialized, unconditionally re-emitting both valve-degree commands corresponding to 100% opening and 0% closing.
- **FR-012 — Public mapping isolation.** The public `SLEEP` to `OFF` mapping shall not impose `OFF` on the underlying climate physical command within FR-001.
- **FR-013 — Application error.** If the underlying climate or a degree entity is unavailable, the system shall preserve applicable public and boiler no-request invariants, and the command failure shall be observable through existing diagnostics or logs. Retry behavior shall remain that of the existing mechanism.

### 5. Business rules

- **BR-001 — State separation.** `SLEEP` is the VTherm internal functional mode; `OFF` is its public representation; active `HEAT` or `COOL` is the TRV physical command. These three concepts shall not be conflated.
- **BR-002 — Physical-mode selection.** The sleep physical mode is `HEAT` when `ac_mode` is false and `COOL` when `ac_mode` is true.
- **BR-003 — Opening priority.** In sleep, the valve objective is 100% open and 0% closed, regardless of the last TPI request.
- **BR-004 — Boiler invariant.** The TRV physical HVAC mode being active is not a VTherm heating request. VTherm and boiler activity indicators remain inactive.
- **BR-005 — Entry transition.** Entering sleep shall apply the active physical mode and sleep degree values as one functional state change, without exposing sleep temporarily as a regulation request.
- **BR-006 — Exit transition.** Exiting sleep shall reapply the requested mode and regulation-calculated values; the 100% / 0% sleep contract then no longer applies.
- **BR-007 — Scope.** `SLEEP` behavior for other types, including `over_valve` without an underlying climate, is outside this specification.

### 6. Functional constraints

- The command shall remain compatible with TRVs that close their valve when their HVAC mode is `OFF`, including the Sonoff TRVZB case described in the review.
- `COOL` shall be used for the TRV only when `ac_mode` is enabled; sending `HEAT` in that case is inconsistent with this contract.
- The regulated or previously sent target temperature shall remain available for devices that require a temperature after switching to `HEAT` or `COOL`. The precise availability and resend mechanism is a design constraint to confirm.
- Configured degree-entity limits shall be respected. If 100% / 0% cannot be accepted, the system shall report the mismatch rather than claim that the valve is open.
- No new access, secret, data flow, or privacy requirement is introduced.

### 7. Acceptance criteria

- **AC-001 — Heating, entering sleep.** Given a `ThermostatOverClimateValve` in `HEAT`, when `SLEEP` is requested, the VTherm exposes `OFF`, keeps internal `SLEEP`, and the underlying climate is in `HEAT`.
- **AC-002 — Open valve.** In AC-001, the degree entities report 100% opening and 0% closing.
- **AC-003 — Activity invariants.** In AC-001, `hvac_action` is `OFF`, `is_device_active` is `false`, `should_device_be_active` is `false` for the VTherm, and `nb_device_actives` is 0; no boiler request is produced.
- **AC-004 — Cooling.** Given `ac_mode: true`, when `SLEEP` is requested, the VTherm exposes `OFF` but the underlying climate receives `COOL`, with the same 100% / 0% values and inactivity invariants.
- **AC-005 — Exit from sleep.** Given AC-001, when `HEAT` is requested, the underlying climate returns to `HEAT`, target temperature and preset are retained, and the valve value becomes the regulation-calculated value, for example below 100% when demand is not maximum.
- **AC-006 — Restart/restore.** Given a VTherm restored in `SLEEP`, after underlying initialization, the system unconditionally re-emits both degree commands, and public state, physical mode, 100% / 0% values, and boiler invariants match AC-001 through AC-004 according to `ac_mode`, even when the restored degree values differed.
- **AC-007 — Error or unavailability.** If the climate or a degree entity is unavailable during the transition, the VTherm shall not become a boiler request as a result of that error, and the failure shall be observable through the existing diagnostic mechanism.
- **AC-008 — Regression safety.** Non-sleep scenarios, including normal `HEAT` or `COOL` operation and actual `OFF`, retain their existing behavior.
- **AC-009 — Scope limitation.** No test of this correction shall require a behavior change in an `over_valve` thermostat without an underlying climate.

### 8. Out-of-scope functions

- Changing `SLEEP` behavior for `over_valve`.
- A manufacturer parameter, Sonoff-specific workaround, or new user setting.
- Changes to TPI algorithms, sleep percentage, valve limits, or existing configuration.
- A global change to `SLEEP` to `OFF` mapping for other thermostats.
- Guaranteeing manufacturer behavior for a TRV that exposes degree entities but rejects `HEAT` or `COOL`; that case shall be reported as an incompatibility and remains an open question.
- Changing Home Assistant state or configuration during solution definition.

### 9. Proposed future enhancements

- Explicitly document the underlying-climate capabilities required by maintenance mode.
- Add a dedicated diagnostic when the physical mode, target temperature, or degree values cannot be applied.
- Study a declarative strategy for devices whose active maintenance mode differs from `HEAT` / `COOL`.
- Add compatibility coverage per TRV family if divergent manufacturer behavior is identified.

### 10. Assumptions, open questions, and traceability

#### Established facts

- The sleep calculation already produces 100% opening and 0% closing.
- The generic path currently sends `OFF` to the underlying climate when the internal mode is `SLEEP`.
- The VTherm exposes `OFF` for `SLEEP` and has activity indicators separate from the underlying climate HVAC state.
- The existing test covers `HEAT -> SLEEP -> HEAT`, but currently expects `OFF` for the underlying climate during sleep.
- User documentation promises a fully open valve in sleep.

#### Assumptions retained for this specification

- `HEAT` is the physical maintenance mode without `ac_mode`, and `COOL` is the physical maintenance mode with `ac_mode`.
- The regulated target temperature can be reused or resent by the existing mechanism when the climate is activated.
- The contract concerns the functional command; effective physical opening also depends on the TRV's capability and state.

#### Open questions and ambiguities

- What exactly shall happen if a TRV accepts degree commands but rejects `HEAT` or `COOL`?
- Shall the restore guarantee be checked at VTherm initialization or only after all degree entities have fully initialized?
- What exact diagnostic behavior is expected when a mode or degree command fails?
- Should user documentation explain that some TRVs require an active physical mode during `SLEEP`?

#### Traceability

The approved [issue-2077-review.md](issue-2077-review.md) is the normative source for scope and decisions. Verified symbols are `ThermostatOverClimateValve.recalculate`, `BaseThermostat.update_states`, `BaseThermostat.is_sleeping`, `UnderlyingClimate.set_hvac_mode`, `UnderlyingValveRegulation.check_initial_state`, `UnderlyingValveRegulation.send_percent_open`, and the `test_over_climate_valve_vtherm_hvac_mode_sleep` test. This specification is consistent with the report: it preserves its scope, recommendation, invariants, transitions, exclusions, and development-gate criteria without introducing a code change.