
# Dépannages

- [Dépannages](#dépannages)
  - [Utilisation d'un Heatzy](#utilisation-dun-heatzy)
  - [Utilisation d'un radiateur avec un fil pilote (Nodon SIN-4-FP-21)](#utilisation-dun-radiateur-avec-un-fil-pilote-nodon-sin-4-fp-21)
  - [Utilisation d'un système Netatmo](#utilisation-dun-système-netatmo)
  - [Seul le premier radiateur chauffe](#seul-le-premier-radiateur-chauffe)
  - [Le radiateur chauffe alors que la température de consigne est dépassée ou ne chauffe pas alors que la température de la pièce est bien en-dessous de la consigne](#le-radiateur-chauffe-alors-que-la-température-de-consigne-est-dépassée-ou-ne-chauffe-pas-alors-que-la-température-de-la-pièce-est-bien-en-dessous-de-la-consigne)
    - [Type `over_switch` ou `over_valve`](#type-over_switch-ou-over_valve)
    - [Type `over_climate`](#type-over_climate)
  - [Régler les paramètres de détection d'ouverture de fenêtre en mode auto](#régler-les-paramètres-de-détection-douverture-de-fenêtre-en-mode-auto)
  - [Pourquoi mon Versatile Thermostat se met en Securite ?](#pourquoi-mon-versatile-thermostat-se-met-en-securite-)
    - [Comment détecter le mode sécurité ?](#comment-détecter-le-mode-sécurité-)
    - [Comment être averti lorsque cela se produit ?](#comment-être-averti-lorsque-cela-se-produit-)
    - [Comment réparer ?](#comment-réparer-)
  - [Utilisation d'un groupe de personnes comme capteur de présence](#utilisation-dun-groupe-de-personnes-comme-capteur-de-présence)
  - [Activer les logs du Versatile Thermostat](#activer-les-logs-du-versatile-thermostat)
  - [VTherm ne suit pas les changements de consigne faits directement depuis le sous-jacents (`over_climate`)](#vtherm-ne-suit-pas-les-changements-de-consigne-faits-directement-depuis-le-sous-jacents-over_climate)
  - [VTherm passe tout seul en mode 'clim' ou en mode 'chauffage'](#vtherm-passe-tout-seul-en-mode-clim-ou-en-mode-chauffage)
  - [La détection de fenêtre ouverte n'empêche pas le changement de preset](#la-détection-de-fenêtre-ouverte-nempêche-pas-le-changement-de-preset)


## Utilisation d'un Heatzy

Le Heatzy est maintenant pris en charge nativement par _VTherm_. Cf. [Démarrage rapide](quick-start.md#heatzy-ou-ecosy-ou-assimilé-entité-climate).

Cette configuration est gardée pour mémoire uniquement.

L'utilisation d'un Heatzy ou Nodon est possible à la condition d'utiliser un switch virtuel sur ce modèle :

```yaml
- platform: template
  switches:
    chauffage_sdb:
      unique_id: chauffage_sdb
      friendly_name: Chauffage salle de bain
      value_template: "{{ is_state_attr('climate.salle_de_bain', 'preset_mode', 'comfort') }}"
      icon_template: >-
        {% if is_state_attr('climate.salle_de_bain', 'preset_mode', 'comfort') %}
          mdi:radiator
        {% elif is_state_attr('climate.salle_de_bain', 'preset_mode', 'away') %}
          mdi:snowflake
        {% else %}
          mdi:radiator-disabled
        {% endif %}
      turn_on:
        service: climate.set_preset_mode
        entity_id: climate.salle_de_bain
        data:
          preset_mode: "comfort"
      turn_off:
        service: climate.set_preset_mode
        entity_id: climate.salle_de_bain
        data:
          preset_mode: "eco"
```
Merci à @gael pour cet exemple.

## Utilisation d'un radiateur avec un fil pilote (Nodon SIN-4-FP-21)

Le Nodon est maintenant pris en charge nativement par _VTherm_. Cf. [Démarrage rapide](quick-start.md#nodon-sin-4-fp-21-ou-assimilé-fil-pilote).

Cette configuration est gardée pour mémoire uniquement.

Comme pour le Heatzy ci-dessus vous pouvez utiliser un switch virtuel qui va changer le preset de votre radiateur en fonction de l'état d'allumage du VTherm.
Exemple :

```yaml
- platform: template
  switches:
    chauffage_chb_parents:
      unique_id: chauffage_chb_parents
      friendly_name: Chauffage chambre parents
      value_template: "{{ is_state('select.fp_chb_parents_pilot_wire_mode', 'comfort') }}"
      icon_template: >-
        {% if is_state('select.fp_chb_parents_pilot_wire_mode', 'comfort') %}
          mdi:radiator
        {% elif is_state('select.fp_chb_parents_pilot_wire_mode', 'frost_protection') %}
          mdi:snowflake
        {% else %}
          mdi:radiator-disabled
        {% endif %}
      turn_on:
        service: select.select_option
        target:
          entity_id: select.fp_chb_parents_pilot_wire_mode
        data:
          option: comfort
      turn_off:
        service: select.select_option
        target:
          entity_id: select.fp_chb_parents_pilot_wire_mode
        data:
          option: eco
```
Un exemple plus complet est [ici](https://github.com/jmcollin78/versatile_thermostat/discussions/431#discussioncomment-11393065)

## Utilisation d'un système Netatmo
Le système à base de TRV Netatmo fonctionne mal avec _VTherm_. Vous avez ici une discussion sur le fonctionnement particulier des systèmes Netatmo (en Français) : https://forum.hacf.fr/t/vannes-netatmo-et-vtherm/56063

## Seul le premier radiateur chauffe

En mode `over_switch` si plusieurs radiateurs sont configurés pour un même _VTherm_, l'alllumage va se faire de façon séquentiel pour lisser au plus possible les pics de consommation.
Cela est tout à fait normal et voulu. C'est décrit ici : [Pour un thermostat de type ```thermostat_over_switch```](over-switch.md#thermostat-de-type-over_switch

## Le radiateur chauffe alors que la température de consigne est dépassée ou ne chauffe pas alors que la température de la pièce est bien en-dessous de la consigne

### Type `over_switch` ou `over_valve`
Avec un _VTherm_ de type `over_switch` ou `over_valve`, ce défaut montre juste que les paramètres de l'algorithme TPI sont mal réglés. Voir [Algorithme TPI](algorithms.md#lalgorithme-tpi) pour optimiser les réglages.

### Type `over_climate`
Avec un _VTherm_ de type `over_climate`, la régulation est faite par le `climate` sous-jacent directement et _VTherm_ se contente de lui transmettre les consignes. Donc si le radiateur chauffe alors que la température de consigne est dépassée, c'est certainement que sa mesure de température interne est biaisée. Ca arrive très souvent avec les TRV et les clims réversibles qui ont un capteur de température interne, soit trop près de l'élément de chauffe (donc trop froid l'hiver).

Exemple de discussion autour de ces sujets: [#348](https://github.com/jmcollin78/versatile_thermostat/issues/348), [#316](https://github.com/jmcollin78/versatile_thermostat/issues/316), [#312](https://github.com/jmcollin78/versatile_thermostat/discussions/312), [#278](https://github.com/jmcollin78/versatile_thermostat/discussions/278)

Pour s'en sortir, VTherm est équipé d'une fonction nommée auto-régulation qui permet d'adapter la consigne envoyée au sous-jacent jusqu'à ce que la consigne soit respectée. Cette fonction permet de compenser le biais de mesure des thermomètres internes. Si le biais est important la régulation doit être importante. Voir [L'auto-régulation](self-regulation.md) pour configurer l'auto-régulation.

## Régler les paramètres de détection d'ouverture de fenêtre en mode auto

Si vous n'arrivez pas à régler la fonction de détection des ouvertures en mode auto (cf. [auto](feature-window.md#le-mode-auto)), vous pouvez essayer de modifier les paramètres de l'algorithme de lissage de la température.
En effet, la détection automatique d'ouverture est basée sur le calcul de la pente de la température (slope). Pour éviter les artefacts due à un capteur de température imprécis, cette pente est calculée sur une température lissée avec un algorithme de lissage nommée Exponential Moving Average (Moyenne mobile exponentielle).
Cet algorithm possède 3 paramètres :
1. `lifecycle_sec` : la durée en secondes prise en compte pour le lissage. Plus elle est forte et plus le lissage sera important mais plus il y aura de délai de détection,
2. `max_alpha` : si deux mesures de température sont éloignées dans le temps, la deuxième aura un poid beaucoup fort. Le paramètre permet de limiter le poid d'une mesure qui arrive bien après la précédente. Cette valeur doit être comprise entre 0 et 1. Plus elle est faible et moins les valeurs éloignées sont prises en compte. La valeur par défaut est de 0,5. Cela fait que lorsqu'une nouvelle valeur de température ne pèsera jamais plus que la moitié de la moyenne mobile,
3. `precision` : le nombre de chiffre après la virgule conservée pour le calcul de la moyenne mobile.

Pour changer ses paramètres, il faut modifier le fichier `configuration.yaml` et ajouter la section suivante (les valeurs sont les valeurs par défaut):

```yaml
versatile_thermostat:
  short_ema_params:
    max_alpha: 0.5
    halflife_sec: 300
    precision: 2
```

Ces paramètres sont sensibles et assez difficiles à régler. Merci de ne les utiliser que si vous savez ce que vous faites et que vos mesures de température ne sont pas déjà lisses.

## Pourquoi mon Versatile Thermostat se met en Securite ?
Le mode sécurité est possible sur les _VTherm_ de type `over_switch` et `over_valve` uniquement. Il survient lorsqu'un des 2 thermomètres qui donne la température de la pièce ou la température extérieure n'a pas envoyé de valeur depuis plus de `safety_delay_min` minutes et que le radiateur chauffait à au moins `safety_min_on_percent`. Cf. [mode sécurité](feature-advanced.md#la-mise-en-sécurité)

Comme l'algorithme est basé sur les mesures de température, si elles ne sont plus reçues par le _VTherm_, il y a un risque de surchauffe et d'incendie. Pour éviter ça, lorsque les conditions rappelées ci-dessus sont détectées, la chauffe est limité au paramètre `safety_default_on_percent`. Cette valeur doit donc être raisonnablement faible (10% est une bonne valeur). Elle permet d'éviter un incendie tout en évitant de couper totalement le radiateur (risque de gel).

Tous ces paramètres se règlent dans la dernière page de la configuration du VTherm : "Paramètres avancés".

### Comment détecter le mode sécurité ?
Le premier symptôme est une température anormalement basse avec un temps de chauffe faible à chaque cycle et régulier.
Exemple:

[security mode](images/security-mode-symptome1.png)

Si vous avez installé la carte [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card), le _VTherm_ en question aura cette forme là :

[security mode UI Card](images/security-mode-symptome2.png)

Vous pouvez aussi vérifier dans les attributs du _VTherm_ les dates de réception des différentes dates. **Les attributs sont disponibles dans les Outils de développement / Etats**.

Exemple :

```yaml
security_state: true
last_temperature_datetime: "2023-12-06T18:43:28.346010+01:00"
last_ext_temperature_datetime: "2023-12-06T13:04:35.164367+01:00"
last_update_datetime: "2023-12-06T18:43:28.351103+01:00"
...
safety_delay_min: 60
```

On voit que :
1. le _VTherm_ est bien en mode sécurité (`security_state: true`),
2. l'heure courante est le 06/12/2023 à 18h43:28 (`last_update_datetime: "2023-12-06T18:43:28.351103+01:00"`),
3. l'heure de dernière réception de la température intérieure est le 06/12/2023 à 18h43:28 (`last_temperature_datetime: "2023-12-06T18:43:28.346010+01:00"`). Elle est donc récente,
4. l'heure de dernière réception de la température extérieure est le 06/12/2023 à 13h04:35 (`last_ext_temperature_datetime: "2023-12-06T13:04:35.164367+01:00`). C'est donc l'heure extérieure qui a plus de 5 h de retard et qui a provoquée le passage en mode sécurité, car le seuil est limité à 60 min (`safety_delay_min: 60`).

### Comment être averti lorsque cela se produit ?
Pour être averti, le _VTherm_ envoie un évènement dès que ça se produit et un en fin d'alerte sécurité. Vous pouvez capter ces évènements dans une automatisation et envoyer une notification par exemple, faire clignoter un voyant, déclencher une sirène, ... A vous de voir.

Pour manipuler les évènements générés par le _VTherm_, cf. [Evènements](reference.md#evènements).

### Comment réparer ?
Cela va dépendre de la cause du problème :
1. Si un capteur est en défaut, il faut le réparer (remettre des piles, le changer, vérifier l'intégration Météo qui donne la température extérieure, ...),
2. Si le paramètre `safety_delay_min` est trop petit, cela risque de générer beaucoup de fausses alertes. Une valeur correcte est de l'ordre de 60 min, surtout si vous avez des capteurs de température à pile. Cf [mes réglages](tuning-examples.md#le-capteur-de-température-alimenté-par-batterie)
3. Certains capteurs de température, n'envoie pas de mesure si la température n'a pas changée. Donc en cas de température très stable pendant longtemps, le mode sécurité peut se déclencher. Ce n'est pas très grave puisqu'il s'enlève dès que le _VTherm_ reçoit à nouveau une température. Sur certain thermomètre (Tuya par exemple ou Zigbee), on peut forcer le délai max entre 2 mesures. Il conviendra de mettre un délai max < `safety_delay_min`,
4. Dès que la température sera a nouveau reçue le mode sécurité s'enlèvera et les valeurs précédentes de preset, température cible et mode seront restaurées.
5. Si c'est le capteur de température extérieur qui est en défaut, vous pouvez désactiver le déclenchement du mode sécurité puisqu'il influe assez peu sur le résultat. Pour ce faire, cf. [ici](feature-advanced.md#la-mise-en-sécurité)

## Utilisation d'un groupe de personnes comme capteur de présence

Malheureusement, les groupes de personnes ne sont pas reconnus comme des capteurs de présence. On ne peut donc pas les utiliser directement dans _VTherm_.
Le contournement est de créer un template de binary_sensor avec le code suivant :

Fichier `template.yaml` :

```yaml
- binary_sensor:
    - name: maison_occupee
      unique_id: maison_occupee
      state: "{{is_state('person.person1', 'home') or is_state('person.person2', 'home') or is_state('input_boolean.force_presence', 'on')}}"
      device_class: occupancy
```

Vous noterez dans cet exemple, l'utilisation d'un input_boolean nommé force_presence qui permet de forcer le capteur à `True` et ainsi de forcer les _VTherm_ qui l'utilise avec présence active. Ca permet par exemple, de forcer un pré-chauffage du logement lors du départ du travail, ou lorsqu'une personne non reconnue nativement dans HA est présente.

Fichier `configuration.yaml`:

```yaml
...
template: !include templates.yaml
...
```

## Activer les logs du Versatile Thermostat
Des fois, vous aurez besoin d'activer les logs pour afiner les analyses. Pour cela, éditer le fichier `logger.yaml` de votre configuration et configurer les logs comme suit :

```yaml
default: xxxx
logs:
  custom_components.versatile_thermostat: info
```
Vous devez recharger la configuration yaml (Outils de dev / Yaml / Toute la configuration Yaml) ou redémarrer Home Assistant pour que ce changement soit pris en compte.

Attention, en mode debug Versatile Thermostat est très verbeux et peut vite ralentir Home Assistant ou saturer votre disque dur. Si vous passez en mode debug pour une analyse d'anomalie il faut s'y mettre juste le temps de reproduire le bug et désactiver le mode debug juste après.

## VTherm ne suit pas les changements de consigne faits directement depuis le sous-jacents (`over_climate`)

Voir le détail de cette fonction [ici](over-climate.md#suivre-les-changements-de-température-du-sous-jacent).

## VTherm passe tout seul en mode 'clim' ou en mode 'chauffage'

Certaine _PAC_ réversibles ont des modes qui permettent de laisser le choix à la _PAC_ de chauffer ou de refroidir. Ces modes sont 'Auto' or 'Heat_cool' selon les marques. Ces 2 modes ne doivent pas être utilisés avec _VTherm_ car les algorithmes de _VTherm_ ont besoin de savoir si ils sont en mode chauffe ou refroidissement ce que ne permettent pas ces modes.
Vous devez donc utiliser uniquement les modes : `Heat`, `Cool`, `Off` ou `Fan` éventuellement (bien que fan n'a aucun sens avec _VTherm)

## La détection de fenêtre ouverte n'empêche pas le changement de preset

En effet, les changements de preset alors qu'une fenêtre est ouverte sont pris en compte et c'est un fonctionnement normal.
Si le mode d'action est réglé sur _Eteindre_ ou _Ventilateur seul_ le changement de preset et de température cible est appliqué immédiatement. Comme l'équipement est éteint ou en mode ventilation seule, il n'y a de risque de chauffer l'extérieur. Lorsque le mode de l'équipement passera à Chauffage ou Refroidissement, le preset et la température seront appliqués et utilisés.

Si le mode d'action est un changement de preset _Hors gel_ ou _Eco_ alors la température du preset est appliquée **mais le preset reste comme il était**. Cela permet de changer de preset pendant que la fenêtre sans changer la température de consigne qui reste celle programmée dans le mode d'action.

Exemple :
1. **Etat initial** : fenêtre fermée, mode d'action sur _Hors gel_, preset sur Confort et la température de consigne sur 19°,
2. **Ouverture de la fenêtre et attente** : preset reste sur Confort, **la température de consigne passe sur 10°** (hors gel). Cet état peut paraitre incohérent car la température de consigne n'est pas en accord avec le preset affiché,
3. **Changement de preset en Boost** (par l'utilisateur ou par le Scheduler) : le preset change pour Boost mais la température de consigne reste à 10° (hors gel). Cet état peut aussi paraitre incohérent,
4. **Fermeture de la fenêtre** : le preset reste sur Boost, la température de consigne passe sur 21° (Boost). L'incohérence a disparue et le changement de preset de l'utilisateur est bien appliqué.
