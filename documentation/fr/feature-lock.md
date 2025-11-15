# Fonctionnalité de Verrouillage

## Aperçu

La fonctionnalité de verrouillage empêche les modifications de la configuration d'un thermostat depuis l'interface utilisateur ou les automatisations tout en gardant le thermostat opérationnel.

## Configuration

La fonctionnalité de verrouillage est configurée dans les paramètres du thermostat, sous la section "Verrouillage". Vous pouvez choisir de bloquer :

- **Utilisateurs**: Empêche les modifications depuis l'interface utilisateur de Home Assistant.
- **Automatisations & intégrations**: Empêche les modifications depuis les automatisations, les scripts et autres intégrations.

Vous pouvez également choisir d'utiliser une configuration centrale pour les paramètres de verrouillage.

## Utilisation

Utilisez ces services pour contrôler l'état de verrouillage :

- `versatile_thermostat.lock` - Verrouille le thermostat
- `versatile_thermostat.unlock` - Déverrouille le thermostat

Exemple d'automatisation :

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

## État de Verrouillage

L'état de verrouillage est :

- Visible dans les attributs `is_locked`, `lock_users` et `lock_automations` de l'entité climat.
- Conservé lors des redémarrages de Home Assistant.
- Spécifique à chaque thermostat (chaque thermostat a son propre verrou).

## Lorsque Verrouillé

**Bloqué (depuis l'interface utilisateur / automatisations / appels externes):**

- Changements de mode CVC (y compris marche/arrêt)
- Changements de température cible
- Changements de préréglages et services de configuration des préréglages VTherm
- Changements d'état de présence via les services VTherm
- Changements de configuration de sécurité via les services VTherm
- Changements de dérogation de fenêtre via les services VTherm
- Modes ventilateur/balancement/ventilation lorsqu'ils sont exposés par VTherm

**Autorisé (logique interne VTherm, toujours active):**

- Détection et actions de fenêtre (arrêt ou éco/hors-gel à l'ouverture, ventilateur seul si applicable, restauration du comportement à la fermeture)
- Protections de sécurité (par ex. préréglages de sécurité surchauffe / hors-gel, gestion de la sécurité marche/arrêt)
- Gestion de la puissance et de la surpuissance (y compris le comportement de `PRESET_POWER`)
- Algorithmes de régulation automatique (TPI / PI / PROP) et boucle de contrôle
- Coordination centrale/parent/enfant et autres automatisations internes de VTherm

**Garantie de comportement :**

- Les actions de fenêtre (par exemple : arrêt à l'ouverture, restauration à la fermeture) fonctionnent même lorsque le thermostat est verrouillé.

**Note d'implémentation :**

- Le verrouillage est appliqué sur les appels externes, tandis que VTherm utilise le contexte de Home Assistant en interne pour que ses propres fonctionnalités puissent toujours ajuster le thermostat lorsqu'il est verrouillé.

## Cas d'utilisation

- Prévenir les modifications accidentelles pendant les périodes critiques
- Fonctionnalité de verrouillage parental