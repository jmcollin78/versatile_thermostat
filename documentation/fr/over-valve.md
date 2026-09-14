# Thermostat de type `thermostat_over_valve`

> ![Attention](images/tips.png) _*Notes*_
> 1. Le type `over_valve` est souvent confondu avec le type `over_climate` équipé d'une auto-régulation avec pilotage direct de la vanne,
> 2. vous ne devriez choisir ce type que lorsque vous n'avez pas d'entité `climate` associé à votre _TRV_ dans Home Assistant et si vous avez juste une entité de type `number` qui permet le contrôle du pourcentage d'ouverture de la vanne. Le `over_climate` avec auto-régulation sur la vanne est bien plus puissant que le type `over_valve`.


## Pré-requis

L'installation doit ressembler à celle pour le VTherm `over_switch` sauf que l'équipement contrôlé est directement la vanne d'un _TRV_  :
![installation `over_valve`](images/over-valve-schema.png)

1. L'utilisateur ou une automatisation ou le Scheduler programme une consigne (setpoint) par le biais d'un pré-réglage ou directement d'une température,
2. régulièrement le thermomètre intérieur (2) ou extérieur (2b) ou interne à l'équipement (2c) envoie la température mesurée. Le thermomètre intérieur doit être placé à une place pertinente pour le ressenti de l'utilisateur : idéalement au milieu du lieu de vie. Evitez de le mettre trop près d'une fenêtre ou trop proche de l'équipement,
3. avec les valeurs de consigne, les différentes températures et des paramètres de l'algorithme TPI (cf. [TPI](algorithms.md#lalgorithme-tpi)), VTherm va calculer un pourcentage d'ouverture de la vanne,
4. et va modifier la valeur des entités `number` sous-jacentes,
5. ces entités `number` sous-jacentes vont alors commander le taux d'ouverture de la vanne sur le _TRV_
6. ce qui va faire chauffer plus ou moins le radiateur

> Le taux d'ouverture est recalculé à chaque cycle et c'est ce qui permet de réguler la température de la pièce.


## Configuration

Configurez d'abord les paramètres principaux et communs à tous les _VTherm_ (cf. [paramètres principaux](base-attributes.md)).
Ensuite cliquez sur l'option de menu "Sous-jacents" et vous allez avoir cette page de configuration. Vous mettez les entités `numnber` ou `input_number`qui vont être controllés par le VTherm :

![image](images/config-linked-entity3.png)

L'algorithme à utiliser est aujourd'hui limité à TPI est disponible. Voir [algorithme](#algorithme).

### Contrôle de l'ouverture de la vanne

`over_valve` peut adapter la commande d'ouverture TPI aux contraintes physiques
de chaque vanne. La configuration utilise les mêmes paramètres que le contrôle
direct de vanne avec `over_climate` :

1. `opening_threshold_degree` : sous ce pourcentage TPI brut, la vanne est
	considérée comme fermée.
2. `max_closing_degree` : pourcentage de fermeture maximal. Sous le seuil, la
	commande est `100 - max_closing_degree` ; conserver la valeur `100` ferme
	complètement la vanne.
3. `min_opening_degrees` : valeurs minimales d'ouverture séparées par des
	virgules, une par vanne sous-jacente. La valeur est appliquée dès que le
	seuil est atteint.
4. `max_opening_degrees` : valeurs maximales d'ouverture séparées par des
	virgules, une par vanne sous-jacente. Les valeurs absentes utilisent le
	maximum supporté par l'entité `number` concernée.

Pour plusieurs vannes, les valeurs suivent l'ordre des entités sous-jacentes.
Les listes courtes utilisent les valeurs par défaut pour les vannes restantes ;
les listes plus longues sont refusées. Avec les valeurs par défaut (`0`, listes
vides, `100`), la commande envoyée reste identique au pourcentage TPI brut.

Il est possible de choisir un thermostat `over-valve` qui commande une climatisation en cochant la case "AC Mode". Dans ce cas, seul le mode refroidissement sera visible.

