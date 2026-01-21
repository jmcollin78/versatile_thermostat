# Recalibrage des vannes (service recalibrate_valves)

- [Recalibrage des vannes (service recalibrate\_valves)](#recalibrage-des-vannes-service-recalibrate_valves)
  - [Pourquoi cette fonctionnalité ?](#pourquoi-cette-fonctionnalité-)
  - [Principe de fonctionnement](#principe-de-fonctionnement)
  - [Restrictions et prérequis](#restrictions-et-prérequis)
  - [Configuration / accès au service](#configuration--accès-au-service)
  - [Paramètres du service](#paramètres-du-service)
  - [Comportement détaillé](#comportement-détaillé)
  - [Exemples d'automatisation](#exemples-dautomatisation)

## Pourquoi cette fonctionnalité ?

Le service `recalibrate_valves` permet d'exécuter une procédure de calibrage simple des vannes thermostatiques pilotées par un _VTherm_ en régulation par vanne. Il force temporairement les vannes sous-jacentes à leurs positions extrêmes (ouverture complète puis fermeture complète) afin de provoquer un recalibrage des vannes du thermostat.

Ce service est utile quand vous suspectez des valeurs d'ouverture/fermeture incorrectes, des vannes mal calibrées, ou après installation/maintenance des équipements sous-jacents. Par exemple, si votre radiateur chauffe alors que les vannes sont fermées, il est possible qu'un recalibrage soit nécessaire.

⚠️ Le recalibrage effectif est de la responsabilité du thermostat sous-jacent. _VTherm_ ne fait que forcer une ouverture, puis une fermeture maximale. Si cette opération ne fonctionne pas, vous devez voir avec le fournisseur de votre _TRV_ ou faire un calibrage constructeur si disponible.

⚠️ Un recalibrage via cette fonction peut limiter la durée de vie des batteries du _TRV_. Il est conseillé de ne l'utiliser que si vous êtes sûr que les vannes de votre _VTherm_ ont un soucis de calibrage.

## Principe de fonctionnement

Le service suit ces étapes pour l'entité ciblée :

1. Vérifie que l'entité cible est un thermostat de type `ThermostatClimateValve` (régulation par vanne). Sinon le service renvoie une erreur.
2. Vérifie que chaque valve sous-jacente dispose d'une entité `number` configurée pour l'ouverture et la fermeture (attributs `opening_degree` et `closing_degree`). Si une valve manque ces entités, le service refuse l'opération.
3. Mémorise l'état demandé (`requested_state`) du thermostat.
4. Passe le _VTherm_ en mode OFF.
5. Attend `delay_seconds`.
6. Pour chaque valve : force l'ouverture à 100% (en envoyant la valeur correspondante aux entités `number`). Attend `delay_seconds`.
7. Pour chaque valve : force la fermeture à 100% (valeur complémentaire sur l'entité `number`). Attend `delay_seconds`.
8. Restaure l'état demandé initial et met à jour les états/attributs.

Pendant la procédure, le système force directement les entités `number` des vannes en ignorant les seuils et protections automatiques normales (seuils d'ouverture, min/max de l'algorithme). Le service exécute l'opération en tâche de fond et renvoie immédiatement une réponse d'accusé : `{"message": "calibrage en cours"}`.

Le délai entre chaque étape est spécifié par l'utilisateur lors de l'appel du service. La valeur par défaut est de 60 sec pour laisser le temps à la vanne de s'ouvrir ou de se fermer totalement. Le maximum est paramétré à 5 min (300 sec). Le minimum est de 30 sec.

## Restrictions et prérequis

- Le service est **disponible uniquement** pour les thermostats `ThermostatClimateValve` (régulation par vanne).
- Chaque valve sous-jacente doit avoir deux entités `number` configurées :
  - `opening_degree_entity_id` (commande d'ouverture)
  - `closing_degree_entity_id` (commande de fermeture)
- Les entités `number` peuvent avoir des attributs `min` et `max` ; le service mappe les pourcentages (0–100 %) sur ces plages. Si `min`/`max` manquent, la plage par défaut est 0–100.
- Le service protège contre les exécutions concurrentes pour la même entité : si un recalibrage est déjà en cours sur ce thermostat, une nouvelle requête est refusée immédiatement (message de retour indiquant que le recalibrage est en cours).

## Configuration / accès au service

Le service est enregistré en tant que service d'entité. Pour l'appeler via l'interface de Home Assistant, vous devez cibler l'entité climate concernée.

Nom du service : `versatile_thermostat.recalibrate_valves`

Exemple d'appel via `Developer Tools / Services` :

```yaml
service: versatile_thermostat.recalibrate_valves
target:
  entity_id: climate.mon_thermostat
data:
  delay_seconds: 30
```

Le service retourne immédiatement :

```json
{"message": "calibrage en cours"}
```

## Paramètres du service

| Paramètre       | Type    | Description                                                                                                                        |
| --------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `delay_seconds` | integer | Délai (en secondes) à attendre après ouverture complète puis après fermeture complète. Valeurs valides : 30–300 (recommandé : 60). |

Le schéma du service limite la valeur entre `30` et `300` secondes.

## Comportement détaillé

- L'opération est exécutée en tâche de fond. L'appelant reçoit une confirmation immédiate et peut suivre la progression via les logs Home Assistant.
- À la fin de l'opération, l'état demandé (`requested_state`) est restauré (mode HVAC, température cible et preset si présents) et les états sont mis à jour. Le _VTherm_ doit revenir à sa position initiale, à condition que les capteurs restent stables, bien sûr.

## Exemples d'automatisation

1) Déclencher le recalibrage automatiquement une fois par mois (exemple) :

Le YAML suivant déclenche le recalibrage à 03:00 le premier jour de chaque mois :

```yaml
alias: Recalibrage vannes mensuel
trigger:
  - platform: time
    at: '03:00:00'
condition:
  - condition: template
    value_template: "{{ now().day == 1 }}"  # n'exécute que le jour 1 du mois et en mode 'heat'
  - condition: state
    entity_id: climate.mon_thermostat
    state: 'heat'
action:
  - service: versatile_thermostat.recalibrate_valves
    target:
      entity_id: climate.mon_thermostat
    data:
      delay_seconds: 60
  - service: persistent_notification.create
    data:
      title: "🔧 Recalibrage mensuel démarré"
      message: "🔧 Un recalibrage de vannes a été lancé pour climate.mon_thermostat"

```

> ![Astuce](images/tips.png) _*Conseils*_
>
> - Testez le recalibrage sur un _VTherm_ qui ne contient qu'une seule vanne pour commencer et surveillez les logs et les valeurs envoyées aux entités `number` avant de l'exécuter sur plusieurs pièces.
> - `delay_seconds` doit être suffisamment long pour permettre à la vanne physique d'atteindre la position (60 s est un bon point de départ pour la plupart des vannes électriques).
