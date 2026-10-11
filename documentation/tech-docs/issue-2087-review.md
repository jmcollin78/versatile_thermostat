# Revue de l’issue #2087 — Inhibition extensible d’un VTherm

- **Issue :** [#2087 — Add an "inhibit" sensor to pause a VTherm](https://github.com/jmcollin78/versatile_thermostat/issues/2087)
- **Statut de revue :** recommandation à valider avant spécification et conception
- **Décision recommandée :** retenir une évolution du core limitée à un mécanisme d’inhibition extensible, puis réaliser la fonctionnalité de capteur dans un plugin.

## 1. Résumé fidèle de l’issue

L’issue propose d’empêcher temporairement un VTherm de commander ses sous-jacents lorsqu’une autre source de chauffage ou de refroidissement est active. Les exemples sont un chauffage sur surplus photovoltaïque et une climatisation qui refroidit une pièce tandis que le radiateur thermostatique ne doit pas chauffer.

Le comportement attendu est le suivant :

- le VTherm cesse de contrôler le chauffage dès l’activation de l’inhibition ;
- à la levée, il reprend l’état demandé courant, y compris les changements de preset ou HVAC intervenus entre-temps ;
- un arrêt manuel effectué pendant l’inhibition est respecté ;
- le redémarrage de Home Assistant conserve la sémantique ;
- l’utilisateur peut piloter directement les sous-jacents pendant l’inhibition, sans que VTherm réémette des ordres ;
- une solution plugin est privilégiée par le mainteneur, mais l’API existante ne permet pas au plugin de participer correctement à la résolution de l’état HVAC.

L’issue suggérait initialement une fonctionnalité core complète nommée *inhibit*. La discussion a convergé vers un point d’extension dans le core et un plugin qui porte la détection et la configuration spécifiques.

## 2. Sources et éléments vérifiés

### Issue et échanges

- Description, alternatives et commentaires de [l’issue #2087](https://github.com/jmcollin78/versatile_thermostat/issues/2087).
- Position initiale du mainteneur : éviter une fonctionnalité core spécifique et favoriser un plugin.
- Analyse de l’auteur : un plugin actuel ne peut qu’appeler des services HVAC et modifierait alors l’état demandé au lieu de l’état effectif.

### Code du dépôt vérifié

- [custom_components/versatile_thermostat/state_manager.py](../../custom_components/versatile_thermostat/state_manager.py) : la résolution de l’état HVAC effectif est centralisée dans `StateManager`; seules les contraintes internes sont aujourd’hui prises en compte.
- [custom_components/versatile_thermostat/base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) : `update_states()` applique les changements d’état aux sous-jacents, et la boucle de contrôle appelle la logique de chauffage puis la réparation d’état.
- [custom_components/versatile_thermostat/prop_handler_tpi.py](../../custom_components/versatile_thermostat/prop_handler_tpi.py) : le contrôle TPI arrête à nouveau un appareil actif quand le HVAC effectif est `OFF`.
- [custom_components/versatile_thermostat/feature_repair_incorrect_state_manager.py](../../custom_components/versatile_thermostat/feature_repair_incorrect_state_manager.py) et [custom_components/versatile_thermostat/underlyings.py](../../custom_components/versatile_thermostat/underlyings.py) : le mécanisme de réparation peut réémettre des ordres vers les sous-jacents.
- [custom_components/vtherm_api/src/vtherm_api/interfaces.py](../../custom_components/vtherm_api/src/vtherm_api/interfaces.py) et [custom_components/vtherm_api/src/vtherm_api/vtherm_api.py](../../custom_components/vtherm_api/src/vtherm_api/vtherm_api.py) : l’API connaît déjà le registre de factories de gestionnaires, mais aucun contrat d’inhibition ni factory dédiée.
- [custom_components/versatile_thermostat/vtherm_state.py](../../custom_components/versatile_thermostat/vtherm_state.py) : l’état sérialisé ne contient actuellement que HVAC, consigne et preset.

## 3. Analyse de pertinence

### Valeur

**Élevée.** Le besoin évite des conflits énergivores entre plusieurs équipements, sans détourner la fonctionnalité de fenêtre. Il répond aussi à un usage avancé : donner temporairement le contrôle effectif des sous-jacents à l’utilisateur ou à une automatisation externe.

### Cohérence avec le projet

**Cohérente sous réserve d’un périmètre réduit.** Une fonctionnalité *inhibit* complète dans le core (flux de configuration, entités, traductions et toutes les actions) dupliquerait en grande partie la fonctionnalité fenêtre et augmenterait la matrice de maintenance.

Un point d’extension core, à sémantique stricte, préserve l’orientation plugin tout en couvrant une lacune réelle de l’API : les managers externes actuels sont rafraîchis après le contrôle de chauffage et ne participent pas à la résolution de l’état effectif.

### Faisabilité apparente

**Faisable.** Le modèle `requested_state` / `current_state` fournit déjà le mécanisme requis pour reprendre le bon état après l’inhibition. Le point délicat est la délégation temporaire du contrôle des sous-jacents : une fois l’arrêt initial appliqué, le cycle de chauffage et la réparation automatique ne doivent plus intervenir jusqu’à la levée de l’inhibition.

## 4. Recommandation

**Retenir l’évolution suivante :**

1. Ajouter dans `vtherm_api` un registre dédié de factories : `register_inhibition_provider_factory(factory)`.
2. Le core instancie au plus un `InhibitionProvider` par VTherm éligible ; tout conflit d’enregistrement doit être explicite.
3. Le provider plugin détecte la condition, ses délais et son éventuel bypass. Il ne pilote ni HVAC ni sous-jacents.
4. Le core porte la politique d’inhibition : arrêt une seule fois à l’entrée, retrait du contrôle du VTherm pendant l’inhibition, puis réconciliation avec l’état demandé à la sortie.
5. Le `StateManager` conserve la responsabilité exclusive de résoudre l’état HVAC effectif. L’inhibition y est une contrainte prioritaire après l’arrêt central et la sécurité, avant fenêtre et auto-start/stop.
6. Le comportement spécifique de capteur, les entités de diagnostic, les services de bypass, la configuration et les délais restent dans un plugin dédié.

## 5. Périmètre proposé

### Inclus dans le core et l’API

- Interface `InhibitionProvider` et factory dédiée dans `vtherm_api`.
- Unicité du provider par VTherm et cycle de vie core (`post_init`, écoute, restauration, arrêt).
- Méthode core de recalcul demandée par le provider lors d’une transition confirmée.
- Règle de résolution HVAC vers `OFF` lorsque l’inhibition est active et que le HVAC demandé n’est pas `OFF`.
- Nouvelle raison stable d’arrêt et de mode, par exemple `hvac_off_inhibition`.
- Mémoire persistée, détenue par le core, indiquant qu’une mise en retrait est active et que le contrôle des sous-jacents a déjà été remis.
- Arrêt physique unique à l’entrée en inhibition.
- Suspension du contrôle de chauffage et de la réparation d’état tant que la mise en retrait est active.
- Reprise et application de l’état demandé courant à la sortie.
- Tests unitaires et d’intégration correspondants.

### Inclus dans le plugin d’inhibition

- Lecture de la ou des entités source.
- Délais d’activation et de désactivation.
- Bypass éventuel, persistance associée et diagnostics spécifiques.
- Configuration, traductions, documentation, services et entités du plugin.

### Exclus de la première itération

- Ajout de `inhibited` dans `requested_state` ou `current_state`.
- Actions alternatives `eco`, `frost`, `fan_only` ou tout autre mode forcé.
- Multiples providers indépendants par VTherm.
- Migration de la fonctionnalité fenêtre vers le nouveau mécanisme.
- Refactorisation générale de toutes les contraintes HVAC.

## 6. Décisions d’architecture proposées

### Séparation des responsabilités

| Composant             | Responsabilité                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------- |
| Plugin                | Détecter la condition d’inhibition et signaler les transitions.                             |
| `InhibitionProvider`  | Exposer `is_detected` et assurer son cycle de vie.                                          |
| Core `BaseThermostat` | Détenir l’état de délégation, piloter les transitions et suspendre les boucles de contrôle. |
| `StateManager`        | Résoudre l’état effectif à partir de l’état demandé et des contraintes.                     |
| Sous-jacents          | Recevoir l’arrêt initial et la reprise normale uniquement hors inhibition.                  |

### Invariant principal

L’état demandé reste l’intention durable appliquée après l’inhibition :

$$
current\_state = f(requested\_state, contraintes\ actives)
$$

L’inhibition est une contrainte externe, non une modification du HVAC ou du preset demandé.

### Mise en retrait contrôlée

L’inhibition est plus riche qu’un simple `OFF` forcé : elle transfère temporairement le contrôle effectif des sous-jacents à l’utilisateur ou à une autre intégration.

| Transition          | Comportement attendu                                                                          |
| ------------------- | --------------------------------------------------------------------------------------------- |
| inactive → active   | Résoudre HVAC `OFF`, envoyer l’arrêt une fois, mémoriser le transfert de contrôle.            |
| active → active     | Ne pas lancer le contrôle chauffage, ne pas réparer les sous-jacents, ne pas réémettre `OFF`. |
| active → inactive   | Recalculer et appliquer le `requested_state` alors courant.                                   |
| inactive → inactive | Fonctionnement VTherm existant.                                                               |

## 7. Impacts et risques

| Domaine                    | Impact / risque                                                                 | Gravité | Probabilité | Mesure proposée                                                                         |
| -------------------------- | ------------------------------------------------------------------------------- | ------- | ----------- | --------------------------------------------------------------------------------------- |
| Fonctionnel                | Le VTherm pourrait reprendre le contrôle pendant l’inhibition.                  | Haute   | Moyenne     | Sortie anticipée de la boucle de chauffage et désactivation du repair.                  |
| Fonctionnel                | Un sous-jacent déjà actif pourrait ne pas être arrêté à la première inhibition. | Haute   | Moyenne     | Gérer explicitement le front d’entrée, indépendamment du seul changement HVAC.          |
| Compatibilité              | Conflit entre deux plugins souhaitant contrôler l’inhibition.                   | Moyenne | Faible      | Imposer un provider unique, erreur explicite lors du conflit.                           |
| Persistance                | Redémarrage pouvant envoyer un second arrêt ou reprendre trop tôt.              | Haute   | Moyenne     | Persister l’état de délégation core et réconcilier avec le provider après démarrage.    |
| Exploitation               | Diagnostics insuffisants pour comprendre pourquoi VTherm est retiré.            | Moyenne | Moyenne     | Raison HVAC dédiée et attributs core de diagnostic.                                     |
| API                        | Contrat public difficile à faire évoluer.                                       | Moyenne | Moyenne     | Limiter l’interface V1 à la détection, au cycle de vie et au signalement de transition. |
| Sécurité / confidentialité | Aucun impact additionnel identifié.                                             | Faible  | Faible      | Pas de données sensibles supplémentaires.                                               |

## 8. Alternatives examinées

### A. Automation qui force `climate.set_hvac_mode`

- **Avantage :** aucune modification de VTherm.
- **Inconvénient :** modifie l’état demandé ; doit mémoriser qui a arrêté, gérer les presets et persister la logique de reprise. Reproduit partiellement une couche déjà présente dans VTherm.
- **Conclusion :** contournement acceptable, mais insuffisant pour le comportement demandé.

### B. Réutiliser le capteur fenêtre

- **Avantage :** déjà fonctionnel et robuste pour la reprise.
- **Inconvénient :** diagnostic erroné (« fenêtre »), interférence avec la détection automatique, impossibilité de représenter la délégation des sous-jacents.
- **Conclusion :** contournement temporaire uniquement.

### C. Extension générique de `FeatureManager` avec override HVAC

- **Avantage :** réutilisable en théorie.
- **Inconvénient :** nécessite de définir les priorités inter-plugins, la résolution des conflits, l’ordonnancement, les raisons et un mécanisme de recalcul. Cela est plus général mais pas plus simple.
- **Conclusion :** non retenue pour l’itération initiale.

### D. Fonctionnalité *inhibit* complète dans le core

- **Avantage :** parcours utilisateur intégré et homogène.
- **Inconvénient :** forte duplication avec fenêtre ; augmentation importante du périmètre et de la maintenance du core.
- **Conclusion :** non retenue ; le core ne fournit que le mécanisme de retrait contrôlé, le plugin porte la fonction métier.

## 9. Hypothèses, décisions nécessaires et questions ouvertes

### Hypothèses

- Le plugin fournit un état fiable après ses délais configurés.
- Le provider est disponible avant ou pendant l’initialisation du VTherm ; le core doit néanmoins gérer l’ordre de chargement.
- `OFF` est la seule action forcée de la V1.

### Décisions à confirmer

1. Valeur définitive de la raison d’arrêt : `hvac_off_inhibition` est proposée.
2. Emplacement et format exact des attributs persistés de délégation.
3. Politique de conflit : refus du second provider, recommandée.
4. Faut-il fournir dès la V1 un bypass dans le plugin, ou le différer ?
5. Faut-il livrer la factory et le plugin dans des pull requests séparées ? Recommandé.

### Questions ouvertes non bloquantes

- Le provider doit-il supporter plusieurs sources nativement ou seulement via un capteur/template agrégé par le plugin ? La V1 recommande un provider unique avec agrégation côté plugin.
- Le plugin doit-il être limité à certains types de VTherm ? La factory décidera son éligibilité.

## 10. Critères de passage au développement

Le développement pourra démarrer après validation explicite de ce rapport et après production convergente des spécifications et de la conception détaillée. Ces documents devront préciser :

- le contrat exact de l’API et les règles de compatibilité ;
- l’ordre des priorités HVAC ;
- les transitions d’inhibition et la persistance ;
- les cas de démarrage et de rechargement ;
- les critères d’acceptation et la matrice de tests ;
- le découpage core/API/plugin et son ordre d’intégration.
