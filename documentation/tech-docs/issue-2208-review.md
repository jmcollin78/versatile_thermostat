# Revue de l'issue #2208 : outils de diagnostic IA

## Synthèse et décision proposée

**Recommandation : retenir la demande.** Le rapport a été approuvé et la spécification et la conception autorisées ; leur validation finale et une autorisation distincte restent nécessaires avant développement. L'issue demande deux outils IA en lecture seule pour un VTherm : consulter ses journaux internes et lister les plugins qui lui sont liés avec leur état interne. Ces informations peuvent améliorer le diagnostic sans changer la régulation.

La priorité `P0` est confirmée par le mainteneur : cette évolution peut réduire fortement les temps de diagnostic et libérer du temps de maintenance. Il s'agit ici d'une priorité forte liée à sa valeur opérationnelle, et non du signalement d'une panne critique ou d'un problème de sécurité, malgré la description habituelle de l'étiquette GitHub.

## Sources et vérifications

- [Issue #2208](https://github.com/jmcollin78/versatile_thermostat/issues/2208), description, métadonnées et chronologie consultées le 8 novembre 2026 : ouverte, étiquettes `enhancement` et `P0`, aucun commentaire, aucun sous-ticket ou blocage déclaré. Une branche de développement apparaît sur la page ; son contenu n'a pas été comparé au dépôt local et aucune PR liée n'est affichée.
- Précision du mainteneur dans la conversation du 8 novembre 2026 : la priorité `P0` reflète le gain attendu sur les temps de diagnostic et la disponibilité du mainteneur.
- Précisions du mainteneur dans la conversation du 8 novembre 2026 : responsabilité des intégrations pour l'attribution des logs, risque de confusion accepté, absence de contrôles d'authentification ou de droits supplémentaires dans l'outil, limitation par nombre de logs et troncature explicite sans pagination ni limite de période.
- Décisions du mainteneur après présentation des documents : quatre familles et sept plugins proposés acceptés ; états partiels acceptés si davantage d'information n'est pas disponible ; plafond proposé de 5 000 logs ; dates normalisées ISO avec fuseau. D'autres plugins pourront apparaître et leur découverte dynamique comme plugins liés n'est pas garantie.
- [PR #2167](https://github.com/jmcollin78/versatile_thermostat/pull/2167), fusionnée : historique et analyse TPI dans les outils LLM/MCP, travail connexe mais pas un doublon de la demande.
- [Issue #2191](https://github.com/jmcollin78/versatile_thermostat/issues/2191), ouverte : perte signalée des enregistrements des factories lors du rechargement du dernier VTherm. Ce ticket connexe n'est pas une dépendance GitHub déclarée ni un correctif inclus ici ; sa reproduction n'a pas été revérifiée.
- [Outils LLM](../../custom_components/versatile_thermostat/llm.py) : liste, état, diagnostic et historique existent déjà ; `async_get_tools` enregistre les outils Assist. Le diagnostic renvoie des attributs et des liens d'aide, pas le contenu du collecteur ni un inventaire de plugins.
- [Collecteur](../../custom_components/vtherm_api/src/vtherm_api/log_collector.py) et [service d'export](../../custom_components/versatile_thermostat/base_thermostat.py) : buffer mémoire borné, filtrage et export manuel existants. `get_entries` inclut les messages sans indication de thermostat même si un nom est demandé.
- [Chargement des gestionnaires externes](../../custom_components/versatile_thermostat/base_thermostat.py), [registres API](../../custom_components/vtherm_api/src/vtherm_api/vtherm_api.py), [interfaces](../../custom_components/vtherm_api/src/vtherm_api/interfaces.py), [factory auto-fan](../../custom_components/vtherm_auto_fan_extended/factory.py) et [factory SmartPI](../../custom_components/vtherm_smartpi/factory.py) : plusieurs modes de liaison existent et les protocoles de factory lus ne définissent pas d'interface universelle d'état de diagnostic.
- [Tests LLM existants](../../tests/test_llm_tpi.py) et [tests du collecteur](../../custom_components/vtherm_api/tests/test_log_collector.py) : points de départ pour les futurs tests, non exécutés pendant cette revue.

**Limites de la revue :** analyse statique des sources locales et des éléments GitHub accessibles ; aucun test, appel à Home Assistant, inspection de logs privés ou comparaison exhaustive des plugins tiers n'a été effectué. La recherche de tickets connexes est ciblée, pas une preuve d'absence de doublon.

## Pertinence et existant

L'API LLM existante est une surface cohérente pour l'assistant et peut être publiée via le serveur MCP officiel de Home Assistant. Les outils existants ne sont proposés que pour des VTherm exposés à l'assistant. Certains, comme `get_history`, ajoutent des contrôles d'authentification et de droit de lecture ; **le mainteneur ne souhaite pas imposer de tels contrôles supplémentaires aux nouveaux outils**. Cela ne modifie pas les mécanismes généraux de Home Assistant et d'Assist.

Le collecteur conserve en mémoire, par défaut, jusqu'à 100 000 entrées et quatre heures, avec purge périodique ; la requête sans fenêtre explicite porte sur la dernière heure. La capacité, l'âge et les redémarrages limitent l'historique disponible. Le filtrage actuel repose sur un indice extrait du texte et sur le nom du thermostat, non sur un identifiant unique : messages sans indice inclus, collisions ou noms modifiés possibles. Il ne garantit donc pas que chaque message retourné concerne uniquement le thermostat demandé.

Le mainteneur considère que ces logs VTherm ne contiennent pas d'informations sensibles et accepte leur éventuel mélange : le risque retenu est une confusion du diagnostic par l'agent, pas un impact de confidentialité dans ce périmètre. L'outil restitue les logs du collecteur par VTherm et par dates, sans traitement spécial pour masquer ou exclure les messages ambigus. Chaque intégration émettrice est responsable d'associer correctement ses logs au bon VTherm ; leur complétude et leur pertinence ne relèvent pas de l'outil de récupération. L'hypothèse d'absence d'informations sensibles est une décision de cadrage du mainteneur, et non le résultat d'un audit exhaustif des logs.

Pour les plugins, le registre des factories est global à l'API : y figurer ne signifie pas être configuré ou actif pour un VTherm donné. Un gestionnaire externe peut être créé selon `supports`, puis configuré séparément ; les algorithmes proportionnels et les liaisons de plugins empruntent aussi d'autres chemins. L'état exact, la couverture et l'identité des plugins détectables doivent être établis par catégorie. **Une liste vide ne doit pas signifier « aucun plugin » si la découverte est partielle ou indisponible.**

## Périmètre proposé

- Deux outils LLM/MCP en lecture seule, ciblant un VTherm chargé et exposé à l'assistant, sans commande de chauffage ni modification des plugins.
- Journaux : récupérer les logs du collecteur pour un VTherm et une période demandée, sans limite imposée sur la durée de cette période. Limiter le nombre de logs retournés, avec un plafond assez élevé pour un diagnostic courant d'environ une heure ; signaler explicitement tout dépassement et toute troncature. Pas de pagination. La rétention effective du collecteur continue de limiter les données disponibles.
- Plugins : identifier ceux dont le lien à ce VTherm est vérifiable, distinguer configuration, chargement, activité et état disponible lorsque ces notions sont démontrables ; signaler explicitement les types ou états non couverts. Ne pas exporter arbitrairement les attributs privés ou la configuration brute.
- Inclure les tests de non-régression, la documentation des outils et des limites, et les vérifications de compatibilité des dépendances.

**Exclusions proposées :** modification de la régulation, commandes de plugins, changement de rétention ou persistance des logs, correction généralisée des logs des intégrations émettrices, correction de #2191, analyse automatique exhaustive par IA, inventaire garanti de tous les plugins tiers sans contrat commun. Les intégrations restent responsables des corrections de leurs propres logs ; ce ticket ne prévoit pas leur correction exhaustive. Une extension de `vtherm_api` ou de plugins reste une option à évaluer, pas une décision acquise.

## Impacts et risques

Les niveaux ci-dessous sont des estimations qualitatives, non des mesures.

| Risque ou impact                                                                             | Gravité                                                                                           | Probabilité                                               | Mesure proposée                                                                                                                                          |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Présence possible de messages d'autres thermostats dans les résultats                        | Non impactant pour la confidentialité selon le mainteneur ; confusion possible pour le diagnostic | Possible, le collecteur incluant les messages sans indice | Risque accepté, sans mesure spéciale dans l'outil ; chaque intégration est responsable de la bonne attribution de ses logs.                              |
| Interprétation d'un texte de journal ou d'un état plugin comme instruction par le modèle     | Élevée                                                                                            | Moyenne                                                   | Responsabilité de l'agent qui interprète les données, hors responsabilité du Tool de récupération.                                                       |
| Liste de plugins incomplète ou état erroné, notamment après rechargement ou démarrage tardif | Moyenne à élevée                                                                                  | Moyenne                                                   | Distinguer configuré, chargé, actif et inconnu ; signaler les limites et tester notamment le cas #2191 sans prétendre le résoudre.                       |
| Logs perdus après redémarrage, collision de noms ou absence de données                       | Moyenne                                                                                           | Moyenne                                                   | Documenter les limites du collecteur ; la complétude et la pertinence des logs relèvent des émetteurs et du collecteur, pas du Tool.                     |
| Réponse volumineuse ou traitement coûteux sur la boucle HA et dans le contexte du modèle     | Moyenne                                                                                           | Moyenne                                                   | Limiter le nombre de logs retournés, signaler explicitement dépassement et troncature ; pas de limite de période ni de pagination.                       |
| Compatibilité HA, API et plugins tiers                                                       | Moyenne                                                                                           | Inconnue                                                  | Respecter les interfaces et versions déclarées ; détecter les capacités et tester l'absence ou l'incompatibilité sans bloquer la régulation.             |
| Effet de bord sur le contrôle ou fuite par introspection de l'état privé                     | Élevée                                                                                            | Faible si lecture strictement isolée                      | N'utiliser que des instantanés/contrats de diagnostic explicites, sans appels de services ni création ou activation de plugin ; tests de non-régression. |

Exploitation et migration : un buffer vide n'est pas une preuve d'absence d'événements. Aucune migration de configuration ou de données n'est présumée nécessaire ; cela dépendra d'une éventuelle évolution des contrats API. Documenter l'exposition Assist/MCP, la troncature, les limites du collecteur et la disponibilité des plugins, dans les langues entretenues par le projet.

## Alternatives

1. **Conserver l'export manuel et l'analyseur existants.** Aucun nouveau canal de données ; mais l'assistant ne consulte pas directement les journaux et l'inventaire des plugins reste manuel.
2. **Réutiliser le filtrage actuel du collecteur.** Continuité avec l'export et simplicité ; il peut inclure des messages non attribués ou des collisions. Le mainteneur accepte ce risque de confusion et demande aux intégrations émettrices de corriger l'attribution de leurs logs.
3. **Retourner uniquement les attributs HA déjà exposés.** Surface initiale limitée ; mais ne garantit ni découverte exhaustive ni accès à l'état interne demandé.
4. **Définir un contrat de diagnostic volontaire pour les plugins, éventuellement complété par des adaptateurs ciblés.** Meilleure maîtrise des données et de leur provenance ; nécessite coordination, compatibilité de versions et une couverture initiale à expliciter.

## Hypothèses et décisions nécessaires

**Décisions du mainteneur :** pas de contrôle d'authentification ou de droits de lecture supplémentaire dans les nouveaux outils ; récupération des logs par VTherm et dates ; limitation du nombre de logs, troncature explicite, sans limite de période ni pagination. Le risque de confusion dû aux logs mal attribués est accepté et leur attribution relève des intégrations émettrices. L'interprétation de contenus comme instructions relève de l'agent, pas du Tool.

**Décisions après convergence initiale :** les quatre familles proposées et leurs sept exemples sont acceptés : SmartPI, Hysteresis, Pellet Regulation, Auto-fan, Heating Failure Detection, Climate Replication et Inhibition. Les états partiels ou inconnus sont acceptables lorsque les informations ne sont pas disponibles. Le mainteneur propose 5 000 logs au lieu de 10 000 et souhaite des dates ISO avec fuseau explicite. La découverte automatique des futurs plugins liés au VTherm n'est pas présumée possible ; signaler les limites de couverture. La conservation des dernières entrées reste la proposition présentée avec le plafond, à confirmer lors de la validation des résultats.

**Hypothèses proposées, non validées :** les outils sont accessibles via l'API Assist existante et les réponses sont en lecture seule. La compatibilité avec les contextes MCP sans utilisateur reste à vérifier sans imposer de nouveau contrôle d'authentification.

**Points à vérifier et à présenter pour validation finale :** la faisabilité de la découverte et des états pour les catégories acceptées, la règle de sélection lors de la troncature et la capacité effective de 5 000 entrées à couvrir un diagnostic courant d'une heure. Le débit réel et la taille des réponses ne sont pas mesurés. Conserver les limites du collecteur, sans ajouter de limite de période ni de pagination.

**Question non bloquante pour la conception :** confirmer les langues de documentation à livrer.

## Suite et critères de passage

1. Rapport approuvé et phase de spécification et conception autorisée par le mainteneur.
2. Mettre à jour les deux documents avec les décisions ci-dessus et vérifier leur convergence sur le périmètre, la faisabilité et les critères d'acceptation. Tout désaccord persistant sera soumis à l'utilisateur.
3. Validation explicite des résultats avant tout développement. Les critères devront couvrir au minimum : récupération par VTherm et dates selon le collecteur, messages non attribués conformément au comportement retenu, plafond de nombre, dépassement et troncature explicites, absence de limite de période et de pagination, erreurs et absence de collecteur, distinction configuré/chargé/actif/inconnu, au moins un exemple par catégorie de plugin retenue, absence de plugin, démarrage/rechargement, compatibilité des contextes et absence d'effets de bord.
4. Après développement, restitution des changements et tests puis nouvelle autorisation avant revue post-développement.