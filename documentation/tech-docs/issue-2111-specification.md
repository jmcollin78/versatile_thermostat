# Issue #2111 - Specification fonctionnelle / Functional Specification

## Version française

### 1. Titre et métadonnées

- **Nom :** Issue #2111 - recalcul immédiat lors d'un changement réel de mode HVAC effectif
- **Version :** 1.0
- **Statut :** convergence documentaire atteinte ; validation humaine requise avant développement
- **Date :** 2026-10-18
- **Propriétaire :** à désigner
- **Périmètre :** thermostats `over_climate` avec régulation directe de vanne
- **Source normative :** [rapport de revue issue-2111-review.md](issue-2111-review.md) et sa version anglaise [issue-2111-review-en.md](issue-2111-review-en.md)
- **Référence :** [issue GitHub #2111](https://github.com/jmcollin78/versatile_thermostat/issues/2111)
- **Conception associée :** [conception bilingue #2111](issue-2111-design.md)
- **Sources de code analysées dans le rapport :** [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) (`update_states`), [thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py) (`recalculate`, envoi régulé)

### 2. Contexte et objectifs

L'issue signale qu'une ouverture de vanne peut rester à 100 % après une transition de `sleep`, alors que le nouveau mode ne justifie plus cette demande. Le mode HVAC effectif change parfois automatiquement et ne doit donc pas être traité uniquement comme une demande de service utilisateur.

L'objectif est de forcer le recalcul et de tenter l'application immédiate, par les chemins existants, de la valeur effectivement retenue lors d'un changement réel du mode HVAC effectif, en franchissant la période minimale de recalcul et le délai d'envoi concerné. La tentative reste soumise aux préconditions, protections et déduplications existantes ; la valeur appliquée reste toujours celle produite par ces protections, et non le résultat TPI brut.

La protection `dpercent` est une protection de calibrage des Sonoff TRVZB selon le mainteneur. Elle ne doit jamais être contournée par ce correctif, y compris avec `force=True` ou lors d'une sortie de `sleep`.

### 3. Acteurs et cas d'utilisation

#### Acteurs

- **Utilisateur ou automatisation :** demande un mode HVAC ou déclenche une transition indirecte.
- **Automatisation et logique interne :** peut provoquer un changement automatique du mode HVAC effectif.
- **VTherm `over_climate` à régulation directe de vanne :** détecte le changement effectif, recalcule, applique les protections et pilote la vanne.
- **Climat sous-jacent et vannes :** reçoivent la commande finale retenue.
- **Scheduler :** déclenche les recalculs et envois selon les cadences existantes hors exception de transition.
- **Fenêtre, central et sécurité :** restent des portes fonctionnelles prioritaires.

#### Cas nominal : transition manuelle ou automatique

1. Le mode HVAC effectif change réellement pour un VTherm du périmètre.
2. Le traitement de transition force le recalcul sans créer de nouvelle mémoire de dernier mode calculé ou envoyé.
3. Le calcul respecte `dpercent`, l'inhibition, les conversions min/max, la fermeture à 0 %, le seuillage des petites valeurs, la déduplication et les autres protections existantes.
4. La valeur ainsi retenue doit faire l'objet d'une tentative d'application immédiate par les chemins existants, en franchissant effectivement la période minimale de recalcul et le délai d'envoi régulé ; cette tentative reste soumise aux préconditions, protections et déduplications existantes.
5. Les services finaux et leurs acquittements observables montrent la commande effectivement envoyée, sans assimiler un état physique à un acquittement synchrone.

#### Cas nominal : mode inchangé ou retour à la cadence

Une demande identique, une contrainte qui masque la demande ou le retour du mode à une valeur constante ne constitue pas un nouveau changement réel. Aucun nouvel événement de forcement n'est créé. Après la transition, les cadences normales et les forcements préexistants restent applicables.

### 4. Exigences fonctionnelles

- **FR-001 — Périmètre.** Le système doit appliquer le nouveau forcement uniquement aux thermostats `over_climate` avec régulation directe de vanne.
- **FR-002 — Changement effectif.** Le système doit déclencher ce forcement uniquement lorsqu'un changement réel du mode HVAC effectif est observé.
- **FR-003 — Transitions manuelles et automatiques.** Le forcement doit couvrir les changements effectifs provenant d'une action manuelle et d'une automatisation.
- **FR-004 — Recalcul forcé.** Lors d'une transition couverte, le système doit forcer le recalcul sans ajouter de mémoire du dernier mode calculé ou envoyé.
- **FR-005 — Application immédiate.** Lors d'une transition couverte, le système doit effectivement franchir la période minimale de recalcul et le délai d'envoi régulé afin de tenter immédiatement, par les chemins existants, l'application de la valeur finalement retenue. Cette exigence ne garantit ni l'appel d'un service, ni une modification si la valeur est dédupliquée, ni le succès du service ou l'acquittement matériel.
- **FR-006 — Valeur retenue.** La commande finale doit utiliser la valeur retenue après les protections existantes, jamais le résultat TPI brut lorsque celui-ci a été filtré.
- **FR-007 — Protection `dpercent`.** Le système ne doit jamais contourner le filtre `dpercent` du fait de ce forcement, de `force=True`, d'une sortie de `sleep` ou d'un passage par le scheduler.
- **FR-008 — Algorithme et bornes.** Le système doit conserver exactement l'algorithme, les conditions, les bornes et l'asymétrie existants de `dpercent`.
- **FR-009 — Protections prioritaires.** L'inhibition, les conversions min/max, la déduplication, la fermeture à 0 %, le seuillage des petites valeurs et les autres protections existantes doivent rester applicables et prioritaires.
- **FR-010 — Sleep.** Le système doit préserver le chemin préexistant où `sleep` impose une ouverture logique de 100 % sans passer par le filtre de variation de la branche TPI ; le correctif ne doit pas ajouter une nouvelle exception.
- **FR-011 — Absence de données.** En cas de donnée de calcul absente, le système doit conserver la politique actuelle, sans promettre une ouverture fraîche ni inventer une fermeture automatique.
- **FR-012 — Distinguer commande et acquittement.** La spécification doit distinguer le calcul et la commande demandée de l'état physique ou de l'acquittement observé du service HA.
- **FR-013 — Cadence normale.** Hors changement réel de mode effectif, le système doit conserver les délais, le scheduler, les appels forcés et la déduplication préexistants. Lors d'une transition couverte, les effets préexistants du `force` sur le scheduler, les fenêtres de cycle, les callbacks et le learning restent applicables et doivent être observés, sans constituer une garantie de cadence inchangée pour la cible.
- **FR-014 — Autres thermostats.** Le nouveau forcement ne doit pas modifier les autres types de thermostats.
- **FR-015 — Modes couverts.** La couverture doit inclure `heat`, `sleep` et `off`, ainsi que `cool` lorsqu'il est supporté par la configuration et le thermostat.

### 5. Règles métier

- **BR-001 — Transition réelle.** Un événement de forcement nouveau est créé uniquement si le mode HVAC effectif change réellement ; une demande identique ou masquée par une contrainte ne suffit pas.
- **BR-002 — Portée stricte.** `BR-001` à `BR-015` ne généralisent pas le forcement aux thermostats hors `over_climate` à régulation directe de vanne.
- **BR-003 — Deux temporisations et scheduler.** La période de recalcul et le délai d'envoi sont deux contrôles distincts ; lors d'une transition couverte, le forcement doit franchir les deux contrôles via les chemins existants pour tenter l'application de la valeur retenue. Le même `force` conserve ses effets préexistants sur le scheduler, les fenêtres de cycle, les callbacks et le learning ; ces effets doivent être testés, sans promettre une cadence de cycles inchangée pour la cible.
- **BR-004 — Pas de nouvelle mémoire.** Aucun dernier mode calculé ou envoyé ne doit être introduit pour décider du forcement.
- **BR-005 — `dpercent` inchangé.** Pour une valeur positive, lorsque le dernier calcul existe, la condition actuelle `-threshold <= delta < threshold` doit rester inchangée. Avec un seuil de 5, `-5` reste filtré et `+5` ne l'est pas, toutes les autres conditions étant réunies.
- **BR-006 — Sortie de sleep.** Si `sleep` conserve 100 % et que la sortie propose 98 % avec un seuil de 5, la valeur retenue reste 100 % et aucune commande 98 % ne doit être envoyée. Cette conservation intentionnelle n'est pas une ouverture obsolète due à un délai.
- **BR-007 — Pas de contournement.** Un forcement ne permet ni d'envoyer une valeur filtrée, ni de désactiver `dpercent`, même à la sortie de `sleep` ou en sortie de scheduler.
- **BR-008 — Sleep préexistant.** Le chemin préexistant imposant 100 % en `sleep` conserve sa sémantique ; il ne constitue pas une raison pour inventer une symétrie ou une exception supplémentaire.
- **BR-009 — Protections.** L'inhibition et les protections de sécurité sont prioritaires sur l'application immédiate ; le forcement ne doit pas les contourner.
- **BR-010 — Zéro et petites valeurs.** L'exception préexistante de fermeture à 0 % et le seuillage des petites valeurs restent inchangés.
- **BR-011 — Valeur positive conservée.** Une absence de commande de chauffage ne peut pas être exigée lorsque `dpercent` conserve intentionnellement une ouverture positive.
- **BR-012 — Données absentes.** L'absence puis le retour d'une donnée suivent la politique actuelle ; aucune nouvelle promesse de comportement n'est créée par cette spécification.
- **BR-013 — Multi-vannes.** Les limites min/max et la valeur retenue doivent rester cohérentes pour plusieurs vannes, sans envoyer la valeur brute avant conversion.
- **BR-014 — Coût matériel.** L'effet sur la batterie n'est pas quantifié ; le recalcul logiciel ne doit pas être présenté comme une mesure de consommation.
- **BR-015 — Matériel.** Le matériel Sonoff TRVZB est une contrainte de calibrage rapportée par le mainteneur, non un résultat de test matériel de cette spécification.

### 6. Contraintes fonctionnelles

- Le périmètre est limité à la régulation directe de vanne via `over_climate`.
- Les protections existantes doivent rester observables dans la commande finale : inhibition, sécurité, conversion min/max, déduplication, zéro et petites valeurs.
- Les commandes finales doivent être observées via les services et le chemin scheduler concernés ; un appel de recalcul seul ne constitue pas une preuve d'application immédiate. L'application immédiate désigne une tentative via les chemins existants après franchissement des délais, non un succès de service ni un acquittement matériel garanti.
- Le mode `cool` n'est exigé que lorsqu'il est effectivement supporté ; aucune capacité nouvelle n'est promise.
- Les données de capteur absentes ou revenues ne font l'objet d'aucune nouvelle politique.
- Aucun réglage utilisateur, stockage, dépendance, modification d'environnement Home Assistant ou changement matériel n'est introduit.
- La batterie ne fait l'objet d'aucune quantification.

### 7. Critères d'acceptation

- **AC-001 — Transition `heat -> sleep`.** Étant donné un `over_climate` à régulation directe en `heat`, quand le mode effectif passe réellement à `sleep`, alors un recalcul forcé est déclenché et une tentative d'application de la valeur finalement retenue franchit la période de recalcul et le délai d'envoi régulé, sous réserve des préconditions, protections et déduplications existantes.
- **AC-002 — Transition `sleep -> heat`.** Étant donné `sleep` avec une ouverture logique de 100 %, quand le mode effectif passe réellement à `heat`, alors le calcul est forcé et la valeur retenue est soumise à toutes les protections existantes avant toute commande.
- **AC-003 — Exemple `100 -> 98`.** Avec un seuil `dpercent` de 5, si la sortie de `sleep` propose 98 % après une valeur retenue de 100 %, alors 100 % est conservé et 98 % n'est pas commandé.
- **AC-004 — Bornes asymétriques.** Avec un seuil de 5 et dans les autres conditions du filtre, une variation de `-5` reste filtrée tandis qu'une variation de `+5` ne l'est pas.
- **AC-005 — Petite valeur et zéro.** Une petite ouverture et la fermeture à 0 % suivent exactement les traitements préexistants ; le forcement ne les remplace ni ne les contourne.
- **AC-006 — Mode constant.** Une demande identique, une contrainte qui masque la demande ou un passage sans changement effectif ne crée pas de nouvel événement de forcement.
- **AC-007 — Retour à la cadence.** Après la transition, une mise à jour sans nouveau changement effectif reprend les délais de recalcul et d'envoi ainsi que le chemin scheduler préexistants ; les effets ponctuels de la transition sur fenêtre, callbacks et learning sont observés séparément et ne doivent pas être interprétés comme une cadence de cycles garantie pour la cible.
- **AC-008 — Automatique.** Une transition automatique réelle produit le même recalcul et la même application protégée qu'une transition manuelle couverte.
- **AC-009 — `sleep -> off -> heat`.** Les deux changements réels sont traités séparément ; aucune réutilisation d'un cache remis à zéro ou à zéro pourcentage ne doit servir à contourner le filtre.
- **AC-010 — Reprise froide.** Lors d'une reprise froide, les données absentes, disponibles ou revenues conservent la politique actuelle ; le système ne promet ni ouverture fraîche ni fermeture automatique non établie.
- **AC-011 — Fenêtre, central et sécurité.** Avec une fenêtre ouverte, une contrainte centrale ou une porte de sécurité active, la protection correspondante reste prioritaire sur l'application immédiate et la valeur commandée reste la valeur retenue par les protections.
- **AC-012 — Inhibition.** Une transition couverte sous inhibition ne contourne pas l'inhibition et n'envoie pas une valeur brute au motif que le recalcul est forcé.
- **AC-013 — `cool` si supporté.** Pour une transition réelle impliquant `cool` dans une configuration qui le supporte, les règles de recalcul, d'application et de protection sont identiques à celles des autres modes ; aucun comportement n'est exigé si `cool` n'est pas supporté.
- **AC-014 — Multi-vannes min/max.** Avec plusieurs vannes et des limites min/max, chaque commande observée respecte les conversions et limites existantes ; aucune valeur TPI brute n'est envoyée.
- **AC-015 — Ouverture positive conservée et télémétrie.** Si le filtre conserve intentionnellement une ouverture positive, l'acceptation ne doit pas exiger l'absence d'une action de chauffage uniquement parce qu'une transition a été forcée. Une télémétrie de cycle, un callback ou une trace du scheduler ne constitue pas à elle seule la preuve d'une commande physique identique ni de l'envoi du résultat TPI brut.
- **AC-016 — Autres thermostats.** Les thermostats qui ne sont pas des `over_climate` à régulation directe ne présentent aucun nouveau forcement du fait de cette spécification.
- **AC-017 — Données et acquittement.** Les observations distinguent la valeur calculée, la commande de service finale et l'état physique éventuellement rapporté ; un état physique absent ou retardé n'est pas interprété comme un acquittement synchrone.

### 8. Fonctions non prises en compte

- Ajouter une mémoire du dernier mode calculé ou envoyé.
- Réinitialiser un cache à zéro ou à zéro pourcentage pour contourner `dpercent`.
- Contourner `dpercent` avec `force=True`, à la sortie de `sleep` ou via le scheduler.
- Généraliser le forcement aux autres types de thermostats.
- Modifier la formule TPI, les bornes, le seuil, les conversions min/max ou les protections existantes.
- Ajouter une politique pour capteur absent ou revenu.
- Modifier la concurrence, l'environnement Home Assistant, la configuration, le matériel ou les dépendances.
- Quantifier la batterie ou garantir le comportement d'un modèle matériel non testé.

### 9. Évolutions futures proposées

- Définir, après observation des services finaux, une stratégie de diagnostic pour distinguer une valeur volontairement conservée d'une commande retardée.
- Compléter la couverture d'intégration des transitions automatiques et des appareils Zigbee lorsque des traces matérielles sont disponibles.
- Documenter séparément les capacités et limites des familles de vannes si des résultats matériels reproductibles sont obtenus.

### 10. Hypothèses, questions ouvertes et traçabilité

#### Faits établis

- Le rapport de revue identifie `update_states` comme connaissant le changement de mode effectif et reliant le recalcul au contrôle.
- Le recalcul forcé peut ignorer la période de recalcul, tandis que l'envoi régulé dispose d'un autre délai.
- `dpercent` ne dépend pas de `force` dans le comportement décrit par le rapport et doit rester séparé de l'exception temporelle.
- Le chemin `sleep` existant impose 100 % sans passer par le filtre de variation de la branche TPI.
- Aucune exécution locale ni validation matérielle n'a été réalisée pour la nouvelle approche.

#### Hypothèses retenues

- Le mode HVAC effectif est la référence fonctionnelle pour distinguer une transition réelle d'une demande identique.
- Les services finaux et le scheduler fournissent des points d'observation distincts pour la valeur retenue, la tentative d'appel de service et la télémétrie de cycle ; la télémétrie de cycle n'est pas équivalente à une commande physique de vanne.
- Le comportement actuel est la référence en cas de données absentes, de retour de données et de capacités non supportées.

#### Questions ouvertes non bloquantes et précisions de test

- Quels effets précis du `force` sur le scheduler, les fenêtres de cycle, les callbacks et le learning seront observés dans les tests, sans promettre une cadence de cycles inchangée pour la cible ?
- Quelle télémétrie de cycle doit être corrélée à la valeur de vanne retenue et à l'appel de service, en gardant explicite qu'elle n'est pas identique à une commande physique ?
- Les tests distinguent-ils bien la tentative immédiate via les chemins existants d'un succès de service ou d'un acquittement matériel, qui ne sont pas garantis ?

#### Traçabilité rapport -> règles -> critères

| Sujet du rapport                                 | Règles métier   | Critères d'acceptation                 |
| ------------------------------------------------ | --------------- | -------------------------------------- |
| Transition réelle, manuelle et automatique       | BR-001, BR-002  | AC-001, AC-002, AC-006, AC-008, AC-009 |
| Deux temporisations et application immédiate     | BR-003, BR-004  | AC-001, AC-002, AC-007, AC-017         |
| Préservation stricte de `dpercent` et des bornes | BR-005 à BR-008 | AC-003, AC-004, AC-005, AC-012, AC-015 |
| Inhibition et protections prioritaires           | BR-009 à BR-013 | AC-005, AC-011, AC-012, AC-014         |
| Données absentes, matériel et batterie           | BR-014, BR-015  | AC-010, AC-017                         |
| Périmètre et non-régression                      | BR-002          | AC-016                                 |

La présente spécification, les deux rapports et la conception ont le même périmètre : les thermostats `over_climate` à régulation directe de vanne lors des changements réels de mode HVAC effectif. Les exigences et critères d'acceptation sont couverts par la décision, le flux et les tests prévus dans la conception. Aucune contradiction bloquante n'est identifiée. La solution est techniquement réalisable et testable via les interfaces inspectées ; les effets scheduler/learning, la télémétrie de cycle et la notion de tentative immédiate restent des précisions de test non bloquantes. Le développement reste non autorisé.

## English Version

### 1. Title and metadata

- **Name:** Issue #2111 - immediate recalculation on an actual effective HVAC mode change
- **Version:** 1.0
- **Status:** documentary convergence reached; human approval required before development
- **Date:** 2026-10-18
- **Owner:** to be assigned
- **Scope:** `over_climate` thermostats with direct valve regulation
- **Normative source:** [issue-2111-review.md](issue-2111-review.md) and its English version [issue-2111-review-en.md](issue-2111-review-en.md)
- **Reference:** [GitHub issue #2111](https://github.com/jmcollin78/versatile_thermostat/issues/2111)
- **Related design:** [bilingual #2111 design](issue-2111-design.md)
- **Code sources analyzed in the review:** [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) (`update_states`), [thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py) (`recalculate`, regulated sending)

### 2. Context and objectives

The issue reports that a valve opening can remain at 100% after a `sleep` transition although the new mode no longer justifies that request. The effective HVAC mode can also change automatically, so the behavior must not be handled only as a user-service request.

The objective is to force recalculation and immediately attempt, through the existing paths, application of the value actually retained when the effective HVAC mode really changes, bypassing the normal recalculation period and relevant sending delay. The attempt remains subject to existing preconditions, protections, and deduplication; the applied value must always be the value produced after those protections, not the raw TPI result.

According to the maintainer, `dpercent` protects Sonoff TRVZB calibration. This correction shall never bypass it, including with `force=True` or when leaving `sleep`.

### 3. Actors and use cases

#### Actors

- **User or automation:** requests an HVAC mode or indirectly triggers a transition.
- **Automation and internal logic:** may cause an automatic effective HVAC mode change.
- **Direct-valve `over_climate` VTherm:** detects the effective change, recalculates, applies protections, and controls the valve.
- **Underlying climate and valves:** receive the final retained command.
- **Scheduler:** triggers recalculations and sends according to existing cadence outside the transition exception.
- **Window, central, and safety logic:** remain higher-priority functional gates.

#### Nominal use case: manual or automatic transition

1. The effective HVAC mode really changes for an in-scope VTherm.
2. Transition handling forces recalculation without creating new last-calculated or last-sent mode state.
3. The calculation respects `dpercent`, inhibition, min/max conversions, closing to 0%, small-value thresholding, deduplication, and all other existing protections.
4. The retained value shall be immediately attempted through the existing paths, effectively bypassing the normal recalculation period and regulated-sending delay; the attempt remains subject to existing preconditions, protections, and deduplication.
5. Final services and observable acknowledgements show the command actually sent, without treating a physical state as a synchronous HA service acknowledgement.

#### Nominal use case: unchanged mode or return to cadence

An identical request, a constraint masking the request, or a mode remaining constant is not a new real change. No new force event is created. After the transition, existing cadence and pre-existing forced calls remain applicable.

### 4. Functional requirements

- **FR-001 — Scope.** The system shall apply the new force behavior only to `over_climate` thermostats with direct valve regulation.
- **FR-002 — Effective change.** The system shall trigger this force behavior only when an actual change of effective HVAC mode is observed.
- **FR-003 — Manual and automatic transitions.** The force behavior shall cover effective changes caused by manual actions and automations.
- **FR-004 — Forced recalculation.** During an in-scope transition, the system shall force recalculation without adding last-calculated or last-sent mode state.
- **FR-005 — Immediate application.** During an in-scope transition, the system shall effectively bypass the normal recalculation period and regulated-sending delay to immediately attempt, through the existing paths, application of the finally retained value. This does not guarantee a service call, a change when the value is deduplicated, service success, or physical acknowledgement.
- **FR-006 — Retained value.** The final command shall use the value retained after existing protections, never the raw TPI result when it was filtered.
- **FR-007 — `dpercent` protection.** The system shall never bypass the `dpercent` filter because of this force behavior, `force=True`, leaving `sleep`, or scheduler execution.
- **FR-008 — Algorithm and boundaries.** The system shall preserve exactly the existing `dpercent` algorithm, conditions, boundaries, and asymmetry.
- **FR-009 — Priority protections.** Inhibition, min/max conversions, deduplication, closing to 0%, small-value thresholding, and other existing protections shall remain applicable and higher priority.
- **FR-010 — Sleep.** The system shall preserve the existing path where `sleep` imposes a logical 100% opening without passing through the TPI branch variation filter; the correction shall add no new exception.
- **FR-011 — Missing data.** When calculation data is missing, the system shall preserve the current policy without promising a fresh opening or inventing automatic closure.
- **FR-012 — Distinguish command and acknowledgement.** The specification shall distinguish calculation and requested command from physical state or observed HA service acknowledgement.
- **FR-013 — Normal cadence.** Outside an actual effective mode change, the system shall preserve existing delays, scheduler behavior, pre-existing forced calls, and deduplication. During an in-scope transition, pre-existing `force` effects on the scheduler, cycle windows, callbacks, and learning remain applicable and shall be observed, without promising an unchanged cycle cadence for the target.
- **FR-014 — Other thermostats.** The new force behavior shall not change other thermostat types.
- **FR-015 — Covered modes.** Coverage shall include `heat`, `sleep`, and `off`, and `cool` when supported by the configuration and thermostat.

### 5. Business rules

- **BR-001 — Actual transition.** A new force event is created only when the effective HVAC mode actually changes; an identical request or a request masked by a constraint is insufficient.
- **BR-002 — Strict scope.** `BR-001` through `BR-015` shall not generalize force behavior to thermostats outside direct-valve `over_climate`.
- **BR-003 — Two timing gates and scheduler.** The recalculation period and sending delay are distinct controls; during an in-scope transition, force behavior shall bypass both through the existing paths to attempt application of the retained value. The same `force` retains its pre-existing effects on the scheduler, cycle windows, callbacks, and learning; these effects shall be tested without promising an unchanged cycle cadence for the target.
- **BR-004 — No new memory.** No last-calculated or last-sent mode shall be introduced to decide whether to force.
- **BR-005 — Unchanged `dpercent`.** For a positive value, when a previous calculation exists, the current condition `-threshold <= delta < threshold` shall remain unchanged. With threshold 5, `-5` remains filtered while `+5` does not, with all other filter conditions met.
- **BR-006 — Leaving sleep.** If `sleep` retains 100% and leaving sleep proposes 98% with threshold 5, the retained value remains 100% and 98% shall not be commanded. This intentional retention is not a stale opening caused by a delay.
- **BR-007 — No bypass.** Force behavior shall neither send a filtered value nor disable `dpercent`, including when leaving `sleep` or through the scheduler.
- **BR-008 — Existing sleep path.** The existing path imposing 100% in `sleep` retains its semantics; it is not a reason to invent symmetry or an additional exception.
- **BR-009 — Protections.** Inhibition and safety protections have priority over immediate application; force behavior shall not bypass them.
- **BR-010 — Zero and small values.** The existing exception for closing to 0% and existing small-opening thresholding remain unchanged.
- **BR-011 — Retained positive value.** Absence of a heating command shall not be required when `dpercent` intentionally retains a positive opening.
- **BR-012 — Missing data.** Missing and returning data follow the current policy; this specification creates no new behavioral promise.
- **BR-013 — Multiple valves.** Min/max limits and retained values remain consistent for multiple valves, without sending the pre-conversion raw value.
- **BR-014 — Hardware cost.** Battery impact is not quantified; software recalculation shall not be presented as a consumption measurement.
- **BR-015 — Hardware.** Sonoff TRVZB is a maintainer-reported calibration constraint, not a hardware test result from this specification.

### 6. Functional constraints

- Scope is limited to direct valve regulation through `over_climate`.
- Existing protections must remain observable in the final command: inhibition, safety, min/max conversion, deduplication, zero, and small values.
- Final commands shall be observed through the relevant services and scheduler path; a recalculation call alone does not prove immediate application. Immediate application means an attempt through the existing paths after bypassing the delays, not guaranteed service success or physical acknowledgement.
- `cool` is required only when actually supported; no new capability is promised.
- Missing or returning sensor data receives no new policy.
- No user setting, storage, dependency, Home Assistant environment change, or hardware change is introduced.
- Battery use is not quantified.

### 7. Acceptance criteria

- **AC-001 — `heat -> sleep`.** Given a direct-valve `over_climate` in `heat`, when the effective mode actually changes to `sleep`, forced recalculation is triggered and an attempt to apply the finally retained value bypasses the recalculation period and regulated-sending delay, subject to existing preconditions, protections, and deduplication.
- **AC-002 — `sleep -> heat`.** Given `sleep` with logical opening at 100%, when the effective mode actually changes to `heat`, calculation is forced and the retained value is subject to all existing protections before any command.
- **AC-003 — `100 -> 98` example.** With `dpercent` threshold 5, if leaving sleep proposes 98% after a retained value of 100%, 100% remains retained and 98% is not commanded.
- **AC-004 — Asymmetric boundaries.** With threshold 5 and all other filter conditions met, a `-5` variation remains filtered while a `+5` variation does not.
- **AC-005 — Small value and zero.** A small opening and closing to 0% follow exactly the existing handling; force behavior neither replaces nor bypasses it.
- **AC-006 — Constant mode.** An identical request, a request masked by a constraint, or a path without an effective change creates no new force event.
- **AC-007 — Return to cadence.** After the transition, an update without another effective mode change resumes existing recalculation and sending delays and the existing scheduler path; the transition's one-off effects on windows, callbacks, and learning are observed separately and shall not be interpreted as a guaranteed cycle cadence for the target.
- **AC-008 — Automatic transition.** An actual automatic transition produces the same recalculation and protected application as an in-scope manual transition.
- **AC-009 — `sleep -> off -> heat`.** Both actual changes are handled separately; no cache reset to zero or zero percent is used to bypass the filter.
- **AC-010 — Cold restart.** During a cold restart, missing, available, or returning data preserves the current policy; no fresh opening or unestablished automatic closure is promised.
- **AC-011 — Window, central, and safety.** With an open window, central constraint, or active safety gate, the corresponding protection remains higher priority than immediate application and the commanded value remains the value retained after protections.
- **AC-012 — Inhibition.** An in-scope transition under inhibition does not bypass inhibition or send a raw value because recalculation was forced.
- **AC-013 — `cool` when supported.** For an actual transition involving `cool` in a configuration supporting it, recalculation, application, and protection rules are the same as for other modes; no behavior is required when `cool` is unsupported.
- **AC-014 — Multiple valves and min/max.** With multiple valves and min/max limits, each observed command respects existing conversions and limits; no raw TPI value is sent.
- **AC-015 — Retained positive opening and telemetry.** If the filter intentionally retains a positive opening, acceptance shall not require absence of heating action merely because a transition was forced. Cycle telemetry, a callback, or a scheduler trace alone is not proof of an identical physical command or of sending the raw TPI result.
- **AC-016 — Other thermostats.** Thermostats other than direct-valve `over_climate` show no new force behavior as a result of this specification.
- **AC-017 — Data and acknowledgement.** Observations distinguish calculated value, final service command, and possibly reported physical state; missing or delayed physical state is not interpreted as synchronous acknowledgement.

### 8. Out-of-scope functions

- Adding last-calculated or last-sent mode memory.
- Resetting a cache to zero or zero percent to bypass `dpercent`.
- Bypassing `dpercent` with `force=True`, when leaving `sleep`, or through the scheduler.
- Generalizing force behavior to other thermostat types.
- Changing the TPI formula, boundaries, threshold, min/max conversions, or existing protections.
- Adding a policy for missing or returning sensors.
- Changing concurrency, the Home Assistant environment, configuration, hardware, or dependencies.
- Quantifying battery use or guaranteeing behavior for untested hardware models.

### 9. Proposed future enhancements

- After observing final services, define diagnostics that distinguish an intentionally retained value from a delayed command.
- Extend integration coverage for automatic transitions and Zigbee devices when hardware traces are available.
- Document valve-family capabilities and limitations separately if reproducible hardware results are obtained.

### 10. Assumptions, open questions, and traceability

#### Established facts

- The review identifies `update_states` as knowing the effective mode change and connecting recalculation to control.
- Forced recalculation can bypass the recalculation period, while regulated sending has a separate delay.
- `dpercent` does not depend on `force` in the behavior described by the review and must remain separate from the timing exception.
- The existing `sleep` path imposes 100% without passing through the TPI branch variation filter.
- No local execution or hardware validation was performed for the new approach.

#### Retained assumptions

- Effective HVAC mode is the functional reference for distinguishing an actual transition from an identical request.
- Final services and the scheduler provide distinct observation points for the retained value, the attempted service command, and cycle telemetry; cycle telemetry is not equivalent to a physical valve command.
- Current behavior is the reference for missing data, returning data, and unsupported capabilities.

#### Non-blocking questions and test clarifications

- What precise effects of `force` on the scheduler, cycle windows, callbacks, and learning will be observed in tests, without promising an unchanged cycle cadence for the target?
- Which cycle telemetry should be correlated with the retained valve value and service call, while making explicit that it is not identical to a physical command?
- Do the tests clearly distinguish an immediate attempt through existing paths from service success or physical acknowledgement, neither of which is guaranteed?

#### Traceability: report -> rules -> acceptance criteria

| Report topic                                     | Business rules   | Acceptance criteria                    |
| ------------------------------------------------ | ---------------- | -------------------------------------- |
| Actual, manual, and automatic transition         | BR-001, BR-002   | AC-001, AC-002, AC-006, AC-008, AC-009 |
| Two timing gates and immediate application       | BR-003, BR-004   | AC-001, AC-002, AC-007, AC-017         |
| Strict preservation of `dpercent` and boundaries | BR-005 to BR-008 | AC-003, AC-004, AC-005, AC-012, AC-015 |
| Priority inhibition and protections              | BR-009 to BR-013 | AC-005, AC-011, AC-012, AC-014         |
| Missing data, hardware, and battery              | BR-014, BR-015   | AC-010, AC-017                         |
| Scope and regression safety                      | BR-002           | AC-016                                 |

This specification, both reports, and the design share the same scope: direct-valve `over_climate` thermostats during actual effective HVAC mode transitions. The requirements and acceptance criteria are covered by the design decision, flow, and planned tests. No blocking contradiction is identified. The solution is technically feasible and testable through the inspected interfaces; the remaining scheduler/learning, cycle-telemetry, and immediate-attempt details are non-blocking test clarifications. Development remains unauthorized.