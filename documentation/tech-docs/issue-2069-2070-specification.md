# Spécification fonctionnelle / Functional Specification — Résolution conjointe des issues #2069 et #2070

---

## Partie 1 — Version française

### 1. Titre et métadonnées

| Champ | Valeur |
| --- | --- |
| Nom | Corrections du plancher `max_closing_degree` et de la détection d'activité des vannes (`over_valve` et régulation de vanne `over_climate`) |
| Identifiant | SPEC-2069-2070 |
| Version | 1.1 |
| Statut | Convergé avec la conception DESIGN-2069-2070 v1.0 |
| Date | 2026-09-24 (v1.1 : clôture QC-001/QC-002) |
| Propriétaire | Mainteneur versatile_thermostat |
| Sources analysées | `documentation/tech-docs/issue-2069-2070.md`, `documentation/tech-docs/issue-2069-2070-en.md`, `documentation/tech-docs/issue-2069-2070-design.md` (DESIGN-2069-2070 v1.0), `custom_components/versatile_thermostat/opening_degree_algorithm.py` (`OpeningClosingDegreeCalculation`), `custom_components/versatile_thermostat/underlyings.py` (`UnderlyingValve`, `UnderlyingValveRegulation`), `custom_components/versatile_thermostat/config_schema.py` (revue, pas de relecture ligne à ligne), issues GitHub #2069 (PR) et #2070 |

### 2. Contexte et objectifs

Deux défauts distincts, à corriger ensemble sur la branche de résolution #2070 :

1. **Issue #2069 (PR fermée sans fusion, correctifs à reprendre)** : pour un VTherm `over_valve`, la commande effective d'arrêt est le plancher `100 - max_closing_degree`. Or les prédicats `should_device_be_active` et `is_device_active` de `UnderlyingValve` comparent la commande effective au minimum de l'entité `number` (`self._min_open`) uniquement. Une vanne maintenue au plancher, donc sans demande de chauffage, est donc déclarée active. De même, lors de `check_initial_state`, une vanne sans demande est refermée au minimum de l'entité (`self._min_open`) et non au plancher effectif.
2. **Issue #2070** : dans `OpeningClosingDegreeCalculation.calculate_opening_closing_degree`, la branche d'interpolation (demande brute `>= opening_threshold`) démarre à `min_opening_degree`, sans garanty de plancher. Si `min_opening_degree < 100 - max_closing_degree`, le franchissement du seuil fait passer la commande de `100 - max_closing_degree` (branche sous le seuil) à une valeur inférieure au plancher : rupture de monotonie et commande pouvant descendre sous `100 - max_closing_degree`.

**Valeur attendue** : cohérence entre l'état publié par VTherm (`hvac_action`, liste des sous-jacents actifs, chaudière centrale) et la demande réelle de chauffage ; comportement physique garanti sur toute la plage de demande.

**Périmètre fonctionnel** : les VTherm de type `over_valve`, et les VTherm `over_climate` avec régulation de vanne pour ce qui relève de l'algorithme partagé `OpeningClosingDegreeCalculation`.

### 3. Acteurs et cas d'utilisation

| Acteur | Cas d'utilisation |
| --- | --- |
| Utilisateur final | Configure un VTherm `over_valve` avec `opening_threshold_degree`, `max_opening_degrees` (et éventuellement `min_opening_degrees`, `max_closing_degree`) ; observe `hvac_action` et la position de vanne |
| VTherm (`over_valve`) | Calcule la commande effective de vanne depuis la demande TPI brute et détermine son état d'activité |
| VTherm (`over_climate` + régulation vanne) | Utilise le même algorithme pour envoyer `opening_degree` / `closing_degree` aux entités dédiées |
| Chaudière centrale / consommateurs d'état | Consomment `is_device_active` / `hvac_action` pour décider de l'activation |
| Vanne physique / entité `number` | Reçoit la commande effective et remonte son état |

