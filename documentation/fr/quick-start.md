# Démarrage rapide

Cette page présente les étapes à suivre pour avoir un _VTherm_ basique mais opérationnel rapidement. Elle est présentée par type d'équipements.

- [Démarrage rapide](#démarrage-rapide)
  - [Nodon SIN-4-FP-21 ou assimilé (fil pilote)](#nodon-sin-4-fp-21-ou-assimilé-fil-pilote)
  - [Heatzy ou eCosy ou assimilé (entité `climate`)](#heatzy-ou-ecosy-ou-assimilé-entité-climate)
  - [Simple switch comme Aqara T1, Nous B2Z, Sonoff ZBMini, Sonoff POW, ...](#simple-switch-comme-aqara-t1-nous-b2z-sonoff-zbmini-sonoff-pow-)
  - [Sonoff TRVZB ou assimilé (TRV avec contrôle de la vanne)](#sonoff-trvzb-ou-assimilé-trv-avec-contrôle-de-la-vanne)
  - [_PAC_ reversibles ou climatisation ou équipements commandables à travers une entité `climate`](#pac-reversibles-ou-climatisation-ou-équipements-commandables-à-travers-une-entité-climate)
- [La suite](#la-suite)
- [Appel à contribution](#appel-à-contribution)


## Nodon SIN-4-FP-21 ou assimilé (fil pilote)

Ce module permet de commander un radiateur avec un fil pilote. Il est visible sous _HA_ sous la forme d'une entité `select` qui permet de choisir le preset de chauffage à appliquer.

_VTherm_ va réguler la température en changeant de preset via les commandes personnalisées régulièrement jusqu'à ce que la consigne soit atteinte.

Pour que cela fonctionne, il faut le preset utiliser pour la commande de chauffage soit supérieur à la température maximale que vous aurez besoin (24° est une bonne valeur).

Pour l'intégrer dans _VTherm_ vous devez :
1. Créer un _VTherm_ de type `over_switch`. Cf. [création d'un _VTherm_](creation.md),
2. Lui donner des principaux attributs (nom, capteur de température de la pièce et capteur de température extérieure au minimium). Cf. [principaux attributs](base-attributes.md),
3. Lui donner un ou plusieurs équipements sous-jacents à contrôler. Le sous-jacent est ici l'entité `select` qui contrôle le Nodon. Cf. [sous-jacent](over-switch.md),
4. Lui donner des commandes d'allumage et extinction personnalisées (obligatoire pour le Nodon). Cf. [sous-jacent](over-switch.md#la-personnalisation-des-commandes). Les commandes personnalisées sont du type `select_option/option:<preset>` comme indiqué dans le lien.

A l'issue de ces 4 étapes vous avez un _VTherm_ opérationnel ultra simple qui contrôle votre Nodon ou assimilé.

## Heatzy ou eCosy ou assimilé (entité `climate`)

Ce module permet de commander un radiateur qui est visible sous _HA_ sous la forme d'une entité `climate` qui permet de choisir le preset de chauffage à appliquer ou le mode (Chauffe / Froid / éteint).

_VTherm_ va réguler la température en allumant / éteignant via les commandes personnalisées régulièrement l'équipement jusqu'à ce que la consigne soit atteinte.

Pour l'intégrer dans _VTherm_ vous devez :
1. Créer un _VTherm_ de type `over_switch`. Cf. [création d'un _VTherm_](creation.md),
2. Lui donner des principaux attributs (nom, capteur de température de la pièce et capteur de température extérieure au minimium). Cf. [principaux attributs](base-attributes.md),
3. Lui donner un ou plusieurs équipements sous-jacents à contrôler. Le sous-jacent est ici l'entité `climate` qui contrôle le Heatzy ou le eCosy. Cf. [sous-jacent](over-switch.md),
4. Lui donner des commandes d'allumage et extinction personnalisées (obligatoire). Cf. [sous-jacent](over-switch.md#la-personnalisation-des-commandes). Les commandes personnalisées sont du type `set_hvac_mode/hvac_mode:<mode>` ou `set_preset_mode/preset_mode:<preset>` comme indiqué dans le lien.

A l'issue de ces 4 étapes vous avez un _VTherm_ opérationnel ultra simple qui commande votre équipement Heatzy ou eCosy ou assimilé.

## Simple switch comme Aqara T1, Nous B2Z, Sonoff ZBMini, Sonoff POW, ...

Ce module permet de commander un radiateur contrôlé par un simple switch. Il est visible sous _HA_ sous la forme d'une entité `switch` qui permet d'allumer ou éteindre directement le radiateur.

_VTherm_ va réguler la température en allumant / éteignant régulièrement le `switch` jusqu'à ce que la consigne soit atteinte.

Pour l'intégrer dans _VTherm_ vous devez :
1. Créer un _VTherm_ de type `over_switch`. Cf. [création d'un _VTherm_](creation.md),
2. Lui donner des principaux attributs (nom, capteur de température de la pièce et capteur de température extérieure au minimium). Cf. [principaux attributs](base-attributes.md),
3. Lui donner un ou plusieurs équipements sous-jacents à contrôler. Le sous-jacent est ici l'entité `switch` qui contrôle le switch. Cf. [sous-jacent](over-switch.md)

A l'issue de ces 3 étapes vous avez un _VTherm_ opérationnel ultra simple qui contrôle votre `switch` ou assimilé.

## Sonoff TRVZB ou assimilé (TRV avec contrôle de la vanne)

Cet équipement de type _TRV_ contrôle l'ouverture d'une vanne qui laisse plus ou moins passer de l'eau chaude produit par une chaudière ou une PAC. Il est visible sous _HA_ sous la forme d'une entité de type `climate` et d'entités de type `number` qui vont permettre le contrôle de la vanne. Ces entités `number` peuvent être cachées et doivent être explicitement ajoutées dans certains cas.

Le _VTherm_ va moduler le taux d'ouverture de la vanne jusqu'à obtention de la température de consigne.

Pour l'intégrer dans _VTherm_ vous devez :
1. Créer un _VTherm_ de type `over_climate`. Cf. [création d'un _VTherm_](creation.md),
2. Lui donner des principaux attributs (nom, capteur de température de la pièce et capteur de température extérieure au minimium). Cf. [principaux attributs](base-attributes.md),
3. Lui donner un ou plusieurs équipements sous-jacents à contrôler. Le sous-jacent est ici l'entité `climate` qui contrôle le TRV. Cf. [sous-jacent](over-climate.md),
4. Spécifiez la régulation de type `Par contrôle direct de la vanne` uniquement. Laissez décochée l'option `Compenser la température interne du sous-jacent`. Cf. [sous-jacent](over-climate.md#lauto-régulation),
5. Lui donner les entités de type `number` nommées `opening_degree`, `closing_degree` et `calibration offset`. Ne pas renseigner l'entité `closing degree` Cf. [sous-jacent](over-switch.md),

Pour que cela fonctionne, il faut que le `closing degree` soit réglé au maximum (100%). Ne cocher pas tout de suite l'entité `Follow underlying temperature change` avant d'avoir bien vérifier que cette configuration de base fonctionne.

A l'issue de ces 5 étapes vous avez un _VTherm_ opérationnel ultra simple qui commande votre équipement Sonoff TRVZB ou assimilé.

## _PAC_ reversibles ou climatisation ou équipements commandables à travers une entité `climate`

Les _PAC_ ou assimilés sont visibles sous _HA_ sous la forme d'une entité `climate` qui permet de choisir le preset de chauffage à appliquer ou le mode (Chauffe / Froid / éteint).

_VTherm_ va réguler la température en commandant la consigne de l'équipement et son mode à l'aide de commandes envoyée à l'entité `climate` sous-jacente.

Pour l'intégrer dans _VTherm_ vous devez :
1. Créer un _VTherm_ de type `over_climate`. Cf. [création d'un _VTherm_](creation.md),
2. Lui donner des principaux attributs (nom, capteur de température de la pièce et capteur de température extérieure au minimium). Cf. [principaux attributs](base-attributes.md),
3. Lui donner un ou plusieurs équipements sous-jacents à contrôler. Le sous-jacent est ici l'entité `climate` qui contrôle la _PAC_ ou la clim... . Cf. [sous-jacent](over-climate.md),

A l'issue de ces 3 étapes vous avez un _VTherm_ opérationnel ultra simple qui commande votre _PAC_, climatisation ou assimilé. Pour aller plus loin, une auto-régulation peut êrte nécessaire en fonction du bon fonctionnement de votre équipement. L'auto-régulation consiste à envoyer des consignes légèrement modifiées par _VTherm_ pour forcer l'équipement à chauffer plus ou moins jusqu'à ce que la consigne soit atteinte. L'auto-régulation est détaillée ici : [auto-régulation](self-regulation.md).

# La suite

Uen fois créé, vous devez paramétrer les températures des presets. Cf. [presets](feature-presets.md) pour avoir une configuration minimale.
Vous pouvez aussi (facultatif mais conseillé) installer la carte dédiée pour vos dashboard. (Cf. [VTHerm UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card))

Une fois cette configuration minimale opérationnelle - et seulement lorsque cette configuration minimale fonctionne -, vous pourrez ajouter des fonctions supplémentaires comme la détection de présence pour éviter de chauffer lorsqu'il n'y a personne. Ajoutez les une par une, vérifiez à chaque nouvelle fonction que _VTherm_ réagit correctement avant de passer à la suivante.

Ensuite vous pourrez ajouter une configuration centrale pour mettre en commum des réglages entre tous les _VTherm_, paraméter le mode central permettant de contrôler tous les _VTherms_ d'un coup ([la configuration centralisée](feature-central-mode.md)), ajouter un éventuel contrôle d'une chaudière centrale ([la chaudière centrale](feature-central-boiler.md)). Cette liste est non exhaustive, merci de consulter le sommaire pour avoir la liste de toutes les fonctions de _VTherm_.

# Appel à contribution

Cette page ne demande qu'à se compléter. N'hésitez pas à proposer vos équipements et la configuration minimale.

