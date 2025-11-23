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

## Release 8.1
> - Pour un VTherm de type `over_climate` avec régulation par contrôle direct de la vanne, deux nouveaux paramètres permettant un contrôle beaucoup plus fin du minimum d'ouverture de la vanne ont été ajoutés au paramètre existant `minimum_opening_degrees`. Les paramètres sont maintenant :
>    - `opening_threshold` : l'ouverture minimale de la vanne en dessous de laquelle la vanne doit être considérée comme fermée, et par conséquent, le paramètre 'max_closing_degree' s'applique,
>    - `max_closing_degree` : le pourcentage de fermeture maximum absolu. La vanne ne se fermera jamais plus que ce qui est indiqué dans cette valeur. Si vous voulez autoriser la fermeture complète de la vanne, alors laissez ce paramètre sur 100,
>    - `minimum_opening_degrees` : le pourcentage d'ouverture minimal lorsque le `opening_threshold` est dépassé et que le VTherm doit chauffer. Ce champ est personnalisable par vanne dans le cas d'un VTherm avec plusieurs vannes. Vous spécifiez la liste des ouvertures minimales séparées par des ','. La valeur par défaut est 0. Exemple : '20, 25, 30'. Lorsque la chauffe démarre (ie l'ouverture demandée est supérieure à `opening_threshold`), la vanne s'ouvrira avec une valeur supérieure ou égale à celle-ci et continuera d'augmenter régulièrement si nécessaire.
>
> Si on représente l'ouverture demandée par l'algorithme TPI en abscisse et l'ouverture réellement envoyée sur la vanne en ordonnée, on obtient cette courbe :
> ![alt text](images/opening-degree-graph.png)
>
> Cette évolution a été largement débattue [ici](https://github.com/jmcollin78/versatile_thermostat/issues/1220).

## Release 8.0
> Cette version est une version majeure. Elle réécrit une bonne partie des mécanismes internes du Versatile Thermostat en introduisant plusieurs nouveautés:
>    1. _état souhaité / état courant_ : maintenant VTherm a 2 états. L'état souhaité est l'état demandé par l'utilisateur (ou le Scheduler). L'état courant est l'état couramment appliqué au VTherm. Ce dernier dépend des différentes fonctions de VTherm. Par exemple, l'utilisateur peut demander (état souhaité) d'avoir le chauffage allumé avec le preset Comfort mais comme la fenêtre a été détectée ouverte le VTherm est en fait éteint. Cette double gestion permet de toujours conservé la demande de l'utilisateur et d'appliquer le résultat des différentes fonctions sur cette demande de l'utilisateur pour avoir l'état courant. Cela permet de mieux gérer les cas où plusieurs fonctions veulent agir sur l'état du VTherm (ouverture d'une fenêtre et délestage par exemple). Cela assure aussi un retour à la demande initiale de l'utilisateur lorsque plus aucune détection n'est en cours,
>    2. _filtrage temporel_ : le fonctionnement du filtrage temporel a été revu. Le filtrage temporel permet de ne pas envoyer trop de commandes à un équipement contrôlé pour éviter de consommer trop de batterie (TRV à pile par exemple), de changer trop fréquement de consignes (pompe à chaleur, poele à pellets, chauffage au sol, ...). Le nouveau fonctionnement est maintenant le suivant : les demandes explicites de l'utilisateur (ou Scheduler) sont toujours immédiatement prises en compte. Elles ne sont pas filtrées. Seules les changements liés à des conditions extérieures (températures de la pièce par exemple) sont potentiellement filtrées. Le filtrage consiste à renvoyer la commande souhaitée plus tard et non pas à ignorer la commande comme c'était le cas précédemment. Le paramètre `auto_regulation_dtemp` permet de régler le délai,
>    3. _amelioration du hvac_action_ : le `hvac_action` reflète l'état courant d'activation de l'équipement commandé. Pour un type `over_switch` il reflète l'état d'activation du switch, pour un `over_valve` ou une régulation par vanne, il est actif lorsque l'ouverture de la vanne est supérieur à l'ouverture minimale de la vanne (ou 0 si non configurée), pour un `over_climate` il reflète le `hvac_action`du `climate` sous-jacent si il est disponible ou une simulation sinon.
>    4. _attributs personnalisés_ : l'organisation des attributs personnalisés accessibles dans Outils de développement / Etat, ont été réorganisés en section dépendant du type de VTherm et de chaque fonction activée. Plus d'informations [ici](documentation/fr/reference.md#attributs-personnalisés).
>    5. _délestage_ : l'algorithme de délestage prend maintenant en compte l'arrêt d'un équipement entre deux mesures de la puissance consommée du logement. Supposons que vous ayez une remontée de la puissance consommée toutes les 5 minutes. Si entre 2 mesures un radiateur est éteint alors l'allumage d'un nouveau pourra être autorisé. Avant, seuls les allumages étaient pris en compte entre 2 mesures. Comme avant, la prochaine remontée de la puissance consommée viendra éventuellement délester plus ou moins.
>    6. _auto-start/stop_ : l'auto-start/stop n'est utile que pour les Vtherm de type `over_climate` sans contrôle direct de la vanne. L'option a été supprimée pour les autres types de VTherm.
>    7. _VTherm UI Card_ : toutes ces modifications ont permis une évolution majeure de la [VTherm UI Card](documentation/fr/additions.md#versatile-thermostat-ui-card) pour y intégrer des messages expliquant l'état courant (pourquoi mon VTherm à cette température cible ?) et si un filtrage temporel est en cours - donc la mise à jour de l'état du sous-jacent a été retardée.
>    8. _amélioration des logs_ : les logs ont été améliorés pour simplifier le debug. Des logs de la forme `--------------------> NEW EVENT: VersatileThermostat-Inversed ...` informe d'un évènement venant impacter l'état du VTherm.
>
> ⚠️ **Attention**
>
> Cette version majeure embarque des changements incompatibles avec la précédente:
> - `versatile_thermostat_security_event` a été renommé en `versatile_thermostat_safety_event`. Si vos automatisations utiles cet évènement, vous devez les mettre à jour,
> - les attributs personnalisés ont été réorganisés. Vous devez mettre à jour vos automisations ou template Jinja qui les utiliseraient,
> - la [VTherm UI Card](documentation/fr/additions.md#versatile-thermostat-ui-card) doit être mise à jour au minimum en V2.0 pour être compatible,
>
> **Malgré les 342 tests automatisés de cette intégration et le soin apporté à cette version majeure, je ne peux garantir que son installation ne viendra pas perturber les états de vos VTherm. Pour chaque VTherm vous devez vérifier le preset, le hvac_mode et éventuellement la température de consigne du VTherm après installation.**
>
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
18. [L'auto-régulation](documentation/fr/self-regulation.md)
19. [Les différents algorithmes](documentation/fr/algorithms.md)
20. [Documentation de référence](documentation/fr/reference.md)
21. [Exemple de réglages](documentation/fr/tuning-examples.md)
22. [Dépannage](documentation/fr/troubleshooting.md)
23. [Notes de version](documentation/fr/releases.md)

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
