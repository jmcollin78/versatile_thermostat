# Revue de l’issue #2135 — désynchronisation en arrêt automatique

**Date :** 2026-10-31  
**Statut :** essai local fourni par l’utilisateur : activation puis arrêt rapides observés ; désynchronisation durable et cause racine de l’incident non confirmées ; accord requis avant spécification et conception.  
**Référence :** [issue #2135](https://github.com/jmcollin78/versatile_thermostat/issues/2135), ouverte, sans étiquette ni PR associée dans les métadonnées consultées.

## Résumé fidèle

L’auteur utilise VTherm 10.6.1 avec Home Assistant 2026.10.2, un `over_climate` Airzone Cloud pilotant un split Daikin, et l’auto-start/stop en niveau `slow`. Il indique qu’à 17 h 30 un programmateur a appelé `climate.set_temperature` avec `hvac_mode: heat` et une consigne de 20 °C alors que VTherm et le sous-jacent étaient arrêtés par auto-stop. Selon son historique, VTherm a envoyé `climate.set_hvac_mode: heat` au sous-jacent ; VTherm est resté `off` avec une demande `heat`, tandis que le sous-jacent serait resté en `heat` plus de deux heures sans ordre `off` correctif.

La désactivation puis la réactivation de l’auto-start/stop auraient resynchronisé les états. L’auteur utilise aussi une automatisation qui éteint le sous-jacent après une minute de désaccord. L’attribut de réparation d’état était désactivé. Les attributs fournis ont été capturés plus tard, après resynchronisation : ils ne constituent pas une capture de l’état désynchronisé. Aucun journal détaillé de l’incident n’est joint ; le mainteneur demande l’utilisation du collecteur de logs. La présence du problème dans une version antérieure est inconnue.

## Sources et faits vérifiés

- [Description et commentaire de l’issue](https://github.com/jmcollin78/versatile_thermostat/issues/2135) ; les observations de terrain ci-dessus sont rapportées, non reproduites ici.
- Dépôt local : branche annoncée `main`, manifeste déclarant la version 10.6.3 dans [manifest.json](../../custom_components/versatile_thermostat/manifest.json). Il ne s’agit pas de la version 10.6.1 du signalement ; l’identité exacte du commit local et la présence de modifications préexistantes n’ont pas été établies par commande Git.
- [Calcul du mode effectif](../../custom_components/versatile_thermostat/state_manager.py#L151-L159) : lorsque l’arrêt automatique est détecté, le mode de demande reste distinct du mode effectif. Selon la configuration et les modes disponibles, le mode effectif peut être un mode d’arrêt autre que `off` ; le cas signalé utilise `off`.
- [Application des états](../../custom_components/versatile_thermostat/base_thermostat.py#L1751-L1837) : l’envoi normal du mode aux sous-jacents dépend du marqueur de changement de mode effectif. Une situation `off` vers `off` ne déclenche pas à elle seule une réémission du mode.
- [Gestionnaire auto-start/stop](../../custom_components/versatile_thermostat/feature_auto_start_stop_manager.py#L99-L175) : il recalcule la détection et demande une mise à jour des états lorsque cette détection change. L’absence de transition n’est pas une preuve que le sous-jacent a reçu ou appliqué `off`.
- [Commande du sous-jacent](../../custom_components/versatile_thermostat/underlyings.py#L644-L704) : un mode n’est pas envoyé si l’état HA et le mode mémorisé correspondent déjà tous deux à la demande ; un renvoi de température différé peut être planifié après `heat` ou `cool` et est annulé lors d’une nouvelle commande de mode. Un appel de service n’est pas un acquittement physique.
- [Entrées de commande](../../custom_components/versatile_thermostat/base_thermostat.py#L1619-L1631) et [température](../../custom_components/versatile_thermostat/base_thermostat.py#L1707-L1728) : les méthodes locales traitent respectivement la demande de mode et la consigne. `async_set_temperature()` ne lit pas elle-même `hvac_mode` ; la décomposition exacte par le service Home Assistant doit être vérifiée par un test de service, pas supposée à partir d’un appel direct de cette méthode.
- [Réparation optionnelle](../../custom_components/versatile_thermostat/feature_repair_incorrect_state_manager.py#L77-L143) et [comparaison du mode climate](../../custom_components/versatile_thermostat/underlyings.py#L1219-L1245) : lorsqu’elle est activée, elle compare le mode attendu au mode rapporté et peut renvoyer le mode pendant un cycle de contrôle. Elle est [désactivée par défaut](../../custom_components/versatile_thermostat/const.py#L532-L535), attend au moins 30 secondes après préparation et limite les tentatives. Son efficacité dans le scénario précis n’a pas été testée ici.
- [Réinitialisation de l’algorithme](../../custom_components/versatile_thermostat/auto_start_stop_algorithm.py#L291-L307) : `reset_switch_delay()` efface notamment la dernière décision d’arrêt, ainsi que les dates de dernier calcul et de dernière commutation. [L’application d’une consigne ou d’un preset marqué comme changé](../../custom_components/versatile_thermostat/base_thermostat.py#L1800-L1818) appelle cette méthode ; les logs de l’essai montrent plusieurs applications et réinitialisations à 19 °C, sans démontrer à elles seules plusieurs changements numériques distincts de consigne. Après remise à zéro, le [calcul d’accumulation et de seuil](../../custom_components/versatile_thermostat/auto_start_stop_algorithm.py#L115-L190) peut réévaluer immédiatement la décision. Les valeurs d’erreur avant l’extrait ne sont pas connues.
- En [version 10.6.1](https://github.com/jmcollin78/versatile_thermostat/blob/10.6.1/custom_components/versatile_thermostat/auto_start_stop_algorithm.py), la même réinitialisation existe et les seuils sont également de `2` pour `fast` et `10` pour `slow` ; [l’application des états](https://github.com/jmcollin78/versatile_thermostat/blob/10.6.1/custom_components/versatile_thermostat/base_thermostat.py) appelle aussi ce reset pour un preset ou une température marqués comme changés. Cette vérification statique ne démontre pas la même séquence lors de l’incident.
- [Contrôle over_climate](../../custom_components/versatile_thermostat/thermostat_climate.py#L1161-L1191) : une modification de la détection déclenche un recalcul des états, susceptible de rappeler le contrôle ; le chemin est compatible avec les transitions observées sans établir à lui seul tous les entrelacements de l’essai.
- [Issue #1654](https://github.com/jmcollin78/versatile_thermostat/issues/1654) : symptôme comparable au démarrage, fermée par [#1719](https://github.com/jmcollin78/versatile_thermostat/pull/1719), sans preuve d’une cause commune. [Issue #2020](https://github.com/jmcollin78/versatile_thermostat/issues/2020) : dérive de mode dans l’autre sens ; discussion de la réparation optionnelle. [PR #2012](https://github.com/jmcollin78/versatile_thermostat/pull/2012) : proposition plus large de modification de la représentation auto-stop, fermée sans fusion. Aucun de ces éléments ne prouve que #2135 est déjà corrigée ou constitue un doublon exact.

## Tentative de reproduction et limites

**Aucun test n’a été exécuté par l’assistant** : aucun outil permettant de lancer une commande ou des tests n’était disponible dans cette session. Aucun test ni code n’a été ajouté au dépôt pendant cette analyse. L’utilisateur a ensuite réalisé un essai local et fourni les traces ci-dessous.

### Essai local fourni le 31 octobre 2026

L’essai **ne reproduit pas la désynchronisation durable**. Les heures ci-dessous sont celles du préfixe des logs ; les horodatages d’état affichent le fuseau local avec une heure de plus.

| Heure | Observation dans l’extrait |
| --- | --- |
| 16:17:24.262–.273 | Demande de mode `heat`, application d’une consigne de 19 °C et réinitialisation de l’algorithme ; avec une pièce à 21 °C, la décision `should_be_off` devient `False` et un événement `start` est émis. |
| 16:17:24.278–.287 | La détection passe de `True` à `False`, VTherm applique `heat` et HA rapporte le sous-jacent `heat`. |
| 16:17:24.294–.295 | Après de nouvelles applications de consigne et réinitialisations, l’erreur accumulée atteint `-2` pour un seuil de `2` : la détection repasse à `True`, VTherm applique `off`. Les applications de `heat` puis `off` sont séparées d’environ 15 ms. |
| 16:17:24.305 | La réparation activée dans cet essai compare `off` attendu à `heat` rapporté et diffère la réparation car une commande est récente. La valeur `FeatureRepairIncorrectStateManager: False` en fin de cycle ne signifie pas que l’option est désactivée : ce gestionnaire était bien appelé, mais ne signalait pas de réparation détectée à cet instant. |
| 16:17:24.340–.406 | HA rapporte le sous-jacent `off`, avec un horodatage d’état à `17:17:24.302655+01:00` ; la comparaison suivante voit `off`/`off`. L’attribut `hvac_action` reste toutefois rapporté `cooling` dans cet extrait : l’état physique et la cohérence de cette action ne sont pas établis. |

Les logs montrent une **tentative d’application** de `heat` puis de `off` et des états HA successifs correspondants ; ils ne contiennent pas le détail indépendant des deux appels de service ni un acquittement physique. Le seuil `2` correspond à `fast` dans le code examiné, alors que le signalement utilise `slow` ; la configuration exacte et la version de l’essai restent à confirmer. Les traces montrent directement une transition `start` puis `stop`, pas une décision constante « rester arrêté ».

La durée très courte entre les applications rend crédible l’hypothèse d’une commande `off` perdue, rejetée, différée ou dépassée par un traitement asynchrone sur un équipement cloud ; **aucune de ces causes n’est prouvée pour l’incident de l’auteur**. Un autre scénario reste possible : absence ou non-envoi de l’ordre `off`. Le signalement indique justement ne pas avoir vu d’ordre `off` dans son historique ; il faut donc obtenir les traces de cet incident avant d’arbitrer.

Le [wrapper des services](../../custom_components/versatile_thermostat/underlyings.py#L226-L247) utilise `blocking=False` par défaut : il ne garantit pas la fin de l’action matérielle avant le retour de l’appel. La [réparation climate](../../custom_components/versatile_thermostat/underlyings.py#L1219-L1245) attend le délai suivant la dernière commande, [fixé à deux secondes](../../custom_components/versatile_thermostat/underlyings.py#L49), avant de réessayer ; dans l’essai, elle a différé puis observé un état HA `off`. Dans l’installation de l’issue, elle était désactivée. Ni cet essai ni ces mécanismes ne prouvent qu’un ordre `off` a échoué chez l’auteur.

Une tentative externe préexistante a néanmoins été inspectée : [trois scénarios de test](https://github.com/giogandola98/versatile_thermostat/blob/3aa14f8924851071f11169c739d701c643684e54/tests/test_auto_start_stop_issue_2135.py) créent un `over_climate` simulé, l’amènent en auto-stop et utilisent les services HA pour tester notamment `set_temperature` avec `heat` et 20 °C, un changement depuis `cool` et `set_hvac_mode` seul. Le [workflow correspondant](https://github.com/giogandola98/versatile_thermostat/blob/3aa14f8924851071f11169c739d701c643684e54/.github/workflows/testus.yaml) cible ce fichier ; l’[étape CI « Run Tests »](https://github.com/giogandola98/versatile_thermostat/actions/runs/39496640347/job/118883287004) est indiquée réussie le 20 octobre 2026. Les journaux détaillés étant soumis à connexion, le nombre exact de tests passés ou ignorés n’a pas été vérifié.

Cette exécution distante est une **tentative tierce**, pas un test réalisé localement. Un succès du job n’est pas une confirmation du défaut. La reproduction utilise le niveau `fast`, un climat simulé à réponse simple et une révision basée sur `bbd0daa`, descendante de 10.6.1 avec sept commits supplémentaires ; elle ne reproduit ni nécessairement les temporisations Airzone Cloud, ni toute la configuration `slow`, ni les conditions de l’incident. Elle n’établit pas non plus le comportement de la version locale 10.6.3. Les assertions portent principalement sur l’état final et ne démontrent pas à elles seules la chronologie complète des commandes.

### Protocole proposé pour un test discriminant

À réaliser dans un environnement de test isolé, sans piloter le matériel réel :

1. Utiliser le service HA `climate.set_temperature` complet, `heat` et 20 °C, avec `over_climate`, `ac_mode`, `slow`, cycle de cinq minutes, réparation désactivée et une température initiale supérieure à la consigne. Établir effectivement l’auto-stop, `requested_state=heat`, VTherm `off` et sous-jacent rapporté `off`.
2. Espionner les appels aux services du sous-jacent avec horodatage et collecter les changements de `requested_state`, `current_state`, détection auto-stop et état HA du sous-jacent. Distinguer commande envoyée, état rapporté et état physique.
3. Vérifier la séquence réelle après la commande, puis après les tâches différées et au moins un cycle ; tester explicitement l’éventuel entrelacement entre rafraîchissement auto-stop, service et retour sous-jacent, sans présupposer l’ordre.
4. Ajouter des variantes de réponse retardée, retour de mode tardif, `off` rejeté ou perdu, services traités dans un ordre différent et état HA optimiste ; puis comparer `fast`/`slow`, réparation activée/désactivée, demande identique/modifiée, `heat`/`cool`, et modes d’arrêt alternatifs pris en charge. Vérifier séparément les appels `heat`/`off`, l’état HA et l’état simulé de l’appareil, y compris au-delà des deux secondes et d’un cycle. Ces variantes sont des hypothèses de reproduction, pas des faits observés.
5. Si un test reproduit bien l’incident, conserver un test de non-régression qui échoue avant correction et réussit après, avec contrôle du flux de services, de l’état effectif, de la demande conservée, du redémarrage légitime et de l’absence de boucles de commandes.

## Pertinence et recommandation

**Retenir l’analyse, demander des précisions et différer le choix du correctif.** L’essai local confirme qu’une demande de mode peut entraîner une application `heat` puis `off` en quelques millisecondes après réinitialisations et recalculs d’auto-stop. Il ne reproduit pas la désynchronisation durable et ne prouve pas l’échec du `off` chez l’auteur. La lecture statique révèle aussi une dépendance aux transitions et donc une possibilité de non-réconciliation d’un écart déjà présent. La cause exacte de l’incident reste ouverte. Le problème rapporté touche à la confiance dans le thermostat, à la consommation et potentiellement au confort ou à la sécurité thermique.

### Périmètre proposé

- Étudier la cohérence entre demande, état effectif auto-stop et mode d’un `over_climate` à la réception d’un ordre et lors des retours asynchrones du sous-jacent.
- Préserver les priorités existantes : inhibition, sécurité, fenêtre et mode central ; considérer les modes d’arrêt autres que `off` et les matériels indisponibles.
- Couvrir les commandes de température et de mode via les services HA, ainsi que l’interaction avec la réparation optionnelle et les éventuels sous-jacents multiples.
- Hors périmètre à ce stade : refonte générale de l’affichage `hvac_mode`/`hvac_action`, changement de l’algorithme de régulation, modification générale par défaut de la réparation, dépendance ou migration. Un élargissement exige une décision distincte.

## Impacts et risques

| Risque ou impact | Gravité potentielle | Probabilité / éléments | Mesure proposée |
| --- | --- | --- | --- |
| Chauffage ou ventilation non souhaités et affichage trompeur | Élevée selon installation | Occurrence rapportée ; fréquence inconnue | Collecter les traces, surveiller les deux états et tester la séquence réelle. |
| Coupure d’un redémarrage légitime ou d’un mode d’arrêt configuré | Élevée | Risque de correction, non observé | Comparer au mode effectif et aux protections ; tester la reprise et les modes alternatifs. |
| Boucles ou répétitions de commandes, retours cloud tardifs | Moyenne à élevée | Plausible ; non quantifiée | Simuler latence, acquittement tardif et commandes perdues ; limiter les tentatives si nécessaire. |
| Régression d’autres thermostats, suivi du sous-jacent ou multi-entités | Moyenne à élevée | Code partagé et interactions existantes | Tests ciblés et régression ; préserver les choix de suivi et les priorités. |
| Réparation ou automatisation de contournement qui agit sur un appareil partagé | Moyenne à élevée | Dépend de l’installation ; non établi ici | Vérifier les usages du sous-jacent et superviser avant toute activation. |

**Confidentialité et exploitation :** les journaux peuvent contenir identifiants d’entités, horaires et informations d’habitation ; demander une anonymisation adaptée. Aucun changement de permission, dépendance, stockage ou migration n’est justifié à ce stade. Une documentation utilisateur et une validation matérielle restent à prévoir si un changement est retenu.

## Alternatives et contournements

1. **Empêcher l’envoi d’une activation incompatible avec l’état effectif** : cible la prévention, mais il faut d’abord identifier la voie qui l’émet et ne pas empêcher une reprise autorisée.
2. **Réconcilier un sous-jacent en désaccord avec le mode effectif** : peut traiter une dérive après coup, mais doit tenir compte des latences, modes d’arrêt, reprises, appareils indisponibles et risques de boucle. Une réémission systématique de `off` n’est pas une solution validée.
3. **Essayer la réparation optionnelle existante**, après vérification de la configuration et sous supervision : évite un changement de code et peut corriger une divergence rapportée ; elle agit au contrôle, pas nécessairement immédiatement, avec temporisations et plafond de tentatives. Son efficacité pour cet incident reste à mesurer.
4. **Automatisation externe signalée par l’auteur** : déjà utilisée sur son installation ; simple, mais commande directement le sous-jacent et risque d’interférer avec une reprise légitime ou un équipement partagé.

## Questions ouvertes et décisions nécessaires

- Obtenir les logs du collecteur et l’historique complet de l’incident, avec heures, versions et configuration exactes ; distinguer un `off` non émis, rejeté, perdu ou exécuté hors ordre, et confirmer l’origine des commandes. Vérifier également la configuration et la version de l’essai local fourni.
- Vérifier le déroulement du service HA pour `hvac_mode`, la valeur de l’accumulation et de la pente, les tâches différées, la latence Airzone et l’éventuelle concurrence avec d’autres automatisations. La cause exacte et la reproductibilité restent **bloquantes pour sélectionner un correctif**.
- Déterminer si la réparation optionnelle et une version récente reproduisent ou corrigent le cas ; vérifier les éventuelles différences de version avant d’en tirer une conclusion.
- Décider, à partir de la reproduction et du périmètre validé, si la solution doit prévenir la commande, réconcilier après dérive, ou combiner ces approches ; définir le délai admissible et les règles pour les autres modes d’arrêt.

## Suite et critères de passage

1. Demander l’accord explicite sur ce rapport et l’autorisation d’élaborer spécification et conception. Cet accord ne vaut pas autorisation de développer.
2. Rechercher une reproduction et les éléments manquants sans modifier l’environnement réel ; si l’exécution locale reste indisponible, obtenir un outil de test ou des résultats vérifiables de l’utilisateur.
3. Faire converger les documents spécialisés sur un périmètre et des critères testables ; documenter les désaccords.
4. Avant tout développement : disposer d’une cause et d’un scénario suffisamment établis, lever les questions bloquantes, valider la convergence et obtenir une nouvelle autorisation explicite. Avant livraison : test de régression démontrant le défaut puis la correction, tests de reprise et protections, et validation d’intégration adaptée au matériel.