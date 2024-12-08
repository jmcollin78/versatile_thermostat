# Quand l'utiliser et ne pas l'utiliser
Ce thermostat peut piloter 3 types d'équipements :
1. un radiateur qui ne fonctionne qu'en mode marche/arrêt (nommé ```thermostat_over_switch```). La configuration minimale nécessaire pour utiliser ce type thermostat est :
   1. un équipement comme un radiateur (un ```switch``` ou équivalent),
   2. une sonde de température pour la pièce (ou un input_number),
   3. un capteur de température externe (pensez à l'intégration météo si vous n'en avez pas)
2. un autre thermostat qui a ses propres modes de fonctionnement (nommé ```thermostat_over_climate```). Pour ce type de thermostat la configuration minimale nécessite :
   1. un équipement - comme une climatisation, une valve thermostatique - qui est pilotée par sa propre entity de type ```climate```,
3. un équipement qui peut prendre une valeur de 0 à 100% (nommée ```thermostat_over_valve```). A 0 le chauffage est coupé, 100% il est ouvert à fond. Ce type permet de piloter une valve thermostatique (cf. valve Shelly) qui expose une entité de type `number.` permetttant de piloter directement l'ouverture de la vanne. Versatile Thermostat régule la température de la pièce en jouant sur le pourcentage d'ouverture, à l'aide des capteurs de température intérieur et extérieur en utilisant l'algorithme TPI décrit ci-dessous.

Le type `over_climate` vous permet d'ajouter à votre équipement existant toutes les fonctionnalités apportées par VersatileThermostat. L'entité `climate` VersatileThermostat contrôlera votre entité climate sous-jacente, l'éteindra si les fenêtres sont ouvertes, la fera passer en mode Eco si personne n'est présent, etc. Voir [ici] (#pourquoi-un-nouveau-thermostat-implémentation). Pour ce type de thermostat, tous les cycles de chauffage sont contrôlés par l'entité climate sous-jacente et non par le thermostat polyvalent lui-même. Une fonction facultative d'auto-régulation permet au Versatile Thermostat d'ajuster la température donnée en consigne au sous-jacent afin d'atteindre la consigne.

Les installations avec fil pilote et diode d'activation bénéficie d'une option qui permet d'inverser la commande on/off du radiateur sous-jacent. Pour cela, utilisez le type `over switch` et cochez l'option d'inversion de la commande.

# Pourquoi une nouvelle implémentation du thermostat ?

Ce composant nommé __Versatile thermostat__ gère les cas d'utilisation suivants :
- Configuration via l'interface graphique d'intégration standard (à l'aide du flux Config Entry),
- Utilisations complètes du **mode préréglages**,
- Désactiver le mode préréglé lorsque la température est **définie manuellement** sur un thermostat,
- Éteindre/allumer un thermostat ou chager de preset lorsqu'une **porte ou des fenêtres sont ouvertes/fermées** après un certain délai,
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

## Incompatibilités
Certains thermostat de type TRV sont réputés incompatibles avec le Versatile Thermostat. C'est le cas des vannes suivantes :
1. les vannes POPP de Danfoss avec retour de température. Il est impossible d'éteindre cette vanne et elle s'auto-régule d'elle-même causant des conflits avec le VTherm,
2. Les thermostats « Homematic » (et éventuellement Homematic IP) sont connus pour rencontrer des problèmes avec le Versatile Thermostat en raison des limitations du protocole RF sous-jacent. Ce problème se produit particulièrement lorsque vous essayez de contrôler plusieurs thermostats Homematic à la fois dans une seule instance de VTherm. Afin de réduire la charge du cycle de service, vous pouvez par ex. regroupez les thermostats avec des procédures spécifiques à Homematic (par exemple en utilisant un thermostat mural) et laissez Versatile Thermostat contrôler uniquement le thermostat mural directement. Une autre option consiste à contrôler un seul thermostat et à propager les changements de mode CVC et de température par un automatisme,
3. les thermostats de type Heatzy qui ne supportent pas les commandes de type set_temperature
4. les thermostats de type Rointe ont tendance a se réveiller tout seul. Le reste fonctionne normalement.
5. les TRV de type Aqara SRTS-A01 et MOES TV01-ZB qui n'ont pas le retour d'état `hvac_action` permettant de savoir si elle chauffe ou pas. Donc les retours d'état sont faussés, le reste à l'air fonctionnel.
6. La clim Airwell avec l'intégration "Midea AC LAN". Si 2 commandes de VTherm sont trop rapprochées, la clim s'arrête d'elle même.
7. Les climates basés sur l'intégration Overkiz ne fonctionnent pas. Il parait impossible d'éteindre ni même de changer la température sur ces systèmes.

