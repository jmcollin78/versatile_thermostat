# Note de versions

## Release 9.3 - version stable
> 1. **Diagnostic des vannes bloquées** : Amélioration majeure de la détection d'anomalie de chauffe. Lorsqu'une anomalie est détectée sur les VTherms de type `over_climate_valve`, le thermostat diagnostique maintenant si le problème est causé par une vanne TRV bloquée (bloquée ouverte ou fermée) en comparant l'état commandé avec l'état réel. Cette information - `root_cause` - est envoyée dans l'événement d'anomalie, vous permettant de prendre les actions appropriées (notification, relance de la vanne, etc.). Plus d'informations [ici](documentation/fr/feature-heating-failure-detection.md),
> 2. **Relockage automatique du verrou** : Ajout du paramètre `auto_relock_sec` à la fonctionnalité de verrouillage. Lorsque configuré, le thermostat se relockera automatiquement après le délai spécifié (en secondes) suivant un déverrouillage. Vous pouvez complètement désactiver cette fonctionnalité en le mettant à 0. Par défaut, le relockage automatique est configuré à 30 secondes pour améliorer la sécurité. Plus d'informations [ici](documentation/fr/feature-lock.md),
> 3. **Re-émission des commandes** : Nouvelle fonctionnalité permettant de détecter et corriger automatiquement les discrepancies entre l'état désiré du thermostat et l'état réel des équipements sous-jacents. Si une commande n'a pas été correctement appliquée à l'équipement, elle est renvoyée. Cela améliore la fiabilité du système en les environnements instables ou avec des équipements non fiables. Plus d'informations [ici](documentation/fr/feature-advanced.md),
> 4. **Restoration du preset temporisé après redémarrage** : Le preset temporisé configuré est maintenant correctement restauré après un redémarrage du thermostat ou d'Home Assistant. Ce preset continue de fonctionner normalement après le redémarrage. Plus d'informations [ici](documentation/fr/feature-timed-preset.md),
> 5. **Précision accrue du contrôle de puissance** : Le seuil d'activation de la chaudière (`power_activation_threshold`) accepte maintenant des valeurs décimales (0.1, 0.5, etc.) pour un contrôle plus fin de la puissance d'activation. Cela offre une meilleure flexibilité pour optimiser votre consommation d'énergie. Plus d'informations [ici](documentation/fr/feature-power.md),
> 6. **Améliorations de disponibilité des capteurs** : Meilleur support de la détermination de la disponibilité des capteurs de température en utilisant la métadonnée `last_updated` de Home Assistant, améliorant ainsi la détection de la perte de signal des capteurs,

## Release 9.2
> 1. Nouvelle façon de gérer les cycles de chauffe/arrêt pour les VTherm `over_switch`. L'algorithme actuel a une dérive dans le temps et les premiers cycles ne sont pas optimum. Ca perturbe le TPI et notamment l'auto-TPI. Le nouveau `Cycle Scheduler` résoud ces difficultés. Cette modification est totalement transparente pour vous,
> 2. Un collecteur de logs. Vos demandes de support échouent souvent sur votre capacité à fournir des logs, sur la bonne période, ciblé sur le thermostat en erreur et au bon niveau de log. C'est particulièrement le cas des bugs difficilement reproductible. Le collecteur de logs vise à résoudre cette difficulté. Il collecte les logs pour vous en arrière plan dans le niveau le plus fin et une action (anciennement service) permet de les extraire dans un fichier. Vous pouvez alors les télécharger pour les joindre à votre demande de support. L'analyseur de logs associé au site web - lancé en 9.1 cf. ci-dessous - s'adapte pour être capable de digérer ces logs. Plus d'informations sur le collecteur de logs [ici](documentation/fr/feature-logs-collector.md),
> 3. stabilisation de la 9.x. La version majeure 9 a amené beaucoup de changement qui ont générés quelques anomalies. Cette version apporte les dernières corrections liées à cette version 9.

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