Déroulement nominal `over_valve` : la demande TPI brute est calculée → `set_valve_open_percent` convertit la demande en commande via `_get_controlled_percent` → la commande est envoyée et bornée aux limites de l'entité → les prédicats d'activité et `hvac_action` sont publiés de manière cohérente avec la demande brute.

### 4. Exigences fonctionnelles

- **FR-001** — Le système doit garantir que, pour toute demande TPI brute de 0 à 100 %, la commande effective d'ouverture envoyée à la vanne reste supérieure ou égale au plancher `100 - max_closing_degree`, après application des bornes de l'entité sous-jacente, pour `over_valve`.
- **FR-002** — Le système doit garantir que la fonction de conversion demande brute → commande effective est monotone croissante (au sens large) sur [0 ; 100], y compris au franchissement de `opening_threshold_degree`.
- **FR-003** — Le système doit déterminer l'activité d'une vanne `over_valve` avec une échelle unique **pour chaque prédicat** : (a) l'activité *désirée* (`should_device_be_active`) doit être évaluée en comparant la demande TPI brute à `opening_threshold_degree` ; (b) l'activité *observée* (`is_device_active`) doit être évaluée en comparant l'ouverture physique réelle de la vanne au plancher physique effectif `max(100 - max_closing_degree, min de l'entité)`. Le système ne doit jamais comparer `opening_threshold_degree` (échelle de demande brute) à la commande effective ou à l'état de la vanne (échelle physique). *(Décision QC-001 entérinée, option 1 — voir DESIGN-2069-2070 §5.3, décision D1.)*
- **FR-004** — Le système doit déclarer inactive une vanne `over_valve` sans demande de chauffage (demande brute nulle) même si sa commande effective (au plancher) est supérieure au minimum de l'entité `number`. La valeur mémorisée de la demande brute doit être remise à zéro lors de l'arrêt (`turn_off`) et de la refermeture au démarrage, afin que les prédicats d'activité restent cohérents avec l'absence de demande. L'état publié correspondant (`hvac_action`) doit être cohérent avec cette inactivité.
- **FR-005** — Le système doit déclarer active une vanne `over_valve` recevant une demande brute supérieure ou égale à `opening_threshold_degree` (et strictement positive), y compris dans le cas valide `opening_threshold_degree > max_opening_degrees` avec une demande brute de 100 %.
- **FR-006** — Lors de `check_initial_state` (démarrage ou rechargement) d'un VTherm `over_valve`, le système doit renvoyer une vanne sans demande au plancher effectif `100 - max_closing_degree` (borné aux limites de l'entité), et non systématiquement au minimum de l'entité `number`.
- **FR-007** — Les exigences FR-001, FR-002 et FR-003 doivent s'appliquer également au VTherm `over_climate` avec régulation de vanne pour la partie relevant de l'algorithme partagé `OpeningClosingDegreeCalculation` (commandes `opening_degree` et `closing_degree`).
- **FR-008** — Le système doit conserver la compatibilité des configurations par défaut et existantes : aucune combinaison aujourd'hui admise par le flux de configuration et le schéma (notamment `max_opening_degrees < opening_threshold_degree`, `max_closing_degree = 100`) ne doit être rejetée ni voir son comportement se dégrader hors des corrections visées.
- **FR-009** — La documentation utilisateur du comportement (plancher, détection d'activité, monotonie) doit être publiée de façon équivalente dans les cinq guides localisés (`en`, `fr`, `cs`, `de`, `pl` — `documentation/*/over-valve.md`) **dans la même livraison que le correctif**. *(Décision QC-002 entérinée — voir DESIGN-2069-2070 §5.5, décision D2.)*

### 5. Règles métier

- **BR-001** — Pour `over_valve` : une vanne est considérée active si et seulement si la demande TPI brute est `> 0` et `>= opening_threshold_degree` (sémantique actuelle de l'algorithme). Exceptions : demande brute nulle → toujours inactive ; demande brute inconnue (avant le premier cycle) → inactive ; configurations sans `opening_threshold_degree` ni `min/max_opening_degrees` configurés (configurations par défaut) → le comportement existant (comparaison de la commande effective au minimum de l'entité) est conservé. Priorité : haute.
- **BR-002** — Plancher effectif : pour toute demande, la commande effective `>= max(100 - max_closing_degree, min de l'entité)` — le plancher algorithmique et la borne basse de l'entité sont appliqués ensemble, sans que l'un annule l'autre. Priorité : haute.
- **BR-003** — Cas valide `opening_threshold_degree > max_opening_degrees` avec demande brute de 100 % : la commande effective vaut `max_opening_degrees` (le maximum configuré, borné au maximum de l'entité) ; l'état doit être `heating` / sous-jacent actif. Priorité : haute.
- **BR-004** — À l'arrêt ou sans demande (`turn_off`, `check_initial_state`), la commande d'une vanne `over_valve` est l'image du plancher : conversion de la demande 0 par le même algorithme que la commande normale (cohérent avec `turn_off` qui appelle `_get_controlled_percent(0)`), et la demande brute mémorisée est remise à zéro dans la même opération. Priorité : moyenne.
- **BR-005** — Pour `UnderlyingValveRegulation` (régulation de vanne `over_climate`) : ses prédicats d'activité déjà redéfinis (comparaison de l'état réel au plancher `100 - max_closing_degree` pour `is_device_active`, comparaison de la demande à `opening_threshold` pour `should_device_be_active`) ne doivent pas être modifiés au titre de #2069 ; seule la correction algorithmique partagée #2070 le concerne. Priorité : moyenne.

### 6. Contraintes fonctionnelles

- Aucune modification de `UnderlyingValveRegulation` n'est imposée par la présente spécification, sauf si l'implémentation de FR-007 l'exige pour préserver le plancher des commandes `opening_degree` / `closing_degree`.
- Aucune nouvelle validation de configuration n'est exigée ; l'ajout d'une validation `max_opening_degrees >= opening_threshold_degree` est explicitement exclu (alternative rejetée par la revue) tant que la correction algorithmique préserve les configurations existantes.
- La correction doit rester compatible avec les limites physiques de l'entité `number` (`min`/`max` de l'état de l'entité, appliqués par `clamp_sent_value`).
- Documentation localisée : le dépôt publie des guides en 5 langues ; toute modification de comportement documentée doit y être reportée (contrainte héritée de la spécification #1348).

### 7. Critères d'acceptation

#### CA-A — Plancher garanti (#2070, FR-001, FR-002, BR-002)

| # | Demande brute | Paramètres | Commande effective attendue (`over_valve`) |
| --- | --- | --- | --- |
| A1 | 0 | défauts (`max_closing_degree=100`) plancher 0 | 0 |
| A2 | 50 | `max_closing_degree=60` (plancher 40), `min_opening_degree=10`, `max_opening_degree=100`, `opening_threshold=30` | ≥ 40 |
| A3 | 35 | mêmes paramètres que A2 (au-dessus du seuil) : l'interpolation part de `min_opening_degree=10` | ≥ 40 (corrigé : l'interpolation doit être bornée au plancher) |
| A4 | 100 | mêmes paramètres que A2 | 100 |
| A5 | 100 | `opening_threshold_degree=60`, `max_opening_degrees=50`, `max_closing_degree=100` | 50, état `heating`, sous-jacent actif (BR-003) |

Le passage de la demande de 29 à 31 (seuil 30) dans A2 ne doit jamais faire diminuer la commande effective (monotonie FR-002).

#### CA-B — Détection d'activité (`over_valve`, #2069, FR-003, FR-004, FR-005, BR-001)

| # | Situation | `hvac_action` attendu | Vanne listée active |
| --- | --- | --- | --- |
| B1 | Demande brute 0, vanne au plancher 40 (supérieur au min entité 0) | `idle` ou `off` (cohérent absence de demande) | Non |
| B2 | Demande brute 100, `opening_threshold_degree=60 > max_opening_degrees=50`, vanne à 50 | `heating` | Oui |
| B3 | Demande brute 25, `opening_threshold_degree=30`, vanne au plancher | `idle` / inactif | Non |
| B4 | Demande brute 30 (égalité de seuil, > 0) | actif | Oui |

#### CA-C — `check_initial_state` (`over_valve`, FR-006, BR-004)

- C1 : VTherm `over_valve` sans demande, vanne ouverte à 60, plancher effectif 40, min entité 0 → après `check_initial_state`, la vanne est à 40 (plancher), pas à 0.
- C2 : VTherm avec demande réelle, vanne refermée au plancher → `check_initial_state` doit renvoyer la commande correspondant à la demande (rattrapage existant).

#### CA-D — Régulation de vanne `over_climate` (FR-007)

- D1 : avec les paramètres A2, toute demande envoyée via `UnderlyingValveRegulation.send_percent_open` produit un `opening_degree >= 40` ; `closing_degree` est le complément à 100 attendu.
- D2 : aucun changement de comportement des prédicats de `UnderlyingValveRegulation`pour des configurations et demandes non visées par #2070 (tests existants inchangés).

#### CA-E — Compatibilité et documentation (FR-008, FR-009)

- E1 : les tests existants de `tests/test_valve.py`, `tests/test_check_initial_state.py`, `tests/test_overclimate_valve.py` non liés aux défauts corrigés restent valides en dehors des attentes explicitement corrigées.
- E2 : les cinq guides `over-valve.md` (`en`, `fr`, `cs`, `de`, `pl`) contiennent le même paragraphe de comportement traduit, livrés dans la même PR que le correctif (décision QC-002 entérinée).
- E3 (nouveau, traçant la garde de compatibilité D3) : pour une configuration `over_valve` sans `opening_threshold_degree` ni `min/max_opening_degrees` configurés, les prédicats d'activité conservent le comportement antérieur (non-régression des configurations par défaut).

### 8. Fonctions non prises en compte

- Toute modification de `UnderlyingValveRegulation` au-delà de ce que FR-007 exige (prédicats, `turn_off`), justifiée par l'exclusion actée lors de la revue de la PR #2069.
- Nouvelle validation de configuration interdisant `max_opening_degrees < opening_threshold_degree` (alternative rejetée seule).
- Refonte générale de l'algorithme TPI ou d'autres types de VTherm (`over_switch`, `over_climate` sans vanne).
- Changement d'API ou de configuration utilisateur.

### 9. Évolutions futures proposées

- Ajout d'un avertissement (non bloquant) dans le flux de configuration lorsque `max_opening_degrees < opening_threshold_degree` ou `max_opening_degrees < 100 - max_closing_degree` — dépend de QC-003 et de la politique de validation.
- Exposition de la demande TPI brute comme attribut/diagnostic pour faciliter l'observation de l'échelle de référence.

### 10. Hypothèses, questions ouvertes et traçabilité

**Faits établis (vérifiés dans le code) :**
- `OpeningClosingDegreeCalculation.calculate_opening_closing_degree` (`opening_degree_algorithm.py`, lignes ~44-74) : sous le seuil, sortie `100 - max_closing_degree` ; au-dessus du seuil, interpolation de `min_opening_degree` vers `max_opening_degree` — sans plancher dans la branche d'interpolation (cause du défaut #2070).
- `UnderlyingValve.should_device_be_active` / `is_device_active` (`underlyings.py`, lignes ~1285-1299) : comparaison à `self._min_open` uniquement, sans prise en compte du plancher.
- `UnderlyingValve.check_initial_state` : fermeture via `send_percent_open(fixed_value=self._min_open)`.
- `UnderlyingValve.turn_off` : `self._percent_open = self._get_controlled_percent(0)` — référence de cohérence pour FR-006.
- `UnderlyingValveRegulation` redéfinit `_get_controlled_percent` (identité brute) et `send_percent_open` (conversion au moment de l'envoi) ; ses prédicats `is_device_active` (comparaison au plancher `100 - max_closing_degree`) et `should_device_be_active` (comparaison de `_percent_open`, valeur brute, à `opening_threshold`) utilisent déjà chacune une échelle cohérente.
- `config_schema.py` : `opening_threshold_degree` et `max_opening_degrees` validés indépendamment (revue issue-2069-2070 ; pas de relecture ligne à ligne dans le cadre de cette spécification).

**Hypothèses (confirmées par la revue) :**
- `opening_threshold_degree` s'interprète sur la demande TPI brute (sémantique de l'algorithme).
- La combinaison du contre-exemple A5 est admise par l'UI ; le traitement YAML reste à vérifier côté développement si une correction touche les validations.

**Décisions actées :**
- #2069 et #2070 sont corrigés ensemble sur la branche de résolution #2070 ; la PR #2069 est fermée sans fusion et ses correctifs repris.
- **QC-001 (tranché — DESIGN-2069-2070 v1.0, décision D1)** : échelle unique *par prédicat*. L'activité désirée (`should_device_be_active`) est évaluée sur la demande TPI brute comparée à `opening_threshold_degree` ; l'activité observée (`is_device_active`) est évaluée sur l'ouverture physique réelle comparée au plancher physique effectif `max(100 - max_closing_degree, min de l'entité)`. L'alternative 2 (conversion du seuil en seuil physique par vanne) est écartée : elle exigerait de dupliquer la formule de conversion (clamp entité inclus) pour un seuil jamais envoyé, avec risque de divergence entre envoi et comparaison. FR-003, FR-004 et BR-001 reflètent cette décision ; BR-001 intègre les exceptions de la garde de compatibilité (configurations par défaut, demande inconnue).
- **QC-002 (tranché — DESIGN-2069-2070 v1.0, décision D2)** : les cinq documentations localisées (`en`, `fr`, `cs`, `de`, `pl`) sont livrées dans la même PR que le correctif, afin d'éviter une fenêtre d'incohérence documentaire entre versions publiées. FR-009 et CA-E2 reflètent cette décision.

**Questions ouvertes (non bloquantes pour le développement) :**
- **QC-003 (nouveau, hérité de la conception — DESIGN-2069-2070 QO-1)** : dans le cas dégénéré où `max_opening_degrees < 100 - max_closing_degree` (le plancher algorithmique dépasse le maximum configuré), le clamp au plancher peut produire une commande supérieure à `max_opening_degree` ; le clamp aux bornes de l'entité `number` reste l'arbitre physique. Ce cas, admis par le flux de configuration actuel, doit être observé à l'implémentation ; le lever éventuel d'un avertissement non bloquant dans le flux de configuration reste une évolution future (section 9).

**Traçabilité de convergence (v1.1) :** la présente spécification v1.1 et DESIGN-2069-2070 v1.0 couvrent le même périmètre (`over_valve` + algorithme partagé `OpeningClosingDegreeCalculation` pour la régulation de vanne `over_climate`) ; toutes les exigences FR-001 à FR-009, règles BR-001 à BR-005 et critères CA-A à CA-E sont couverts par la conception (matrice de traçabilité DESIGN §11) ; aucune contradiction entre les deux documents n'a été relevée lors du cycle de convergence ; les deux questions initiales (QC-001, QC-002) sont fermées et les questions restantes (QC-003/QO) sont déclarées non bloquantes.

### 11. Historique des versions

- Version 1.1 (2026-09-24) — cycle de convergence avec la conception : QC-001 clôturée (option 1, décision D1) et reflétée dans FR-003/FR-004/BR-001/BR-004 ; QC-002 clôturée (décision D2) et reflétée dans FR-009/CA-E2 ; FR-003 précisé en échelle unique *par prédicat* ; garde de compatibilité des configurations par défaut tracée par BR-001 et le nouveau critère CA-E3 ; question QC-003 créée (cas dégénéré `max_opening_degrees < 100 - max_closing_degree`, non bloquante). Aucune exigence supprimée ni affaiblie.
- Version 1.0 (2026-09-24) — création initiale.
