# Documentation de Versatile Thermostat

Versatile Thermostat (_VTherm_) est une intégration Home Assistant qui transforme vos radiateurs électriques, pilotés par un simple interrupteur ou un module fil pilote, en thermostats intelligents : presets, détection d'ouverture, présence, délestage et régulation précise avec l'algorithme SmartPI ou TPI.

_VTherm_ pilote aussi les pompes à chaleur, les climatisations et les vannes thermostatiques. Toutes les fonctions se configurent depuis l'interface de Home Assistant, sans script ni automatisation compliquée : la pièce est vide, une fenêtre est ouverte, la puissance disponible est dépassée ? Le thermostat le gère nativement.

- [Documentation de Versatile Thermostat](#documentation-de-versatile-thermostat)
  - [Exemple d'installation](#exemple-dinstallation)
  - [Équipements pris en charge](#équipements-pris-en-charge)
  - [Prérequis](#prérequis)
  - [Matériels](#matériels)
  - [Sommaire de la documentation](#sommaire-de-la-documentation)
    - [Démarrer](#démarrer)
    - [Types de VTherm](#types-de-vtherm)
    - [Fonctions](#fonctions)
    - [Régulation](#régulation)
    - [Aide et référence](#aide-et-référence)
    - [Aller plus loin](#aller-plus-loin)
  - [Étape suivante](#étape-suivante)

## Exemple d'installation

Pour des radiateurs électriques :

1. Créez un _VTherm_ de type [`over_switch`](over-switch.md) pour chaque radiateur, ou pour chaque groupe de radiateurs d'une même pièce.
2. Pilotez le radiateur avec un interrupteur, ou avec un module fil pilote et la [personnalisation des commandes](over-switch.md#la-personnalisation-des-commandes). Le [démarrage rapide fil pilote](https://www.versatile-thermostat.org/fr/quick-start/pilot-wire/) du site détaille la configuration pas à pas.
3. Choisissez l'algorithme de régulation : [SmartPI](algorithms.md#smartpi-recommandé) (recommandé), qui apprend le comportement thermique de la pièce, ou le [TPI](algorithms.md#lalgorithme-tpi) intégré.
4. Ajoutez les fonctions utiles : [délestage](feature-power.md), [gestion de la présence](feature-presence.md), [détection d'ouverture](feature-window.md) et [presets](feature-presets.md) pilotés par un [planificateur](additions.md#un-planificateur-graphique-recommandé).

## Équipements pris en charge

_VTherm_ pilote les équipements de chauffage et de climatisation visibles dans Home Assistant :

- **Radiateurs électriques**, commandés par un interrupteur ou par un module fil pilote : [guide fil pilote](https://www.versatile-thermostat.org/fr/quick-start/pilot-wire/),
- **Pompes à chaleur, climatisations et systèmes HVAC** exposés par une entité `climate` : [guide pompe à chaleur](https://www.versatile-thermostat.org/fr/quick-start/heat-pump/),
- **Radiateurs à eau** équipés de vannes thermostatiques (TRV), avec ou sans pilotage direct de la vanne : [guide TRV](https://www.versatile-thermostat.org/fr/quick-start/trv/),
- **Vannes** pilotables par une entité `number`, sans thermostat associé,
- **Poêles à granulés**, avec le plugin [VTherm Pellet stove](https://www.versatile-thermostat.org/fr/plugins/#jmcollin78/vtherm_pellet_stove) : [guide poêle à granulés](https://www.versatile-thermostat.org/fr/quick-start/pellet-stove/),
- **Chaudière centrale** : _VTherm_ l'allume dès qu'une pièce demande de la chaleur (voir [Chaudière centrale](feature-central-boiler.md)).

Le type de _VTherm_ à créer pour chaque équipement est expliqué dans [Choix du VTherm](creation.md#le-bon-choix).

## Prérequis

- Home Assistant et l'intégration Versatile Thermostat installée depuis HACS (voir [Installation](installation.md)),
- l'équipement à piloter, visible dans Home Assistant,
- un capteur de température de la pièce : n'importe quel capteur disponible dans Home Assistant convient, ou un `input_number`,
- un capteur de température extérieure : l'intégration météo de Home Assistant suffit, et le plugin [Météo-France Observation](https://www.versatile-thermostat.org/fr/plugins/#bontiv/ha-meteofrance-observation) fournit une mesure précise issue des stations Météo-France.

## Matériels

Les équipements de chauffage électrique testés avec _VTherm_ (interrupteurs, modules fil pilote) sont listés dans le [catalogue des matériels](https://www.versatile-thermostat.org/fr/devices/?type=electric) du site, avec leur niveau de support et des conseils de configuration. Le catalogue recense aussi les [thermomètres](https://www.versatile-thermostat.org/fr/devices/?type=sensor), les [vannes thermostatiques](https://www.versatile-thermostat.org/fr/devices/?type=trv) et les [équipements `climate`](https://www.versatile-thermostat.org/fr/devices/?type=climate).

Ce catalogue n'est pas exhaustif : un matériel qui n'y figure pas n'est pas forcément incompatible. Les [matériels incompatibles](https://www.versatile-thermostat.org/fr/devices/?state=unsupported) et les [matériels partiellement supportés](https://www.versatile-thermostat.org/fr/devices/?state=partially) y sont décrits avec leurs limitations connues.

## Sommaire de la documentation

### Démarrer

- [Installation](installation.md) : installer l'intégration avec HACS.
- [Démarrage rapide](quick-start.md) : un _VTherm_ opérationnel en quelques étapes, selon l'équipement.
- [Choix du VTherm](creation.md) : configuration centralisée ou non, choix du type de _VTherm_.
- [Choix des attributs de base](base-attributes.md) : nom, capteurs de température et fonctions à activer.

### Types de VTherm

- [Thermostat de type `over_switch`](over-switch.md) : radiateurs électriques commandés par un interrupteur ou un fil pilote.
- [Thermostat de type `over_climate`](over-climate.md) : pompes à chaleur, climatisations et vannes thermostatiques exposées par une entité `climate`.
- [Thermostat de type `over_valve`](over-valve.md) : vannes pilotables par une entité `number`.

### Fonctions

- **Confort et économies**
  - [Les presets](feature-presets.md) : températures pré-réglées (Confort, Eco, Hors-gel...).
  - [Preset temporisé](feature-timed-preset.md) : appliquer un preset pendant une durée donnée.
  - [Gestion de la présence](feature-presence.md) : baisser la consigne quand personne n'est là.
  - [Détection de mouvement](feature-motion.md) : changer de preset selon l'activité dans la pièce.
  - [Détection d'ouverture](feature-window.md) : réagir à l'ouverture d'une porte ou d'une fenêtre.
  - [Capteur d'humidité](feature-humidity.md) : afficher l'humidité mesurée par un capteur externe.
- **Pilotage de l'installation**
  - [Gestion de la puissance (délestage)](feature-power.md) : ne pas dépasser la puissance disponible.
  - [Démarrage / arrêt automatique](feature-auto-start-stop.md) : arrêter un `over_climate` quand il n'est pas utile.
  - [Contrôle centralisé](feature-central-mode.md) : piloter tous les _VTherm_ en une seule fois.
  - [Chaudière centrale](feature-central-boiler.md) : allumer la chaudière quand un _VTherm_ a besoin de chauffer.
  - [Verrouillage](feature-lock.md) : empêcher les modifications depuis l'interface ou les automatisations.
- **Sécurité**
  - [Configuration avancée et mode sécurité](feature-advanced.md) : capteur qui ne répond plus, état incohérent des équipements.
  - [Détection d'anomalie de chauffe](feature-heating-failure-detection.md) : la température ne suit pas la commande.

### Régulation

- [Les algorithmes](algorithms.md) : TPI, SmartPI et autres algorithmes disponibles en plugin.
- [Auto TPI](feature-autotpi.md) : apprentissage automatique des coefficients du TPI.
  - [Auto TPI : guide technique](feature-autotpi-technical.md)
- [L'auto-régulation](self-regulation.md) : corriger la consigne envoyée à un `over_climate`, ou piloter directement la vanne.
- [Synchronisation de la température interne](feature-sync_device_temp.md) : recaler le thermomètre interne de l'équipement.
- [Recalibrage des vannes](feature-recalibrate-valves.md) : le service `recalibrate_valves`.
- [Exemples de réglage](tuning-examples.md) : des réglages commentés selon le type d'installation.

### Aide et référence

- [Dépannages](troubleshooting.md) : les problèmes fréquents et leurs solutions.
- [Télécharger les logs](feature-logs-collector.md) : collecter des logs ciblés, puis les ouvrir dans l'[analyseur de logs](https://www.versatile-thermostat.org/fr/debugger/) du site.
- [Documentation de référence](reference.md) : paramètres, capteurs, actions, événements et attributs.
- [Notes de versions](releases.md)

### Aller plus loin

- [Quelques compléments indispensables](additions.md) : carte UI, planificateur, courbes, notifications.
- [Catalogue des plugins](https://www.versatile-thermostat.org/fr/plugins/) : algorithmes, cartes et aides pour les équipements.
- [Catalogue des matériels](https://www.versatile-thermostat.org/fr/devices/) : les matériels testés et leur niveau de support.

## Étape suivante

[Installation](installation.md) : installer Versatile Thermostat dans Home Assistant.

Pour un équipement courant, le [démarrage rapide](quick-start.md) résume toute la configuration sur une seule page.
