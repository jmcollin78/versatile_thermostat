# Thermostat de type ```over_switch```

- [Thermostat de type ```over_switch```](#thermostat-de-type-over_switch)
  - [Pré-requis](#pré-requis)
  - [Configuration](#configuration)
    - [les sous-jacents](#les-sous-jacents)
    - [Le keep-alive](#le-keep-alive)
    - [Le mode AC](#le-mode-ac)
    - [L'inversion de la commande](#linversion-de-la-commande)
    - [La personnalisation des commandes](#la-personnalisation-des-commandes)

## Pré-requis

L'installation doit ressembler à ça :

![installation `over_switch`](images/over-switch-schema.png)

1. L'utilisateur ou une automatisation ou le Sheduler programme une consigne (setpoint) par le biais d'un pre-réglage ou directement d'une température,
2. régulièrement le thermomètre intérieur (2) ou extérieur (2b) envoie la température mesurée. Le thermomètre interieur doit être placé à une place pertinente pour le ressenti de l'utilisateur : idéalement au milieu du lieu de vie. Evitez de le mettre trop près d'une fenêtre ou trop proche du radiateur,
3. avec les valeurs de consigne, les différentes températures et des paramètres de l'algorithme TPI (cf. [TPI](algorithms.md#lalgorithme-tpi)), VTherm va calculer un pourcentage de temps d'allumage,
4. et va régulièrement commander l'allumage et l'extinction du ou des entités `switch` (ou `select` ou `climate`) sous-jacentes,
5. ces entités sous-jacentes vont alors commander l'équipement physique
6. la commande du switch physique allumera ou éteindra le radiateur.

> Le pourcentage d'allumage est recalculé à chaque cycle et c'est ce qui permet de réguler la température de la pièce.

## Configuration

Configurez d'abord les paramètres principaux et communs à tous les _VTherm_ (cf. [paramètres principaux](base-attributes.md)).
Ensuite cliquez sur l'option de menu "Sous-jacents" et vous allez avoir cette page de configuration :

![image](images/config-linked-entity.png)

### les sous-jacents
Dans la "liste des équipements à contrôler" vous mettez les switchs qui vont être controllés par le VTherm. Seuls les entités de type `switch` ou `input_boolean` ou `select` ou `input_select` ou `climate` sont acceptées.

Si un des sous-jacents n'est pas un `switch` alors la personnalisation des commandes est obligatoires. Par défaut pour les `switch` les commandes sont les commandes classique d'allumage / extinction du switch (`turn_on`, `turn_off`)

L'algorithme à utiliser est aujourd'hui limité à TPI est disponible. Voir [algorithme](#algorithme).
Si plusieurs entités de type sont configurées, la thermostat décale les activations afin de minimiser le nombre de switch actif à un instant t. Ca permet une meilleure répartition de la puissance puisque chaque radiateur va s'allumer à son tour.

VTherm va donc lisser la puissance consommée le plus possible en alternant les activations. Exemple d'activations décalées :

![image](images/multi-switch-activation.png)

Evidemment si la puissance demandée (`on_percent`) est trop forte, alors il y aura un recouvrement des activations.

### Le keep-alive

Certains équipements nécessitent d'être périodiquement sollicités pour empêcher un arrêt de sécurité. Connu sous le nom de "keep-alive" cette fonction est activable en entrant un nombre de secondes non nul dans le champ d'intervalle keep-alive du thermostat. Pour désactiver la fonction ou en cas de doute, laissez-le vide ou entrez zéro (valeur par défaut).

### Le mode AC

Il est possible de choisir un thermostat over switch qui commande une climatisation en cochant la case "AC Mode". Dans ce cas, seul le mode refroidissement sera visible.

### L'inversion de la commande

Si votre équipement est commandé par un fil pilote avec un diode, vous aurez certainement besoin de cocher la case "Inverser la case". Elle permet de mettre le switch à `On` lorsqu'on doit étiendre l'équipement et à `Off` lorsqu'on doit l'allumer. Les temps de cycle sont donc inversés avec cette option.

### La personnalisation des commandes

Cette section de configuration permet de personnaliser les commandes d'allumage et d'extinction envoyée à l'équipement sous-jacent,
Ces commandes sont obligatoires si un des sous-jacents n'est pas un `switch` (pour les `switchs` les commandes d'allumage/extinction classiques sont utilisées).

Pour personnaliser les commande, cliquez sur `Ajouter` en bas de page sur les commandes d'allumage et sur les commandes d'extinction :

![virtual switch](images/config-vswitch1.png)

et donner la commande d'allumage et d'exinction avec le format `commande[/attribut[:valeur]]`.
Les commandes possibles dépendent du type de sous-jacents :

| type de sous-jacent         | commandes d'allumage possibles        | commandes d'extinction possibles               | S'applique à                   |
| --------------------------- | ------------------------------------- | ---------------------------------------------- | ------------------------------ |
| `switch` ou `input_boolean` | `turn_on`                             | `turn_off`                                     | tous les switchs               |
| `select` ou `input_select`  | `select_option/option:comfort`        | `select_option/option:frost_protection`           | Nodon SIN-4-FP-21 et assimilés |
| `climate` (hvac_mode)       | `set_hvac_mode/hvac_mode:heat`        | `set_hvac_mode/hvac_mode:off`                  | eCosy (via Tuya Local)         |
| `climate` (preset)          | `set_preset_mode/preset_mode:comfort` | `set_preset_mode/preset_mode:frost_protection` | Heatzy                         |

Evidemment, tous ces exemples peuvent être adaptés à votre cas.

Exemple pour un Nodon SIN-4-FP-21 :
![virtual switch Nodon](images/config-vswitch2.png)

Cliquez sur valider pour accepter les modifications.

Si l'erreur suivante se produit :

> La configuration de la personnalisation des commandes est incorrecte. Elle est obligatoire pour les sous-jacents non switch et le format doit être 'service_name[/attribut:valeur]'. Plus d'informations dans le README.

Cela signifie que une des commandes saisies est invalide. Les règles à respecter sont les suivantes :
1. chaque commande doit avoir le format `commande[/attribut[:valeur]]` (ex: `select_option/option:comfort` ou `turn_on`) sans blanc et sans caractères spéciaux sauf '_',
2. il doit y avoir autant de commandes qu'il y a de sous-jacents déclarés sauf si tous les sous-jacents sont des `switchs` auquel cas il n'est pas nécessaire de paramétrer les commandes,
3. si plusieurs sous-jacents sont configurés, les commandes doivent être dans le même ordre. Le nombre de commandes d'allumage doit être égal au nombre de commandes d'extinction et de sous-jacents (dans l'ordre donc). Il est possible de mettre des sous-jacents de type différent. À partir du moment où un sous-jacent n'est pas un `switch`, il faut paramétrer toutes les commandes de tous les sous-jacents y compris des éventuels switchs.
