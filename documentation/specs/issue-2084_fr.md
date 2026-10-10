# Spécification fonctionnelle — Issue #2084

## 1. Titre et métadonnées

- **Nom :** Préservation du préréglage utilisateur lors de la restauration et du rechargement central
- **Version :** 1.1
- **Statut :** convergée avec la conception technique — cycle 1
- **Date :** 2026-10-10
- **Propriétaire :** Projet Versatile Thermostat
- **Issue :** [#2084 — Le préréglage caché Safety devient le choix demandé après redémarrage](https://github.com/jmcollin78/versatile_thermostat/issues/2084)
- **Rapport approuvé :** [issue-2084-review.md](../tech-docs/issue-2084-review.md)
- **Périmètre :** séparation entre `requested_state.preset` utilisateur et `current_state.preset` caché (`safety`/`power`), pendant le démarrage et le rechargement central, ainsi que les tests de régression associés.
- **Sources analysées :** [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py), [vtherm_preset.py](../../custom_components/versatile_thermostat/vtherm_preset.py), [state_manager.py](../../custom_components/versatile_thermostat/state_manager.py), [feature_safety_manager.py](../../custom_components/versatile_thermostat/feature_safety_manager.py), [vtherm_central_api.py](../../custom_components/versatile_thermostat/vtherm_central_api.py), [test_safety.py](../../tests/test_safety.py), [test_last_seen.py](../../tests/test_last_seen.py) et [test_state_manager.py](../../tests/test_state_manager.py).

## 2. Contexte et objectifs

Les préréglages `safety` et `power` sont des préréglages cachés utilisés comme surcharges temporaires de l’état courant. Le préréglage demandé représente le choix utilisateur et doit rester disponible comme valeur de retour lorsque la surcharge disparaît.

Le rapport approuvé établit qu’après restauration d’un état où la sécurité était active, la réapplication des préréglages peut recopier `current_state.preset: safety` vers `requested_state.preset`, alors que le choix utilisateur était par exemple `comfort`. Lorsque la sécurité n’est plus active après le démarrage, le thermostat peut alors rester durablement sur le mauvais préréglage. Le même chemin est accessible lors d’un rechargement de la configuration centrale.

L’objectif est de préserver cette séparation sans modifier les algorithmes TPI, la logique des seuils ou la persistance de l’état actif de sécurité.

## 3. Acteurs et cas d’utilisation

### Acteurs

- **Utilisateur ou automatisation :** choisit un préréglage visible tel que `comfort`.
- **VTherm :** restaure les états, initialise les préréglages et calcule l’état courant.
- **Gestionnaire de sécurité ou de puissance :** applique une surcharge cachée à l’état courant lorsque la condition correspondante est active.
- **Configuration centrale :** déclenche la réinitialisation des préréglages pour les thermostats concernés.
- **Suite de tests :** vérifie les invariants de restauration, de démarrage et de rechargement.

### Cas nominal — démarrage après sécurité active

1. Avant le redémarrage, `requested_state.preset` vaut le préréglage utilisateur, par exemple `comfort`.
2. La sécurité active produit `current_state.preset: safety`.
3. L’état persistant est restauré.
4. Après démarrage, la sécurité n’est plus active.
5. Le système conserve `requested_state.preset: comfort` et recalcule `current_state.preset: comfort`.

### Cas nominal — rechargement central

1. Un VTherm utilise la configuration centrale des préréglages.
2. Une surcharge cachée peut être présente dans `current_state` sans représenter le choix utilisateur.
3. Le rechargement réinitialise les préréglages.
4. Le choix utilisateur demandé reste inchangé ; l’état courant revient au choix demandé lorsque la surcharge n’est plus active.

## 4. Exigences fonctionnelles

- **FR-001 — Séparation des états :** Le système doit préserver indépendamment `requested_state.preset` et `current_state.preset` lors de la restauration et de l’initialisation des préréglages.
- **FR-002 — Source utilisateur :** Le système doit considérer le préréglage visible et actuellement configuré présent dans `requested_state.preset` comme le choix utilisateur à conserver et à réappliquer.
- **FR-003 — Surcharge cachée :** Le système ne doit pas transformer `current_state.preset` égal à `safety` ou `power` en choix demandé durable.
- **FR-004 — Démarrage :** Après restauration d’un état où `current_state.preset` est caché et `requested_state.preset` est visible, le système doit conserver le préréglage visible demandé.
- **FR-005 — Recalcul après démarrage :** Lorsque la sécurité ou la puissance n’est plus active, le système doit permettre à `current_state.preset` de revenir au préréglage demandé conservé.
- **FR-006 — Rechargement central :** L’initialisation des préréglages issue de la configuration centrale doit respecter les mêmes invariants que le démarrage.
- **FR-007 — Couverture générique :** La protection doit couvrir `HIDDEN_PRESETS`, notamment `safety` et `power`, sans correction ad hoc limitée à `safety`.
- **FR-008 — Préservation des transitions existantes :** Une surcharge réellement active doit continuer à pouvoir apparaître dans `current_state.preset` sans écraser le préréglage utilisateur dans `requested_state.preset`.
- **FR-009 — Tests de régression :** La suite de tests doit couvrir la restauration après sécurité active, le retour au préréglage utilisateur, le rechargement central et le cas `power` lorsque le chemin générique des préréglages cachés est utilisé.

## 5. Règles métier et invariants

- **BR-001 — Rôle de `requested_state` :** `requested_state.preset` représente le dernier choix de préréglage utilisateur valide et visible.
- **BR-002 — Rôle de `current_state` :** `current_state.preset` représente le préréglage actuellement effectif, y compris une surcharge cachée temporaire.
- **BR-003 — Non-contamination :** Une valeur cachée de `current_state.preset` ne doit jamais contaminer `requested_state.preset` lors d’un démarrage ou d’un rechargement.
- **BR-004 — Priorité de surcharge :** Tant que la condition de sécurité ou de puissance est active, la surcharge peut rester visible dans `current_state.preset`, tandis que `requested_state.preset` reste le choix utilisateur.
- **BR-005 — Retour :** Lorsque la surcharge n’est plus active, `current_state.preset` doit être calculé à partir du préréglage demandé conservé.
- **BR-006 — Généralisation :** Les mêmes invariants s’appliquent à toutes les valeurs de `HIDDEN_PRESETS` concernées par le chemin commun.
- **BR-007 — Historique déjà contaminé :** Si aucun préréglage utilisateur fiable n’est disponible parce que les deux états persistés sont déjà cachés, le système ne doit pas réparer automatiquement ni inventer silencieusement un choix utilisateur ; il doit conserver l’historique disponible et attendre une commande explicite pour rétablir un préréglage visible.

## 6. Contraintes fonctionnelles et risques

### Contraintes

- Le périmètre doit rester limité au démarrage, à la restauration, au rechargement central et aux tests de régression associés.
- Aucun algorithme TPI, seuil, délai de sécurité, commande publique de préréglage ou mécanisme de persistance de la sécurité active ne doit être redéfini par cette spécification.
- Les comportements existants d’entrée et de sortie de sécurité pendant une même exécution doivent être conservés.
- Aucun nouvel accès, secret, appel réseau, traitement de données personnelles ou paramètre utilisateur ne doit être introduit.

### Risques

| Risque                                                                        | Gravité | Mesure de maîtrise                                                                                       |
| ----------------------------------------------------------------------------- | ------: | -------------------------------------------------------------------------------------------------------- |
| Le préréglage utilisateur reste remplacé par `safety` après redémarrage.      |  Élevée | Test de restauration avec sécurité inactive après reprise et assertions sur les deux états.              |
| Une correction de `safety` laisse le même défaut pour `power`.                | Moyenne | Couverture de `HIDDEN_PRESETS` et test spécifique de `power`.                                            |
| La réapplication du préréglage visible modifie un cas légitime de démarrage.  | Moyenne | Test d’un préréglage visible restauré et du rechargement central.                                        |
| Le rechargement central diverge du chemin de démarrage.                       | Moyenne | Scénario et test distincts pour l’initialisation centrale.                                               |
| Un historique déjà contaminé ne permet pas de retrouver le choix utilisateur. | Moyenne | Documenter une politique de récupération ; ne pas présenter une valeur inventée comme choix utilisateur. |

## 7. Critères d’acceptation

- **AC-001 — Conservation avant redémarrage :** Étant donné une sécurité active, `current_state.preset` peut valoir `safety`, mais `requested_state.preset` conserve le préréglage utilisateur `comfort`.
- **AC-002 — Restauration avec sécurité inactive :** Étant donné un état persistant avec `current_state.preset: safety` et `requested_state.preset: comfort`, après démarrage et désactivation de la sécurité, `requested_state.preset` vaut toujours `comfort` et `current_state.preset` revient à `comfort` lors du premier calcul applicable.
- **AC-003 — Aucun effet durable caché :** Aucun appel de démarrage ou d’initialisation des préréglages ne doit écrire `safety` ou `power` dans `requested_state.preset` uniquement parce que cette valeur était dans `current_state.preset`.
- **AC-004 — Rechargement central :** Avec la même séparation d’états, le rechargement de la configuration centrale conserve le préréglage utilisateur et permet le retour de l’état courant à ce préréglage lorsque la surcharge est inactive.
- **AC-005 — Sécurité toujours active :** Si la sécurité est réellement active après l’initialisation, `current_state.preset` peut rester `safety` tandis que `requested_state.preset` reste le préréglage visible demandé.
- **AC-006 — Régression `power` :** Le scénario équivalent avec `power` respecte la même séparation lorsque `power` appartient à `HIDDEN_PRESETS`.
- **AC-007 — Transitions existantes :** Les tests existants de déclenchement et de sortie de sécurité pendant une même exécution continuent de réussir sans changement de contrat.
- **AC-008 — Tests automatisés :** Des tests de régression couvrent les scénarios AC-002, AC-004 et AC-006 et échouent si un préréglage caché est copié dans `requested_state`.
- **AC-009 — Hors périmètre préservé :** Aucun critère ne nécessite de modifier les algorithmes TPI, la configuration utilisateur ou l’environnement Home Assistant.
- **AC-010 — Historique irrécupérable :** Lorsque `current_state.preset` et `requested_state.preset` sont tous deux cachés, l’initialisation ne doit sélectionner ni inventer automatiquement un préréglage visible, ni réappliquer un préréglage caché ; une commande explicite ultérieure doit rester le moyen de rétablissement.

## 8. Fonctions non prises en compte

- Modification des algorithmes TPI, des seuils, des temporisations ou de la stratégie de sécurité.
- Restauration de l’état actif de sécurité lui-même dans `feature_safety_manager`.
- Ajout d’un nouveau préréglage, d’un paramètre utilisateur, d’une migration ou d’une automatisation de contournement.
- Modification générale des commandes publiques de préréglage au-delà de la protection nécessaire contre la contamination par un préréglage caché.
- Correction d’autres problèmes de démarrage ou de rechargement non liés à la séparation `requested_state` / `current_state`.
- Modification de code produit, de configuration, de dépendance ou d’état Home Assistant dans le cadre de cette spécification.

## 9. Évolutions futures proposées

- Ajouter un diagnostic explicite lorsqu’un historique persistant contient uniquement des préréglages cachés et qu’aucun choix utilisateur fiable n’est récupérable.
- Documenter les règles de récupération des états historiques déjà contaminés.
- Étendre les tests aux futures valeurs ajoutées à `HIDDEN_PRESETS`.
- Ajouter une télémétrie ou un journal contrôlé pour faciliter le diagnostic des restaurations, si un besoin opérationnel est confirmé.

## 10. Hypothèses, questions ouvertes et traçabilité

### Faits établis

- `safety` et `power` sont des valeurs de `HIDDEN_PRESETS`.
- La sécurité affecte l’état courant et le calcul normal utilise le préréglage demandé lorsque la surcharge est absente.
- La restauration lit séparément `current_state` et `requested_state`.
- Le chemin d’initialisation actuel réapplique un préréglage à partir de l’état courant et peut donc contaminer l’état demandé.
- `init_presets()` est également appelé lors de la réinitialisation des préréglages centraux.
- Les tests existants couvrent les transitions pendant une même exécution, mais pas le scénario de persistance suivi d’un redémarrage ou d’un rechargement central décrit ici.

### Hypothèses retenues

- Un préréglage visible, valide et actuellement configuré dans `requested_state.preset` est la source de vérité à conserver et à réappliquer.
- Une surcharge cachée ne constitue jamais un choix utilisateur durable.
- Les utilitaires de test existants permettent de simuler une restauration suffisamment complète sans modifier l’environnement Home Assistant.

### Questions ouvertes

- **Q-001 — Résolue au cycle 1 :** si `current_state.preset` et `requested_state.preset` sont tous deux `safety` ou `power`, aucune réparation automatique ni inférence ne doit être effectuée ; une commande explicite est requise.
- **Q-002 — Non bloquante :** faut-il produire un journal lorsque la restauration ignore un préréglage caché ?
- **Q-003 — Non bloquante :** le rechargement central peut-il être déclenché pendant une surcharge `power` dans les scénarios supportés ?

### Traçabilité

Le [rapport approuvé de l’issue #2084](../tech-docs/issue-2084-review.md) est la source normative du périmètre. Les faits et symboles vérifiés sont `BaseThermostat.async_startup`, `BaseThermostat.get_my_previous_state`, `BaseThermostat.init_presets`, `BaseThermostat.async_set_preset_mode_internal`, `StateManager.calculate_current_preset`, `FeatureSafetyManager`, `HIDDEN_PRESETS` et `init_vtherm_preset_with_central`. Les tests concernés sont ceux de [test_safety.py](../../tests/test_safety.py), [test_last_seen.py](../../tests/test_last_seen.py) et [test_state_manager.py](../../tests/test_state_manager.py).
