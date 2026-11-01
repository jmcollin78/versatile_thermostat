# Revue de l’issue #2116 — Renommage des entités Home Assistant

| Élément          | Constat au 1er novembre 2026                                                                                                                             |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Issue            | [#2116 — Handle entity_id changes in place](https://github.com/jmcollin78/versatile_thermostat/issues/2116), ouverte le 13 octobre 2026 par @emontnemery |
| Statut           | Ouverte ; étiquettes `enhancement` et `P1` ; aucun responsable, jalon ou PR associé affiché                                                              |
| Recommandation   | **Retenir**, traiter en priorité le cœur VTherm et les défauts connexes déjà présents, et organiser séparément l’audit des plugins                       |
| État de la revue | Analyse statique ; rapport soumis à validation ; aucune spécification, conception détaillée ou implémentation autorisée à ce stade                       |

## 1. Résumé et pertinence

Home Assistant prévoit, à partir de Core 2026.11, de modifier l’`entity_id` d’une entité **en place** au lieu de la retirer et de la réajouter. Le callback synchrone `async_entity_id_changed(old_entity_id)` permet de réadapter les éléments indexés par le propre identifiant de l’entité. L’ancien état est retiré ; `self.entity_id` contient le nouvel identifiant quand le callback est appelé ; le nouvel état peut ne pas encore être écrit à ce moment.

Une transition protège certaines intégrations personnalisées : si une classe propre à l’intégration implémente un hook d’ajout ou de retrait, il faut que cette classe ou une sous-classe définisse aussi le nouveau callback pour permettre le changement en place. Un callback uniquement dans une classe parente ne couvre pas forcément une sous-classe qui définit elle-même ces hooks. Cette compatibilité est annoncée jusqu’à Core 2027.11 ; ensuite toutes les entités seraient renommées en place. Les classes de base fournies par Core ne comptent pas dans ce contrôle. Source : [annonce officielle Home Assistant](https://contributors.home-assistant.io/blog/2026/10/12/new-entity-lifecycle-hooks/#changing-the-entity-id-in-place).

L’issue identifie la chaudière centrale, Auto TPI et deux suivis du thermostat par d’autres entités. Elle signale également des problèmes déjà possibles lors du cycle historique retrait/réajout. Le mainteneur demande de considérer aussi les plugins ; @KipK indique devoir terminer des travaux SmartPI avant examen.

**Pertinence : élevée.** Le code local conserve effectivement des identifiants et des abonnements dépendants de ceux-ci. Les impacts sont conditionnés au renommage et aux fonctionnalités utilisées : il ne s’agit pas d’une panne générale à chaque mise à jour de Home Assistant. La lecture statique établit les mécanismes et les risques, mais pas leur fréquence ni une défaillance observée sur une installation.

## 2. Sources et limites

### Sources externes

- [Issue, description et commentaires](https://github.com/jmcollin78/versatile_thermostat/issues/2116), [métadonnées](https://api.github.com/repos/jmcollin78/versatile_thermostat/issues/2116) et [chronologie](https://api.github.com/repos/jmcollin78/versatile_thermostat/issues/2116/timeline).
- [Annonce officielle des hooks de cycle de vie](https://contributors.home-assistant.io/blog/2026/10/12/new-entity-lifecycle-hooks/#changing-the-entity-id-in-place). Elle précise notamment l’appel à `super()`, l’ordre d’écriture de l’état, le nettoyage et les tâches asynchrones.
- Recherche GitHub ciblée sur `async_entity_id_changed` et sur le renommage : aucun doublon évident ou PR directement liée identifié parmi les résultats examinés. Une recherche par mots clés ne garantit pas l’exhaustivité.

### Sources locales et méthode

- Cœur : [entités associées](../../custom_components/versatile_thermostat/base_entity.py#L46-L106), [cycle du thermostat](../../custom_components/versatile_thermostat/base_thermostat.py#L474-L537), [gestionnaire de chaudière](../../custom_components/versatile_thermostat/feature_central_boiler_manager.py#L73-L112), [enregistrements](../../custom_components/versatile_thermostat/feature_central_boiler_manager.py#L335-L359), [identifiants suivis](../../custom_components/versatile_thermostat/feature_central_boiler_manager.py#L430-L455), [capteurs de chaudière](../../custom_components/versatile_thermostat/sensor.py#L835-L1125), [Auto TPI](../../custom_components/versatile_thermostat/prop_handler_tpi.py#L182-L188) et [calibration](../../custom_components/versatile_thermostat/auto_tpi_manager.py#L2503-L2536).
- Compatibilité : [version minimale HACS](../../hacs.json), [dépendances de développement](../../requirements_dev.txt), [dépendances de test](../../requirements_test.txt) et [manifeste](../../custom_components/versatile_thermostat/manifest.json).
- Plugins : [capteur SmartPI](../../custom_components/vtherm_smartpi/sensor.py#L32-L52), [abonnement SmartPI](../../custom_components/vtherm_smartpi/sensor.py#L170-L239) et [suivi du registre dans inhibition](../../custom_components/vtherm_inhibition/link.py#L285-L358).
- Tests fonctionnels existants : [chaudière centrale](../../tests/test_central_boiler.py), [Auto TPI](../../tests/test_auto_tpi.py). Recherche ciblée : aucun test dédié au nouveau callback ou au renommage d’entité identifié dans les fichiers de test examinés.

Analyse sur le code local, dont le manifeste indique `10.6.3` ; le commit exact et les éventuelles modifications locales n’ont pas été déterminés. Aucun test, aucune reproduction Home Assistant, aucune commande sur une installation ni inspection de matériel n’ont été exécutés. La compatibilité avec les versions futures ne peut pas être déclarée validée.

## 3. Constats techniques

### 3.1 Chaudière centrale : changement du propre identifiant

Les deux seuils `number`, le capteur du nombre d’appareils actifs et celui de puissance totale s’enregistrent à l’ajout. Chaque enregistrement planifie `start_listening(force=True)` ; le gestionnaire reconstruit alors la liste des quatre identifiants et s’abonne aux changements d’état correspondants. Voir [seuils](../../custom_components/versatile_thermostat/number.py#L207-L214), [second seuil](../../custom_components/versatile_thermostat/number.py#L274-L281), [capteurs](../../custom_components/versatile_thermostat/sensor.py#L835-L840), [capteur de puissance](../../custom_components/versatile_thermostat/sensor.py#L996-L1000) et [gestionnaire](../../custom_components/versatile_thermostat/feature_central_boiler_manager.py#L335-L359).

**Inférence fondée sur le code :** si l’une de ces quatre entités est renommée en place sans réinscription, le gestionnaire peut continuer à écouter son ancien identifiant. Sa modification ultérieure ne déclenchera alors pas le recalcul par cet abonnement, même si d’autres événements peuvent toujours le déclencher. Les conséquences possibles sont une activation ou une désactivation tardive de la chaudière.

### 3.2 Renommage du thermostat : consommateurs distincts

Les entités dérivées de `VersatileThermostatBaseEntity` s’abonnent à l’identifiant du thermostat trouvé lors de leur ajout. Le thermostat peut être renommé sans que ces entités soient elles-mêmes réajoutées : leur abonnement peut rester associé à l’ancien identifiant **même avec l’ancien cycle de vie**. Les mises à jour de certaines entités associées risquent alors de ne plus suivre le thermostat. Source : [abonnement](../../custom_components/versatile_thermostat/base_entity.py#L82-L106).

Le capteur `TotalPowerActiveDeviceForBoilerSensor` construit de même un abonnement sur les identifiants des thermostats participant à la chaudière ; son calcul de puissance risque de rester obsolète après leur renommage. Source : [suivi des thermostats](../../custom_components/versatile_thermostat/sensor.py#L1002-L1034).

**Précision :** dans le code courant, `NbActiveDeviceForBoilerSensor.listen_vtherms_entities()` collecte des objets thermostat ; son ancien abonnement aux sous-jacents est commenté. Il ne faut pas lui attribuer le même abonnement actif que celui du capteur de puissance. Sa propre entité reste cependant l’une des quatre suivies par le gestionnaire de chaudière. Source : [collecte du nombre d’appareils](../../custom_components/versatile_thermostat/sensor.py#L842-L882).

### 3.3 Auto TPI

À l’ajout, `TPIHandler` copie l’`entity_id` du thermostat dans le gestionnaire Auto TPI. La calibration pré-bootstrap le réutilise pour lire l’état et appeler le service de calibration. Après un renommage en place sans synchronisation, cet identifiant peut être périmé ; la recherche d’état et la calibration concernées risquent d’échouer ou de manquer de données. Le repli construit avec `unique_id` n’est pas une garantie qu’il corresponde à l’identifiant courant. Sources : [copie](../../custom_components/versatile_thermostat/prop_handler_tpi.py#L182-L188), [utilisation](../../custom_components/versatile_thermostat/auto_tpi_manager.py#L2503-L2536).

### 3.4 Retrait et réajout historiques

Le thermostat enregistre `remove_thermostat()` pour le retrait, marque `_is_removed` et arrête notamment les gestionnaires, les sous-jacents et le scheduler ; le chemin d’ajout consulté ne montre pas de remise en route symétrique complète. Le capteur de puissance annule son abonnement au retrait et son ajout ne relance pas directement `listen_vtherms_entities()`. Un renommage utilisant encore retrait/réajout peut donc affecter le fonctionnement, sous réserve de l’ordre exact et des autres appels à la remise en écoute. Sources : [cycle du thermostat](../../custom_components/versatile_thermostat/base_thermostat.py#L474-L537), [capteur de puissance](../../custom_components/versatile_thermostat/sensor.py#L996-L1002) et [nettoyage](../../custom_components/versatile_thermostat/sensor.py#L1117-L1125). Ce diagnostic demande une reproduction avant de conclure à une panne systématique.

### 3.5 Plugins et dépendances externes

Le capteur diagnostique SmartPI résout le thermostat au démarrage puis stocke son identifiant, l’écoute et le relit : un renommage du thermostat **pourrait** laisser ce capteur sur l’ancien identifiant. La casse effective et sa couverture par les autres mécanismes n’ont pas été reproduites. À l’inverse, le plugin inhibition comporte déjà une résolution et un suivi explicites des changements du registre ; c’est un exemple utile, pas une preuve de compatibilité complète pour tous ses cas.

Le propriétaire de l’issue évoque tous les plugins ; leur inventaire exhaustif, leurs dépôts de référence, leurs versions publiées et les contrats de `vtherm_api` n’ont pas été audités. Il serait imprudent de promettre leur correction complète dans le même lot sans décision de périmètre et sans revue complémentaire.

## 4. Compatibilité, exploitation et migration

- [HACS](../../hacs.json) annonce **2026.3.1** comme minimum, tandis que [les dépendances de développement](../../requirements_dev.txt) épinglent Core **2026.8.2** ; le comportement de renommage en place est annoncé pour **2026.11**. Le minimum réellement engagé contractuellement et la matrice CI effective restent à confirmer. Un appel inconditionnel à une méthode `super()` introduite plus tard doit être vérifié sur les anciennes versions ; ne pas supposer que l’exemple de l’issue est directement compatible avec 2026.3.1.
- Il faudra tester aussi bien l’ancien cycle que le nouveau, sans déclarer la version future 2027.11 testée tant qu’elle n’est pas disponible. L’activation anticipée du nouveau comportement ne doit intervenir qu’après vérification de chaque hiérarchie et de ses dépendances.
- L’issue ne demande pas de migration de données, de changement d’`unique_id` ni d’interface utilisateur. Les références en configuration, tableaux de bord ou automatisations externes ne sont pas automatiquement garanties par ce correctif ; leur traitement est hors périmètre proposé.
- L’ordre des événements est important : au moment du callback, le nouvel état peut ne pas encore exister. Une tâche doit gérer un second renommage ou un retrait pendant un `await`, sans conserver un abonnement périmé ou dupliquer les calculs. Le nettoyage doit viser **l’abonnement courant**, pas uniquement le premier.
- Contournement temporaire possible : éviter les renommages des entités concernées ; si un renommage est indispensable, vérifier les états et redémarrer ou recharger l’intégration selon les procédures usuelles. Ce n’est **pas une correction garantie** ; aucun de ces gestes n’a été testé ici et il peut interrompre momentanément la régulation.

## 5. Impacts et risques

Gravité et probabilité sont des estimations qualitatives conditionnées à l’usage, sans données de fréquence. « Probabilité » ci-dessous signifie probabilité d’exposition, non probabilité mesurée de panne.

| Risque                                                                          | Gravité                                                              | Exposition estimée                                                           | État de preuve et mitigation envisagée                                                         |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Chaudière non réévaluée après renommage d’un seuil/capteur                      | Élevée : chauffage insuffisant ou chaudière maintenue plus longtemps | Faible à moyenne : chaudière configurée et entité renommée                   | Dépendance et écoute vérifiées statiquement ; réabonnement et tests fonctionnels nécessaires   |
| Puissance centrale ou entités associées obsolètes après renommage du thermostat | Élevée pour la commande chaudière, moyenne pour l’affichage          | Faible à moyenne : thermostat renommé avec fonctions concernées              | Abonnements vérifiés ; défaut connexe potentiellement présent avant 2026.11                    |
| Retrait/réajout interrompt des ressources du thermostat                         | Élevée                                                               | Faible à moyenne : renommage pendant la transition ou sur version antérieure | Nettoyage vérifié, effets exacts non reproduits ; tester cycle et continuité                   |
| Calibration Auto TPI utilisant un identifiant périmé                            | Moyenne                                                              | Faible : Auto TPI et calibration pré-bootstrap concernés                     | Stockage et lecture vérifiés ; tester état et résultat de calibration                          |
| Fuite, abonnement doublé ou résultat périmé après renommages rapides/retrait    | Moyenne à élevée selon commande                                      | Inconnue                                                                     | Risque de conception asynchrone, non démontré en exécution ; tests d’interleaving et nettoyage |
| Régression sur Home Assistant antérieur à 2026.11                               | Élevée : erreur potentielle au renommage                             | Inconnue : installations sur versions antérieures                            | Minimum annoncé 2026.3.1 ; vérifier la disponibilité des API et tester la matrice              |
| Plugin conservant l’ancien identifiant                                          | Variable, potentiellement élevée selon plugin                        | Inconnue                                                                     | Cas SmartPI identifié statiquement, audit non exhaustif ; suivi distinct à décider             |

**Sécurité et confidentialité :** aucun nouveau flux réseau, collecte de données ou changement de droits n’est requis par l’objectif. Le principal enjeu est la sûreté d’exploitation du chauffage ; ne pas déduire une protection matérielle ni une surchauffe effective de la seule lecture du code. Les journaux éventuels doivent rester limités aux identifiants nécessaires et ne pas ajouter de données personnelles inutiles.

## 6. Périmètre recommandé et alternatives

### Périmètre proposé pour le cœur

1. Préserver la continuité d’un thermostat et de ses entités associées après renommage, y compris les abonnements des autres entités du cœur à ce thermostat.
2. Réadapter le suivi des quatre entités d’entrée de la chaudière et la liste des thermostats suivis pour la puissance ; recalculer au bon moment, sans multiplier les abonnements ou les commandes.
3. Garantir qu’Auto TPI utilise l’identifiant courant lors de sa calibration.
4. Examiner toutes les hiérarchies du cœur avec hooks d’ajout/retrait et n’activer le renommage en place que si toutes leurs dépendances sont couvertes.
5. Ajouter des tests de cycle de vie et de compatibilité ainsi qu’une documentation de limites et de dépannage si nécessaire.

**Exclusions proposées :** renommage général d’entités externes configurées comme capteurs ou sous-jacents, migration de tableaux de bord/automatisations, modification de l’algorithme de chauffage, changements matériels, et correction de tous les plugins dans ce même lot. L’audit des plugins et le suivi de leurs corrections sont recommandés, mais leur inclusion dans l’implémentation est une décision ouverte.

### Alternatives

| Option                                                                       | Avantages                                                                                    | Inconvénients                                                                                                    |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Callbacks HA avec réabonnements et notification des consommateurs            | Suit l’API cible ; peut éviter le retrait/réajout ; traite les propres identifiants          | Hiérarchies multiples, ordre des événements, compatibilité antérieure et nettoyage à concevoir soigneusement     |
| Suivi des événements du registre et résolution par identifiant stable        | Peut traiter aussi les consommateurs d’une autre entité ; motif déjà présent dans inhibition | Complexité des abonnements et de l’ordre état/registre ; ne dispense pas de vérifier le cycle propre des entités |
| Différer jusqu’à 2027.11 ou limiter l’action aux quatre entités de chaudière | Travail immédiat réduit                                                                      | Défauts actuels des consommateurs et du retrait/réajout non traités ; risque accru lors de l’échéance            |

L’issue suggère de réutiliser les méthodes `register_*`, un signal fondé sur l’identifiant stable et `reload_central_boiler_binary_listener()`. Cette piste est plausible, **non validée comme conception définitive** : vérifier les effets d’un réenregistrement, la hiérarchie de `TotalPowerActiveDeviceForBoilerSensor`, le moment d’écriture de l’état, les désabonnements et les courses. Une recherche dynamique de l’identifiant Auto TPI dans le registre est une autre possibilité ; ses compromis de disponibilité et de cycle de vie sont à évaluer.

## 7. Critères proposés pour une future validation

- Renommer par le registre chaque thermostat concerné et chacun des quatre seuils/capteurs chaudière ; vérifier la continuité des valeurs et les décisions d’activation/désactivation sur le **nouvel** identifiant.
- Vérifier les entités associées au thermostat, la puissance totale et la calibration Auto TPI après renommage, y compris lorsque le nouvel état n’est pas encore écrit.
- Couvrir les types `over_switch`, `over_valve`, `over_climate` et `over_climate_valve`, les fonctions optionnelles désactivées et une chaudière absente ou non prête.
- Exercer renommages rapides successifs, ancien identifiant réutilisé, désactivation/retrait/rechargement pendant une tâche, aucune fuite ni abonnement doublé, et absence de commande chaudière intempestive.
- Vérifier le cycle historique et le comportement en place sur une matrice de versions HA convenue, dont le minimum supporté et une version disposant du nouveau hook ; ne pas simuler un résultat comme s’il provenait d’une version future non disponible.
- Exécuter les tests ciblés et les suites de non-régression pertinentes ; documenter les limites et résultats réels, y compris les plugins exclus.

## 8. Hypothèses, décisions et suite

**Hypothèses de travail :** préserver le minimum annoncé de 2026.3.1, traiter les défauts connexes du cœur dans le même lot et traiter les plugins séparément après audit. Aucune n’est une décision déjà approuvée.

**Décisions ouvertes à lever avant développement :**

1. Confirmer le minimum HA réellement supporté et les versions de test disponibles ; un relèvement du minimum ne doit pas être implicite.
2. Confirmer si les plugins, en particulier SmartPI, sont inclus dans le développement de #2116 ou suivis dans des travaux distincts ; identifier leurs propriétaires et dépôts de référence.
3. Confirmer l’inclusion des défauts de suivi déjà présents avant 2026.11 et de l’activation anticipée du comportement en place, proposée après couverture complète des hiérarchies.

**Suite proposée :** après approbation explicite du présent rapport, rédiger les spécifications puis la conception, les faire converger sur le périmètre et les critères de test, et soumettre les résultats à une nouvelle validation humaine. Aucun développement ne doit commencer si les décisions bloquantes, la compatibilité ou la couverture demeurent indéterminées. Après implémentation autorisée, présenter les résultats et demander une nouvelle validation avant la revue post-développement.