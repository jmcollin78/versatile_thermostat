# Le contrôle d'une chaudière centrale

- [Le contrôle d'une chaudière centrale](#le-contrôle-dune-chaudière-centrale)
  - [Principe](#principe)
    - [Calcul de la puissance activée](#calcul-de-la-puissance-activée)
  - [Configuration](#configuration)
    - [Comment trouver la bonne action ?](#comment-trouver-la-bonne-action-)
  - [Les évènements](#les-évènements)
  - [Avertissement](#avertissement)

Vous avez la possibilité de contrôler une chaudière centrale. A partir du moment où il est possible de déclencher ou stopper cette chaudière depuis Home Assistant, alors Versatile Thermostat va pouvoir la commander directement en fonction de l'état de certains _VTherm_. Si suffisamment de _VTherm_ demande à chauffer alors la chaudière sera allumée après un certain délai paramétrable.

## Principe
Le principe mis en place est globalement le suivant :
1. une nouvelle entité de type `binary_sensor` et nommée par défaut `binary_sensor.central_configuration_central_boiler` est ajoutée,
2. dans la configuration des _VTherm_ vous indiquez si le VTherm doit contrôler la chaudière. En effet, dans une installation hétérogène, certains VTherm doivent commander la chaudière et d'autres non. Vous devez donc indiquer dans chaque configuration de VTherm si il contrôle la chaudière ou pas. A chauque _VTherm_ controlant la chaudière vous pouvez associer une puissance,
3. le `binary_sensor.central_configuration_central_boiler` écoute les changements d'états des équipements des VTherm marqués comme contrôlant la chaudière,
4. dès que le nombre d'équipements pilotés par le VTherm demandant du chauffage (ie son `hvac_action` passe à `Heating`)  ou que le total des puissance dépasse un seuil paramétrable, alors le `binary_sensor.central_configuration_central_boiler` passe à `on` et **si un service d'activation a été configuré, alors ce service est appelé**,
5. si le nombre d'équipements nécessitant du chauffage repasse en dessous du seuil, alors le `binary_sensor.central_configuration_central_boiler` passe à `off` et si **un service de désactivation a été configuré, alors ce service est appelé**,
6. vous avez accès à 4 entités :
   - une de type `number` nommée par défaut `number.boiler_activation_threshold`, donne le seuil de déclenchement. Ce seuil est en nombre d'équipements (radiateurs) qui demandent du chauffage et non pas le nombre de _VTherm_ demandant du chauffage.
   - une de type `sensor` nommée par défaut `sensor.nb_device_active_for_boiler`, donne le nombre d'équipements qui demandent du chauffage. Par exemple, un VTherm ayant 4 vannes dont 3 demandent du chauffage fera passer ce capteur à 3. Seuls les équipements des _VTherm_ qui sont marqués pour contrôler la chaudière centrale sont comptabilisés.
   - une de type `number` nommée `number.boiler_power_activation_threshold` qui donne le seuil de puissance de déclenchement. Si le total des puissances activées par des _Vtherm_ controlant la chaudière est dépassé alors la chaudière sera activée,
   - une de type `sensor` nommée `sensor.total_power_active_for_boiler` qui donne le dernier total de puissance calculé.

Vous avez donc en permanence, les informations qui permettent de piloter et régler le déclenchement de la chaudière.

Toutes ces entités sont rattachées au service de configuration centrale :

![Les entités pilotant la chaudière](images/entitites-central-boiler.png)

Dans cet exemple :
1. la chaudière est éteinte,
2. elle se déclenche si 3 équipements sont actifs ou si un total de puissance active est de 500,
3. le nombre d'équipements actifs est 1,
4. le total de la puissance activée est 230.

### Calcul de la puissance activée
Le calcul de la puissance activée est dépendant du type de _VTherm_ :
1. pour tous les _VTherm_ basés sur le [TPI](./algorithms.md#lalgorithme-tpi) la puissance active est [la puissance configurée pour l'équipement](base-attributes.md#choix-des-attributs-de-base) x `on_percent` issue de l'algo TPI. Pour tous ces _VTherm_ la puissance est donc variable et évolue en fonction de la puissance de chauffage demandé. Les puissances n'ont pas d'unités, vous pouvez mettre ce que vous voulez, l'important c'est que toutes les puissances exprimées dans tous les _VTherm_ aient la même unité.
2. pour les _VTherm_ `over_climate` la puissance calculée est du tout ou rien. Si l'équipement est actif (`is_device_ative`) alors la puissance est celle de du _VTherm_ sinon elle est nulle. Il n'y a pas moyen dans cette configuration de moduler la puissance demandée.

## Configuration
Pour configurer cette fonction, vous devez avoir une configuration centralisée (cf. [Configuration](#configuration)) et cocher la case 'Ajouter une chaudière centrale' :

![Ajout d'une chaudière centrale](images/config-central-boiler-1.png)

Sur la page suivante vous pouvez donner la configuration des actions (ex services) à appeler lors de l'allumage / extinction de la chaudière :

![Ajout d'une chaudière centrale](images/config-central-boiler-2.png)

Le premier paramètre donne un délai en secondes avant d'activer la chaudière. La valeur par défaut est de 0 donc la chaudière est activée tout de suite dès qu'un seuil est franchi. Si vous avez besoin de laisser du temps aux vannes de s'ouvrir (par exemple), mettez une valeur positive en secondes. Certaines vannes pour des planchers chauffant peuvent mettre plusieurs minutes à s'ouvrir et il peut être dommageable d'activer la pompe de la chaudière avant que les vannes ne soient ouvertes.

Les actions (ex services) se configurent comme indiqué dans la page :
1. le format général est `entity_id/service_id[/attribut:valeur]` (où `/attribut:valeur` est facultatif),
2. `entity_id` est le nom de l'entité qui commande la chaudière sous la forme `domain.entity_name`. Par exemple: `switch.chaudiere` pour les chaudière commandée par un switch ou `climate.chaudière` pour une chaudière commandée par un thermostat ou tout autre entité qui permet le contrôle de la chaudière (il n'y a pas de limitation).  On peut aussi commuter des entrées (`helpers`) comme des `input_boolean` ou `input_number`.
3. `service_id` est le nom du service à appeler sous la forme `domain.service_name`. Par exemple: `switch.turn_on`, `switch.turn_off`, `climate.set_temperature`, `climate.set_hvac_mode` sont des exemples valides.
4. pour certain service vous aurez besoin d'un paramètre. Cela peut être le 'Mode CVC' `climate.set_hvac_mode` ou la température cible pour `climate.set_temperature`. Ce paramètre doit être configuré sous la forme `attribut:valeur` en fin de chaine.

Exemples (à ajuster à votre cas) :
- `climate.chaudiere/climate.set_hvac_mode/hvac_mode:heat` : pour allumer le thermostat de la chaudière en mode chauffage,
- `climate.chaudiere/climate.set_hvac_mode/hvac_mode:off` : pour stopper le thermostat de la chaudière,
- `switch.pompe_chaudiere/switch.turn_on` : pour allumer le swicth qui alimente la pompe de la chaudière,
- `switch.pompe_chaudiere/switch.turn_off` : pour allumer le swicth qui alimente la pompe de la chaudière,
- ...

> **Note**
> Il n'y a pas de délai pour l'extinction de la chaudière. C'est volontaire pour vous éviter de laisser tourner la chaudière alors que toutes les vannes sont fermées. Il faudrait un délai négatif pour bien faire (ie couper la chaudière avant de fermer les vannes) mais ce n'est pas possible en l'état puisque c'est la manipulation des vannes qui délcenche la chaudière et pas l'inverse.

### Comment trouver la bonne action ?
Pour trouver l'action à utiliser, le mieux est d'aller dans "Outils de développement / Actions", chercher l'action à appeler, l'entité à commander et l'éventuel paramètre à donner.
Cliquez sur 'Appeler l'action'. Si votre chaudière s'allume vous avez la bonne configuration. Passez alors en mode Yaml et recopiez les paramètres.

Exemple:

Sous "Outils de développement / Actions" :

![Configuration du service](images/dev-tools-turnon-boiler-1.png)

En mode yaml :

![Configuration du service](images/dev-tools-turnon-boiler-2.png)

Le service à configurer est alors le suivant: `climate.empty_thermostast/climate.set_hvac_mode/hvac_mode:heat` (notez la suppression du blanc dans `hvac_mode:heat`)

Faite alors de même pour le service d'extinction et vous êtes parés.

## Les évènements

A chaque allumage ou extinction réussie de la chaudière un évènement est envoyé par Versatile Thermostat. Il peut avantageusement être capté par une automatisation, par exemple pour notifier un changement.
Les évènements ressemblent à ça :

Un évènement d'allumage :
```yaml
event_type: versatile_thermostat_central_boiler_event
data:
  central_boiler: true
  entity_id: binary_sensor.central_configuration_central_boiler
  name: Central boiler
  state_attributes: null
origin: LOCAL
time_fired: "2024-01-14T11:33:52.342026+00:00"
context:
  id: 01HM3VZRJP3WYYWPNSDAFARW1T
  parent_id: null
  user_id: null
```

Un évènement d'extinction :
```yaml
event_type: versatile_thermostat_central_boiler_event
data:
  central_boiler: false
  entity_id: binary_sensor.central_configuration_central_boiler
  name: Central boiler
  state_attributes: null
origin: LOCAL
time_fired: "2024-01-14T11:43:52.342026+00:00"
context:
  id: 01HM3VZRJP3WYYWPNSDAFBRW1T
  parent_id: null
  user_id: null
```

## Avertissement

> ![Astuce](images/tips.png) _*Notes*_
>
> Le contrôle par du logiciel ou du matériel de type domotique d'une chaudière centrale peut induire des risques pour son bon fonctionnement. Assurez-vous avant d'utiliser ces fonctions, que votre chaudière possède bien des fonctions de sécurité et que celles-ci fonctionnent. Allumer une chaudière si tous les robinets sont fermés peut générer de la sur-pression par exemple.