## Release 8.4
> 1. ajout de l'auto TPI (expérimental). Cette nouvelle fonction permet de calculer automatiquement les meilleurs coefficients pour l'algorithme du TPI. Plus d'informations [ici](documentation/fr/feature-autotpi.md)
> 2. ajout d'une fonction de synchronisation des températures d'un équipement piloté en mode `over_climate`. Suivant, les fonctionnalités de votre équipement, _VTherm_ peut contrôler une entité de calibrage de l'offset ou directement une entité de température externe. Plus d'informations [ici](documentation/fr/feature-sync_device_temp.md)
> 3. ajout d'une fonction nommée preset temporisé permettant de sélectionner un preset pendant un temps donné et revenir au précédent une fois le délai expiré. La fonction est décrite [ici](documentation/fr/feature-timed-preset.md).

## Release 8.3
> 1. ajout d'un délai configurable avant l'activation de la chaudière centrale,
> 2. ajout d'un déclenchement de la chaudière centrale si le total de la puissance activée dépasse un seuil. Pour faire marcher cette fonction il faut :
> - configurer le seuil de puissance qui va déclencher la chaudière. C'est une nouvelle entité qui est disponible dans l'appareil 'configuration centrale',
> - configurez les puissances des Vtherms. Ca se trouve dans la première page de configuration des VTherms,
> - cochez la case `Utilisé par la chaudière centrale`.
>
> A chaque fois que le VTherm sera activé, sa puissance configurée viendra s'ajoutée et si le seuil est dépassé, la chaudière centrale sera activée après le délai configuré en 1.
>
> L'ancien compteur du nombres de devices activés et son seuil existent toujours. Pour désactiver l'un des seuils (le seuil de puissance ou le seuil du nombre de devices activés), il faut le mettre à zéro. Dès que l'un des 2 seuils différents de zéro est dépassé, la chaudière est activée. C'est donc un "ou logique" entre les 2 seuils qui est appliqué.
>
> Plus d'informations [ici](documentation/fr/feature-central-boiler.md).

## Release 8.2
- Ajout d'une fonction permettant de verrouiller / déverouiller un _VTherm_ avec potentiellement un code. Plus d'informations [ici](documentation/fr/feature-lock.md)

