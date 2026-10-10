# Revue de l’issue #2084 — le préréglage caché Safety devient le choix demandé après redémarrage

- **Référence :** [jmcollin78/versatile_thermostat#2084](https://github.com/jmcollin78/versatile_thermostat/issues/2084)
- **État vérifié :** ouverte, non assignée, étiquetée `bug` et `P0`, sans jalon, relation, branche ni pull request liée.
- **Date de revue :** 2026-10-10.
- **Recommandation :** **retenir** comme correction de bug ciblée et prioritaire.

## 1. Résumé fidèle de l’issue

L’issue décrit deux VTherm `over_switch` utilisant TPI et la fonctionnalité de sécurité. Avant un redémarrage de Home Assistant, quand la sécurité est active, l’état effectif est correctement `safety` tandis que le préréglage demandé reste `comfort`. Après le redémarrage alors que la sécurité était active, le capteur de sécurité redevient inactif, mais le préréglage affiché, le `current_state.preset` et le `requested_state.preset` restent tous à `safety`.

Le thermostat fonctionne encore, mais il demeure dans cet état jusqu’à une nouvelle commande externe de préréglage ou au prochain changement planifié. L’auteur fournit un chemin reproductible et identifie que la réapplication du préréglage durant l’initialisation copie le préréglage effectif — qui peut être caché — vers l’état demandé. Le même mécanisme peut être atteint lors d’un rechargement de la configuration centrale.

L’issue fait suite à [#1909](https://github.com/jmcollin78/versatile_thermostat/issues/1909), fermé faute de reproduction à l’époque. Cette issue documente désormais un scénario de reproduction précis.

## 2. Sources et éléments vérifiés

### Sources GitHub

- [Issue #2084](https://github.com/jmcollin78/versatile_thermostat/issues/2084) : description, scénario, analyse de chemin d’exécution, suggestion de correction, commentaire du mainteneur, métadonnées et absence de développement lié, consultés le 2026-10-10.
- [Issue #1909](https://github.com/jmcollin78/versatile_thermostat/issues/1909) : symptôme historique analogue ; le mainteneur y constate que `requested_state.preset: safety` est anormal et suspecte une restauration après redémarrage. Elle a été fermée sans reproduction fiable.

### Dépôt local — faits établis

- [custom_components/versatile_thermostat/base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) restaure séparément `current_state` et `requested_state` depuis les attributs enregistrés. Cette restauration préserve donc bien un `requested_state.preset` utilisateur lorsqu’il est présent.
- Le même fichier appelle `get_my_previous_state()` avant `init_presets()` pendant `async_startup()`. En fin d’initialisation des préréglages, il rappelle `async_set_preset_mode_internal()` avec `current_state.preset`, et non avec `requested_state.preset`.
- [custom_components/versatile_thermostat/vtherm_preset.py](../../custom_components/versatile_thermostat/vtherm_preset.py) définit `safety` et `power` comme `HIDDEN_PRESETS`.
- [custom_components/versatile_thermostat/base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) accepte explicitement les `HIDDEN_PRESETS` dans `async_set_preset_mode_internal()`, qui les écrit dans `requested_state`.
- [custom_components/versatile_thermostat/state_manager.py](../../custom_components/versatile_thermostat/state_manager.py) attribue `SAFETY` au seul état courant si la sécurité est détectée ; sinon il recopie le préréglage demandé dans l’état courant. Le contrat attendu est donc bien que la sécurité n’écrase pas le choix utilisateur demandé.
- [custom_components/versatile_thermostat/feature_safety_manager.py](../../custom_components/versatile_thermostat/feature_safety_manager.py) initialise la sécurité à `unknown`, puis à `off` lorsqu’elle n’est pas à redéclencher. Aucun état actif de sécurité n’est restauré par le gestionnaire.
- [custom_components/versatile_thermostat/base_manager.py](../../custom_components/versatile_thermostat/base_manager.py) fournit une méthode `restore_state()` vide par défaut, dont hérite le gestionnaire de sécurité.
- [custom_components/versatile_thermostat/vtherm_central_api.py](../../custom_components/versatile_thermostat/vtherm_central_api.py) appelle également `init_presets()` lors de la réinitialisation des préréglages utilisant la configuration centrale : l’impact n’est donc pas limité au redémarrage de Home Assistant.
- [tests/test_safety.py](../../tests/test_safety.py) et [tests/test_last_seen.py](../../tests/test_last_seen.py) vérifient le retour de `SAFETY` vers le préréglage demandé durant une même exécution, mais aucun test trouvé ne couvre la persistance puis le redémarrage/rechargement alors que la sécurité est active.
- [tests/test_state_manager.py](../../tests/test_state_manager.py) confirme l’invariant métier de base : `SAFETY` est calculé comme un état courant temporaire lorsque la sécurité est détectée, alors que le préréglage demandé reste utilisateur.

## 3. Analyse de pertinence

### Faits établis

1. Les préréglages `safety` et `power` sont explicitement cachés et représentent des surcharges calculées de l’état courant.
2. `requested_state` représente le choix utilisateur et est la source de repli de `StateManager.calculate_current_preset()` en l’absence de surcharge.
3. Lors de l’initialisation, le code restaure d’abord correctement les deux états, puis remplace potentiellement le choix demandé par le préréglage courant caché.
4. Après le redémarrage, le gestionnaire de sécurité ne considère plus nécessairement la sécurité active ; le calcul normal recopie alors le `requested_state` contaminé vers le `current_state`, ce qui explique l’état durable décrit.
5. Le même appel à `init_presets()` est accessible via le rafraîchissement de la configuration centrale.

### Hypothèse confirmable par test de régression

Le défaut est vraisemblablement déterministe lorsque l’état persistant contient `current_state.preset: safety` et `requested_state.preset` avec un préréglage utilisateur, puis que `init_presets()` est exécuté avant que les recalculs de sécurité ne restaurent l’état courant. Un test d’intégration de restauration doit le confirmer sur l’environnement de test du dépôt.

### Recommandation

**Retenir.** Le défaut contredit la séparation existante entre état demandé et surcharge de sécurité, possède un scénario de reproduction concret, et peut empêcher indéfiniment le retour au réglage planifié. Le correctif paraît local, réversible et testable. L’étiquette P0 est cohérente avec le risque de maintien d’un mode de chauffage non souhaité ; la correction doit néanmoins préserver les comportements `power`, sécurité active et configuration centrale.

## 4. Périmètre proposé

### Inclus

- Préserver le préréglage utilisateur restauré dans `requested_state` lorsque le préréglage courant est un `HIDDEN_PRESET`.
- Modifier la réapplication effectuée par `init_presets()` afin qu’elle applique le préréglage demandé, ou qu’elle ignore explicitement les préréglages cachés ; la conception devra retenir l’option qui conserve le mieux les invariants généraux.
- Couvrir le scénario de redémarrage/restauration avec `current_state.preset: safety`, `requested_state.preset: comfort`, sécurité inactive après reprise, puis retour à `comfort`.
- Couvrir le même invariant lors de `init_vtherm_preset_with_central()` pour un thermostat utilisant les températures centrales.
- Ajouter une régression pour `power` si la correction s’appuie sur la liste générique `HIDDEN_PRESETS`, afin d’éviter de traiter `safety` de manière ad hoc.
- Conserver les tests existants : une sécurité réellement active doit continuer d’afficher `safety` dans l’état courant tout en gardant le dernier choix utilisateur demandé.

### Exclus

- Toute modification de l’algorithme TPI, des seuils ou des délais de sécurité.
- La persistance/restauration de l’état actif de sécurité elle-même.
- Un nouveau paramètre utilisateur, une migration de configuration ou une automatisation de contournement.
- Toute modification du comportement public des commandes de préréglage qui dépasserait la protection nécessaire contre les préréglages cachés.
- Toute modification de code, de configuration, de dépendance ou d’état Home Assistant pendant cette phase de revue.

## 5. Impacts et risques

| Domaine       | Risque                                                                                                                                 | Gravité | Probabilité | Mesure proposée                                                                                          |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------- | ----------- | -------------------------------------------------------------------------------------------------------- |
| Fonctionnel   | Après redémarrage/rechargement, le VTherm conserve `safety` comme choix demandé et ne revient pas au programme utilisateur.            | Élevée  | Élevée      | Test de restauration avec sécurité inactive après démarrage et assertion sur les deux états.             |
| Chauffage     | Le thermostat peut maintenir une consigne ou un cycle associés à `safety` jusqu’à une intervention ou une transition planifiée.        | Élevée  | Moyenne     | Vérifier le retour au préréglage utilisateur et à sa température après la première mise à jour d’état.   |
| Régression    | La correction peut empêcher l’application légitime d’un préréglage utilisateur lors de l’initialisation.                               | Moyenne | Faible      | Couvrir un préréglage visible restauré et le rechargement de configuration centrale.                     |
| Régression    | Un correctif spécifique à `safety` peut laisser le même défaut sur `power`.                                                            | Moyenne | Moyenne     | Utiliser/tester l’invariant générique `HIDDEN_PRESETS`, ou documenter explicitement l’exception retenue. |
| Compatibilité | Interdire globalement les préréglages cachés pourrait rompre des appels internes valides.                                              | Moyenne | Moyenne     | Limiter le changement au chemin de réapplication/restauration, sauf justification validée en conception. |
| Exploitation  | Le déclenchement est lié à un redémarrage ou rechargement, donc difficile à diagnostiquer a posteriori sans les attributs persistants. | Moyenne | Moyenne     | Ajouter des tests d’intégration et conserver les journaux de restauration existants.                     |

**Sécurité et confidentialité :** aucun nouvel accès, secret, appel réseau ou traitement de données personnelles n’est introduit.

## 6. Alternatives examinées

1. **Réappliquer `requested_state.preset` dans `init_presets()` plutôt que `current_state.preset`.**
   - Avantages : aligne l’initialisation sur la source de vérité utilisateur ; corrige les préréglages cachés de manière générique ; couvre aussi le rechargement central.
   - Inconvénients : doit être vérifié pour les cas où l’état demandé serait absent ou invalide après restauration.
   - **Option privilégiée sous réserve de conception.**

2. **Ne pas réappliquer de préréglage lorsque `current_state.preset` appartient à `HIDDEN_PRESETS`.**
   - Avantages : changement minimal et directement ciblé sur la contamination.
   - Inconvénients : ne réapplique pas explicitement le choix utilisateur restauré ; le comportement de tout autre état intermédiaire doit être défini.

3. **Assainir `requested_state` dans `get_my_previous_state()` lorsqu’il contient un préréglage caché.**
   - Avantages : défense en profondeur pour les états déjà contaminés et le chemin de secours basé sur `preset_mode`.
   - Inconvénients : la valeur de remplacement fiable n’est pas toujours disponible si l’historique est déjà contaminé ; seul, ce correctif ne traite pas la cause d’écriture ultérieure.

4. **Refuser les préréglages cachés dans `async_set_preset_mode_internal()`.**
   - Avantages : rend l’invariant de `requested_state` plus strict.
   - Inconvénients : méthode interne utilisée par plusieurs flux ; risque de casser des appels internes légitimes sans séparation préalable des API.
   - **À ne retenir qu’en complément, après audit complet des appelants.**

5. **Ne rien modifier et recommander une automatisation de contournement.**
   - Avantage : aucun risque de régression logicielle immédiat.
   - Inconvénient : laisse un défaut P0 reproductible et impose une configuration utilisateur fragile.
   - **Écartée.**

## 7. Hypothèses, décisions nécessaires et questions ouvertes

### Hypothèses à valider en conception

- `requested_state.preset` est toujours la source de vérité à réappliquer après chargement des préréglages lorsque sa valeur est visible et configurée.
- Les préréglages cachés ne doivent jamais constituer un choix durable dans `requested_state`; ils restent des états courants calculés.
- Le test de restauration peut simuler un état historique complet sans lancer une seconde instance Home Assistant, selon les utilitaires de tests existants.

### Questions ouvertes non bloquantes

- Quel comportement de récupération adopter si les deux états persistés sont déjà `safety` ou `power` et qu’aucun dernier préréglage utilisateur fiable n’est disponible ? La correction doit éviter toute nouvelle contamination ; une restauration parfaite d’un historique déjà corrompu peut nécessiter une politique explicite.
- Le rechargement central peut-il survenir pendant une surcharge `power` ? La couverture doit confirmer que la solution retenue conserve l’invariant pour les deux préréglages cachés.
- Faut-il ajouter un journal avertissant qu’un préréglage caché est ignoré à la restauration ? Cela est utile pour le diagnostic mais n’est pas requis pour le correctif fonctionnel.

## 8. Suite proposée et critères de passage au développement

1. Approbation explicite de ce rapport et du périmètre proposé.
2. Rédaction d’une spécification fonctionnelle définissant les invariants entre préréglage demandé, préréglage courant et surcharges cachées.
3. Conception technique identifiant le point de correction minimal, les chemins de démarrage/rechargement central et la stratégie de récupération des historiques déjà contaminés.
4. Convergence explicite de la spécification et de la conception, puis approbation utilisateur avant tout développement.
5. Développement avec les critères d’acceptation minimaux suivants :
   - avant un redémarrage, une sécurité active affiche `current_state.preset: safety` tout en conservant le préréglage utilisateur dans `requested_state`;
   - après restauration avec sécurité inactive, `requested_state.preset` reste le préréglage utilisateur et `current_state.preset` y revient lors du premier calcul d’état;
   - aucun appel à `init_presets()` ne copie `safety` ou `power` de l’état courant vers l’état demandé;
   - le rechargement des préréglages centraux respecte le même invariant;
   - les transitions existantes entrée/sortie de sécurité conservent leur comportement;
   - les tests concernés passent sans modifier les algorithmes TPI ni la configuration utilisateur.

Aucun code, configuration, dépendance ou état Home Assistant n’a été modifié durant cette revue.