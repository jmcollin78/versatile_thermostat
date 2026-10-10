# Revue de l’issue #2088 — chaudière centrale inactive

**Statut :** à valider avant spécification et conception
**Issue :** [#2088 — Central Boiler Configuration Not Working](https://github.com/jmcollin78/versatile_thermostat/issues/2088)
**Dépôt examiné :** `jmcollin78/versatile_thermostat`, branche `main`
**Date de revue :** 2026-10-10

## 1. Résumé fidèle de l’issue

Avec VTherm 10.5.0, la chaudière centrale ne s’active plus alors que plusieurs VTherm demandent du chauffage. Le journal contient `Found only 2/4 entities` ; l’entité de chaudière publie `is_central_boiler_configured: true` mais `is_central_boiler_ready: false`. Les services d’activation et de désactivation sont correctement analysés, mais ne sont donc jamais appelés. Un autre utilisateur déclare rencontrer le même symptôme.

## 2. Sources et éléments vérifiés

- Description, commentaires, journal et métadonnées de [#2088](https://github.com/jmcollin78/versatile_thermostat/issues/2088) : issue ouverte, étiquetée `question` et `Not VTherm issue`, sans PR ou branche associée. Le mainteneur prévoit une bêta instrumentée pour identifier les entités manquantes.
- Le gestionnaire exige une entité binaire de chaudière et quatre entités auxiliaires avant de calculer l’état : [custom_components/versatile_thermostat/feature_central_boiler_manager.py](../../custom_components/versatile_thermostat/feature_central_boiler_manager.py#L69-L107) et [custom_components/versatile_thermostat/feature_central_boiler_manager.py](../../custom_components/versatile_thermostat/feature_central_boiler_manager.py#L417-L456).
- S’il n’est pas prêt, le gestionnaire ne calcule pas l’état et n’appelle aucun service : [custom_components/versatile_thermostat/feature_central_boiler_manager.py](../../custom_components/versatile_thermostat/feature_central_boiler_manager.py#L170-L178).
- Les plateformes créent les deux seuils, les deux capteurs et l’entité binaire lorsque la fonction est activée : [custom_components/versatile_thermostat/number.py](../../custom_components/versatile_thermostat/number.py#L123-L127), [custom_components/versatile_thermostat/sensor.py](../../custom_components/versatile_thermostat/sensor.py#L72-L87) et [custom_components/versatile_thermostat/binary_sensor.py](../../custom_components/versatile_thermostat/binary_sensor.py#L421-L435).
- Les scénarios nominaux sont couverts, mais pas le diagnostic de préparation incomplète ni l’ordre d’enregistrement au rechargement : [tests/test_central_boiler.py](../../tests/test_central_boiler.py#L119-L392).

Aucun test n’a été exécuté et aucun état Home Assistant n’a été modifié pendant cette revue.

## 3. Les quatre entités auxiliaires nécessaires

L’entité binaire `binary_sensor.<configuration_centrale>_central_boiler` doit aussi être présente, mais elle **ne fait pas partie du compteur `2/4`**. Ce compteur ne recense que les quatre composants suivants :

| Rôle requis                          | Classe                                  | Identifiant habituel avec une configuration nommée « Central configuration » | Valeur attendue                              |
| ------------------------------------ | --------------------------------------- | ---------------------------------------------------------------------------- | -------------------------------------------- |
| Seuil du nombre d’équipements actifs | `ActivateBoilerThresholdNumber`         | `number.central_configuration_number_activation_threshold`                   | Un nombre entier ; `0` désactive ce critère. |
| Seuil de puissance active            | `ActivateBoilerPowerThresholdNumber`    | `number.central_configuration_power_activation_threshold`                    | Une puissance ; `0` désactive ce critère.    |
| Nombre d’équipements actifs          | `NbActiveDeviceForBoilerSensor`         | `sensor.central_configuration_nb_device_active_for_boiler`                   | Le nombre courant d’équipements actifs.      |
| Puissance totale active              | `TotalPowerActiveDeviceForBoilerSensor` | `sensor.central_configuration_total_power_active_for_boiler`                 | La somme courante des puissances actives.    |

Les identifiants d’entité peuvent différer si Home Assistant a ajouté un suffixe ou si le nom de la configuration centrale est différent ; les classes et les rôles sont invariants. La liste des quatre est construite dans [custom_components/versatile_thermostat/feature_central_boiler_manager.py](../../custom_components/versatile_thermostat/feature_central_boiler_manager.py#L417-L430). La documentation utilisateur les décrit également dans [documentation/fr/feature-central-boiler.md](../fr/feature-central-boiler.md#L19-L30).

Dans le cas de #2088, le journal ne dit pas **quelles** deux entités manquent : c’est l’information à obtenir de la bêta instrumentée ou en vérifiant les entités du dispositif de configuration centrale dans Home Assistant.

### Conditions de création des entités de puissance

Le code ne comporte **aucune condition spécifique à la puissance**. Pour une config entry de type `thermostat_central_config`, l’unique condition est `use_central_boiler_feature: true` :

- la plateforme `number` ajoute systématiquement les deux nombres, y compris le seuil de puissance ;
- la plateforme `sensor` ajoute systématiquement les deux capteurs, y compris la puissance totale.

Ainsi, le fait de ne pas renseigner une puissance sur un VTherm, de désactiver la fonction de gestion de puissance globale, ou de définir le seuil à `0` ne doit pas empêcher la création ou l’enregistrement des deux entités de puissance. Ces réglages peuvent rendre leur valeur nulle ou désactiver un critère, mais pas les faire disparaître.

Si les deux composants de puissance sont réellement absents après la fin du démarrage, les causes plausibles sont donc externes à la logique de sélection :

1. les entités ont été désactivées dans le registre d’entités Home Assistant ;
2. le chargement d’une des plateformes `number` ou `sensor` a échoué ou a été interrompu — les logs de démarrage doivent alors contenir une exception ;
3. le message correspond à un instant transitoire de démarrage avant l’enregistrement de toutes les entités, auquel cas un état durablement `is_central_boiler_ready: false` signalerait un problème de cycle de vie ou de rechargement ;
4. la configuration centrale effectivement chargée ne porte plus `use_central_boiler_feature: true`, ou n’est pas celle inspectée.

La vérification prioritaire est de relever l’état du registre pour les quatre identifiants, puis les traces de chargement des plateformes `number` et `sensor` autour de `async_setup_entry`.

### Impact possible de la migration des unités de puissance

La modification récente des unités est pertinente pour l’investigation, car elle touche précisément les deux composants de puissance :

- `ActivateBoilerPowerThresholdNumber.native_unit_of_measurement` délègue maintenant au gestionnaire de puissance central ;
- `TotalPowerActiveDeviceForBoilerSensor.native_unit_of_measurement` fait la même délégation ;
- la restauration du seuil de puissance convertit désormais l’ancienne valeur et son unité avant de l’exposer.

Toutefois, l’analyse statique ne met pas en évidence un chemin nominal qui supprimerait ces entités : le gestionnaire résout toujours une unité légale et se replie explicitement sur `W` si `power_unit` est `auto`, si les capteurs centraux sont absents ou si leur unité est invalide. La migration attribue en outre `power_unit: auto` aux configurations centrales existantes.

La piste devient crédible seulement si les logs révèlent une exception pendant le chargement ou la restauration de l’une des deux entités de puissance. Les recherches doivent cibler une exception issue de `number.py`, `sensor.py`, `feature_central_power_manager.py`, ou une erreur Home Assistant de validation de `device_class: power` / `native_unit_of_measurement`. Le test de régression à ajouter doit charger une configuration centrale historique migrée, sans gestion de puissance centrale active et avec la chaudière centrale activée, puis vérifier les quatre enregistrements et `is_central_boiler_ready: true`.

## 4. Pertinence et recommandation

### Recommandation : retenir une investigation corrective limitée

Le risque fonctionnel est élevé : une chaudière réellement sollicitée peut rester arrêtée. L’issue est donc pertinente et mérite une investigation reproductible ainsi qu’un diagnostic plus précis.

Aucun correctif de logique d’activation ne doit toutefois être engagé sans identifier les deux entités absentes : les informations accessibles ne permettent pas de déterminer si elles ne sont pas créées, sont désactivées/supprimées dans Home Assistant, ou échouent à se réenregistrer après un rechargement.

La réponse recommandée est :

1. produire la bêta instrumentée annoncée ;
2. journaliser les quatre rôles attendus, leurs identifiants et leur présence au démarrage/rechargement ;
3. reproduire le problème, identifier la plateforme ou le composant absent ;
4. ne corriger le cycle de vie qu’après cette identification.

## 5. Périmètre proposé

### Inclus

- Diagnostic du cycle de vie de la chaudière centrale au démarrage et au rechargement.
- Identification des composants auxiliaires absents parmi les deux nombres et les deux capteurs.
- Test de l’état non prêt et de la transition vers l’état prêt.
- Instrumentation permettant de distinguer une entité non créée, indisponible ou non enregistrée.

### Exclus

- Modification des seuils, des calculs TPI, de la régulation des vannes ou du mode sommeil.
- Diagnostic de l’entité de commande de chaudière elle-même hors intégration VTherm.
- Migration automatique des configurations utilisateur.

## 6. Impacts et risques

| Risque                                                          | Gravité | Probabilité | Mesure proposée                                                                                             |
| --------------------------------------------------------------- | ------- | ----------- | ----------------------------------------------------------------------------------------------------------- |
| Absence de chauffage lorsque le gestionnaire reste non prêt     | Élevée  | Moyenne     | Identifier les entités absentes, reproduire le rechargement et ajouter un test de régression.               |
| Diagnostic insuffisant, donc support utilisateur long et ambigu | Moyenne | Élevée      | Exposer les rôles/identifiants absents dans les logs et attributs de diagnostic.                            |
| Régression lors de l’initialisation asynchrone                  | Moyenne | Moyenne     | Tester différents ordres d’enregistrement et le rechargement de config entry.                               |
| Confidentialité                                                 | Faible  | Faible      | Les logs peuvent contenir des noms d’entités ; ne pas enregistrer d’informations supplémentaires sensibles. |

## 7. Alternatives examinées

| Alternative                                                           | Avantages                                                  | Inconvénients                                                                              | Décision |
| --------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------ | -------- |
| Forcer l’activation avec une configuration incomplète                 | Peut masquer l’incident pour certains utilisateurs         | Risque d’activation avec des seuils/états inconnus ; contourne le garde-fou de préparation | Écartée  |
| Corriger immédiatement la séquence d’enregistrement sans reproduction | Réponse rapide                                             | Cause inconnue, risque de masquer un problème Home Assistant ou de créer une régression    | Différée |
| Ajouter des diagnostics et des tests, puis cibler le correctif        | Décision fondée sur faits, améliore durablement le support | Nécessite une collecte complémentaire                                                      | Retenue  |

## 8. Hypothèses, décisions nécessaires et critères de passage

### Hypothèses à vérifier

- Deux entités auxiliaires ne sont pas enregistrées au moment où le gestionnaire démarre.
- Cette absence peut relever de l’ordre de chargement asynchrone, d’un rechargement de l’intégration, ou de l’état du registre d’entités Home Assistant.

### Inconnues bloquantes

- Les quatre identifiants effectivement trouvés et ceux manquants dans l’installation de l’auteur.
- La version Home Assistant et l’historique exact de mise à jour.
- Une reproduction avec journaux instrumentés.

### Critères de passage à la spécification et conception

- Le présent rapport est approuvé.
- Le périmètre de diagnostic/test est accepté.
- Les inconnues ci-dessus sont acceptées comme objectifs de collecte testables de la conception.

### Critères de passage au développement

- Les exigences et la conception précisent les diagnostics à produire et les scénarios de cycle de vie à couvrir.
- Les nouveaux tests couvrent l’état incomplet, la transition vers l’état prêt et le rechargement concerné.
- La source du cas #2088 est reproduite ou le mécanisme de collecte est défini de façon testable.
- Une autorisation explicite de développement est fournie après validation des spécifications et de la conception.