## Release 8.1
- Pour un VTherm de type `over_climate` avec régulation par contrôle direct de la vanne, deux nouveaux paramètres permettant un contrôle beaucoup plus fin du minimum d'ouverture de la vanne ont été ajoutés au paramètre existant `minimum_opening_degrees`. Les paramètres sont maintenant :
  - `opening_threshold` : l'ouverture minimale de la vanne en dessous de laquelle la vanne doit être considérée comme fermée, et par conséquent, le paramètre 'max_closing_degree' s'applique,
  - `max_closing_degree` : le pourcentage de fermeture maximum absolu. La vanne ne se fermera jamais plus que ce qui est indiqué dans cette valeur. Si vous voulez autoriser la fermeture complète de la vanne, alors laissez ce paramètre sur 100,
  - `minimum_opening_degrees` : le pourcentage d'ouverture minimal lorsque le `opening_threshold` est dépassé et que le VTherm doit chauffer. Ce champ est personnalisable par vanne dans le cas d'un VTherm avec plusieurs vannes. Vous spécifiez la liste des ouvertures minimales séparées par des ','. La valeur par défaut est 0. Exemple : '20, 25, 30'. Lorsque la chauffe démarre (ie l'ouverture demandée est supérieure à `opening_threshold`), la vanne s'ouvrira avec une valeur supérieure ou égale à celle-ci et continuera d'augmenter régulièrement si nécessaire.

Si on représente l'ouverture demandée par l'algorithme TPI en abscisse et l'ouverture réellement envoyée sur la vanne en ordonnée, on obtient cette courbe :

![alt text](images/opening-degree-graph.png)

Cette évolution a été largement débattue [ici](https://github.com/jmcollin78/versatile_thermostat/issues/1220).

## Release 8.0
Cette version est une version majeure. Elle réécrit une bonne partie des mécanismes internes du Versatile Thermostat en introduisant plusieurs nouveautés:
  1. _état souhaité / état courant_ : maintenant VTherm a 2 états. L'état souhaité est l'état demandé par l'utilisateur (ou le Scheduler). L'état courant est l'état couramment appliqué au VTherm. Ce dernier dépend des différentes fonctions de VTherm. Par exemple, l'utilisateur peut demander (état souhaité) d'avoir le chauffage allumé avec le preset Comfort mais comme la fenêtre a été détectée ouverte le VTherm est en fait éteint. Cette double gestion permet de toujours conservé la demande de l'utilisateur et d'appliquer le résultat des différentes fonctions sur cette demande de l'utilisateur pour avoir l'état courant. Cela permet de mieux gérer les cas où plusieurs fonctions veulent agir sur l'état du VTherm (ouverture d'une fenêtre et délestage par exemple). Cela assure aussi un retour à la demande initiale de l'utilisateur lorsque plus aucune détection n'est en cours,
  2. _filtrage temporel_ : le fonctionnement du filtrage temporel a été revu. Le filtrage temporel permet de ne pas envoyer trop de commandes à un équipement contrôlé pour éviter de consommer trop de batterie (TRV à pile par exemple), de changer trop fréquement de consignes (pompe à chaleur, poele à pellets, chauffage au sol, ...). Le nouveau fonctionnement est maintenant le suivant : les demandes explicites de l'utilisateur (ou Scheduler) sont toujours immédiatement prises en compte. Elles ne sont pas filtrées. Seules les changements liés à des conditions extérieures (températures de la pièce par exemple) sont potentiellement filtrées. Le filtrage consiste à renvoyer la commande souhaitée plus tard et non pas à ignorer la commande comme c'était le cas précédemment. Le paramètre `auto_regulation_dtemp` permet de régler le délai,
  3. _amelioration du hvac_action_ : le `hvac_action` reflète l'état courant d'activation de l'équipement commandé. Pour un type `over_switch` il reflète l'état d'activation du switch, pour un `over_valve` ou une régulation par vanne, il est actif lorsque l'ouverture de la vanne est supérieur à l'ouverture minimale de la vanne (ou 0 si non configurée), pour un `over_climate` il reflète le `hvac_action`du `climate` sous-jacent si il est disponible ou une simulation sinon.
  4. _attributs personnalisés_ : l'organisation des attributs personnalisés accessibles dans Outils de développement / Etat, ont été réorganisés en section dépendant du type de VTherm et de chaque fonction activée. Plus d'informations [ici](documentation/fr/reference.md#attributs-personnalisés).
  5. _délestage_ : l'algorithme de délestage prend maintenant en compte l'arrêt d'un équipement entre deux mesures de la puissance consommée du logement. Supposons que vous ayez une remontée de la puissance consommée toutes les 5 minutes. Si entre 2 mesures un radiateur est éteint alors l'allumage d'un nouveau pourra être autorisé. Avant, seuls les allumages étaient pris en compte entre 2 mesures. Comme avant, la prochaine remontée de la puissance consommée viendra éventuellement délester plus ou moins.
  6. _auto-start/stop_ : l'auto-start/stop n'est utile que pour les Vtherm de type `over_climate` sans contrôle direct de la vanne. L'option a été supprimée pour les autres types de VTherm.
  7. _VTherm UI Card_ : toutes ces modifications ont permis une évolution majeure de la [VTherm UI Card](documentation/fr/additions.md#versatile-thermostat-ui-card) pour y intégrer des messages expliquant l'état courant (pourquoi mon VTherm à cette température cible ?) et si un filtrage temporel est en cours - donc la mise à jour de l'état du sous-jacent a été retardée.
  8. _amélioration des logs_ : les logs ont été améliorés pour simplifier le debug. Des logs de la forme `--------------------> NEW EVENT: VersatileThermostat-Inversed ...` informe d'un évènement venant impacter l'état du VTherm.

⚠️ **Attention**

> Cette version majeure embarque des changements incompatibles avec la précédente:
> - `versatile_thermostat_security_event` a été renommé en `versatile_thermostat_safety_event`. Si vos automatisations utiles cet évènement, vous devez les mettre à jour,
> - les attributs personnalisés ont été réorganisés. Vous devez mettre à jour vos automisations ou template Jinja qui les utiliseraient,
> - la [VTherm UI Card](documentation/fr/additions.md#versatile-thermostat-ui-card) doit être mise à jour au minimum en V2.0 pour être compatible,
>
> **Malgré les 342 tests automatisés de cette intégration et le soin apporté à cette version majeure, je ne peux garantir que son installation ne viendra pas perturber les états de vos VTherm. Pour chaque VTherm vous devez vérifier le preset, le hvac_mode et éventuellement la température de consigne du VTherm après installation.**


## Release 7.4

- Ajout de seuils permettant d'activer ou de désactiver l'algorithme TPI lorsque la température dépasse la consigne. Cela permet d'éviter les allumages/extinction d'un radiateur sur des faibles durées. Idéal pour les poeles à bois qui mettent beaucoup de temps à monter en température. Cf. [TPI](documentation/fr/algorithms.md#lalgorithme-tpi),
- Ajout d'un mode sleep pour les VTherm de type `over_climate` avec régulation par contrôle direct de la vanne. Ce mode permet de mettre le thermostat en mode éteint mais avec la vanne 100% ouverte. C'est utile pour les longues périodes sans utiisation du chauffage si la chaudière fait circuler un peu d'eau de temps en temps. Attention, vous devez mettre à jour la VTHerm UI Card pour visualiser ce nouveau mode. Cf. [VTherm UI Card](documentation/fr/additions.md#versatile-thermostat-ui-card).

## Release 7.2

  - Prise en compte native des équipements pilotable via une entité de type `select` (ou `input_select`) ou `climate` pour des _VTherm_ de type `over_switch`. Cette évolution rend obsolète, la création de switch virtuels pour l'intégration des Nodon ou Heaty ou eCosy ... etc. Plus d'informations [ici](documentation/fr/over-switch.md#la-personnalisation-des-commandes).

  - Lien vers la documentation : cette version 7.2 expérimente des liens vers la documentation depuis les pages de configuration. Le lien est accessible via l'icone [![?](https://img.icons8.com/color/18/help.png)](https://github.com/jmcollin78/versatile_thermostat/blob/main/documentation/fr/over-switch.md#configuration). Elle est expérimentée sur certaines pages de la configuration.

  - Ajout d'un chapitre dans la documentation nommé 'Démarrage rapide' permettant de mettre en oeuvre rapidement un _VTherm_ en fonction de votre équipement. La page est [ici](documentation/quick-start.md)

## Release 7.1

  - Refonte de la fonction de délestage (gestion de la puissance). Le délestage est maintenant géré de façon centralisé (auparavent chaque _VTherm_ était autonome). Cela permet une gestion bien plus efficace et de prioriser le délestage sur les équipements qui sont proches de la consigne. Attention, vous devez impérativement avoir une configuration centralisée avec gestion de la puissance pour que cela fonctionne. Plus d'infos [ici](./feature-power.md)

## Release 6.8

  - Ajout d'une nouvelle méthode de régulation pour les Versatile Thermostat de type `over_climate`. Cette méthode nommée 'Contrôle direct de la vanne' permet de contrôler directement la vanne d'un TRV et éventuellement un décalage pour calibrer le thermomètre interne de votre TRV. Cette nouvelle méthode a été testée avec des Sonoff TRVZB et généralisée pour d'autre type de TRV pour lesquels la vanne est directement commandable via des entités de type `number`. Plus d'informations [ici](over-climate.md#lauto-régulation) et [ici](self-regulation.md#auto-régulation-par-contrôle-direct-de-la-vanne).

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