# Preset Temporisé

- [Preset Temporisé](#preset-temporisé)
  - [Objectif](#objectif)
  - [Comment ça fonctionne](#comment-ça-fonctionne)
  - [Activer un preset temporisé](#activer-un-preset-temporisé)
  - [Annuler un preset temporisé](#annuler-un-preset-temporisé)
  - [Attributs personnalisés](#attributs-personnalisés)
  - [Évènements](#évènements)
  - [Dérogation manuelle avec retour automatique](#dérogation-manuelle-avec-retour-automatique)
  - [Exemples d'automatisation](#exemples-dautomatisation)
    - [Boost de 30 minutes à la rentrée](#boost-de-30-minutes-à-la-rentrée)
    - [Notification à la fin du boost](#notification-à-la-fin-du-boost)
    - [Bouton de boost sur le dashboard](#bouton-de-boost-sur-le-dashboard)

## Objectif

La fonction de preset temporisé permet de forcer un preset sur un _VTherm_ pour une durée déterminée. À la fin de cette durée, le preset original (celui qui était défini dans `requested_state`) est automatiquement restauré.

Cette fonctionnalité est utile dans plusieurs scénarios :
- **Boost de chauffage** : Augmenter temporairement la température (ex: preset Confort) pendant 30 minutes lorsque vous rentrez chez vous
- **Mode invité** : Activer un preset plus chaud pour quelques heures lorsque vous recevez des invités
- **Séchage** : Forcer un preset haut pendant un temps limité pour accélérer le séchage d'une pièce
- **Économies ponctuelles** : Forcer temporairement un preset Eco pendant une période d'absence courte

## Comment ça fonctionne

1. Vous appelez le service `versatile_thermostat.set_timed_preset` avec un preset et une durée
2. Le _VTherm_ bascule immédiatement sur le preset spécifié
3. Un timer est démarré pour la durée indiquée
4. À la fin du timer, le _VTherm_ restaure automatiquement le preset original
5. Un évènement `versatile_thermostat_timed_preset_event` est émis à chaque changement

> ![Tip](images/tips.png) _*Notes*_
> - Le preset temporisé a une priorité intermédiaire : il est appliqué après les contrôles de sécurité et de puissance (délestage), mais avant les autres fonctionnalités (présence, mouvement, etc.)
> - Si vous changez manuellement le preset pendant qu'un preset temporisé est actif, le timer est annulé
> - La durée maximale est de 1440 minutes (24 heures)

## Activer un preset temporisé

Pour activer un preset temporisé, utilisez soit la _VTherM UI Card_, soit l'action (le service) `versatile_thermostat.set_timed_preset` :

```yaml
service: versatile_thermostat.set_timed_preset
data:
  preset: "boost"
  duration_minutes: 30
target:
  entity_id: climate.mon_thermostat
```

Paramètres :
- `preset` : Le nom du preset à activer. Doit être un preset valide configuré sur le _VTherm_ (ex: `eco`, `comfort`, `boost`, `frost`, etc.)
- `duration_minutes` : La durée en minutes (entre 1 et 1440)

## Annuler un preset temporisé

Pour annuler un preset temporisé avant la fin de sa durée, utilisez soit la _VTherM UI Card_, soit l'action (le service) `versatile_thermostat.cancel_timed_preset` :

```yaml
service: versatile_thermostat.cancel_timed_preset
target:
  entity_id: climate.mon_thermostat
```

Lorsque vous annulez un preset temporisé, le preset original est immédiatement restauré.

## Attributs personnalisés

Lorsqu'un preset temporisé est actif, les attributs suivants sont disponibles dans la section `timed_preset_manager` des attributs du _VTherm_ :

| Attribut             | Signification                                                         |
| -------------------- | --------------------------------------------------------------------- |
| `is_active`          | `true` si un preset temporisé est actif, `false` sinon                |
| `preset`             | Le nom du preset temporisé actif (ou `null` si aucun)                 |
| `end_time`           | La date/heure de fin du preset temporisé (format ISO)                 |
| `remaining_time_min` | Le temps restant en minutes avant la fin du preset temporisé (entier) |

Exemple d'attributs :
```yaml
timed_preset_manager:
  is_active: true
  preset: "boost"
  end_time: "2024-01-15T14:30:00+00:00"
  remaining_time_min: 25
```

## Évènements

L'évènement `versatile_thermostat_timed_preset_event` est émis lors des changements de preset temporisé.

Données de l'évènement :
- `entity_id` : L'identifiant du _VTherm_
- `name` : Le nom du _VTherm_
- `timed_preset_active` : `true` si un preset temporisé vient d'être activé, `false` s'il vient d'être désactivé
- `timed_preset_preset` : Le nom du preset temporisé
- `old_preset` : Le preset précédent (avant l'activation du preset temporisé)
- `new_preset` : Le nouveau preset actif

## Dérogation manuelle avec retour automatique

Lorsque vous changez manuellement la température cible, _VTherm_ passe normalement sur le preset `none` et y reste jusqu'à ce que vous sélectionniez à nouveau un preset. Si une **durée de dérogation manuelle** est configurée, _VTherm_ revient automatiquement en arrière après cette durée.

La durée se règle dans la configuration avancée (`manual_override_duration_min`, en minutes). Elle peut être définie dans la configuration centrale et surchargée par _VTherm_. Voir [configuration avancée](feature-advanced.md#durée-de-dérogation-manuelle). La valeur par défaut `0` désactive la fonction et le comportement reste alors inchangé.

Fonctionnement :
1. Un changement manuel de la température cible (depuis l'interface, depuis une automatisation qui appelle `climate.set_temperature`, ou depuis l'équipement sous-jacent quand `Follow underlying temperature change` est activé) démarre une dérogation manuelle. La température manuelle s'applique immédiatement.
2. Un nouveau changement manuel pendant la dérogation relance le minuteur avec la durée complète.
3. À l'expiration du minuteur, le preset actif avant le changement manuel est restauré.
4. Si un preset temporisé était actif au moment du changement manuel, il reprend à la fin de la dérogation, jusqu'à sa propre heure de fin. Si cette heure est déjà passée, le preset actif avant le preset temporisé est restauré.
5. Si aucun preset n'était actif (`none`) avant le changement manuel, aucune dérogation ne démarre.

La dérogation manuelle réutilise le mécanisme des presets temporisés : elle apparaît comme un preset temporisé `none` et survit à un redémarrage de Home Assistant.

> ![Astuce](images/tips.png) _*Notes*_
> - Sélectionner un preset pendant la dérogation manuelle l'annule : le preset sélectionné s'applique et rien n'est restauré plus tard.
> - Activer un preset temporisé pendant la dérogation manuelle la remplace.
> - Annuler le preset temporisé pendant la dérogation manuelle restaure le preset actif avant le changement manuel.
> - La fenêtre, la sécurité, le délestage et le mode central gardent leur priorité pendant la dérogation manuelle.

Les attributs `timed_preset_manager` comportent trois clés supplémentaires :

| Attribut             | Signification                                                                  |
| -------------------- | ------------------------------------------------------------------------------ |
| `is_manual_override` | `true` si le preset temporisé actif est une dérogation manuelle                |
| `resume_preset`      | Le preset temporisé interrompu par la dérogation manuelle, repris à sa fin     |
| `resume_end_time`    | La date/heure de fin du preset temporisé interrompu (format ISO)               |

L'évènement `versatile_thermostat_timed_preset_event` contient aussi un champ `manual_override` à `true` lorsque l'évènement concerne une dérogation manuelle.

## Exemples d'automatisation

### Boost de 30 minutes à la rentrée

```yaml
automation:
  - alias: "Boost chauffage à la rentrée"
    trigger:
      - platform: state
        entity_id: binary_sensor.presence_maison
        to: "on"
    condition:
      - condition: numeric_state
        entity_id: climate.salon
        attribute: current_temperature
        below: 19
    action:
      - service: versatile_thermostat.set_timed_preset
        data:
          preset: "boost"
          duration_minutes: 30
        target:
          entity_id: climate.salon
```

### Notification à la fin du boost

```yaml
automation:
  - alias: "Notification fin de boost"
    trigger:
      - platform: event
        event_type: versatile_thermostat_timed_preset_event
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.timed_preset_active == false }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Thermostat"
          message: "Le boost de {{ trigger.event.data.name }} est terminé"
```

### Bouton de boost sur le dashboard

Créez un bouton avec une carte de type `button` :

```yaml
type: button
tap_action:
  action: call-service
  service: versatile_thermostat.set_timed_preset
  data:
    preset: boost
    duration_minutes: 30
  target:
    entity_id: climate.salon
name: Boost 30 min
icon: mdi:fire
```
