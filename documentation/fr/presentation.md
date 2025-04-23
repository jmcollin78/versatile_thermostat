# Quand l'utiliser et ne pas l'utiliser
Ce thermostat peut piloter 3 types d'équipements :
1. un radiateur qui ne fonctionne qu'en mode marche/arrêt (nommé ```thermostat_over_switch```). La configuration minimale nécessaire pour utiliser ce type thermostat est :
   1. un équipement comme un radiateur (un ```switch``` ou équivalent),
   2. une sonde de température pour la pièce (ou un input_number),
   3. un capteur de température externe (pensez à l'intégration météo si vous n'en avez pas)
2. un autre thermostat qui a ses propres modes de fonctionnement (nommé ```thermostat_over_climate```). Pour ce type de thermostat la configuration minimale nécessite :
   1. un équipement - comme une climatisation, une vanne thermostatique - qui est pilotée par sa propre entity de type ```climate```,
3. un équipement qui peut prendre une valeur de 0 à 100% (nommée ```thermostat_over_valve```). A 0 le chauffage est coupé, 100% il est ouvert à fond. Ce type permet de piloter une vanne thermostatique (cf. TRV Shelly) qui expose une entité de type `number.` permetttant de piloter directement l'ouverture de la vanne. Versatile Thermostat régule la température de la pièce en jouant sur le pourcentage d'ouverture, à l'aide des capteurs de température intérieur et extérieur en utilisant l'algorithme TPI décrit ci-dessous.

