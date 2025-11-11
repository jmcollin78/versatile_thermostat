# Fonction de verrouillage

## Vue d'ensemble

La fonction de verrouillage empêche toute modification de la configuration d'un thermostat depuis l'interface utilisateur ou via des automatisations, tout en laissant le thermostat pleinement opérationnel.

## Utilisation

Utilisez les services suivants pour contrôler l'état de verrouillage :

- `versatile_thermostat.lock` - Verrouille le thermostat
- `versatile_thermostat.unlock` - Déverrouille le thermostat

Exemple d'automatisation :

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

## État de verrouillage

L'état de verrouillage est :

- Visible dans l'attribut `is_locked` de l'entité climate
- Conservé lors des redémarrages de Home Assistant
- Propre à chaque thermostat (chaque thermostat possède son propre verrouillage)

## Lorsque le thermostat est verrouillé

**Bloqué (depuis l'UI / automatisations / appels externes) :**

- Changement de mode HVAC (y compris marche/arrêt)
- Modification de la température de consigne
- Changement de préréglage et services VTherm de configuration des préréglages
- Changement d'état de présence via les services VTherm
- Modification de la configuration de sécurité via les services VTherm
- Contournement de la détection de fenêtre (window bypass) via les services VTherm
- Modes ventilation / oscillation lorsque exposés par VTherm

**Autorisé (logique interne VTherm, toujours active) :**

- Détection de fenêtre ouverte et actions associées (arrêt, température éco/gel, mode ventilation seul, restauration à la fermeture)
- Protections de sécurité (surchauffe, hors-gel, préréglages de sécurité)
- Gestion de puissance / délestage et comportements liés au mode puissance
- Algorithmes automatiques de régulation (TPI / PI / PROP) et boucle de contrôle
- Coordination centrale / parent / enfant et autres automatismes internes VTherm

**Garantie de comportement :**

- Les actions liées aux fenêtres (par exemple arrêt à l'ouverture, restauration à la fermeture) fonctionnent même lorsque le thermostat est verrouillé.

## Cas d'usage

- Empêcher toute modification accidentelle pendant des périodes critiques
- Fonctionnalité de verrouillage enfant