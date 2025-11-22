# Fonctionnalité de Verrouillage

## Aperçu

La fonctionnalité de verrouillage empêche les modifications d'un thermostat depuis l'interface utilisateur ou les automatisations tout en gardant le thermostat opérationnel.

## Configuration

La fonctionnalité de verrouillage est configurée dans les paramètres du thermostat, sous la section "Verrouillage". Vous pouvez choisir de bloquer :

- **Utilisateurs**: Empêche les modifications depuis l'interface utilisateur de Home Assistant.
- **Automatisations & intégrations**: Empêche les modifications depuis les automatisations, les scripts et autres intégrations.

Vous pouvez également choisir d'utiliser une configuration centrale pour les paramètres de verrouillage.

Vous pouvez également configurer un **Code de Verrouillage** optionnel :

- **Code de Verrouillage** : Un code PIN numérique à 4 chiffres (par exemple, "1234"). S'il est défini, ce code est requis pour verrouiller/déverrouiller le thermostat. Ceci est optionnel et si non configuré, aucun code n'est requis.

## Utilisation

Utilisez ces services pour contrôler l'état de verrouillage :

- `versatile_thermostat.lock` - Verrouille le thermostat
- `versatile_thermostat.unlock` - Déverrouille le thermostat (requiert `code` si configuré)

Exemple d'automatisation :

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

Exemple d'automatisation de déverrouillage avec code :

```yaml
service: versatile_thermostat.unlock
target:
  entity_id: climate.my_thermostat
data:
  code: "1234"
```

## État de Verrouillage

L'état de verrouillage est :

- Visible dans les attributs `is_locked`, `lock_users` et `lock_automations` de l'entité climat.
- Conservé lors des redémarrages de Home Assistant (y compris le code PIN si défini).
- Spécifique à chaque thermostat (chaque thermostat a son propre verrou et code PIN optionnel).

## Lorsque Verrouillé

**Bloqué (depuis l'UI / automatisations / appels externes selon le type de verrou dans la configuration):**

- Changements de mode CVC (y compris marche/arrêt)
- Changements de température cible
- Changements de préréglages et services de configuration des préréglages VTherm
- Appel de service d'action HA

**Autorisé (logique interne VTherm, toujours active):**

- Détection et actions de fenêtre (arrêt ou éco/hors-gel à l'ouverture, ventilateur seul si applicable, restauration du comportement à la fermeture)
- Protections de sécurité (par ex. préréglages de sécurité surchauffe / hors-gel, gestion de la sécurité marche/arrêt)
- Gestion de la puissance et de la surpuissance (y compris le comportement de `PRESET_POWER`)
- Algorithmes de régulation automatique (TPI / PI / PROP) et boucle de contrôle
- Coordination centrale/parent/enfant et autres automatisations internes de VTherm

**Garantie de comportement :**

- Les actions de fenêtre (par exemple : arrêt à l'ouverture, restauration à la fermeture) fonctionnent même lorsque le thermostat est verrouillé.

**Note d'implémentation :**

- Le verrouillage est appliqué sur les appels externes, qui sont les seuls à modifier le `requested_state`. Les opérations internes (comme celles du `SafetyManager` ou du `PowerManager`) contournent le verrouillage par conception car le `StateManager` priorise leur sortie sur les requêtes externes. Le verrouillage empêche uniquement les appels externes de modifier le `requested_state`.

## Cas d'utilisation

- Prévenir les modifications accidentelles pendant les périodes critiques
- Fonctionnalité de verrouillage enfant
- Empêcher temporairement le scheduler de modifier les paramètres actuels
- Sécurité contre le déverrouillage non autorisé (en utilisant le code PIN)