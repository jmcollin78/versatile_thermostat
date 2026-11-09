# Thermostat de type `thermostat_over_valve`

> ![Attention](images/tips.png) _*Notes*_
> 1. Le type `over_valve` est souvent confondu avec le type `over_climate` équipé d'une auto-régulation avec pilotage direct de la vanne,
> 2. vous ne devriez choisir ce type que lorsque vous n'avez pas d'entité `climate` associé à votre _TRV_ dans Home Assistant et si vous avez juste une entité de type `number` qui permet le contrôle du pourcentage d'ouverture de la vanne. Le `over_climate` avec auto-régulation sur la vanne est bien plus puissant que le type `over_valve`.


## Pré-requis

Les vannes thermostatiques utilisables avec un _VTherm_ `over_valve`, comme la [Shelly BLU TRV](https://www.versatile-thermostat.org/fr/devices/over-valve/), sont listées dans le [catalogue des matériels](https://www.versatile-thermostat.org/fr/devices/?type=trv).

L'installation doit ressembler à celle pour le VTherm `over_switch` sauf que l'équipement contrôlé est directement la vanne d'un _TRV_  :
![installation `over_valve`](images/over-valve-schema.png)

1. L'utilisateur ou une automatisation ou le Scheduler programme une consigne (setpoint) par le biais d'un pré-réglage ou directement d'une température,
2. régulièrement le thermomètre intérieur (2) ou extérieur (2b) ou interne à l'équipement (2c) envoie la température mesurée. Le thermomètre intérieur doit être placé à une place pertinente pour le ressenti de l'utilisateur : idéalement au milieu du lieu de vie. Evitez de le mettre trop près d'une fenêtre ou trop proche de l'équipement,
3. avec les valeurs de consigne, les différentes températures et des paramètres de l'algorithme TPI (cf. [TPI](algorithms.md#lalgorithme-tpi) ou les [autres algorithmes](algorithms.md#autres-algorithmes-plugins)), VTherm va calculer un pourcentage d'ouverture de la vanne,
4. et va modifier la valeur des entités `number` sous-jacentes,
5. ces entités `number` sous-jacentes vont alors commander le taux d'ouverture de la vanne sur le _TRV_
6. ce qui va faire chauffer plus ou moins le radiateur

> Le taux d'ouverture est recalculé à chaque cycle et c'est ce qui permet de réguler la température de la pièce.


## Configuration

Configurez d'abord les paramètres principaux et communs à tous les _VTherm_ (cf. [paramètres principaux](base-attributes.md)).
Configurez ensuite les sous-jacents. À la création du _VTherm_, l'assistant les affiche après les principaux attributs. Ensuite, choisissez « Sous-jacents » dans le menu. Ce menu liste :
- « Réglages communs » : les réglages partagés par toutes les vannes (algorithme, mode AC, seuil et période de régulation, seuil d'ouverture, fermeture maximale),
- une entrée par vanne pilotée, avec son entité et ses ouvertures,
- « Ajouter un appareil ».

« Ajouter un appareil » demande d'abord l'entité `number` de la vanne. Seules les entités `number` ou `input_number` sont acceptées. L'écran suivant affiche les réglages de cette vanne : ses ouvertures minimale et maximale (voir [Contrôle de l'ouverture de la vanne](#contrôle-de-louverture-de-la-vanne)). Ouvrir une vanne dans la liste affiche les mêmes réglages, avec « Remplacer l'entité » et « Supprimer cet appareil ».

Le champ « Algorithme » des réglages communs permet de choisir l'algorithme de régulation : le TPI intégré, ou un algorithme installé sous forme de plugin. Voir [les algorithmes](algorithms.md).

### Seuil et période de régulation

Deux champs limitent le nombre de commandes envoyées à la vanne :
1. **Seuil de régulation** (défaut `10`) : variation minimale de l'ouverture, en %, en dessous de laquelle une nouvelle ouverture n'est pas envoyée,
2. **Période minimale de régulation** (défaut `5` minutes) : délai minimal entre deux calculs de l'ouverture.

### Contrôle de l'ouverture de la vanne

`over_valve` peut adapter la commande d'ouverture TPI aux contraintes physiques
de chaque vanne. La configuration utilise les mêmes paramètres que le contrôle
direct de vanne avec `over_climate` :

1. `opening_threshold_degree`, dans les réglages communs : sous ce
	pourcentage TPI brut, la vanne est considérée comme fermée.
2. `max_closing_degree`, dans les réglages communs : pourcentage de fermeture
	maximal. Sous le seuil, la commande est `100 - max_closing_degree` ;
	conserver la valeur `100` ferme complètement la vanne.
3. « Ouverture minimale (%) » (`min_opening_degrees`), dans les réglages de
	chaque vanne : appliquée dès que le seuil est atteint. Vaut `0` par défaut.
4. « Ouverture maximale (%) » (`max_opening_degrees`), dans les réglages de
	chaque vanne : la vanne ne s'ouvre jamais plus que cette valeur. Elle ne
	peut pas dépasser le maximum supporté par l'entité `number`, qui est la
	valeur par défaut.

La commande physique ne descend jamais sous `100 - max_closing_degree`, y
compris lorsque la demande TPI brute atteint `opening_threshold_degree`, et
elle reste monotone lorsque la demande augmente. La demande de chauffage est
déterminée à partir du pourcentage TPI brut positif, supérieur ou égal au
seuil ; la vanne observée n'est active qu'au-dessus de son plancher physique
effectif, également borné par le minimum de l'entité. Au démarrage ou après un
rechargement, une vanne sans demande revient à ce plancher.

Chaque vanne a ses propres ouvertures minimale et maximale. Avec les valeurs
par défaut (seuil `0`, minimum `0`, maximum de la vanne, fermeture maximale
`100`), la commande envoyée reste identique au pourcentage TPI brut.

Il est possible de choisir un thermostat `over-valve` qui commande une climatisation en cochant la case "AC Mode". Dans ce cas, seul le mode refroidissement sera visible.

### Mode sommeil

`over_valve` prend en charge le mode sommeil. La sélection de `sleep`, ou
l'appel de l'action `versatile_thermostat.set_hvac_mode_sleep`, présente le
VTherm comme arrêté tout en envoyant une demande brute d'ouverture à 100 % à
chaque vanne sous-jacente. Cette demande conserve la conversion normale de
contrôle d'ouverture : `max_opening_degrees` et les bornes de l'entité `number`
peuvent donc plafonner l'ouverture physique. Le sommeil ne sollicite pas la
chaudière centrale ; l'attribut `is_sleeping` identifie cet état.

## Étape suivante

[Les coefficients du TPI](algorithms.md#configurez-les-coefficients-de-lalgorithme-tpi) : régler l'algorithme de régulation (menu « Paramètres TPI »). Sans configuration centrale, cette étape est nécessaire pour finaliser la création.

Si vous utilisez un algorithme en plugin, comme SmartPI, suivez sa documentation, puis passez directement aux [presets](feature-presets.md).
