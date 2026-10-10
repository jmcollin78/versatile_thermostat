# Revue de l’issue #2049 — blocage d’initialisation de la régulation de vanne

**Statut :** à valider avant spécification et conception
**Issue :** [#2049 — auto_regulation_valve deadlocks permanently when opening/closing degree numbers stay unknown after restart (Sonoff TRVZB)](https://github.com/jmcollin78/versatile_thermostat/issues/2049)
**Dépôt examiné :** `jmcollin78/versatile_thermostat`, branche `main`
**Date de revue :** 2026-10-10

## 1. Résumé fidèle de l’issue

Avec VTherm 10.2.0 et une configuration `over_climate` utilisant `auto_regulation_valve`, l’auteur indique que neuf thermostats Sonoff TRVZB sur dix sont restés durablement arrêtés après un redémarrage Home Assistant. Les entités `number` configurées pour les degrés d’ouverture et de fermeture de vanne étaient à l’état `unknown`, tandis que les entités `climate` sous-jacentes restaient normales.

L’issue rapporte que `is_initialized` ne devient jamais vrai, que le message `not_initialized` persiste et que le thermostat ne renvoie aucune commande susceptible de sortir les nombres de cet état. L’écriture manuelle d’une valeur sur chaque nombre d’ouverture et de fermeture débloque immédiatement le thermostat.

L’auteur attribue ce cas aux attributs Zigbee2MQTT du Sonoff TRVZB : ils seraient des consignes d’écriture sans retour de position réel. Une perte du cache Zigbee2MQTT au redémarrage laisserait donc leurs valeurs à `unknown` de manière permanente. Il propose de ne pas attendre indéfiniment, de réécrire une valeur calculée/restaurée au démarrage et/ou de documenter cette contrainte.

Le mainteneur a accusé réception. L’issue est ouverte, non assignée, sans branche ni pull request associée, et porte les étiquettes `P0` et `question`.

## 2. Sources et éléments vérifiés

- Description, configuration, diagnostic, commentaires et métadonnées de [#2049](https://github.com/jmcollin78/versatile_thermostat/issues/2049). Aucun journal de débogage exploitable n’est joint à ce stade, mais l’auteur indique pouvoir le fournir.
- Le gestionnaire d’état considère une entité comme non initialisée lorsque son état est absent, `unknown` ou `unavailable` : [custom_components/versatile_thermostat/underlying_state_manager.py](../../custom_components/versatile_thermostat/underlying_state_manager.py#L101-L125).
- Les entités `opening_degree` et `closing_degree` de la régulation de vanne sont explicitement suivies par le gestionnaire d’état lors du démarrage : [custom_components/versatile_thermostat/underlyings.py](../../custom_components/versatile_thermostat/underlyings.py#L1429-L1598).
- Un thermostat `over_climate_valve` exige l’initialisation du thermostat parent et de chaque sous-jacent de régulation de vanne : [custom_components/versatile_thermostat/thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L161-L171).
- Les tests existants confirment que les états `unknown` et `unavailable` restent non initialisés, mais ne couvrent pas une entité de consigne de vanne définitivement inconnue après redémarrage : [tests/test_check_initial_state.py](../../tests/test_check_initial_state.py#L1-L150) et [tests/test_overclimate_valve.py](../../tests/test_overclimate_valve.py#L1-L220).
- La documentation décrit les entités de régulation de vanne et mentionne déjà le Sonoff TRVZB, sans documenter ce scénario de blocage : [documentation/en/over-climate.md](../en/over-climate.md#L43-L62) et [documentation/en/feature-recalibrate-valves.md](../en/feature-recalibrate-valves.md#L11-L46).

Aucun test n’a été exécuté et aucun état Home Assistant, code, configuration ou dépendance n’a été modifié pendant la revue.

## 3. Pertinence et recommandation

### Recommandation : retenir une correction ciblée de l’amorçage de la régulation de vanne

Le chemin analysé confirme la plausibilité technique du blocage : les nombres utilisés pour commander la vanne contribuent à la condition globale d’initialisation ; `unknown` les maintient indéfiniment non initialisés. Pour une entité de commande sans retour d’état fiable, cela peut former une boucle sans sortie : VTherm attend un état qui ne sera produit que par une commande VTherm non émise tant qu’il reste non initialisé.

Le problème est pertinent et de gravité élevée : il peut empêcher durablement le chauffage de plusieurs zones après un redémarrage. Il ne s’agit toutefois pas d’une justification pour relâcher globalement la règle de sécurité sur les états inconnus. La correction doit être limitée aux nombres propres à `auto_regulation_valve`, après avoir défini une valeur d’amorçage sûre et son déclencheur.

Une information complémentaire reste souhaitable, mais n’est pas bloquante pour spécifier une solution : les journaux de démarrage du cas réel et la confirmation du comportement en écriture seule de la version Zigbee2MQTT/firmware concernée. Ils serviront à valider la reproduction et la documentation, non à justifier une exception globale.

## 4. Périmètre proposé

### Inclus

- Traitement spécifique de l’état initial `unknown`/`unavailable` des entités `number` configurées comme degrés d’ouverture ou de fermeture dans `auto_regulation_valve`.
- Définition d’un amorçage sûr, borné et idempotent pour éviter l’attente infinie après le démarrage ou le rechargement de l’intégration.
- Préservation du blocage d’initialisation pour les autres sous-jacents et pour les erreurs non couvertes par cette exception ciblée.
- Tests de régression couvrant un démarrage avec les nombres de valve inconnus, la sortie de l’état non initialisé et le fonctionnement nominal existant.
- Documentation de la compatibilité des périphériques à retour de position incertain et de la récupération attendue.

### Exclus

- Modification de la sémantique générale de `UnderlyingStateManager` pour toutes les entités `unknown` ou `unavailable`.
- Détection générique de marque, modèle ou firmware Zigbee.
- Modification du cache Zigbee2MQTT, du firmware TRVZB ou de l’état Home Assistant hors VTherm.
- Refonte de l’algorithme TPI, des seuils de vanne ou du mécanisme de recalibrage manuel.

## 5. Impacts et risques

| Risque                                                                                 | Gravité | Probabilité                                     | Mesure proposée                                                                                                                                                                                                                                                                                                  |
| -------------------------------------------------------------------------------------- | ------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Chauffage durablement indisponible après redémarrage                                   | Élevée  | Moyenne à élevée pour les appareils sans retour | Amorçage ciblé, test de régression et indication diagnostique claire.                                                                                                                                                                                                                                            |
| Masquage d’une panne réelle d’une entité de régulation                                 | Élevée  | Moyenne                                         | Limiter l’exception aux nombres `opening_degree`/`closing_degree` de `auto_regulation_valve`; ne pas modifier la règle globale.                                                                                                                                                                                  |
| Envoi d’une consigne de démarrage inadaptée à la vanne                                 | Élevée  | Moyenne                                         | Concevoir une valeur sûre explicite, bornée par les seuils configurés et réémise de manière idempotente.                                                                                                                                                                                                         |
| Régression du démarrage normal des appareils avec retour d’état                        | Moyenne | Moyenne                                         | Conserver le flux nominal et ajouter des tests pour les valeurs disponibles comme pour les valeurs inconnues.                                                                                                                                                                                                    |
| Régression fonctionnelle de cas nominaux par une exception d’initialisation trop large | Élevée  | Élevée                                          | Vérifier prioritairement, par tests de non-régression, les démarrages avec états disponibles, les états réellement indisponibles, les commandes normales, les seuils configurés et les appareils avec retour d’état ; le nouveau comportement ne doit s’appliquer qu’aux nombres ciblés dans le scénario défini. |
| Documentation insuffisante sur les entités de commande sans retour                     | Moyenne | Élevée                                          | Ajouter une limite de compatibilité et une procédure de diagnostic/récupération.                                                                                                                                                                                                                                 |
| Confidentialité                                                                        | Faible  | Faible                                          | Ne journaliser que les identifiants d’entités et états techniques déjà exposés.                                                                                                                                                                                                                                  |

## 6. Alternatives examinées

| Alternative                                                                               | Avantages                                                | Inconvénients                                                                               | Décision                                 |
| ----------------------------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Ignorer globalement `unknown` et `unavailable` à l’initialisation                         | Simple et étend le démarrage à tous les cas              | Masque des capteurs et sous-jacents réellement défaillants; risque de sécurité              | Écartée                                  |
| Attendre passivement un état valable sans limite                                          | Préserve strictement la logique actuelle                 | Provoque le blocage permanent documenté                                                     | Écartée                                  |
| Forcer seulement une valeur manuelle par l’utilisateur                                    | Aucun changement logiciel                                | Non fiable, non scalable et incompatible avec la récupération automatique après redémarrage | Écartée                                  |
| Amorcer de façon ciblée les nombres de régulation de vanne avec une valeur sûre/restaurée | Résout la boucle tout en préservant le garde-fou général | Exige de définir précisément la valeur, le moment et les limites d’écriture                 | Retenue pour spécification et conception |
| Documenter uniquement la limitation                                                       | Faible coût                                              | Ne corrige pas les installations existantes ni la perte de chauffage                        | Complément retenu, insuffisant seul      |

## 7. Hypothèses, décisions nécessaires et questions ouvertes

### Hypothèses à vérifier

- Les nombres Sonoff TRVZB concernés sont des consignes d’écriture sans retour de position utile à VTherm.
- Lorsqu’ils sont `unknown` après redémarrage, aucune source externe ne les ramène spontanément à une valeur numérique.
- La valeur de commande restaurée ou calculée par VTherm est disponible, ou une valeur sûre peut être définie à partir de la configuration.

### Décisions à prendre pendant la conception

1. Déterminer la valeur d’amorçage prioritaire : dernière valeur restaurée, valeur TPI recalculée, ou repli sûr explicite.
2. Fixer le déclencheur et la limite de tentatives afin d’éviter les écritures répétées ou une boucle de démarrage.
3. Définir le comportement si l’écriture de la valeur d’amorçage échoue ou si l’entité reste `unknown` après cette tentative.
4. Définir les attributs/journaux de diagnostic nécessaires, sans considérer un état défaillant comme sain de façon silencieuse.

### Questions ouvertes non bloquantes

- Versions précises de Home Assistant, Zigbee2MQTT et firmware TRVZB du cas remonté.
- Journaux détaillés du redémarrage, notamment la liste des entités non initialisées et les appels de service éventuels.
- Reproduction après rechargement du config entry, en plus du redémarrage complet de Home Assistant.

## 8. Suite proposée et critères de passage

### Proposition de suite

Après validation de cette revue, rédiger une spécification fonctionnelle puis une conception technique convergentes pour l’amorçage sécurisé des nombres de régulation de vanne. Ces documents devront définir les états, commandes, limites de reprise, erreurs et scénarios de tests. Aucun développement ne doit commencer avant leur validation explicite.

### Critères de passage à la spécification et à la conception

- Le présent rapport est approuvé.
- Le périmètre ciblé, incluant l’amorçage contrôlé et la documentation, est accepté.
- Les questions ouvertes sont acceptées comme points de validation et non comme des prérequis au démarrage de la conception.

### Critères de passage au développement

- La spécification et la conception partagent un même comportement d’amorçage, y compris les échecs et les limites de répétition.
- Les tests prévus couvrent les nombres inconnus au démarrage, les nombres normalement disponibles, un échec d’écriture et l’absence de régression de l’initialisation des autres sous-jacents.
- Les tests de non-régression démontrent explicitement que les cas nominaux de régulation de vanne conservent leur comportement avant et après l’amorçage ciblé.
- La documentation de compatibilité et de diagnostic est définie.
- Une autorisation explicite de développement est fournie après validation des documents de spécification et de conception.