Le type `over_climate` vous permet d'ajouter à votre équipement existant toutes les fonctionnalités apportées par VersatileThermostat. L'entité `climate` VersatileThermostat contrôlera votre entité climate sous-jacente, l'éteindra si les fenêtres sont ouvertes, la fera passer en mode Eco si personne n'est présent, etc. Voir [ici] (#pourquoi-un-nouveau-thermostat-implémentation). Pour ce type de thermostat, tous les cycles de chauffage sont contrôlés par l'entité climate sous-jacente et non par le thermostat polyvalent lui-même. Une fonction facultative d'auto-régulation permet au Versatile Thermostat d'ajuster la température donnée en consigne au sous-jacent afin d'atteindre la consigne.

Les installations avec fil pilote et diode d'activation bénéficie d'une option qui permet d'inverser la commande on/off du radiateur sous-jacent. Pour cela, utilisez le type `over switch` et cochez l'option d'inversion de la commande.

# Pourquoi une nouvelle implémentation du thermostat ?

Ce composant nommé __Versatile thermostat__ gère les cas d'utilisation suivants :
- Configuration via l'interface graphique d'intégration standard (à l'aide du flux Config Entry),
- Utilisations complètes du **mode préréglages**,
- Désactiver le mode préréglé lorsque la température est **définie manuellement** sur un thermostat,
- Éteindre/allumer un thermostat ou changer de preset lorsqu'une **porte ou des fenêtres sont ouvertes/fermées** après un certain délai,
- Changer de preset lorsqu'une **activité est détectée** ou non dans une pièce pendant un temps défini,
- Utiliser un algorithme **TPI (Time Proportional Interval)** grâce à l'algorithme [[Argonaute](https://forum.hacf.fr/u/argonaute/summary)] ,
- Ajouter une **gestion de délestage** ou une régulation pour ne pas dépasser une puissance totale définie. Lorsque la puissance maximale est dépassée, un préréglage caché de « puissance » est défini sur l'entité climatique. Lorsque la puissance passe en dessous du maximum, le préréglage précédent est restauré.
- La **gestion de la présence à domicile**. Cette fonctionnalité vous permet de modifier dynamiquement la température du préréglage en tenant compte d'un capteur de présence de votre maison.
- Des **actions pour interagir avec le thermostat** à partir d'autres intégrations : vous pouvez forcer la présence / la non-présence à l'aide d'un service, et vous pouvez modifier dynamiquement la température des préréglages et changer les paramètres de sécurité.
- Ajouter des capteurs pour voir les états internes du thermostat,
- Contrôle centralisé de tous les Versatile Thermostat pour les stopper tous, les passer tous en hors-gel, les forcer en mode Chauffage (l'hiver), les forcer en mode Climatisation (l'été).
- Contrôle d'une chaudière centrale et des VTherm qui doivent contrôler cette chaudière.
- Un arrêt démarrage automatique basé sur une prévision d'usage pour les `over_climate`.

Toutes ces fonctions sont configurables de façon centralisée ou individuelle en fonction de vos besoins.

# Materiels

Pour faire fonctionner _VTherm_ vous aurez besoin de matériels. La liste ci-dessous est non exhaustive mais contient les matériels les plus utilisés qui sont totalement compatibles avec Home Assistant et _Vtherm_. Il s'agit de liens affiliés vers la boutique partenaire [Domadoo](https://www.domadoo.fr/fr/?domid=97), ce qui me permet de profiter d'un petit pourcentage si vous passez par ces liens pour acheter. Commander avec [Domadoo](https://www.domadoo.fr/fr/?domid=97) vous permettra d'avoir des prix compétitifs, une garantie de retour et un délai de livraison très court comparable à d'autres grandes enseignes en ligne. Leur note de 4,8/5 est là pour en témoigner.

⭐ : le plus utilisé et donc le meilleur choix.

## Thermomètres
Indispensables dans une installation _VTherm_ une mesure de température externalisée de l'appareil et placé où là où vous vivez, vous assure une température fiable, confortable et stable.

- [⭐ Sonoff SNZB Zigbee](https://www.domadoo.fr/fr/suivi-energie/6614-sonoff-capteur-de-temperature-et-d-humidite-zigbee-30-avec-ecran-6920075740004.html??domid=97)
- [ Neo Tuya Wifi](https://www.domadoo.fr/fr/produits-compatibles-jeedom/7564-neo-capteur-de-temperature-et-humidite-zigbee-30-tuya.html?domid=97)

## Commutateurs (switchs)
Pour commander un radiateur électrique directement. Utilisable avec les _VTherm_ [`over_switch`](over-switch.md) :

- [⭐ Switch de puissance 25A Sonoff Wifi](https://www.domadoo.fr/fr/peripheriques/5853-sonoff-commutateur-intelligent-wifi-haute-puissance-25a-6920075776768.html?domid=97)
- [⭐ Nodon SIN-4-1-20 Zigbee](https://www.domadoo.fr/fr/peripheriques/5688-nodon-micromodule-commutateur-multifonctions-zigbee-16a-3700313925188.html?domid=97)
- [Sonoff 4 canaux Wifi](https://www.domadoo.fr/fr/peripheriques/5279-sonoff-commutateur-intelligent-wifi-433-mhz-4-canaux-6920075775815.html?domid=97)
- [Prise intelligente pour petit équipements de chauffage Zigbee](https://www.domadoo.fr/fr/peripheriques/5880-sonoff-prise-intelligente-16a-zigbee-30-version-fr.html?domid=97)

## Switchs avec fil pilote
Pour commander un radiateur électrique équipé d'un fil pilote directement. Utilisable avec les _VTherm_ [`over_switch`](over-switch.md) et la [personnalisation des commandes](over-switch.md#la-personnalisation-des-commandes) :

- [⭐ Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6828-nodon-module-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)
- [⭐ 4 x Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7050-nodon-pack-4x-modules-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)


## Vannes thermostatiques
Pour contrôler un radiateur à eau. Fonctionne avec un _VTherm_ [`over_valve`](over-valve.md) ou [`over_climate` avec contrôle direct de la vanne](over-climate.md#thermostat-de-type-over_climate) :

- [⭐ Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6776-sonoff-tete-thermostatique-connectee-zigbee-30.html?domid=97) avec [`over_climate` avec contrôle direct de la vanne](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 2 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7477-sonoff-pack-de-2x-tete-thermostatique-connectee-zigbee-30.html?domid=97) avec [`over_climate` avec contrôle direct de la vanne](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 4 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7478-sonoff-pack-de-4x-tete-thermostatique-connectee-zigbee-30.html?domid=97) avec [`over_climate` avec contrôle direct de la vanne](over-climate.md#thermostat-de-type-over_climate),
- [Shelly BLU TRV BLE](https://www.domadoo.fr/fr/black-friday-domotique/7567-shelly-robinet-thermostatique-de-radiateur-a-commande-bluetooth-shelly-blu-trv-3800235264980.html?domid=97) avec [`over_valve`](over-valve.md),
- [Moes TRV Zigbee](https://www.domadoo.fr/fr/peripheriques/5783-moes-tete-thermostatique-intelligente-zigbee-30-brt-100-trv-blanc.html?domid=97) avec [`over_climate` (sans contrôle direct de la vanne)](over-climate.md#thermostat-de-type-over_climate)
- [Schneider Wiser TRV Zigbee](https://www.domadoo.fr/fr/controle-chauffage-clim/5497-schneider-electric-tete-de-vanne-thermostatique-connectee-zigbee-3606489582821.html?domid=97) avec [`over_climate` (sans contrôle direct de la vanne)](over-climate.md#thermostat-de-type-over_climate)

## Incompatibilités
Certains thermostat de type TRV sont réputés incompatibles avec le Versatile Thermostat. C'est le cas des vannes suivantes :
1. les vannes POPP de Danfoss avec retour de température. Il est impossible d'éteindre cette vanne et elle s'auto-régule d'elle-même causant des conflits avec le _VTherm_,
2. Les thermostats « Homematic » (et éventuellement Homematic IP) sont connus pour rencontrer des problèmes avec le Versatile Thermostat en raison des limitations du protocole RF sous-jacent. Ce problème se produit particulièrement lorsque vous essayez de contrôler plusieurs thermostats Homematic à la fois dans une seule instance de VTherm. Afin de réduire la charge du cycle de service, vous pouvez par ex. regroupez les thermostats avec des procédures spécifiques à Homematic (par exemple en utilisant un thermostat mural) et laissez Versatile Thermostat contrôler uniquement le thermostat mural directement. Une autre option consiste à contrôler un seul thermostat et à propager les changements de mode CVC et de température par un automatisme,
3. les thermostats de type Heatzy qui ne supportent pas les commandes de type set_temperature
4. les thermostats de type Rointe ont tendance a se réveiller tout seul. Le reste fonctionne normalement.
5. les TRV de type Aqara SRTS-A01 et MOES TV01-ZB qui n'ont pas le retour d'état `hvac_action` permettant de savoir si elle chauffe ou pas. Donc les retours d'état sont faussés, le reste à l'air fonctionnel.
6. La clim Airwell avec l'intégration "Midea AC LAN". Si 2 commandes de VTherm sont trop rapprochées, la clim s'arrête d'elle même.
7. Les climates basés sur l'intégration Overkiz ne fonctionnent pas. Il parait impossible d'éteindre ni même de changer la température sur ces systèmes.
8. Les systèmes de chauffage basés sur Netatmo fonctionnent mal. Les plannings Netatmo viennent en concurrence de la programmation _VTherm_. Les sous-jacents Netatmo repasse en mode `Auto` tout le temps et ce mode est très mal géré avec _VTherm_ qui ne peut pas savoir si le sysème chauffe ou refroidit et donc quel algorithme choisir. Certains ont quand même réussi à le faire fonctionner avec un switch virtuel entre le _VTherm_ et le sous-jacent mais sans garantie de stabilité. Un exemple est donné dans la section [dépannage](troubleshooting.md)

