# Revue de l'issue #2077 - Sleep/Maintenance Mode Issue

- **Référence :** [jmcollin78/versatile_thermostat#2077](https://github.com/jmcollin78/versatile_thermostat/issues/2077)
- **État vérifié :** ouverte, non assignée, sans étiquette, jalon, relation ni pull request liée.
- **Branche indiquée par GitHub :** `2077-sleepmaintenance-mode-issue`.
- **Date de revue :** 2026-09-29.
- **Recommandation :** **retenir** comme correction de bug ciblée.

## 1. Résumé fidèle de l'issue

L'auteur utilise une TRV Sonoff TRVZB, configurée comme VTherm `over_climate` avec régulation directe de vanne. Il souhaite le mode sommeil comme mode maintenance : ouvrir physiquement la vanne sans demander de chauffage à la chaudière.

Lors du passage en sommeil, les entités de degré d'ouverture et de fermeture affichent bien respectivement 100 % et 0 %. Toutefois, la TRV reste en `hvac_mode: off`. Pour ce matériel, cet état ferme physiquement la vanne, quelle que soit la valeur envoyée aux entités de degré. Le commentaire du mainteneur confirme ce diagnostic.

## 2. Sources et éléments vérifiés

### Sources GitHub

- Issue #2077 : description, illustration, métadonnées et commentaire du mainteneur, consultés le 2026-09-29.
- Discussion liée #2072 : référencée par l'issue, mais son contenu détaillé n'était pas accessible dans les sources consultées.

### Dépôt local

- [custom_components/versatile_thermostat/thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py) force `valve_open_percent` à 100 quand `is_sleeping` est vrai, tout en exposant le VTherm comme inactif.
- [custom_components/versatile_thermostat/base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) transmet le changement de HVAC à chaque `UnderlyingClimate` lors d'une transition d'état.
- [custom_components/versatile_thermostat/underlyings.py](../../custom_components/versatile_thermostat/underlyings.py) convertit le mode interne `SLEEP` vers le mode Home Assistant `OFF` avant d'appeler `climate.set_hvac_mode` sur le sous-jacent.
- [custom_components/versatile_thermostat/vtherm_hvac_mode.py](../../custom_components/versatile_thermostat/vtherm_hvac_mode.py) confirme que seul l'état affiché du VTherm doit mapper `SLEEP` vers `OFF`; cette conversion ne doit pas nécessairement être réutilisée pour la TRV physique.
- [tests/test_overclimate_valve.py](../../tests/test_overclimate_valve.py) couvre `HEAT -> SLEEP -> HEAT`, mais attend actuellement que le climat sous-jacent soit `OFF` pendant le sommeil, en contradiction avec la promesse d'une vanne ouverte sur les TRV qui ferment à l'arrêt.
- [documentation/fr/over-climate.md](../fr/over-climate.md) décrit le sommeil comme un arrêt du VTherm « tout en maintenant la vanne totalement 100% ouverte ». Les pages EN, DE, CS et PL portent la même promesse fonctionnelle.

## 3. Analyse de pertinence

### Faits établis

1. Le calcul et l'envoi direct des degrés d'ouverture/fermeture atteignent déjà 100 % / 0 % pendant le sommeil.
2. Dans le même flux, le climat sous-jacent reçoit `OFF`, car `SLEEP` est converti vers `OFF` par le chemin générique.
3. La TRVZB signalée ferme physiquement sa vanne lorsque son HVAC est `OFF`; le résultat physique ne correspond donc pas aux entités de degré.
4. Les protections du VTherm pendant le sommeil sont déjà indépendantes de l'état matériel de la TRV : `hvac_action` est `OFF`, `should_device_be_active` est faux et `device_actives` est vide. La chaudière centrale ne doit donc pas être sollicitée.

### Recommandation

**Retenir.** Il s'agit d'une régression fonctionnelle du mode sommeil documenté, reproductible par le test unitaire existant. La correction doit séparer l'état public du VTherm (`OFF` affiché pour le sommeil) de la commande HVAC physique adressée à la TRV.

## 4. Périmètre proposé

### Inclus

- Pour `ThermostatOverClimateValve` uniquement, ne pas transmettre `OFF` au climat sous-jacent lorsque le VTherm entre ou reste en `SLEEP`.
- Commander le mode physique actif correspondant à la configuration du VTherm (`HEAT` en chauffage, `COOL` avec `ac_mode`) afin que la commande de vanne à 100 % puisse être effectivement appliquée par les TRV qui ferment en `OFF`.
- Conserver l'état public Home Assistant du VTherm à `OFF`, le mode interne à `SLEEP`, `hvac_action` à `OFF`, `is_sleeping` à vrai, l'absence d'équipement actif et l'absence de demande chaudière.
- À la sortie de sommeil, conserver la transition existante vers le mode demandé et la régulation normale.
- Corriger le test de transition existant pour vérifier le mode physique actif du climat sous-jacent et ajouter les assertions de non-déclenchement fonctionnel du VTherm.
- Ajouter la couverture de démarrage/restauration en sommeil si elle ne vérifie pas déjà le HVAC sous-jacent actif.

### Exclus

- Toute modification du comportement `SLEEP` de `over_valve`, qui ne pilote pas d'entité `climate` sous-jacente.
- Un paramètre par fabricant, un contournement spécifique Sonoff ou un nouveau réglage utilisateur.
- Tout changement des algorithmes TPI, du pourcentage de sommeil (100 %) ou des limites de vanne.
- Toute modification d'état Home Assistant ou de configuration durant l'analyse.

## 5. Impacts et risques

| Domaine            | Risque                                                                 | Gravité | Probabilité | Mesure proposée                                                                                         |
| ------------------ | ---------------------------------------------------------------------- | ------- | ----------- | ------------------------------------------------------------------------------------------------------- |
| Fonctionnel        | La TRV reste en `OFF` et ferme malgré les nombres à 100 %.             | Élevée  | Élevée      | Tester le HVAC physique actif et les degrés 100 % / 0 %.                                                |
| Chaudière centrale | Une TRV active est comptée comme une demande de chauffage.             | Élevée  | Faible      | Préserver et tester `hvac_action=OFF`, `is_device_active=False` et `device_actives=[]`.                 |
| Compatibilité      | Une TRV pourrait interpréter `HEAT`/`COOL` avec sa consigne mémorisée. | Moyenne | Moyenne     | Réutiliser la consigne régulée déjà envoyée et limiter le changement au sommeil de la classe concernée. |
| Climatisation      | Envoyer `HEAT` à une configuration `ac_mode` serait incohérent.        | Moyenne | Faible      | Couvrir le choix de `COOL` pour `ac_mode`.                                                              |
| Régression         | La sortie de sommeil ne rétablit pas la régulation actuelle.           | Moyenne | Faible      | Tester `HEAT -> SLEEP -> HEAT` et la conservation de consigne/préréglage.                               |

**Sécurité et confidentialité :** aucun nouvel accès, secret ou flux de données.

## 6. Alternatives examinées

1. **Conserver `OFF` et documenter une incompatibilité TRV.**
   - Avantage : aucune modification.
   - Inconvénient : contredit la fonctionnalité documentée et le besoin de maintenance; écartée.

2. **Piloter uniquement les entités `number`.**
   - Avantage : chemin déjà en place.
   - Inconvénient : insuffisant pour les TRV dont `OFF` a priorité sur l'ouverture; écartée.

3. **Maintenir le climat sous-jacent dans son mode physique actif pendant `SLEEP`.**
   - Avantages : traite la cause racine sans changer l'état affiché du VTherm ni le contrat chaudière.
   - Inconvénient : nécessite une distinction explicite entre commande interne au sous-jacent et représentation publique du sommeil; retenue.

## 7. Hypothèses, décisions nécessaires et questions ouvertes

### Hypothèses à valider en conception

- Le bon mode physique est `HEAT` hors `ac_mode` et `COOL` avec `ac_mode`.
- La consigne régulée est déjà disponible ou renvoyée selon le mécanisme existant après l'activation du mode physique, y compris pour les TRV qui exigent une consigne après le changement de HVAC.

### Questions ouvertes

- Aucun comportement constructeur alternatif n'est décrit pour les TRV qui supportent les degrés d'ouverture mais refusent `HEAT`/`COOL`; cette information n'est pas bloquante pour corriger le comportement contractuel courant.
- La mise à jour de la documentation utilisateur n'est a priori pas nécessaire, car sa promesse est déjà correcte; la conception confirmera si une précision opérationnelle doit être ajoutée.

## 8. Suite proposée et critères de passage au développement

1. Approbation explicite de ce rapport et du périmètre.
2. Spécification fonctionnelle couvrant la dissociation état public/commande TRV, les invariants chaudière et les transitions.
3. Conception technique identifiant le point d'interception le plus local, sans modifier le mapping global de `SLEEP` vers `OFF`.
4. Validation utilisateur de la spécification et de la conception convergentes.
5. Développement avec, au minimum, les critères d'acceptation suivants :
   - en `HEAT -> SLEEP`, le VTherm reste affiché `OFF` et la TRV reçoit `HEAT`;
   - la vanne reçoit 100 % / 0 % et s'ouvre physiquement sur une TRV qui ferme en `OFF`;
   - `hvac_action`, activité VTherm et demande chaudière restent à l'arrêt;
   - la sortie de sommeil rétablit la régulation sans perdre consigne ni préréglage;
   - le scénario `ac_mode` transmet `COOL` au sous-jacent;
   - les tests existants hors sommeil restent inchangés.

Aucun code, configuration, dépendance ou état Home Assistant n'a été modifié durant cette revue.