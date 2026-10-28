# Démarrage rapide

Cette page résume les étapes pour obtenir un _VTherm_ fonctionnel, quel que soit l'équipement piloté. Chaque étape renvoie vers la page qui la détaille. Pour un tutoriel par type de chauffage (fil pilote, vanne thermostatique, pompe à chaleur, poêle à granulés), voir les [guides de démarrage du site](https://www.versatile-thermostat.org/fr/quick-start/). Pour les réglages propres à un matériel, voir sa fiche dans le [catalogue des matériels](https://www.versatile-thermostat.org/fr/devices/).

- [Démarrage rapide](#démarrage-rapide)
  - [Avant de commencer](#avant-de-commencer)
  - [Créer le VTherm](#créer-le-vtherm)
  - [Régler et vérifier](#régler-et-vérifier)
  - [Étape suivante](#étape-suivante)

## Avant de commencer

- Versatile Thermostat est installé (voir [Installation](installation.md)).
- L'équipement à piloter est visible dans Home Assistant, ainsi qu'un capteur de température de la pièce et un capteur de température extérieure.
- Vous savez quelle entité l'équipement expose (`switch`, `select`, `climate` ou `number`) : c'est elle qui détermine le type de _VTherm_ (voir [Le bon choix](creation.md#le-bon-choix)).

## Créer le VTherm

1. **Ajoutez l'intégration** Versatile Thermostat depuis la page des intégrations et choisissez le type de _VTherm_ adapté à l'équipement (voir [Choix du VTherm](creation.md)). La configuration centrale est facultative : sans elle, laissez décochées les cases « Utiliser la configuration centrale ».
2. **Principaux attributs** : donnez un nom au _VTherm_ et choisissez le capteur de température de la pièce, puis le capteur de température extérieure. Gardez la durée de cycle par défaut (voir [Choix des attributs de base](base-attributes.md)).
3. **Fonctions** : n'en activez aucune pour l'instant. Vous les ajouterez une fois le _VTherm_ fonctionnel.
4. **Sous-jacents** : sélectionnez l'entité de l'équipement. Les réglages dépendent du type :
   - [`over_switch`](over-switch.md) : un `switch` suffit. Pour un module fil pilote (`select`) ou une entité `climate`, renseignez les [commandes personnalisées](over-switch.md#la-personnalisation-des-commandes).
   - [`over_climate`](over-climate.md) : si l'ouverture de la vanne d'un TRV est pilotable, choisissez le [contrôle direct de la vanne](self-regulation.md#auto-régulation-par-contrôle-direct-de-la-vanne). Sinon, laissez l'auto-régulation désactivée pour commencer.
   - [`over_valve`](over-valve.md) : sélectionnez l'entité `number` de la vanne.

   Les réglages propres à un matériel (entités à utiliser, commandes, pièges connus) sont dans sa fiche du [catalogue des matériels](https://www.versatile-thermostat.org/fr/devices/).
5. **Paramètres TPI**, si ce menu est proposé : gardez les valeurs par défaut (voir [les coefficients du TPI](algorithms.md#configurez-les-coefficients-de-lalgorithme-tpi)).
6. **Pre-réglages** : validez le menu (voir [Les presets](feature-presets.md)).
7. **Paramètres avancés** : gardez les valeurs par défaut du mode sécurité (voir [Paramètres de sécurité](feature-advanced.md#paramètres-de-sécurité)).
8. **Finaliser la création** : le _VTherm_ est créé.

## Régler et vérifier

1. Réglez la température de chaque preset avec les entités du _VTherm_ (voir [Les presets](feature-presets.md)).
2. Mettez le _VTherm_ en mode Chauffage et choisissez le preset Confort, avec une consigne supérieure à la température de la pièce.
3. Vérifiez que l'équipement réagit : le radiateur s'allume, la vanne s'ouvre ou l'équipement reçoit la consigne.

Si rien ne se passe, consultez les [dépannages](troubleshooting.md), puis [téléchargez les logs](feature-logs-collector.md) et ouvrez-les dans l'[analyseur de logs](https://www.versatile-thermostat.org/fr/debugger/) du site.

## Étape suivante

Une fois ce _VTherm_ de base fonctionnel :

- installez la carte UI et un planificateur, présentés dans les [compléments indispensables](additions.md),
- activez les [fonctions](base-attributes.md#choix-des-fonctions-utilisées) utiles une par une, en vérifiant à chaque fois que le _VTherm_ réagit correctement : [détection d'ouverture](feature-window.md), [gestion de la présence](feature-presence.md), [gestion de la puissance](feature-power.md)...
- ensuite, si besoin : [configuration centrale](creation.md#configuration-centralisée), [contrôle centralisé](feature-central-mode.md), [chaudière centrale](feature-central-boiler.md), [réglage de l'auto-régulation](self-regulation.md) et [exemples de réglage](tuning-examples.md).
