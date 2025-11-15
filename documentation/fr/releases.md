# Note de versions

![Nouveau](images/new-icon.png)
>
> * **Release 7.4**:
>
> - Ajout de seuils permettant d'activer ou de désactiver l'algorithme TPI lorsque la température dépasse la consigne. Cela permet d'éviter les allumages/extinction d'un radiateur sur des faibles durées. Idéal pour les poeles à bois qui mettent beaucoup de temps à monter en température. Cf. [TPI](documentation/fr/algorithms.md#lalgorithme-tpi),
> - Ajout d'un mode sleep pour les VTherm de type `over_climate` avec régulation par contrôle direct de la vanne. Ce mode permet de mettre le thermostat en mode éteint mais avec la vanne 100% ouverte. C'est utile pour les longues périodes sans utiisation du chauffage si la chaudière fait circuler un peu d'eau de temps en temps. Attention, vous devez mettre à jour la VTHerm UI Card pour visualiser ce nouveau mode. Cf. [VTherm UI Card](documentation/fr/additions.md#versatile-thermostat-ui-card).

> * **Release 7.2**:
>
> - Prise en compte native des équipements pilotable via une entité de type `select` (ou `input_select`) ou `climate` pour des _VTherm_ de type `over_switch`. Cette évolution rend obsolète, la création de switch virtuels pour l'intégration des Nodon ou Heaty ou eCosy ... etc. Plus d'informations [ici](documentation/fr/over-switch.md#la-personnalisation-des-commandes).
>
> - Lien vers la documentation : cette version 7.2 expérimente des liens vers la documentation depuis les pages de configuration. Le lien est accessible via l'icone [![?](https://img.icons8.com/color/18/help.png)](https://github.com/jmcollin78/versatile_thermostat/blob/main/documentation/fr/over-switch.md#configuration). Elle est expérimentée sur certaines pages de la configuration.
>
> - Ajout d'un chapitre dans la documentation nommé 'Démarrage rapide' permettant de mettre en oeuvre rapidement un _VTherm_ en fonction de votre équipement. La page est [ici](documentation/quick-start.md)

> * **Release 7.1**:
>   - Refonte de la fonction de délestage (gestion de la puissance). Le délestage est maintenant géré de façon centralisé (auparavent chaque _VTherm_ était autonome). Cela permet une gestion bien plus efficace et de prioriser le délestage sur les équipements qui sont proches de la consigne. Attention, vous devez impérativement avoir une configuration centralisée avec gestion de la puissance pour que cela fonctionne. Plus d'infos [ici](./feature-power.md)

> * **Release 6.8**:
>   - Ajout d'une nouvelle méthode de régulation pour les Versatile Thermostat de type `over_climate`. Cette méthode nommée 'Contrôle direct de la vanne' permet de contrôler directement la vanne d'un TRV et éventuellement un décalage pour calibrer le thermomètre interne de votre TRV. Cette nouvelle méthode a été testée avec des Sonoff TRVZB et généralisée pour d'autre type de TRV pour lesquels la vanne est directement commandable via des entités de type `number`. Plus d'informations [ici](over-climate.md#lauto-régulation) et [ici](self-regulation.md#auto-régulation-par-contrôle-direct-de-la-vanne).

## **Release 6.5** :
  - Ajout d'une nouvelle fonction permettant l'arrêt et la relance automatique d'un VTherm `over_climate` [585](https://github.com/jmcollin78/versatile_thermostat/issues/585)
  - Amélioration de la gestion des ouvertures au démarrage. Permet de mémoriser et de recalculer l'état d'une ouverture au redémarage de Home Assistant [504](https://github.com/jmcollin78/versatile_thermostat/issues/504)

## **Release 6.0** :
  - Ajout d'entités du domaine `number` permettant de configurer les températures des presets [354](https://github.com/jmcollin78/versatile_thermostat/issues/354)
  - Refonte complète du menu de configuration pour supprimer les températures et utililsation d'un menu au lieu d'un tunnel de configuration [354](https://github.com/jmcollin78/versatile_thermostat/issues/354)

## **Release 5.4** :
  - Ajout du pas de température [#311](https://github.com/jmcollin78/versatile_thermostat/issues/311),
  - ajout de seuils de régulation pour les `over_valve` pour éviter de trop vider la batterie des TRV [#338](https://github.com/jmcollin78/versatile_thermostat/issues/338),
  - ajout d'une option permettant d'utiliser la température interne d'un TRV pour forcer l' auto-régulation [#348](https://github.com/jmcollin78/versatile_thermostat/issues/348),
  - ajout d'une fonction de keep-alive pour les VTherm `over_switch` [#345](https://github.com/jmcollin78/versatile_thermostat/issues/345)

<details>
<summary>Autres versions plus anciennes</summary>

> * **Release 5.3** : Ajout d'une fonction de pilotage d'une chaudière centrale [#234](https://github.com/jmcollin78/versatile_thermostat/issues/234) - plus d'infos ici: [Le contrôle d'une chaudière centrale](#le-contrôle-dune-chaudière-centrale). Ajout de la possibilité de désactiver le mode sécurité pour le thermomètre extérieur [#343](https://github.com/jmcollin78/versatile_thermostat/issues/343)
> * **Release 5.2** : Ajout d'un `central_mode` permettant de piloter tous les _VTherm_ de façon centralisée [#158](https://github.com/jmcollin78/versatile_thermostat/issues/158).
> * **Release 5.1** : Limitation des valeurs envoyées aux vannes et au température envoyées au climate sous-jacent.
> * **Release 5.0** : Ajout d'une configuration centrale permettant de mettre en commun les attributs qui peuvent l'être [#239](https://github.com/jmcollin78/versatile_thermostat/issues/239).
> * **Release 4.3** : Ajout d'un mode auto-fan pour le type `over_climate` permettant d'activer la ventilation si l'écart de température est important [#223](https://github.com/jmcollin78/versatile_thermostat/issues/223).
> * **Release 4.2** : Le calcul de la pente de la courbe de température se fait maintenant en °/heure et non plus en °/min [#242](https://github.com/jmcollin78/versatile_thermostat/issues/242). Correction de la détection automatique des ouvertures par l'ajout d'un lissage de la courbe de température .
> * **Release 4.1** : Ajout d'un mode de régulation **Expert** dans lequel l'utilisateur peut spécifier ses propres paramètres d'auto-régulation au lieu d'utiliser les pre-programmés [#194](https://github.com/jmcollin78/versatile_thermostat/issues/194).
> * **Release 4.0** : Ajout de la prise en charge de la **Versatile Thermostat UI Card**. Voir [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card). Ajout d'un mode de régulation **Slow** pour les appareils de chauffage à latence lente [#168](https://github.com/jmcollin78/versatile_thermostat/issues/168). Changement de la façon dont **la puissance est calculée** dans le cas de VTherm avec des équipements multi-sous-jacents [#146](https://github.com/jmcollin78/versatile_thermostat/issues/146). Ajout de la prise en charge de AC et Heat pour VTherm via un interrupteur également [#144](https://github.com/jmcollin78/versatile_thermostat/pull/144)
> * **Release 3.8**: Ajout d'une **fonction d'auto-régulation** pour les thermostats `over climate` dont la régulation est faite par le climate sous-jacent. Cf. [L'auto-régulation](#lauto-régulation) et [#129](https://github.com/jmcollin78/versatile_thermostat/issues/129). Ajout de la **possibilité d'inverser la commande** pour un thermostat `over switch` pour adresser les installations avec fil pilote et diode [#124](https://github.com/jmcollin78/versatile_thermostat/issues/124).
> * **Release 3.7**: Ajout du type de **Versatile Thermostat `over valve`** pour piloter une vanne TRV directement ou tout autre équipement type gradateur pour le chauffage. La régulation se fait alors directement en agissant sur le pourcentage d'ouverture de l'entité sous-jacente : 0 la vanne est coupée, 100 : la vanne est ouverte à fond. Cf. [#131](https://github.com/jmcollin78/versatile_thermostat/issues/131). Ajout d'une fonction permettant le bypass de la détection d'ouverture [#138](https://github.com/jmcollin78/versatile_thermostat/issues/138). Ajout de la langue Slovaque
> * **Release 3.6**: Ajout du paramètre `motion_off_delay` pour améliorer la gestion de des mouvements [#116](https://github.com/jmcollin78/versatile_thermostat/issues/116), [#128](https://github.com/jmcollin78/versatile_thermostat/issues/128). Ajout du mode AC (air conditionné) pour un VTherm over switch. Préparation du projet Github pour faciliter les contributions [#127](https://github.com/jmcollin78/versatile_thermostat/issues/127)
> * **Release 3.5**: Plusieurs thermostats sont possibles en "thermostat over climate" mode [#113](https://github.com/jmcollin78/versatile_thermostat/issues/113)
> * **Release 3.4**: bug fix et exposition des preset temperatures pour le mode AC [#103](https://github.com/jmcollin78/versatile_thermostat/issues/103)
> * **Release 3.3**: ajout du mode Air Conditionné (AC). Cette fonction vous permet d'utiliser le mode AC de votre thermostat sous-jacent. Pour l'utiliser, vous devez cocher l'option "Uitliser le mode AC" et définir les valeurs de température pour les presets et pour les presets en cas d'absence
> * **Release 3.2** : ajout de la possibilité de commander plusieurs switch à partir du même thermostat. Dans ce mode, les switchs sont déclenchés avec un délai pour minimiser la puissance nécessaire à un instant (on minimise les périodes de recouvrement). Voir [Configuration](#sélectionnez-des-entités-pilotées)
> * **Release 3.1** : ajout d'une détection de fenêtres/portes ouvertes par chute de température. Cette nouvelle fonction permet de stopper automatiquement un radiateur lorsque la température chute brutalement. Voir [Le mode auto](#le-mode-auto)
> * **Release majeure 3.0** : ajout d'un équipement thermostat et de capteurs (binaires et non binaires) associés. Beaucoup plus proche de la philosphie Home Assistant, vous avez maintenant un accès direct à l'énergie consommée par le radiateur piloté par le thermostat et à plein d'autres capteurs qui seront utiles dans vos automatisations et dashboard.
> * **release 2.3** : ajout de la mesure de puissance et d'énergie du radiateur piloté par le thermostat.
> * **release 2.2** : ajout de fonction de sécurité permettant de ne pas laisser éternellement en chauffe un radiateur en cas de panne du thermomètre
> * **release majeure 2.0** : ajout du thermostat "over climate" permettant de transformer n'importe quel thermostat en Versatile Thermostat et lui ajouter toutes les fonctions de ce dernier.
</details>

> ![Astuce](images/tips.png) _*Notes*_
>
> Toutes les notes de versions complètes sont disponibles sur le [github de l'intégration](https://github.com/jmcollin78/versatile_thermostat/releases/).