[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Versatile Thermostat

Ce fichier README est disponible en
[Anglais](README.md) | [Français](README-fr.md) | [Allemand](README-de.md) | [Czech](README-cs.md) | [Polski](README-pl.md)

<p align="center">
<img src="https://github.com/jmcollin78/versatile_thermostat/blob/main/images/icon.png" />
</p>

> ![Tip](images/tips.png) Cette intégration de thermostat vise à simplifier considérablement vos automatisations autour de la gestion du chauffage. Parce que tous les événements autour du chauffage classiques sont gérés nativement par le thermostat (personne à la maison ?, activité détectée dans une pièce ?, fenêtre ouverte ?, délestage de puissance ?), vous n'avez pas à vous encombrer de scripts et d'automatismes compliqués pour gérer vos thermostats. ;-).

Ce composant personnalisé pour Home Assistant est une mise à niveau et une réécriture complète du composant "Awesome thermostat" (voir [Github](https://github.com/dadge/awesome_thermostat)) avec l'ajout de fonctionnalités.

# Captures d'écran

Le composant Versatile Thermostat UI Card (Disponible sur [Github](https://github.com/jmcollin78/versatile-thermostat-ui-card)) :

![Card1](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/1.png) ![Card2](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/7.png)

# Quoi de neuf ?
![Nouveau](images/new-icon.png)

## Release 9.1
> 1. Nouveau logo . Inspiré par les travaux de @Krzysztonek (voir [ici](https://github.com/jmcollin78/versatile_thermostat/pull/1598)), VTherm profite d'une nouvelle fonction de [HA 206.03](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api/) pour changer de logo. Toute l'équipe espère qu'il vous plaira. Enjoy !
> 2. Un site web réalisé par @bontiv va résoudre une des difficulté majeure de VTherm : la documentation. Ce site permet en plus d'analyser vos logs ! Donnez lui vos logs (en mode debug) et vous pourrez les analyser, zoomer sur un thermostat, sur une période, filter ce qui vous intéresse, ... Je vous laisse découvrir ce site en 1ère version : [Versatile Thermostat Web site](https://www.versatile-thermostat.org/). Un énorme merci à @bontiv pour cette belle réalisation.
> 3. La publication en version officielle de l'auto-TPI. Cette fonction permet de déterminer par le calcul les meilleurs valeurs des coefficients du [TPI](documentation/fr/algorithms.md#lalgorithme-tpi). On peut saluer le travail incroyable de @KipK et de @gael1980 sur ce sujet. Ne faites pas l'économie de lire la documentation si vous souhaitez l'utiliser.
> 4. VTherm se repose maintenant sur l'état remonté par équipements sous-jacents dans HA. Tant que tous les sous-jacents n'ont pas d'état connu dans HA, alors le VTherm est désactivé.

## Release 8.6
> 1. ajout du paramètre `max_opening_degrees` pour les VTherms de type `over_climate_valve` permettant de limiter le pourcentage d'ouverture maximal de chaque vanne afin de contrôler le débit d'eau chaude et optimiser la consommation d'énergie (ou autre cas d'usage).
> 2. ajout de la fonction de recalibrage des vannes d'un _VTherm_ `over_climate_valve` permettant de forcer une ouverture maximale puis une fermeture maximale pour tenter de recalibrer un _TRV_. Plus d'informations [ici](documentation/fr/feature-recalibrate-valves.md).

## Release 8.5
> 1. ajout de la détection d'anomalie de chauffe pour les VTherms utilisant l'algorithme TPI. Cette fonction détecte deux types d'anomalies :
>    - **anomalie de chauffage** : le radiateur chauffe fortement (on_percent élevé) mais la température n'augmente pas,
>    - **anomalie de refroidissement** : le radiateur ne chauffe pas (on_percent à 0) mais la température continue d'augmenter.
>
> Ces anomalies peuvent indiquer une fenêtre ouverte, un radiateur défaillant ou une source de chaleur externe. La fonctionnalité envoie des événements qui peuvent être utilisés pour déclencher des automatisations (notifications, alertes, etc.). Plus d'informations [ici](documentation/fr/feature-heating-failure-detection.md).

L'historique des releases est accessible [ici](documentation/fr/releases.md)

# 🍻 Merci pour les bières 🍻
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jmcollin78)

Un grand merci à tous mes fournisseurs de bières pour leurs dons et leurs encouragments. Ca me fait très plaisir et ça m'encourage à continuer ! Si cette intégration vous a fait économiser, payez moi une p'tite bière en retour, j'en vous en serais très reconnaissant !

# Glossaire

  `VTherm` : Versatile Thermostat dans la suite de ce document

  `TRV` : tête thermostatique équipée d'une vanne. La vanne s'ouvre ou se ferme permettant le passage de l'eau chaude

  `AC` : Air conditionné. Un équipement est AC si il fait du froid. Les températures sont alors inversées : Eco est plus chaud que Confort qui est plus chaud que Boost. Les algorithmes tiennent compte de cette information.

  `EMA` : Exponential Moving Average. Utilisé pour lisser les mesures de températures de capteur. Elle correspond à une moyenne glissante de la température de la pièce. Elle est utilisée pour calculer la pente de la courbe de température (slope) qui serait trop instable sur la courbe brute.

  `slope` : la pente de la courbe de température. Elle est mesurée en °(C ou K)/h. Elle est positive si la température augmente et négative si elle diminue. Cette pente est calculée sur l'`EMA`

  `PAC` : Pompe à chaleur

  `HA` : Home Assistant

  `sous-jacent` : l'équipement controlé par `VTherm`


# Documentation

La documentation est maintenant découpée en plusieurs pages pour faciliter la lecture et la recherche d'informations :
1. [Présentation](documentation/fr/presentation.md)
2. [Installation](documentation/fr/installation.md)
3. [Démarrage rapide](documentation/fr/quick-start.md)
4. [Choisir un type de VTherm](documentation/fr/creation.md)
5. [Les attributs de base](documentation/fr/base-attributes.md)
6. [Configurer un VTherm sur un `switch`](documentation/fr/over-switch.md)
7. [Configurer un VTherm sur un `climate`](documentation/fr/over-climate.md)
8. [Configurer un VTherm sur une vanne](documentation/fr/over-valve.md)
9. [Les pré-régages (preset)](documentation/fr/feature-presets.md)
10. [La gestion des ouvertures](documentation/fr/feature-window.md)
11. [La gestion de la présence](documentation/fr/feature-presence.md)
12. [La gestion de mouvement](documentation/fr/feature-motion.md)
13. [La gestion de la puissance](documentation/fr/feature-power.md)
14. [L'auto start and stop](documentation/fr/feature-auto-start-stop.md)
15. [La contrôle centralisé de tous vos VTherms](documentation/fr/feature-central-mode.md)
16. [La commande du chauffage central](documentation/fr/feature-central-boiler.md)
17. [Aspects avancés, mode sécurité](documentation/fr/feature-advanced.md)
18. [Détection d'anomalie de chauffe](documentation/fr/feature-heating-failure-detection.md)
19. [L'auto-régulation](documentation/fr/self-regulation.md)
20. [L'apprentissage Auto TPI](documentation/fr/feature-autotpi.md)
21. [Verrouillage / Déverrouillage](documentation/fr/feature-lock.md)
22. [Synchronisation des température](documentation/fr/feature-sync_device_temp.md)
23. [Preset temporisé](documentation/fr/feature-timed-preset.md)
24. [Exemple de réglages](documentation/fr/tuning-examples.md)
25. [Les algorithmes](documentation/fr/algorithms.md)
26. [Documentation de référence](documentation/fr/reference.md)
27. [Dépannage](documentation/fr/troubleshooting.md)
28. [Notes de version](documentation/fr/releases.md)

# Quelques résultats

**Stabilité de la température autour de la cible configurée par preset:** :

![image](documentation/fr/images/results-1.png)

**Cycle de marche/arrêt calculé par l'intégration `over_climate`** :

![image](documentation/fr/images/results-2.png)

**Régulation avec un `over_switch`** :

![image](documentation/fr/images/results-4.png)

**Regulation forte en `over_climate`** :

![image](documentation/fr/images/results-over-climate-1.png)

**Regulation avec contrôle direct de la vanne en `over_climate`** :

![image](documentation/fr/images/results-over-climate-2.png)

# Quelques commentaires sur l'intégration
|                                             |                                             |                                             |
| ------------------------------------------- | ------------------------------------------- | ------------------------------------------- |
| ![testimonial 1](images/testimonials-1.png) | ![testimonial 2](images/testimonials-2.png) | ![testimonial 3](images/testimonials-3.png) |
| ![testimonial 4](images/testimonials-4.png) | ![testimonial 5](images/testimonials-5.png) | ![testimonial 6](images/testimonials-6.png) |


Enjoy !

# ⭐ Star history

[![Star History Chart](https://api.star-history.com/svg?repos=jmcollin78/versatile_thermostat&type=Date)](https://star-history.com/#jmcollin78/versatile_thermostat&Date)

# Les contributions sont les bienvenues !

Si vous souhaitez contribuer, veuillez lire les [directives de contribution](CONTRIBUTING.md)

***

[versatile_thermostat]: https://github.com/jmcollin78/versatile_thermostat
[buymecoffee]: https://www.buymeacoffee.com/jmcollin78
[buymecoffeebadge]: https://img.shields.io/badge/Buy%20me%20a%20beer-%245-orange?style=for-the-badge&logo=buy-me-a-beer
[commits-shield]: https://img.shields.io/github/commit-activity/y/jmcollin78/versatile_thermostat.svg?style=for-the-badge
[commits]: https://github.com/jmcollin78/versatile_thermostat/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacs_badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/jmcollin78/versatile_thermostat.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Joakim%20Sørensen%20%40ludeeus-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/jmcollin78/versatile_thermostat.svg?style=for-the-badge
[releases]: https://github.com/jmcollin78/versatile_thermostat/releases
