[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

![Tip](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/icon.png?raw=true)

> ![Tip](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/tips.png?raw=true?raw=true) Cette intégration de thermostat vise à simplifier considérablement vos automatisations autour de la gestion du chauffage. Parce que tous les événements autour du chauffage classiques sont gérés nativement par le thermostat (personne à la maison ?, activité détectée dans une pièce ?, fenêtre ouverte ?, délestage de courant ?), vous n'avez pas à vous encombrer de scripts et d'automatismes compliqués pour gérer vos climats. ;-).

- [Quand l'utiliser et ne pas l'utiliser](#quand-lutiliser-et-ne-pas-lutiliser)
- [Pourquoi une nouvelle implémentation du thermostat ?](#pourquoi-une-nouvelle-implémentation-du-thermostat-)
- [Comment installer cet incroyable Thermostat Versatile ?](#comment-installer-cet-incroyable-thermostat-versatile-)
  - [HACS installation (recommendé)](#hacs-installation-recommendé)
  - [Installation manuelle](#installation-manuelle)
- [Configuration](#configuration)
  - [Choix des attributs de base](#choix-des-attributs-de-base)
  - [Sélectionnez des entités pilotées](#sélectionnez-des-entités-pilotées)
  - [Configurez les coefficients de l'algorithme TPI](#configurez-les-coefficients-de-lalgorithme-tpi)
  - [Configurer la température préréglée](#configurer-la-température-préréglée)
  - [Configurer les portes/fenêtres en allumant/éteignant les thermostats](#configurer-les-portesfenêtres-en-allumantéteignant-les-thermostats)
    - [Le mode capteur](#le-mode-capteur)
    - [Le mode auto](#le-mode-auto)
  - [Configurer le mode d'activité ou la détection de mouvement](#configurer-le-mode-dactivité-ou-la-détection-de-mouvement)
  - [Configurer la gestion de la puissance](#configurer-la-gestion-de-la-puissance)
  - [Configurer la présence ou l'occupation](#configurer-la-présence-ou-loccupation)
  - [Configuration avancée](#configuration-avancée)
- [Exemples de réglage](#exemples-de-réglage)
  - [Chauffage électrique](#chauffage-électrique)
  - [Chauffage central (chauffage gaz ou fuel)](#chauffage-central-chauffage-gaz-ou-fuel)
  - [Le capteur de température alimenté par batterie](#le-capteur-de-température-alimenté-par-batterie)
  - [Capteur de température réactif (sur secteur)](#capteur-de-température-réactif-sur-secteur)
  - [Mes presets](#mes-presets)
- [Algorithme](#algorithme)
  - [Algorithme TPI](#algorithme-tpi)
- [Capteurs](#capteurs)
- [Services](#services)
  - [Forcer la présence/occupation](#forcer-la-présenceoccupation)
  - [Modifier la température des préréglages](#modifier-la-température-des-préréglages)
  - [Modifier les paramètres de sécurité](#modifier-les-paramètres-de-sécurité)
- [Notifications](#notifications)
- [Attributs personnalisés](#attributs-personnalisés)
- [Quelques résultats](#quelques-résultats)
- [Encore mieux](#encore-mieux)
  - [Encore mieux avec le composant Scheduler !](#encore-mieux-avec-le-composant-scheduler-)
  - [Encore bien mieux avec la custom:simple-thermostat front integration](#encore-bien-mieux-avec-la-customsimple-thermostat-front-integration)
  - [Toujours mieux avec Apex-chart pour régler votre thermostat](#toujours-mieux-avec-apex-chart-pour-régler-votre-thermostat)
  - [Et toujours de mieux en mieux avec l'AappDaemon NOTIFIER pour notifier les évènements](#et-toujours-de-mieux-en-mieux-avec-laappdaemon-notifier-pour-notifier-les-évènements)
- [Les contributions sont les bienvenues !](#les-contributions-sont-les-bienvenues)


Ce composant personnalisé pour Home Assistant est une mise à niveau et est une réécriture complète du composant "Awesome thermostat" (voir [Github](https://github.com/dadge/awesome_thermostat)) avec l'ajout de fonctionnalités.


> ![Nouveau](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/new-icon.png?raw=true) _*Nouveautés*_
> * **Release 3.2** : ajout de la possibilité de commander plusieurs switch à partir du même thermostat. Dans ce mode, les switchs sont déclenchés avec un délai pour minimiser la puisssance nécessaire à un instant (on minimise les périodes de recouvrement). Voir [Configuration](#sélectionnez-des-entités-pilotées)
> * **Release 3.1** : ajout d'une détection de fenêtres/portes ouvertes par chute de température. Cette nouvelle fonction permet de stopper automatiquement un radiateur lorsque la température chute brutalement. Voir [Le mode auto](#le-mode-auto)
> * **Release majeure 3.0** : ajout d'un équipement thermostat et de capteurs (binaires et non binaires) associés. Beaucoup plus proche de la philosphie Home Assistant, vous avez maintenant un accès direct à l'énergie consommée par le radiateur piloté par le thermostat et à plein d'autres capteurs qui seront utiles dans vos automatisations et dashboard.
> * **release 2.3** : ajout de la mesure de puissance et d'énergie du radiateur piloté par le thermostat.
> * **release 2.2** : ajout de fonction de sécurité permettant de ne pas laisser éternellement en chauffe un radiateur en cas de panne du thermomètre
> * **release majeure 2.0** : ajout du thermostat "over climate" permettant de transformer n'importe quel thermostat en Versatile Thermostat et lui ajouter toutes les fonctions de ce dernier.

# Quand l'utiliser et ne pas l'utiliser
Ce thermostat peut piloter 2 types d'équipement:
1. un radiateur qui ne fonctionne qu'en mode marche/arrêt (nommé ```thermostat_over_switch```). La configuration minimale nécessaire pour utiliser ce type thermostat est :
   a. un équipement comme un radiateur (un ```switch``` ou équivalent),
   b. une sonde de température pour la pièce (ou un input_number),
   c. un capteur de température externe (pensez à l'intégration météo si vous n'en avez pas)
2. un autre thermostat qui a ses propres modes de fonctionnement (nommé ```thermostat_over_climate```). Pour ce type de thermostat la configuration minimale nécessite :
   a. un équipement comme une climatisation qui est pilotée par sa propre entity de type ```climate```,
   b. une sonde de température pour la pièce (ou un input_number),
   c. un capteur de température externe (pensez à l'intégration météo si vous n'en avez pas)

Le type ```thermostat_over_climate``` permet d'ajouter à votre équipement existant toutes les fonctionnalités fournies par VersatileThermostat. L'entité climate VersatileThermostat pilotera votre entité climate, en la coupant si les fenêtres sont ouvertes, la passant en mode Eco si personne n'est présent, etc. Cf. [ici](#pourquoi-une-nouvelle-implémentation-du-thermostat). Pour ce type de thermostat, les cycles éventuels de chauffe sont pilotés par l'entité climate sous-jacente et pas par le Versatile Thermostat lui-même.

Parce que cette intégration vise à commander le radiateur en tenant compte du préréglage configuré (preset) et de la température ambiante, ces informations sont obligatoires.

# Pourquoi une nouvelle implémentation du thermostat ?

Ce composant nommé __Versatile thermostat__ gère les cas d'utilisation suivants :
- Configuration via l'interface graphique d'intégration standard (à l'aide du flux Config Entry),
- Utilisations complètes du **mode préréglages**,
- Désactiver le mode préréglé lorsque la température est **définie manuellement** sur un thermostat,
- Éteindre/allumer un thermostat lorsqu'une **porte ou des fenêtres sont ouvertes/fermées** après un certain délai,
- Changer de preset lorsqu'une **activité est détectée** ou non dans une pièce pendant un temps défini,
- Utiliser un algorithme **TPI (Time Proportional Interval)** grâce à l'algorithme [[Argonaute](https://forum.hacf.fr/u/argonaute/summary)] ,
- Ajouter une **gestion de délestage** ou une régulation pour ne pas dépasser une puissance totale définie. Lorsque la puissance maximale est dépassée, un préréglage caché de « puissance » est défini sur l'entité climatique. Lorsque la puissance passe en dessous du maximum, le préréglage précédent est restauré.
- La **gestion de la présence à domicile**. Cette fonctionnalité vous permet de modifier dynamiquement la température du préréglage en tenant compte d'un capteur de présence de votre maison.
- Des **services pour interagir avec le thermostat** à partir d'autres intégrations : vous pouvez forcer la présence / la non-présence à l'aide d'un service, et vous pouvez modifier dynamiquement la température des préréglages et changer les paramètres de sécurité.
- Ajouter des capteurs pour voir les états internes du thermostat.

# Comment installer cet incroyable Thermostat Versatile ?

## HACS installation (recommendé)

1. Installez [HACS](https://hacs.xyz/). De cette façon, vous obtenez automatiquement les mises à jour.
2. Ajoutez ce repository Github en tant que repository personnalisé dans les paramètres HACS.
3. recherchez et installez "Versatile Thermostat" dans HACS et cliquez sur "installer".
4. Redémarrez Home Assistant.
5. Ensuite, vous pouvez ajouter une intégration de Versatile Thermostat dans la page d'intégration. Vous ajoutez autant de thermostats dont vous avez besoin (généralement un par radiateur qui doit être géré ou par pompe dans le cas d'un chauffage centralisé)


## Installation manuelle

1. À l'aide de l'outil de votre choix, ouvrez le répertoire (dossier) de votre configuration HA (où vous trouverez `configuration.yaml`).
2. Si vous n'avez pas de répertoire (dossier) `custom_components`, vous devez le créer.
3. Dans le répertoire (dossier) `custom_components`, créez un nouveau dossier appelé `versatile_thermostat`.
4. Téléchargez _tous_ les fichiers du répertoire `custom_components/versatile_thermostat/` (dossier) dans ce référentiel.
5. Placez les fichiers que vous avez téléchargés dans le nouveau répertoire (dossier) que vous avez créé.
6. Redémarrez l'assistant domestique
7. Configurer la nouvelle intégration du Versatile Thermostat

# Configuration

Note: aucune configuration dans configuration.yaml n'est nécessaire car toute la configuration est effectuée via l'interface graphique standard lors de l'ajout de l'intégration.

Cliquez sur le bouton Ajouter une intégration dans la page d'intégration

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/add-an-integration.png?raw=true)

La configuration peut être modifiée via la même interface. Sélectionnez simplement le thermostat à modifier, appuyez sur "Configurer" et vous pourrez modifier certains paramètres ou la configuration.

Suivez ensuite les étapes de configuration comme suit :

## Choix des attributs de base

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-main.png?raw=true)

Donnez les principaux attributs obligatoires :
1. un nom (sera le nom de l'intégration et aussi le nom de l'entité climate)
2. le type de thermostat ```thermostat_over_switch``` pour piloter un radiateur commandé par un switch ou ```thermostat_over_climate``` pour piloter un autre thermostat. Cf. [ci-dessus](#pourquoi-une-nouvelle-implémentation-du-thermostat)
4. un identifiant d'entité de capteur de température qui donne la température de la pièce dans laquelle le radiateur est installé,
5. une entité capteur de température donnant la température extérieure. Si vous n'avez pas de capteur externe, vous pouvez utiliser l'intégration météo locale
6. une durée de cycle en minutes. A chaque cycle, le radiateur s'allumera puis s'éteindra pendant une durée calculée afin d'atteindre la température ciblée (voir [preset](#configure-the-preset-temperature) ci-dessous),
7. les températures minimales et maximales du thermostat,
8. une puissance de l'équipement ce qui va activer les capteurs de puissance et énergie consommée par l'appareil,
9. la liste des fonctionnalités qui seront utilisées pour ce thermostat. En fonction de vos choix, les écrans de configuration suivants s'afficheront ou pas.

> ![Astuce](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/tips.png?raw=true) _*Notes*_
      1. avec le type ```thermostat_over_swutch```, les calculs sont effectués à chaque cycle. Donc en cas de changement de conditions, il faudra attendre le prochain cycle pour voir un changement. Pour cette raison, le cycle ne doit pas être trop long. **5 min est une bonne valeur**,
      2. si le cycle est trop court, le radiateur ne pourra jamais atteindre la température cible en effet pour le radiateur à accumulation et il sera sollicité inutilement

## Sélectionnez des entités pilotées
En fonction de votre choix sur le type de thermostat, vous devrez choisir une ou plusieurs entités de type switch ou une entité de type climate. Seules les entités compatibles sont présentées.

Pour un thermostat de type ```thermostat_over_switch```:
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-linked-entity.png?raw=true)
L'algorithme à utiliser est aujourd'hui limité à TPI est disponible. Voir [algorithme](#algorithme).
Si plusieurs entités de type sont configurées, la thermostat décale les activations afin de minimiser le nombre de switch actif à un instant t. Ca permet une meilleure répartition de la puissance puisque chaque radiateur va s'allumer à son tour.
Exemple de déclenchement synchronisé :
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/multi-switch-activation.png?raw=true)


Pour un thermostat de type ```thermostat_over_climate```:
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-linked-entity2.png?raw=true)

## Configurez les coefficients de l'algorithme TPI

Si vous avez choisi un thermostat de type ```thermostat_over_switch``` vous arriverez sur cette page :

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-tpi.png?raw=true)

Vous devez donner :
1. le coefficient coef_int de l'algorithme TPI,
2. le coefficient coef_ext de l'algorithme TPI


Pour plus d'informations sur l'algorithme TPI et son réglage, veuillez vous référer à [algorithm](#algorithm).

## Configurer la température préréglée
Cliquez sur 'Valider' sur la page précédente et vous y arriverez :

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-presets.png?raw=true)

Le mode préréglé (preset) vous permet de préconfigurer la température ciblée. Utilisé en conjonction avec Scheduler (voir [scheduler](#even-better-with-scheduler-component) vous aurez un moyen puissant et simple d'optimiser la température par rapport à la consommation électrique de votre maison. Les préréglages gérés sont les suivants :
 - **Eco** : l'appareil est en mode d'économie d'énergie
 - **Confort** : l'appareil est en mode confort
 - **Boost** : l'appareil tourne toutes les vannes à fond

**Aucun** est toujours ajouté dans la liste des modes, car c'est un moyen de ne pas utiliser les preset mais une **température manuelle** à la place.

> ![Astuce](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/tips.png?raw=true) _*Notes*_
    1. En modifiant manuellement la température cible, réglez le préréglage sur Aucun (pas de préréglage). De cette façon, vous pouvez toujours définir une température cible même si aucun préréglage n'est disponible.
    2. Le préréglage standard ``Away`` est un préréglage caché qui n'est pas directement sélectionnable. Versatile Thermostat utilise la gestion de présence ou la gestion de mouvement pour régler automatiquement et dynamiquement la température cible en fonction d'une présence dans le logement ou d'une activité dans la pièce. Voir [gestion de la présence](#configure-the-presence-management).
    3. Si vous utilisez la gestion du délestage, vous verrez un préréglage caché nommé ``power``. Le préréglage de l'élément chauffant est réglé sur « puissance » lorsque des conditions de surpuissance sont rencontrées et que le délestage est actif pour cet élément chauffant. Voir [gestion de l'alimentation](#configure-the-power-management).
    4. si vous utilisez la configuration avancée, vous verrez le préréglage défini sur ``sécurité`` si la température n'a pas pu être récupérée après un certain délai
    5. Si vous ne souhaitez pas utiliser le préréglage, indiquez 0 comme température. Le préréglage sera alors ignoré et ne s'affichera pas dans le composant front

## Configurer les portes/fenêtres en allumant/éteignant les thermostats
Vous devez avoir choisi la fonctionnalité ```Avec détection des ouvertures``` dans la première page pour arriver sur cette page.
La détecttion des ouvertures peut se faire de 2 manières:
1. soit avec un capteur placé sur l'ouverture (mode capteur),
2. soit en détectant une chute brutale de température (mode auto)

### Le mode capteur
En mode capteur, vous devez renseigner les informations suivantes:
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-window-sensor.png?raw=true)

1. un identifiant d'entité d'un **capteur de fenêtre/porte**. Cela devrait être un binary_sensor ou un input_boolean. L'état de l'entité doit être 'on' lorsque la fenêtre est ouverte ou 'off' lorsqu'elle est fermée
2. un **délai en secondes** avant tout changement. Cela permet d'ouvrir rapidement une fenêtre sans arrêter le chauffage.


### Le mode auto
En mode auto, la configuration est la suivante:
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-window-auto.png?raw=true)

1. un seuil de détection en degré par minute. Lorsque la température chute au delà de ce seuil, le thermostat s'éteindra. Plus cette valeur est faible et plus la détection sera rapide (en contre-partie d'un risque de faux positif),
2. un seuil de fin de détection en degré par minute. Lorsque la chute de température repassera au-dessus cette valeur, le thermostat se remettra dans le mode précédent (mode et preset),
3. une durée maximale de détection. Au delà de cette durée, le thermostat se remettra dans son mode et preset précédent même si la température continue de chuter.

Pour régler les seuils il est conseillé de commencer avec les valeurs de référence et d'ajuster les seuils de détection. Quelques essais m'ont donné les valeurs suivantes (pour un bureau):
- seuil de détection : 0,05 °C/min
- seuil de non détection: 0 °C/min
- durée max : 60 min.

Un nouveau capteur "slope" a été ajouté pour tous les thermostats. Il donne la pente de la courbe de température en °C/min (ou °K/min). Cette pente est lissée et filtrée pour éviter les valeurs abérrantes des thermomètres qui viendraient pertuber la mesure.
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/temperature-slope.png?raw=true)

Pour bien régler il est conseillé d'affocher sur un même graphique historique la courbe de température et la pente de la courbe (le "slope") :
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/window-auto-tuning.png?raw=true)

Et c'est tout ! votre thermostat s'éteindra lorsque les fenêtres seront ouvertes et se rallumera lorsqu'il sera fermé.

> ![Astuce](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/tips.png?raw=true) _*Notes*_
    1. Si vous souhaitez utiliser **plusieurs capteurs de porte/fenêtre** pour automatiser votre thermostat, créez simplement un groupe avec le comportement habituel (https://www.home-assistant.io/integrations/binary_sensor.group/)
    2. Si vous n'avez pas de capteur de fenêtre/porte dans votre chambre, laissez simplement l'identifiant de l'entité du capteur vide,
    3. **Un seul mode est permis**. On ne peut pas configurer un thermostat avec un capteur et une détection automatique. Les 2 modes risquant de se contredire, il n'est pas possible d'avoir les 2 modes en même temps,
    4. Il est déconseillé d'utiliser le mode automatique pour un équipement soumis à des variations de température fréquentes et normales (couloirs, zones ouvertes, ...)

## Configurer le mode d'activité ou la détection de mouvement
Si vous avez choisi la fonctionnalité ```Avec détection de mouvement```, cliquez sur 'Valider' sur la page précédente et vous y arriverez :

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-motion.png?raw=true)

Nous allons maintenant voir comment configurer le nouveau mode Activité.
Ce dont nous avons besoin:
- un **capteur de mouvement**. ID d'entité d'un capteur de mouvement. Les états du capteur de mouvement doivent être « on » (mouvement détecté) ou « off » (aucun mouvement détecté)
- une durée de **délai de mouvement** (en secondes) définissant combien de temps nous attendons la confirmation du mouvement avant de considérer le mouvement
- un **préréglage de "mouvement" **. Nous utiliserons la température de ce préréglage lorsqu'une activité sera détectée.
- un **préréglage "pas de mouvement"**. Nous utiliserons la température de ce deuxième préréglage lorsqu'aucune activité n'est détectée.

Alors imaginons que nous voulions avoir le comportement suivant :
- nous avons une pièce avec un thermostat réglé en mode activité, le mode "mouvement" choisi est confort (21.5C), le mode "pas de mouvement" choisi est Eco (18.5C) et la temporisation du mouvement est de 5 min.
- la pièce est vide depuis un moment (aucune activité détectée), la température de cette pièce est de 18,5 C
- quelqu'un entre dans la pièce, une activité est détectée la température est fixée à 21,5 C
- la personne quitte la chambre, au bout de 5 min la température est ramenée à 18,5 C

Pour que cela fonctionne, le thermostat climatique doit être en mode préréglé « Activité ».

> ![Astuce](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/tips.png?raw=true) _*Notes*_
    1. Sachez que comme pour les autres modes prédéfinis, ``Activity`` ne sera proposé que s'il est correctement configuré. En d'autres termes, les 4 clés de configuration doivent être définies si vous souhaitez voir l'activité dans l'interface de l'assistant domestique

## Configurer la gestion de la puissance

Si vous avez choisi la fonctionnalité ```Avec détection de la puissance```, cliquez sur 'Valider' sur la page précédente et vous arriverez ici :

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-power.png?raw=true)

Cette fonction vous permet de réguler la consommation électrique de vos radiateurs. Connue sous le nom de délestage, cette fonction vous permet de limiter la consommation électrique de votre appareil de chauffage si des conditions de surpuissance sont détectées. Donnez un **capteur à la consommation électrique actuelle de votre maison**, un **capteur à la puissance max** qu'il ne faut pas dépasser, la **consommation électrique de votre chauffage** (en étape 1 de la configuration) et l'algorithme ne démarrera pas un radiateur si la puissance maximale sera dépassée après le démarrage du radiateur.

Notez que toutes les valeurs de puissance doivent avoir les mêmes unités (kW ou W par exemple).
Cela vous permet de modifier la puissance maximale au fil du temps à l'aide d'un planificateur ou de ce que vous voulez.

> ![Astuce](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/tips.png?raw=true) _*Notes*_
    1. En cas de délestage, le radiateur est réglé sur le préréglage nommé ```power```. Il s'agit d'un préréglage caché, vous ne pouvez pas le sélectionner manuellement.
    2. Je l'utilise pour éviter de dépasser la limite de mon contrat d'électricité lorsqu'un véhicule électrique est en charge. Cela crée une sorte d'autorégulation.
    3. Gardez toujours une marge, car la puissance max peut être brièvement dépassée en attendant le calcul du prochain cycle typiquement ou par des équipements non régulés.
    4. Si vous ne souhaitez pas utiliser cette fonctionnalité, laissez simplement l'identifiant des entités vide

## Configurer la présence ou l'occupation
Si sélectionnée en première page, cette fonction vous permet de modifier dynamiquement la température de tous les préréglages du thermostat configurés lorsque personne n'est à la maison ou lorsque quelqu'un rentre à la maison. Pour cela, vous devez configurer la température qui sera utilisée pour chaque préréglage lorsque la présence est désactivée. Lorsque le capteur de présence s'éteint, ces températures seront utilisées. Lorsqu'il se rallume, la température "normale" configurée pour le préréglage est utilisée. Voir [gestion des préréglages](#configure-the-preset-temperature).
Pour configurer la présence remplissez ce formulaire :

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-presence.png?raw=true)

Pour cela, vous devez configurer :
1. Un **capteur d'occupation** dont l'état doit être 'on' ou 'home' si quelqu'un est présent ou 'off' ou 'not_home' sinon,
2. La **température utilisée en Eco** prédéfinie en cas d'absence,
3. La **température utilisée en Confort** préréglée en cas d'absence,
4. La **température utilisée en Boost** préréglée en cas d'absence

> ![Astuce](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/tips.png?raw=true) _*Notes*_
      1. le changement de température est immédiat et se répercute sur le volet avant. Le calcul prendra en compte la nouvelle température cible au prochain calcul du cycle,
      2. vous pouvez utiliser le capteur direct person.xxxx ou un groupe de capteurs de Home Assistant. Le capteur de présence gère les états ``on`` ou ``home`` comme présents et les états ``off`` ou ``not_home`` comme absents.

## Configuration avancée
Ces paramètres permettent d'affiner le réglage du thermostat.
Le formulaire de configuration avancée est le suivant :

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/config-advanced.png?raw=true)

Le premier délai (minimal_activation_delay_sec) en secondes est le délai minimum acceptable pour allumer le chauffage. Lorsque le calcul donne un délai de mise sous tension inférieur à cette valeur, le chauffage reste éteint.

Le deuxième délai (``security_delay_min``) est le délai maximal entre deux mesures de température avant de régler le préréglage sur ``security``. Si le capteur de température ne donne plus de mesures de température, le thermostat et le radiateur passeront en mode ``security`` après ce délai. Ceci est utile pour éviter une surchauffe si la batterie de votre capteur de température est trop faible.

Le troisième paramétre (``security_min_on_percent``) est la valeur minimal de ``on_percent`` en dessous de laquelle le préréglage sécurité ne sera pas activé. Ce paramètre permet de ne pas mettre en sécurité un thermostat, si le radiateur piloté ne chauffe pas suffisament.
Mettre ce paramètre à ``0.00`` déclenchera le préréglage sécurité quelque soit la dernière consigne de chauffage, à l'inverse ``1.00`` ne déclenchera jamais le préréglage sécurité ( ce qui revient à désactiver la fonction).

Le quatrième param§tre (``security_default_on_percent``) est la valeur de ``on_percent`` qui sera utilisée lorsque le thermostat passe en mode ``security``. Si vous mettez ``0`` alors le thermostat sera coupé lorsqu'il passe en mode ``security``, mettre 0,2% par exemple permet de garder un peu de chauffage (20% dans ce cas), même en mode ``security``. Ca évite de retrouver son logement totalement gelé lors d'une panne de thermomètre.

Voir [exemple de réglages](#examples-tuning) pour avoir des exemples de réglage communs

> ![Astuce](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/tips.png?raw=true) _*Notes*_
    1. Lorsque le capteur de température viendra à la vie et renverra les températures, le préréglage sera restauré à sa valeur précédente,
    3. Attention, deux températures sont nécessaires : la température interne et la température externe et chacune doit donner la température, sinon le thermostat sera en préréglage "security",
    4. Un service est disponible qui permet de régler les 3 paramètres de sécurité. Ca peut servir à adapter la fonction de sécurité à votre usage,
    5. Pour un usage naturel, le ``security_default_on_percent`` doit être inférieur à ``security_min_on_percent``,
    6. Lorsqu'un thermostat de type ``thermostat_over_climate`` passe en mode ``security`` il est éteint. Les paramètres ``security_min_on_percent`` et ``security_default_on_percent`` ne sont alors pas utilisés.

# Exemples de réglage

## Chauffage électrique
- cycle : entre 5 et 10 minutes,
- minimal_activation_delay_sec : 30 secondes

## Chauffage central (chauffage gaz ou fuel)
- cycle : entre 30 et 60 min,
- minimal_activation_delay_sec : 300 secondes (à cause du temps de réponse)

## Le capteur de température alimenté par batterie
- security_delay_min : 60 min (parce que ces capteurs sont paresseux)
- security_min_on_percent : 0,5 (50% - on passe en preset ``security`` si le radiateur chauffait plus de 50% du temps)
- security_default_on_percent : 0,1 (10% - en preset ``security``, on garde un fond de chauffe de 20% du temps)

Il faut comprendre ces réglages comme suit :

> Si le thermomètre n'envoie plus la température pendant 1 heure et que le pourcentage de chauffe (``on_percent``) était supérieur à 50 %, alors on ramène ce pourcentage de chauffe à 10 %.

A vous d'adapter ces réglages à votre cas !

Ce qui est important c'est de ne pas prendre trop de risque avec ces paramètres : supposez que vous êtes absent pour une longue période, que les piles de votre thermomètre arrivent en fin de vie, votre radiateur va chauffer 10% du temps pendant toute la durée de la panne.

Versatile Thermostat vous permet d'être notifié lorsqu'un évènement de ce type survient. Mettez en place, les alertes qui vont bien dès l'utilisation de ce thermostat. Cf. (#notifications)

## Capteur de température réactif (sur secteur)
- security_delay_min : 15 min
- security_min_on_percent : 0,7 (70% - on passe en preset ``security`` si le radiateur chauffait plus de 70% du temps)
- security_default_on_percent : 0,25 (25% - en preset ``security``, on garde un fond de chauffe de 25% du temps)

## Mes presets
Ceci est juste un exemple de la façon dont j'utilise le préréglage. A vous de vous adapter à votre configuration mais cela peut être utile pour comprendre son fonctionnement.
``Éco`` : 17 °C
``Confort`` : 19 °C
``Boost`` : 20 °C

Lorsque la présence est désactivée :
``Éco`` : 16,5 °C
``Confort`` : 17 °C
``Boost`` : 18 °C

Le détecteur de mouvement de mon bureau est configuré pour utiliser ``Boost`` lorsqu'un mouvement est détecté et ``Eco`` sinon.

# Algorithme
Cette intégration utilise un algorithme proportionnel. Un algorithme proportionnel est utile pour éviter l'oscillation autour de la température cible. Cet algorithme est basé sur un cycle qui alterne le chauffage et l'arrêt du chauffage. La proportion de chauffage par rapport à l'absence de chauffage est déterminée par la différence entre la température et la température cible. Plus grande est la différence et plus grande est la proportion de chauffage à l'intérieur du cycle.

Cet algorithme fait converger la température et arrête d'osciller.

## Algorithme TPI
L'algorithme TPI consiste à calculer à chaque cycle un pourcentage d'état On vs Off pour le radiateur en utilisant la température cible, la température actuelle dans la pièce et la température extérieure actuelle.

Le pourcentage est calculé avec cette formule :

    on_percent = coef_int * (température cible - température actuelle) + coef_ext * (température cible - température extérieure)
    Ensuite, faites 0 <= on_percent <= 1

Les valeurs par défaut pour coef_int et coef_ext sont respectivement : ``0.6`` et ``0.01``. Ces valeurs par défaut conviennent à une pièce standard bien isolée.

Pour régler ces coefficients, gardez à l'esprit que :
1. **si la température cible n'est pas atteinte** après une situation stable, vous devez augmenter le ``coef_ext`` (le ``on_percent`` est trop bas),
2. **si la température cible est dépassée** après une situation stable, vous devez diminuer le ``coef_ext`` (le ``on_percent`` est trop haut),
3. **si l'atteinte de la température cible est trop lente**, vous pouvez augmenter le ``coef_int`` pour donner plus de puissance au réchauffeur,
4. **si l'atteinte de la température cible est trop rapide et que des oscillations apparaissent** autour de la cible, vous pouvez diminuer le ``coef_int`` pour donner moins de puissance au radiateur

Voir quelques situations à [examples](#some-results).

# Capteurs

Avec le thermostat sont disponibles des capteurs qui permettent de visualiser les alertes et l'état interne du thermostat. Ils sont disponibles dans les entités de l'appareil associé au thermostat :

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/thermostat-sensors.png?raw=true)

Dans l'ordre, il y a :
1. l'entité principale climate de commande du thermostat,
2. l'énergie consommée par le thermostat (valeur qui s'incrémente en permanence),
3. l'heure de réception de la dernière température extérieure,
4. l'heure de réception de la dernière température intérieure,
5. la puissance moyenne de l'appareil sur le cycle (pour les TPI seulement),
6. le temps passé à l'état éteint dans le cycle (TPI seulement),
7. le temps passé à l'état allumé dans le cycle (TPI seulement),
8. l'état de délestage,
9. le pourcentage de puissance sur le cycle (TPI seulement),
10. l'état de présence (si la gestion de la présence est configurée),
11. l'état de sécurité,
12. l'état de l'ouverture (si la gestion des ouvertures est configurée),
13. l'état du mouvement (si la gestion du mouvements est configurée)

Pour colorer les capteurs, ajouter ces lignes et personnalisez les au besoin, dans votre configuration.yaml :

```
frontend:
  themes:
    versatile_thermostat_theme:
      state-binary_sensor-safety-on-color: "#FF0B0B"
      state-binary_sensor-power-on-color: "#FF0B0B"
      state-binary_sensor-window-on-color: "rgb(156, 39, 176)"
      state-binary_sensor-motion-on-color: "rgb(156, 39, 176)"
      state-binary_sensor-presence-on-color: "lightgreen"
```
et choisissez le thème ```versatile_thermostat_theme``` dans la configuration du panel. Vous obtiendrez quelque-chose qui va ressembler à ça :

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/colored-thermostat-sensors.png?raw=true)

# Services

Cette implémentation personnalisée offre des services spécifiques pour faciliter l'intégration avec d'autres composants Home Assistant.

## Forcer la présence/occupation
Ce service permet de forcer l'état de présence indépendamment du capteur de présence. Cela peut être utile si vous souhaitez gérer la présence via un service et non via un capteur. Par exemple, vous pouvez utiliser votre réveil pour forcer l'absence lorsqu'il est allumé.

Le code pour appeler ce service est le suivant :
```
service : thermostat_polyvalent.set_presence
Les données:
    présence : "off"
cible:
    entity_id : climate.my_thermostat
```

## Modifier la température des préréglages
Ce service est utile si vous souhaitez modifier dynamiquement la température préréglée. Au lieu de changer de préréglage, certains cas d'utilisation doivent modifier la température du préréglage. Ainsi, vous pouvez garder le Programmateur inchangé pour gérer le préréglage et ajuster la température du préréglage.
Si le préréglage modifié est actuellement sélectionné, la modification de la température cible est immédiate et sera prise en compte au prochain cycle de calcul.

Vous pouvez modifier l'une ou les deux températures (lorsqu'elles sont présentes ou absentes) de chaque préréglage.

Utilisez le code suivant pour régler la température du préréglage :
```
service : thermostat_polyvalent.set_preset_temperature
date:
    preset : boost
    temperature : 17,8
    temperature_away : 15
target:
    entity_id : climate.my_thermostat
```

> ![Astuce](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/tips.png?raw=true) _*Notes*_
    - après un redémarrage, les préréglages sont réinitialisés à la température configurée. Si vous souhaitez que votre changement soit permanent, vous devez modifier le préréglage de la température dans la configuration de l'intégration.

## Modifier les paramètres de sécurité
Ce service permet de modifier dynamiquement les paramètres de sécurité décrits ici [Configuration avancée](#configuration-avancée).
Si le thermostat est en mode ``security`` les nouveaux paramètres sont appliqués immédiatement.

Pour changer les paramètres de sécurité utilisez le code suivant :
```
service : thermostat_polyvalent.set_security
date:
    min_on_percent: "0.5"
    default_on_percent: "0.1"
    delay_min: 60
target:
    entity_id : climate.my_thermostat
```

# Notifications
Les évènements marquant du thermostat sont notifiés par l'intermédiaire du bus de message.
Les évènements notifiés sont les suivants: 

- ``versatile_thermostat_security_event`` : un thermostat entre ou sort du preset ``security``
- ``versatile_thermostat_power_event`` : un thermostat entre ou sort du preset ``power``
- ``versatile_thermostat_temperature_event`` : une ou les deux mesures de température d'un thermostat n'ont pas été mis à jour depuis plus de `security_delay_min`` minutes
- ``versatile_thermostat_hvac_mode_event`` : le thermostat est allumé ou éteint. Cet évènement est aussi diffusé au démarrage du thermostat
- ``versatile_thermostat_preset_event`` : un nouveau preset est sélectionné sur le thermostat. Cet évènement est aussi diffusé au démarrage du thermostat

Si vous avez bien suivi, lorsqu'un thermostat passe en mode sécurité, 3 évènements sont déclenchés :
1. ``versatile_thermostat_temperature_event`` pour indiquer qu'un thermomètre ne répond plus,
2. ``versatile_thermostat_preset_event`` pour indiquer le passage en preset ```security```,
3. ``versatile_thermostat_hvac_mode_event`` pour indiquer l'extinction éventuelle du thermostat

Chaque évènement porte les valeurs clés de l'évènement (températures, preset courant, puissance courante, ...) ainsi que les états du thermostat.

Vous pouvez très facilement capter ses évènements dans une automatisation par exemple pour notifier les utilisateurs.

# Attributs personnalisés

Pour régler l'algorithme, vous avez accès à tout le contexte vu et calculé par le thermostat via des attributs dédiés. Vous pouvez voir (et utiliser) ces attributs dans l'IHM "Outils de développement / états" de HA. Entrez votre thermostat et vous verrez quelque chose comme ceci :
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/dev-tools-climate.png?raw=true)

Les attributs personnalisés sont les suivants :

| Attribut | Signification |
| ----------| --------|
| ``hvac_modes`` | La liste des modes supportés par le thermostat |
| ``temp_min`` | La température minimale |
| ``temp_max`` | La température maximale |
| ``preset_modes`` | Les préréglages visibles pour ce thermostat. Les préréglages cachés ne sont pas affichés ici |
| ``temperature_actuelle`` | La température actuelle telle que rapportée par le capteur |
| ``temperature`` | La température cible |
| ``action_hvac`` | L'action en cours d'exécution par le réchauffeur. Peut être inactif, chauffage |
| ``preset_mode`` | Le préréglage actuellement sélectionné. Peut être l'un des 'preset_modes' ou un préréglage caché comme power |
| ``[eco/confort/boost]_temp`` | La température configurée pour le préréglage xxx |
| ``[eco/confort/boost]_away_temp`` | La température configurée pour le préréglage xxx lorsque la présence est désactivée ou not_home |
| ``temp_power`` | La température utilisée lors de la détection de la perte |
| ``on_percent`` | (déprécié) Le pourcentage sur calculé par l'algorithme TPI |
| ``on_time_sec`` | (déprécié) La période On en sec. Doit être ```on_percent * cycle_min``` |
| ``off_time_sec`` | (déprécié) La période d'arrêt en sec. Doit être ```(1 - on_percent) * cycle_min``` |
| ``cycle_min`` | Le cycle de calcul en minutes |
| ``function`` | L'algorithme utilisé pour le calcul du cycle |
| ``tpi_coef_int`` | Le ``coef_int`` de l'algorithme TPI |
| ``tpi_coef_ext`` | Le ``coef_ext`` de l'algorithme TPI |
| ``saved_preset_mode`` | Le dernier preset utilisé avant le basculement automatique du preset |
| ``saved_target_temp`` | La dernière température utilisée avant la commutation automatique |
| ``window_state`` | (déprécié) Le dernier état connu du capteur de fenêtre. Aucun si la fenêtre n'est pas configurée |
| ``motion_state`` | (déprécié) Le dernier état connu du capteur de mouvement. Aucun si le mouvement n'est pas configuré |
| ``overpowering_state`` | (déprécié) Le dernier état connu du capteur surpuissant. Aucun si la gestion de l'alimentation n'est pas configurée |
| ``presence_state`` | (déprécié) Le dernier état connu du capteur de présence. Aucun si la gestion de présence n'est pas configurée |
| ``security_delay_min`` | Le délai avant de régler le mode de sécurité lorsque le capteur de température est éteint |
| ``security_min_on_percent`` | Pourcentage de chauffe en dessous duquel le thermostat ne passera pas en sécurité |
| ``security_default_on_percent`` | Pourcentage de chauffe utilisé lorsque le thermostat est en sécurité |
| ``last_temperature_datetime`` | (déprécié) La date et l'heure au format ISO8866 de la dernière réception de température interne |
| ``last_ext_temperature_datetime`` | (déprécié) La date et l'heure au format ISO8866 de la dernière réception de température extérieure |
| ``security_state`` | (déprécié) L'état de sécurité. vrai ou faux |
| ``minimal_activation_delay_sec`` | Le délai d'activation minimal en secondes |
| ``last_update_datetime`` | La date et l'heure au format ISO8866 de cet état |
| ``friendly_name`` | Le nom du thermostat |
| ``supported_features`` | Une combinaison de toutes les fonctionnalités prises en charge par ce thermostat. Voir la documentation officielle sur l'intégration climatique pour plus d'informations |

# Quelques résultats

**Convergence de la température vers la cible configurée par preset:**
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/results-1.png?raw=true)

[Cycle de marche/arrêt calculé par l'intégration :](https://)
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/results-2.png?raw=true)

**Coef_int trop élevé (oscillations autour de la cible)**
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/results-3.png?raw=true)

**Évolution du calcul de l'algorithme**
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/results-4.png?raw=true)
Voir le code de ce composant [[ci-dessous](#even-better-with-apex-chart-to-tune-your-thermostat)]

**Thermostat finement réglé**
Merci [impuR_Shozz](https://forum.hacf.fr/u/impur_shozz/summary) !
On peut voir une stabilité autour de la température cible (consigne) et lorsqu'à cible le on_percent (puissance) est proche de 0,3 ce qui semble une très bonne valeur.

![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/results-fine-tuned.png?raw=true)

Enjoy !

# Encore mieux

## Encore mieux avec le composant Scheduler !

Afin de profiter de toute la puissance du Versatile Thermostat, je vous invite à l'utiliser avec https://github.com/nielsfaber/scheduler-component
En effet, le composant scheduler propose une gestion de la base climatique sur les modes prédéfinis. Cette fonctionnalité a un intérêt limité avec le thermostat générique mais elle devient très puissante avec le thermostat Awesome :

À partir d'ici, je suppose que vous avez installé Awesome Thermostat et Scheduler Component.

Dans Scheduler, ajoutez un planning :

![image](https://user-images.githubusercontent.com/1717155/119146454-ee1a9d80-ba4a-11eb-80ae-3074c3511830.png)

Choisissez le groupe "climat", choisissez une (ou plusieurs) entité(s), sélectionnez "MAKE SCHEME" et cliquez sur suivant :
(il est possible de choisir "SET PRESET", mais je préfère utiliser "MAKE SCHEME")

![image](https://user-images.githubusercontent.com/1717155/119147210-aa746380-ba4b-11eb-8def-479a741c0ba7.png)

Définissez votre schéma de mode et enregistrez :


![image](https://user-images.githubusercontent.com/1717155/119147784-2f5f7d00-ba4c-11eb-9de4-5e62ff5e71a8.png)

Dans cet exemple, j'ai réglé le mode ECO pendant la nuit et le jour lorsqu'il n'y a personne à la maison BOOST le matin et CONFORT le soir.


J'espère que cet exemple vous aidera, n'hésitez pas à me faire part de vos retours !

## Encore bien mieux avec la custom:simple-thermostat front integration
Le ``custom:simple-thermostat`` [ici](https://github.com/nervetattoo/simple-thermostat) est une excellente intégration qui permet une certaine personnalisation qui s'adapte bien à ce thermostat.
Vous pouvez avoir quelque chose comme ça très facilement ![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/simple-thermostat.png?raw=true)
Exemple de configuration :

```
      type: custom:simple-thermostat
      entity: climate.thermostat_sam2
      layout:
        step: row
      label:
        temperature: T°
        state: Etat
      hide:
        state: false
      control:
        hvac:
          _name: Mode
        preset:
          _name: Preset
      sensors:
        - entity: sensor.total_puissance_radiateur_sam2
          icon: mdi:lightning-bolt-outline
      header:
        toggle:
          entity: input_boolean.etat_ouverture_porte_sam
          name: Porte sam
```

Vous pouvez personnaliser ce composant à l'aide du composant HACS card-mod pour ajuster les couleurs des alertes. Exemple pour afficher en rouge les alertes sécurité et délestage :

```
          card_mod:
            style: |
              {% if is_state('binary_sensor.thermostat_chambre_security_state', 'on') %}
              ha-card .body .sensor-heading ha-icon[icon="mdi:alert-outline"] {
                color: red;
              }
              {% endif %}
              {% if is_state('binary_sensor.thermostat_chambre_overpowering_state', 'on') %}
              ha-card .body .sensor-heading ha-icon[icon="mdi:flash"] {
                color: red;
              }
              {% endif %}
```
![image](https://github.com/jmcollin78/versatile_thermostat/blob/main/images/custom-css-thermostat.png?raw=true)

## Toujours mieux avec Apex-chart pour régler votre thermostat
Vous pouvez obtenir une courbe comme celle présentée dans [some results](#some-results) avec une sorte de configuration de graphique Apex uniquement en utilisant les attributs personnalisés du thermostat décrits [ici](#custom-attributes) :

```
type: custom:apexcharts-card
header:
  show: true
  title: Tuning chauffage
  show_states: true
  colorize_states: true
update_interval: 60sec
graph_span: 4h
yaxis:
  - id: left
    show: true
    decimals: 2
  - id: right
    decimals: 2
    show: true
    opposite: true
series:
  - entity: climate.thermostat_mythermostat
    attribute: temperature
    type: line
    name: Target temp
    curve: smooth
    yaxis_id: left
  - entity: climate.thermostat_mythermostat
    attribute: current_temperature
    name: Current temp
    curve: smooth
    yaxis_id: left
  - entity: climate.thermostat_mythermostat
    attribute: on_percent
    name: Power percent
    curve: stepline
    yaxis_id: right
```

## Et toujours de mieux en mieux avec l'AappDaemon NOTIFIER pour notifier les évènements
Cette automatisation utilise l'excellente App Daemon nommée NOTIFIER développée par Horizon Domotique que vous trouverez en démonstration [ici](https://www.youtube.com/watch?v=chJylIK0ASo&ab_channel=HorizonDomotique) et le code est [ici](https://github.com/jlpouffier/home-assistant-config/blob/master/appdaemon/apps/notifier.py). Elle permet de notifier les utilisateurs du logement lorsqu'un des évènements touchant à la sécurité survient sur un des Versatile Thermostats.

C'est un excellent exemple de l'utilisation des notifications décrites ici [notification](#notifications).

```
alias: Surveillance Mode Sécurité chauffage
description: Envoi une notification si un thermostat passe en mode sécurité ou power
trigger:
  - platform: event
    event_type: versatile_thermostat_security_event
    id: versatile_thermostat_security_event
  - platform: event
    event_type: versatile_thermostat_power_event
    id: versatile_thermostat_power_event
  - platform: event
    event_type: versatile_thermostat_temperature_event
    id: versatile_thermostat_temperature_event
condition: []
action:
  - choose:
      - conditions:
          - condition: trigger
            id: versatile_thermostat_security_event
        sequence:
          - event: NOTIFIER
            event_data:
              action: send_to_jmc
              title: >-
                Radiateur {{ trigger.event.data.name }} - {{
                trigger.event.data.type }} Sécurité
              message: >-
                Le radiateur {{ trigger.event.data.name }} est passé en {{
                trigger.event.data.type }} sécurité car le thermomètre ne répond
                plus.\n{{ trigger.event.data }}
              callback:
                - title: Stopper chauffage
                  event: stopper_chauffage
              image_url: /media/local/alerte-securite.jpg
              click_url: /lovelace-chauffage/4
              icon: mdi:radiator-off
              tag: radiateur_security_alerte
              persistent: true
      - conditions:
          - condition: trigger
            id: versatile_thermostat_power_event
        sequence:
          - event: NOTIFIER
            event_data:
              action: send_to_jmc
              title: >-
                Radiateur {{ trigger.event.data.name }} - {{
                trigger.event.data.type }} Délestage
              message: >-
                Le radiateur {{ trigger.event.data.name }} est passé en {{
                trigger.event.data.type }} délestage car la puissance max est
                dépassée.\n{{ trigger.event.data }}
              callback:
                - title: Stopper chauffage
                  event: stopper_chauffage
              image_url: /media/local/alerte-delestage.jpg
              click_url: /lovelace-chauffage/4
              icon: mdi:radiator-off
              tag: radiateur_power_alerte
              persistent: true
      - conditions:
          - condition: trigger
            id: versatile_thermostat_temperature_event
        sequence:
          - event: NOTIFIER
            event_data:
              action: send_to_jmc
              title: >-
                Le thermomètre du radiateur {{ trigger.event.data.name }} ne
                répond plus
              message: >-
                Le thermomètre du radiateur {{ trigger.event.data.name }} ne
                répond plus depuis longtemps.\n{{ trigger.event.data }}
              image_url: /media/local/thermometre-alerte.jpg
              click_url: /lovelace-chauffage/4
              icon: mdi:radiator-disabled
              tag: radiateur_thermometre_alerte
              persistent: true
mode: queued
max: 30
```


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
