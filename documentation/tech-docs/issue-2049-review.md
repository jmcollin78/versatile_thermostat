# Revue de l’issue #2049 — blocage d’initialisation de la régulation de vanne

**Statut :** revue validée ; solution simplifiée implémentée, à vérifier avant livraison
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
- Les entités `opening_degree` et `closing_degree` de la régulation de vanne sont explicitement suivies par le gestionnaire d’état lors du démarrage. Le seed one-shot est exécuté après l’enregistrement normal des listeners, sans modifier l’autorité du gestionnaire : [custom_components/versatile_thermostat/underlyings.py](../../custom_components/versatile_thermostat/underlyings.py#L1548-L1658).
- Un thermostat `over_climate_valve` exige l’initialisation du thermostat parent et de chaque sous-jacent de régulation de vanne ; le flux historique est conservé : [custom_components/versatile_thermostat/thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L146-L155).
- Les tests couvrent désormais le seed `unknown`, l’absence de readiness sans retour numérique, l’atomicité sur une cible `unavailable`, les bornes invalides, l’erreur de service et le chemin nominal : [tests/test_check_initial_state.py](../../tests/test_check_initial_state.py#L1-L175).
- La documentation utilisateur française et anglaise couvre le seed, ses limites et le dépannage : [documentation/fr/over-climate.md](../fr/over-climate.md) et [documentation/en/over-climate.md](../en/over-climate.md).

Les tests ciblés ont été exécutés lors de l’implémentation (81 réussis). Aucun état Home Assistant, code de dépendance ou configuration d’exécution n’a été modifié pendant la revue initiale.

## 3. Pertinence et recommandation

### Recommandation : retenir une correction ciblée de l’amorçage de la régulation de vanne

Le chemin analysé confirme la plausibilité technique du blocage : les nombres utilisés pour commander la vanne contribuent à la condition globale d’initialisation ; `unknown` les maintient indéfiniment non initialisés. Pour une entité de commande sans retour d’état fiable, cela peut former une boucle sans sortie : VTherm attend un état qui ne sera produit que par une commande VTherm non émise tant qu’il reste non initialisé.

Le problème est pertinent et de gravité élevée : il peut empêcher durablement le chauffage de plusieurs zones après un redémarrage. Il ne s’agit toutefois pas d’une justification pour relâcher globalement la règle de sécurité sur les états inconnus. La correction doit être limitée aux nombres propres à `auto_regulation_valve`, après avoir défini une valeur d’amorçage sûre et son déclencheur.

La solution retenue est un **seed one-shot minimal** : après les listeners normaux, VTherm peut écrire une seule paire sûre de fermeture calculée avec $d=0$, uniquement sur les cibles exactement `unknown`. Cette écriture ne rend jamais la vanne prête ; seul un événement numérique ultérieur, traité par `UnderlyingStateManager`, peut poursuivre le flux historique d’initialisation.

## 4. Périmètre proposé

### Inclus

- Traitement spécifique de l’état initial exactement `unknown` des entités `number` configurées comme degrés d’ouverture ou de fermeture dans `auto_regulation_valve`.
- Seed de fermeture sûr, borné et idempotent : au plus une écriture par cible et par instance, calculée avec $d=0$.
- Atomicité de paire : une cible `unavailable`, absente, invalide ou à bornes incohérentes interdit toute écriture de la paire.
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
| Chauffage durablement indisponible après redémarrage                                   | Élevée  | Moyenne à élevée pour les appareils sans retour | Seed ciblé sur `unknown`, test de régression et indication diagnostique claire ; sans retour numérique, l’état non prêt est conservé.                                                                                                                                                                            |
| Masquage d’une panne réelle d’une entité de régulation                                 | Élevée  | Moyenne                                         | Limiter l’exception aux nombres `opening_degree`/`closing_degree` de `auto_regulation_valve`; ne pas modifier la règle globale.                                                                                                                                                                                  |
| Envoi d’une consigne de démarrage inadaptée à la vanne                                 | Élevée  | Moyenne                                         | Concevoir une valeur sûre explicite, bornée par les seuils configurés et réémise de manière idempotente.                                                                                                                                                                                                         |
| Régression du démarrage normal des appareils avec retour d’état                        | Moyenne | Moyenne                                         | Conserver le flux nominal et ajouter des tests pour les valeurs disponibles comme pour les valeurs inconnues.                                                                                                                                                                                                    |
| Régression fonctionnelle de cas nominaux par une exception d’initialisation trop large | Élevée  | Élevée                                          | Vérifier prioritairement, par tests de non-régression, les démarrages avec états disponibles, les états réellement indisponibles, les commandes normales, les seuils configurés et les appareils avec retour d’état ; le nouveau comportement ne doit s’appliquer qu’aux nombres ciblés dans le scénario défini. |
| Documentation insuffisante sur les entités de commande sans retour                     | Moyenne | Élevée                                          | Ajouter une limite de compatibilité et une procédure de diagnostic/récupération.                                                                                                                                                                                                                                 |
| Confidentialité                                                                        | Faible  | Faible                                          | Ne journaliser que les identifiants d’entités et états techniques déjà exposés.                                                                                                                                                                                                                                  |

## 6. Alternatives examinées

| Alternative                                                                               | Avantages                                                   | Inconvénients                                                                               | Décision                            |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------- |
| Ignorer globalement `unknown` et `unavailable` à l’initialisation                         | Simple et étend le démarrage à tous les cas                 | Masque des capteurs et sous-jacents réellement défaillants; risque de sécurité              | Écartée                             |
| Déclarer la vanne prête sur acceptation du service                                        | Peut sembler récupérer le chauffage sans retour d’état      | Masque une panne et contourne le contrat d’initialisation                                   | Écartée                             |
| Forcer seulement une valeur manuelle par l’utilisateur                                    | Aucun changement logiciel                                   | Non fiable, non scalable et incompatible avec la récupération automatique après redémarrage | Écartée                             |
| Seed one-shot ciblé avec une paire de fermeture à $d=0$, puis attente du retour numérique | Rompt la boucle sans créer de second cycle d’initialisation | Ne peut pas rendre prêt un appareil qui ne publie jamais de retour numérique                | Retenue et implémentée              |
| Documenter uniquement la limitation                                                       | Faible coût                                                 | Ne corrige pas les installations existantes ni la perte de chauffage                        | Complément retenu, insuffisant seul |

## 7. Hypothèses, décisions nécessaires et questions ouvertes

### Hypothèses à vérifier

- Les nombres Sonoff TRVZB concernés sont des consignes d’écriture sans retour de position utile à VTherm.
- Lorsqu’ils sont `unknown` après redémarrage, aucune source externe ne les ramène spontanément à une valeur numérique.
- La valeur de commande restaurée ou calculée par VTherm est disponible, ou une valeur sûre peut être définie à partir de la configuration.

### Décisions retenues

1. La valeur d’amorçage est la paire de fermeture calculée par l’algorithme existant avec $d=0$.
2. Le seed est déclenché une fois par cible et par instance, après l’enregistrement des listeners ; aucun timeout ni retry n’est ajouté.
3. Si l’écriture échoue ou si l’état reste `unknown`, le sous-jacent reste non prêt ; l’acceptation du service ne vaut pas feedback ni readiness.
4. Les diagnostics décrivent l’action ou le motif de blocage, sans affirmer que la vanne est prête.

### Questions ouvertes non bloquantes

- Versions précises de Home Assistant, Zigbee2MQTT et firmware TRVZB du cas remonté.
- Journaux détaillés du redémarrage, notamment la liste des entités non initialisées et les appels de service éventuels.
- Reproduction après rechargement du config entry, en plus du redémarrage complet de Home Assistant.

## 8. Suite proposée et critères de passage

### Proposition de suite

La spécification, la conception et l’implémentation ont été réalisées. Avant livraison, vérifier les tests de non-régression requis et, si possible, le comportement sur le matériel concerné.

### Critères de passage au développement

Les critères ont été satisfaits par l’autorisation explicite, la spécification, la conception et l’implémentation. Le gate de livraison restant est l’exécution des tests de non-régression exigés et la validation matérielle lorsque disponible.
