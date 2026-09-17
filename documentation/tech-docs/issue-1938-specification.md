# Spécification fonctionnelle — Issue #1938 : Mode sommeil (Sleep Mode) pour les VTherm de type `over_valve`

# Functional Specification — Issue #1938: Sleep Mode for `over_valve` VTherms

---

## Version française

### 1. Titre et métadonnées

| Champ                       | Valeur                                                                                                                                                         |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Nom**                     | Mode sommeil pour `ThermostatOverValve` (`over_valve`)                                                                                                         |
| **Version**                 | 1.1                                                                                                                                                            |
| **Statut**                  | Validée, implémentée, revue de conception et testée manuellement                                                                                               |
| **Date**                    | 15 septembre 2026                                                                                                                                              |
| **Propriétaire**            | Équipe Versatile Thermostat                                                                                                                                    |
| **Référence issue**         | [jmcollin78/versatile_thermostat#1938](https://github.com/jmcollin78/versatile_thermostat/issues/1938) (ouverte ; libellés `enhancement`, `Vote needed`, `P1`) |
| **Rapport de revue validé** | `documentation/tech-docs/issue-1938-review.md` (revue du 15 septembre 2026, recommandation : retenir)                                                          |

**Sources analysées (vérifiées) :**

- `custom_components/versatile_thermostat/base_thermostat.py` :
  - `build_hvac_list()` (l. ~915-927) : modes par défaut `HEAT`/`OFF` (ou `HEAT`, `COOL`, `OFF` en `ac_mode`) ;
  - `is_sleeping` (l. ~1445-1447) : retourne `False` par défaut ;
  - `service_set_hvac_mode_sleep()` (l. ~2274-2291) : lève `NotImplementedError` hors `over_climate` avec régulation directe de vanne ;
  - `activable_underlying_entities` (l. ~1385-1388), `device_actives` / `nb_device_actives` (l. ~1063-1077) : base du comptage des équipements actifs pour la chaudière centrale ;
  - `update_custom_attributes()` (l. ~1990-2050) : expose déjà l'attribut `is_sleeping`.
- `custom_components/versatile_thermostat/thermostat_climate_valve.py` : implémentation de référence — `build_hvac_list()` exposant `HEAT`, `SLEEP`, `OFF` / `COOL`, `SLEEP`, `OFF` (l. ~341-348), `recalculate()` plafonnant la demande brute à 100 % pendant le sommeil (l. ~341-348 et ~426-447), `calculate_hvac_action()` forçant `OFF` pendant le sommeil, `should_device_be_active` / `device_actives` vides pendant le sommeil, `is_sleeping` (l. ~430), `service_set_hvac_mode_sleep()` (l. ~438-447), `restore_specific_previous_state()` restaurant `hvac_off_reason = HVAC_OFF_REASON_SLEEP_MODE`.
- `custom_components/versatile_thermostat/thermostat_valve.py` : `ThermostatOverValve` ne redéfinit ni `build_hvac_list`, ni `is_sleeping`, ni le service sommeil ; `recalculate()`/`apply_valve_command_percent()` (l. ~242-358) constituent le chemin de conversion TPI actuel ; `update_custom_attributes()` expose `valve_command_percent` / `valve_command_by_valve`.
- `custom_components/versatile_thermostat/underlyings.py` :
  - `UnderlyingValve` (l. ~1167-1405) : `set_valve_open_percent()` transmet `thermostat.valve_open_percent` via `_get_controlled_percent()` qui applique `calculate_opening_closing_degree` (plafonnement par `min_opening_degrees`/`max_opening_degrees`/`max_closing_degree`/`opening_threshold_degree`) puis `clamp_sent_value` (bornes min/max de l'entité `number`) ; `is_device_active` retourne `current_opening > min_open`.
  - `UnderlyingValveRegulation` (l. ~1406-1550) : chemin sommeil de référence pour `over_climate` — `check_initial_state()` force `_percent_open = 100` si `thermostat.is_sleeping` (l. ~1472-1474) puis `send_percent_open()` réapplique `calculate_opening_closing_degree` (l. ~1519-1543).
- `custom_components/versatile_thermostat/state_manager.py` (l. ~150-200) : gestion déjà générique de `VThermHvacMode_SLEEP` dans le calcul de l'état courant (affichage `OFF`, `hvac_off_reason = HVAC_OFF_REASON_SLEEP_MODE`).
- `custom_components/versatile_thermostat/sensor.py` (`NbActiveDeviceForBoilerSensor.calculate_nb_active_devices`, l. ~865-925) : la chaudière centrale est pilotée à partir de `device_actives` de chaque VTherm.
- `custom_components/versatile_thermostat/services.yaml` (l. ~132-140) : le service `set_hvac_mode_sleep` est décrit comme restreint à `over_climate` avec régulation directe de vanne.
- `custom_components/versatile_thermostat/const.py` (l. 146-149) : paramètres de contrôle d'ouverture issus de #1348 (`min_opening_degrees`, `max_opening_degrees`, `max_closing_degree`, `opening_threshold_degree`).
- `tests/test_overclimate_valve.py` (`test_over_climate_valve_vtherm_hvac_mode_sleep`, l. 597-777) : scénario de référence `HEAT → SLEEP → HEAT`.
- `tests/test_valve.py` (`test_over_valve_full_start`, l. 19-120) : confirme que `over_valve` n'expose aujourd'hui que `HEAT`/`OFF` et qu'aucun test sommeil n'existe pour ce type.
- `documentation/fr/reference.md` (l. 438-446), `documentation/en/reference.md` (l. 445), `documentation/en/over-climate.md` (l. 102-104), `documentation/fr/over-valve.md` : étendue documentaire actuelle du mode sommeil (restreinte à `over_climate`).
- Traductions : `custom_components/versatile_thermostat/translations/` (10 fichiers ; aucune clé sommeil identifiée dans `en.json` — les libellés de service proviennent de `services.yaml`).

### 2. Contexte et objectifs

#### Problème

Le mode sommeil (dormant / `SLEEP`) permet d'ouvrir les vannes thermostatiques (TRV) à la demande maximale sans demander de chauffage à la chaudière centrale : le VTherm est présenté `OFF`, `hvac_action` est `OFF`, aucun équipement n'est considéré actif. Cette fonctionnalité n'existe aujourd'hui que pour les VTherm `over_climate` avec régulation directe de vanne (classe `ThermostatOverClimateValve`).

Les VTherm de type `over_valve` pilotent directement une ou plusieurs entités `number` (degré d'ouverture) lorsque le TRV n'expose pas d'entité `climate`. Ces utilisateurs ne disposent d'aucun moyen intégré d'atteindre l'état « vannes ouvertes sans demande de chauffage » : ils doivent retirer manuellement les TRV (voir discussion [#1937](https://github.com/jmcollin78/versatile_thermostat/discussions/1937)).

#### Valeur attendue

- Permettre, via un mode HVAC standard et un service dédié, d'ouvrir les vannes `over_valve` sans solliciter la chaudière centrale.
- Offrir une expérience homogène avec le mode sommeil `over_climate` : mêmes modes exposés, mêmes attributs, même sémantique d'état.
- Supprimer le recours à des automatisations externes ou au retrait physique des TRV.

#### Périmètre fonctionnel

Voir § 4 (exigences) et § 8 (exclusions).

### 3. Acteurs et cas d'utilisation

#### Acteurs

| Acteur                                              | Description                                                                                                                                       |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Utilisateur final**                               | Propriétaire d'un VTherm `over_valve` souhaitant ouvrir les vannes sans chauffage (ex. : rincer un circuit, circulation gravitaire, purge d'air). |
| **Automatisation Home Assistant**                   | Scénario appelant le service `versatile_thermostat.set_hvac_mode_sleep` / `climate.set_hvac_mode` sur l'entité VTherm.                            |
| **Chaudière centrale**                              | Dispositif piloté via `NbActiveDeviceForBoilerSensor` ; ne doit jamais être sollicitée par un VTherm endormi.                                     |
| **Entités `number` sous-jacentes**                  | Vannes TRV exposant un degré d'ouverture `number` (une à plusieurs par VTherm).                                                                   |
| **Interface utilisateur (carte VTherm / Lovelace)** | Restitue l'état `OFF`, l'attribut `is_sleeping` et le reason `sleep_mode`.                                                                        |

#### Cas d'utilisation

**UC-001 — Mise en sommeil depuis l'interface**
- **Déclencheur** : l'utilisateur sélectionne le mode `SLEEP` de l'entité climate VTherm.
- **Déroulement nominal** : le VTherm passe en mode interne `SLEEP` ; l'état Home Assistant affiché devient `OFF` ; `hvac_off_reason` passe à `sleep_mode` ; une demande brute d'ouverture de 100 % est calculée ; la commande convertie est envoyée à chaque vanne sous-jacente.
- **Résultat attendu** : vannes ouvertes selon la commande convertie (potentiellement plafonnée), VTherm `OFF`, aucune sollicitation de la chaudière centrale.

**UC-002 — Mise en sommeil depuis une automatisation**
- **Déclencheur** : appel du service `versatile_thermostat.set_hvac_mode_sleep`.
- **Déroulement nominal** : identique à UC-001 (le service est aujourd'hui enregistré pour toutes les entités de l'intégration — `climate.py` l. 128-141 — mais échoue avec `NotImplementedError` pour `over_valve` ; il doit aboutir).
- **Résultat attendu** : mode `SLEEP` sélectionné sans erreur.

**UC-003 — Sortie de sommeil**
- **Déclencheur** : sélection d'un autre mode (`HEAT` ou `COOL`) ou `OFF`.
- **Déroulement nominal** : le VTherm reprend la régulation TPI ; consigne et préréglage sont conservés ; la commande effective TPI courante est renvoyée aux vannes.
- **Résultat attendu** : comportement identique à `over_climate` (test `test_over_climate_valve_vtherm_hvac_mode_sleep` étape 4 : retour à la valeur TPI d'avant sommeil, consigne 19 °C et préréglage COMFORT inchangés).

**UC-004 — Redémarrage de Home Assistant pendant le sommeil**
- **Déclencheur** : rechargement/Redémarrage avec un VTherm en `SLEEP`.
- **Déroulement nominal** : l'état `SLEEP` et `hvac_off_reason = sleep_mode` sont restaurés ; les vannes reçoivent à nouveau la demande brute 100 % convertie (comme le fait `UnderlyingValveRegulation.check_initial_state` pour `over_climate`).
- **Résultat attendu** : persistance de l'état de sommeil, pas de retour involontaire au chauffage.

**UC-005 — Mode sommeil avec plusieurs vannes**
- **Déclencheur** : mise en sommeil d'un VTherm pilotant plusieurs entités `number`.
- **Résultat attendu** : chaque vanne reçoit la demande brute 100 %, chacune convertie avec ses propres paramètres/bornes.

**UC-006 — Mode sommeil en `AC mode`**
- **Déclencheur** : VTherm `over_valve` configuré avec `ac_mode` activé.
- **Résultat attendu** : modes exposés `COOL`, `SLEEP`, `OFF` ; sémantique de sommeil identique.

### 4. Exigences fonctionnelles

> Formulation impérative ; chaque exigence est vérifiable. Identifiants stables, identiques dans la version anglaise.

**FR-001** — Le système doit exposer, pour tout VTherm de type `over_valve` sans `AC mode`, la liste de modes HVAC `heat`, `sleep`, `off` (voir note vocabulaire § Vocabulaire).

**FR-002** — Le système doit exposer, pour tout VTherm de type `over_valve` avec `AC mode` activé, la liste de modes HVAC `cool`, `sleep`, `off` (conformément à la convention déjà appliquée par `ThermostatOverClimateValve.build_hvac_list()` ; ce cas, bien qu'atypique pour une vanne, est inclus car l'option `ac_mode` est proposée par le type `over_valve`).

**FR-003** — Le système doit faire aboutir, pour un VTherm `over_valve`, l'appel du service `versatile_thermostat.set_hvac_mode_sleep` en sélectionnant le mode interne `SLEEP`, sans lever d'exception.

**FR-004** — Le système doit exposer l'attribut d'état `is_sleeping` à `true` pour un VTherm `over_valve` dont le mode interne est `SLEEP`, et à `false` sinon.

**FR-005** — Pendant le sommeil d'un VTherm `over_valve`, le système doit présenter l'entité climate dans l'état Home Assistant `off` (mode HVAC affiché `off` alors que le mode interne est `SLEEP`), avec `hvac_off_reason` égal à `sleep_mode`.

**FR-006** — Pendant le sommeil d'un VTherm `over_valve`, le système doit positionner `hvac_action` à `off`.

**FR-007** — Pendant le sommeil d'un VTherm `over_valve`, le système doit comptabiliser aucun équipement actif pour ce VTherm (`device_actives` vide, `nb_device_actives` = 0), de sorte que les capteurs de chaudière centrale (`Nb device active for boiler`, `Total power active device for boiler`) ne changent pas du fait du sommeil. Cette exigence doit être vérifiée par un test unitaire **paramétré (matrice)** couvrant explicitement chaque profil de paramètres d'ouverture #1348 — notamment le cas `max_opening_degrees = 70` avec une vanne physiquement ouverte à 70 — et confirmant, pour chaque profil de la matrice, `device_actives = []`, `nb_device_actives = 0` et l'absence de variation ou d'activation des capteurs/conditions de chaudière centrale.

**FR-008** — Pendant le sommeil, le système doit continuer à convertir la demande brute en commande physique via le chemin de contrôle existant, de sorte que `min_opening_degrees`/`max_opening_degrees`/`max_closing_degree`/`opening_threshold_degree` (paramètres #1348) et les bornes min/max de chaque entité `number` puissent plafonner la commande effectivement envoyée. Le système ne doit pas garantir une ouverture physique de 100 % ; seule la demande brute vaut 100 %.

**FR-009** — À la sortie de sommeil (sélection de `heat`, `cool` ou `off`), le système doit rétablir la régulation TPI proportionnelle : recalcul du `valve_open_percent` selon la consigne et les températures courantes, et envoi de cette commande effective aux vannes.

**FR-010** — À la sortie de sommeil, le système doit conserver la consigne de température et le préréglage sélectionnés avant l'entrée en sommeil, et effacer `hvac_off_reason` (comportement identique à `over_climate`).

**FR-011** — Après un redémarrage de Home Assistant avec un VTherm `over_valve` en sommeil, le système doit restaurer l'état de sommeil (mode interne `SLEEP`, `hvac_off_reason = sleep_mode`) et renvoyer la demande brute convertie aux vannes.

**FR-012** — Le système doit appliquer la demande brute à 100 % à chaque entité `number` sous-jacente d'un VTherm `over_valve` endormi, indépendamment les unes des autres (multi-vannes).

**FR-013** — Le système doit mettre à jour la description du service `set_hvac_mode_sleep` (`services.yaml` et traductions associées) pour couvrir les types `over_climate` avec régulation directe de vanne et `over_valve`.

**FR-014** — Le système doit mettre à jour l'ensemble des documentations concernées dans les cinq langues publiées (EN, FR, DE, CS, PL) : pages de type (`over-valve.md`), pages de référence des attributs (`reference.md`) et toute page mentionnant le mode sommeil ou les modes disponibles par type.

**FR-015** — L'entrée et la sortie de sommeil ne doivent modifier aucun paramètre de configuration du VTherm, y compris les paramètres de contrôle d'ouverture #1348 (`opening_threshold_degree`, `min_opening_degrees`, `max_opening_degrees`, `max_closing_degree`).

### 5. Règles métier

**BR-001** — *Séparation demande brute / activité de chauffage.* Pendant le sommeil, la demande brute de 100 % et l'activité de chauffage sont volontairement découplées : les vannes reçoivent la commande convertie, mais `hvac_action`, `should_device_be_active`, `is_device_active`, `device_actives` et les capteurs de chaudière centrale restent à l'arrêt. Conditions : mode interne `SLEEP`. Exceptions : aucune. Priorité : haute.

**BR-002** — *Plafonnement de la commande physique.* La commande effectivement envoyée à chaque vanne est le résultat de la conversion de la demande brute (100 %) par le chemin de contrôle existant : `calculate_opening_closing_degree` puis contraintes min/max de l'entité `number`. En conséquence, si `max_opening_degrees` ou les bornes de l'entité plafonnent l'ouverture, la commande physique est inférieure à 100 %. Le système ne promet jamais une ouverture physique de 100 %. Conditions : paramètres #1348 non neutres ou bornes d'entité < 100. Exceptions : aucune — le plafonnement est le comportement attendu. Priorité : haute.

**BR-003** — *Cohérence d'affichage.* Le mode interne `SLEEP` est restitué à Home Assistant comme un mode `off` (via la machine d'états existante du `state_manager`), avec un reason explicite `sleep_mode`, afin que l'utilisateur et les automatisations puissent distinguer un arrêt manuel d'un sommeil. Priorité : moyenne.

**BR-004** — *Conservation de la consigne et du préréglage.* Le sommeil ne modifie ni la consigne, ni le préréglage, ni les paramètres. À la sortie de sommeil, la régulation reprend avec les valeurs en vigueur avant l'entrée en sommeil. Priorité : haute.

**BR-005** — *Inclusion du `AC mode`.* Bien qu'atypique pour une vanne, le mode `ac_mode` est exposé par le type `over_valve` ; le sommeil doit y être disponible avec la liste `cool`, `sleep`, `off` et la même sémantique. Priorité : moyenne.

**BR-006** — *Non-régression hors sommeil.* Aucun chemin de régulation, conversion ou comptage existant ne doit changer de comportement tant que `SLEEP` n'est pas sélectionné. Les installations `over_valve` existantes continuent d'exposer et de se comporter comme avant (hors ajout du mode `SLEEP` à la liste exposée). Priorité : haute.

**BR-007** — *Indépendance du mécanisme `over_climate`.* L'implémentation doit être spécifique au chemin `over_valve` (`UnderlyingValve`) et ne doit pas réutiliser ni altérer le mécanisme `UnderlyingValveRegulation` propre à l'architecture `over_climate`, dont le cycle de vie diffère. Priorité : haute (contrainte de conception fonctionnelle : homogénéité de comportement, distinction de mécanisme).

**BR-008** — *Persistance de l'état de sommeil.* Après redémarrage, un VTherm endormi reste endormi et ses vannes reçoivent à nouveau la commande convertie, sans intervention de l'utilisateur. Priorité : moyenne.

**BR-009** — *Aucune demande de chaudière centrale.* Pendant le sommeil, le VTherm ne doit jamais contribuer à l'activation de la chaudière centrale, quel que soit le nombre de vannes ouvertes physiquement, et **regardless of the #1348 opening-parameter profile** in force (`min_opening_degrees`, `max_opening_degrees`, `max_closing_degree`, `opening_threshold_degree`). A physically open valve — including one open below 100 (e.g. 70 with `max_opening_degrees = 70`) — shall never be interpreted as an active device. This rule shall be covered by a parameterised (matrix) unit test explicitly listing each #1348 profile, including the case `max_opening_degrees = 70` with a valve physically open at 70, and verifying for each profile: `device_actives = []`, `nb_device_actives = 0`, and the absence of any variation or activation of the central boiler sensors and conditions. Priority: high (functional safety: a physically open valve must not be interpreted as an active device — a tricky case since `UnderlyingValve.is_device_active` is currently based on the actual opening; see risks).

### 6. Contraintes fonctionnelles

- **Compatibilité** : ne pas modifier le comportement du mode sommeil existant `over_climate` (voir exclusions).
- **Compatibilité des paramètres** : les paramètres #1348 sont hors périmètre de modification ; ils sont uniquement testés en interaction avec le sommeil.
- **Documentation / internationalisation** : toutes les documentations et traductions concernées doivent être mises à jour dans les cinq langues publiées (EN, FR, DE, CS, PL). Les traductions `custom_components/versatile_thermostat/translations/` incluent 10 fichiers ; les cinq langues publiées au minimum sont concernées.
- **Sécurité / confidentialité** : aucun nouveau secret, accès réseau ni traitement de données personnelles (constaté dans le rapport de revue).
- **Expérience utilisateur** : l'état présenté doit pouvoir être distingué d'un simple arrêt manuel (attribut `hvac_off_reason = sleep_mode`, `is_sleeping`).
- **Aucune modification d'état Home Assistant pendant la spécification / conception.**

### 7. Critères d'acceptation

> Scénarios observables, incluant cas limites et erreurs attendues. Chaque critère est testable.

**AC-001 (disponibilité du mode)** — Étant donné un VTherm `over_valve` sans `ac_mode`, ses modes HVAC exposés contiennent exactement `heat`, `sleep`, `off`. Réf. FR-001.

**AC-002 (disponibilité en AC mode)** — Étant donné un VTherm `over_valve` avec `ac_mode`, ses modes HVAC exposés contiennent exactement `cool`, `sleep`, `off`. Réf. FR-002, BR-005.

**AC-003 (service)** — L'appel de `versatile_thermostat.set_hvac_mode_sleep` sur l'entité `over_valve` aboutit sans exception et le mode interne devient `SLEEP`. Réf. FR-003.

**AC-004 (entrée en sommeil depuis HEAT)** — Étant donné un VTherm `over_valve` en `heat` régulant à 40 %, la sélection de `sleep` entraîne : mode interne `SLEEP` ; état Home Assistant affiché `off` ; `is_sleeping = true` ; `hvac_action = off` ; `hvac_off_reason = sleep_mode` ; consigne et préréglage inchangés ; demande brute `valve_open_percent = 100`. Réf. FR-004 à FR-006, FR-008, BR-003, BR-004. (Scénario calqué sur le test de référence `test_over_climate_valve_vtherm_hvac_mode_sleep` étape 3.)

**AC-005 (commande sans plafonnement)** — Avec des paramètres #1348 neutres et une entité `number` de bornes 0-100, la commande effectivement envoyée à chaque vanne pendant le sommeil est 100. Réf. FR-008, FR-009, BR-002.

**AC-006 (commande plafonnée par max_opening_degrees)** — Avec `max_opening_degrees = 70` et une entité `number` de bornes 0-100, la demande brute vaut 100 et la commande physique envoyée à la vanne est déterministe : **70** (conversion identique à celle hors sommeil, confirmée par l'analyse de conception du chemin `over_valve` via `UnderlyingValve._get_controlled_percent`). Aucune promesse d'une ouverture physique de 100 % n'est faite. Réf. FR-009, BR-002. *(Question ouverte OQ-002 — résolue par la conception.)*

**AC-007 (bornes de l'entité number)** — Si l'entité `number` sous-jacente a un max inférieur à 100 (ex. max = 90), la commande convertie est contrainte par ce max, comme pour toute commande hors sommeil. Réf. FR-009, BR-002.

**AC-008 (absence de sollicitation de la chaudière centrale)** — Étant donné un VTherm `over_valve` endormi et des vannes physiquement ouvertes, `device_actives` est vide, `nb_device_actives = 0`, et les capteurs/conditions de chaudière centrale (`Nb device active for boiler`, `Total power active device for boiler`) restent inchangés par rapport à l'instant précédant le sommeil. Réf. FR-006, FR-007, BR-001, BR-009.

**AC-008.a (parameterised unit test — no boiler impact for any #1348 profile)** — The AC-008 scenario shall be covered by a **parameterised (matrix) unit test** run for each #1348 opening-parameter profile — the case `max_opening_degrees = 70` must appear **explicitly** as a data set of the matrix, not merely implicitly. For each profile of the matrix, the scenario is: (1) an `over_valve` VTherm regulates in `heat`; (2) it enters `SLEEP`; (3) the underlying valves are physically open (for the `max_opening_degrees = 70` profile: the valve is physically open at 70 — cf. AC-006); (4) the test verifies: `device_actives = []`, `nb_device_actives = 0`, no variation of the `Nb device active for boiler` and `Total power active device for boiler` sensors, and no activation of the central boiler control conditions, compared to the instant before sleep. The test fails if any of these points is not observed for any profile of the matrix. Ref. FR-006, FR-007, BR-001, BR-009, AC-006, AC-008.

**AC-009 (sortie de sommeil)** — Étant donné un VTherm `over_valve` endormi, la sélection de `heat` rétablit : mode interne `heat` ; consigne et préréglage restaurés ; `is_sleeping = false` ; `hvac_off_reason = none` ; `valve_open_percent` recalculé par TPI (ex. 40 % dans les mêmes conditions qu'avant le sommeil) et envoyé aux vannes ; `hvac_action = heating` et un équipement actif si le TPI l'exige. Réf. FR-010, FR-011, BR-004. (Calqué sur le test de référence étape 4.)

**AC-010 (sortie vers OFF)** — Depuis le sommeil, la sélection de `off` retire la commande d'ouverture (vanne fermée / à sa borne minimale) sans erreur. Réf. FR-010.

**AC-011 (multi-vannes)** — Étant donné un VTherm `over_valve` pilotant N vannes (`N ≥ 2`), l'entrée en sommeil envoie la demande brute convertie à chacune des N entités `number`, chacune avec ses propres paramètres ; aucune vanne n'est omise. Réf. FR-013.

**AC-012 (redémarrage pendant sommeil)** — Après rechargement de l'intégration / redémarrage de Home Assistant, un VTherm `over_valve` endormi reste endormi : `is_sleeping = true`, `hvac_off_reason = sleep_mode`, et les vannes reçoivent à nouveau la commande convertie. Réf. FR-012, BR-008.

**AC-013 (interaction avec #1348)** — L'entrée/sortie de sommeil ne modifie la valeur d'aucun paramètre `opening_threshold_degree`, `min_opening_degrees`, `max_opening_degrees`, `max_closing_degree`, et la conversion hors sommeil après réveil reste conforme aux paramètres configurés. Réf. FR-016, BR-002, BR-006.

**AC-014 (non-régression HEAT/OFF)** — Un VTherm `over_valve` existant n'ayant jamais sélectionné `SLEEP` présente un comportement de régulation et de comptage identique à l'existant. Réf. BR-006.

**AC-015 (documentation)** — Les pages `over-valve.md`, `reference.md` (attribut `is_sleeping`, description service) et pages associées existent et décrivent le mode sommeil `over_valve` dans les cinq langues (EN, FR, DE, CS, PL); la description du service `set_hvac_mode_sleep` reflète le support des deux types. Réf. FR-014, FR-015.

**AC-016 (erreur attendue pour types non supportés)** — Pour les types ne supportant pas le sommeil (ex. `over_switch`, `over_climate` sans régulation directe de vanne), l'appel du service continue de lever `NotImplementedError` / `HomeAssistantError` avec un message clair. Réf. exclusion § 8, rapport de revue.

### 8. Fonctions non prises en charge (exclusions)

- **Modification du comportement sommeil existant de `over_climate`** avec régulation directe de vanne : hors périmètre ; l'implémentation de référence reste inchangée (justification : non-régression d'une fonctionnalité publiée).
- **Modification des paramètres #1348** (`opening_threshold_degree`, `min_opening_degrees`, `max_opening_degrees`, `max_closing_degree`) — formules, configuration ou valeurs par défaut : hors périmètre ; uniquement testés en interaction (justification : périmètre de l'issue #1348, déjà implémenté sur la branche).
- **Création d'une entité `climate` factice** ou compatibilité spécifique à un fabricant de TRV : rejeté (rapport de revue § 6, alternative 1 ne répond pas au besoin).
- **Nouveau paramètre configurable du mode sommeil** (ex. pourcentage d'ouverture autre que 100 %) : rejeté pour ne pas complexifier la sémantique et rester cohérent avec `over_climate`.
- **Modification du code de la carte VTherm UI Card** : hors périmètre de ce dépôt ; question ouverte sur sa représentation du mode (OQ-001).
- **Modification d'état Home Assistant** pendant la spécification et la conception : exclue.

### 9. Évolutions futures proposées

- *Pourcentage d'ouverture de sommeil configurable* — Dépendance : décision produit sur la valeur ajoutée vs complexité. Question à trancher : faut-il un paramètre optionnel (défaut 100 %) ?
- *Représentation dédiée du sommeil dans la carte VTherm UI Card* — Dépendance : dépôt de la carte ; coordonnation de mise à jour (cf. OQ-001).
- *Sélection temporelle du sommeil (durée/planification)* — Dépendance : alignement sur les évolutions éventuelles du mode préréglage temporisé (`feature-timed-preset`).
- *Statistiques d'énergie spécifiques au sommeil* — Dépendance : clarifier la sémantique de comptage énergétique d'un VTherm endormi (aujourd'hui aucun comptage car aucun équipement actif).

### 10. Hypothèses, questions ouvertes et traçabilité

#### Vocabulaire

- **Mode interne `SLEEP` (`VThermHvacMode_SLEEP`)** : mode propre à l'intégration, sélectionnable par l'utilisateur/automatisation ; restitué à Home Assistant comme un état `off` avec reason `sleep_mode`.
- **Demande brute (raw demand)** : valeur de 100 % calculée par le thermostat pendant le sommeil (exposée via `valve_open_percent`), avant conversion.
- **Commande physique (effective command)** : valeur effectivement envoyée à l'entité `number` après conversion/plafonnement (exposée via `valve_command_percent` / `valve_command_by_valve` / `last_sent_opening_value`).
- **Conversion** : chemin de contrôle transformant la demande brute en commande physique — `calculate_opening_closing_degree` (paramètres #1348) puis contraintes min/max de l'entité (`clamp_sent_value`).
- **`over_valve` / `ThermostatOverValve`** : VTherm pilotant une ou plusieurs entités `number`.
- **`over_climate` valve / `ThermostatOverClimateValve`** : VTherm `over_climate` avec régulation directe de vanne ; implémentation de référence du sommeil.

#### Hypothèses retenues

- **H-001** — La persistance des consignes et préréglages à travers `heat → sleep → heat` est identique au comportement `over_climate` (**confirmée par l'analyse de conception** : aucun chemin sommeil n'écrit sur la consigne ou le préréglage ; comportement hérité de la machine d'états commune, déjà testé pour `over_climate`).
- **H-002** — La machine d'états `state_manager` (générique) gère correctement `SLEEP` pour `over_valve` sans modification, l'affichage `off` et le reason `sleep_mode` étant déjà implémentés génériquement (constaté `state_manager.py` l. ~150-200).
- **H-003** — La carte VTherm UI Card restitue déjà correctement un état `off` avec reason, ou sera mise à jour séparément ; le non-fonctionnement éventuel de la carte n'obère pas la spécification fonctionnelle côté intégration.
- **H-004** — L'énergie n'est pas comptabilisée pendant le sommeil (aucun équipement actif), comme pour `over_climate`.

#### Questions ouvertes

- **OQ-001** — La carte VTherm UI Card représente-t-elle le mode `SLEEP` pour un type `over_valve`, ou une mise à jour coordonnée est-elle requise ? (Non déterminable depuis l'issue et le dépôt ; question non bloquante identifiée dans le rapport de revue § 7.)
- **OQ-002** — La conversion exacte de la demande brute 100 % dans le chemin `over_valve` (via `UnderlyingValve._get_controlled_percent`) doit être validée en conception : la sémantique « rigoureusement cohérente avec over_climate » porte sur le *comportement* (demande brute 100 %, puis conversion et plafonnement possibles), pas sur une arithmétique identique ligne à ligne. La valeur physique attendue avec `max_opening_degrees = 70` et des bornes 0-100 est fixée à **70** (critère AC-006).
- **OQ-003** — Do the centralised boiler control conditions have a direct test for a sleeping `over_valve`? The existing coverage shall be verified and completed during design (report § 7); addressed in the design test plan (T-SLEEP-06). This specification now explicitly mandates this test in parameterised form (matrix of #1348 profiles including case 70 — cf. AC-008.a, BR-009, FR-007): the question is now only about the test's location/name, not its existence.

#### Traçabilité exigences ↔ critères ↔ sources

| Exigence               | Critères                       | Sources principales                                                                                                                                                                                                                                                                                                  |
| ---------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-001 / FR-002        | AC-001, AC-002                 | `thermostat_climate_valve.py` `build_hvac_list()`; `base_thermostat.py` `build_hvac_list()`; `test_valve.py` l. 81; `test_overclimate_valve.py` l. 93                                                                                                                                                                |
| FR-003                 | AC-003                         | `base_thermostat.py` `service_set_hvac_mode_sleep()`; `climate.py` service registration                                                                                                                                                                                                                              |
| FR-004, FR-012         | AC-004, AC-012                 | `thermostat_climate_valve.py` `is_sleeping`, `restore_specific_previous_state()`; `base_thermostat.py` `is_sleeping`                                                                                                                                                                                                 |
| FR-005, FR-006, FR-007 | AC-004, AC-008, AC-008.a       | `thermostat_climate_valve.py` `calculate_hvac_action()`, `device_actives`; `state_manager.py` l. ~173; `sensor.py` `calculate_nb_active_devices`                                                                                                                                                                     |
| FR-008, FR-009, FR-013 | AC-005, AC-006, AC-007, AC-011 | `thermostat_climate_valve.py` `recalculate()` (sleep → 100); `underlyings.py` `UnderlyingValveRegulation.check_initial_state()` l. ~1472-1474 and `send_percent_open()` l. ~1519-1543; `UnderlyingValve._get_controlled_percent()`, `clamp_sent_value()`                                                             |
| FR-010, FR-011         | AC-009, AC-010                 | `test_overclimate_valve.py` step 4 (target 19, COMFORT preserved, back to 40%)                                                                                                                                                                                                                                       |
| FR-016                 | AC-013                         | `const.py` l. 146-149; `thermostat_valve.py` `post_init()` (parameters)                                                                                                                                                                                                                                              |
| FR-014, FR-015         | AC-015                         | `services.yaml` l. ~132-140; `documentation/en                                                                                                                                                                                                                                                                       | fr/reference.md`; `documentation/en | fr/over-climate.md` l. 102-104; `documentation/fr/over-valve.md` |
| BR-009                 | AC-008, AC-008.a               | `underlyings.py` `UnderlyingValve.is_device_active` (based on actual opening); `base_thermostat.py` `device_actives`; `sensor.py` `calculate_nb_active_devices`; matrix/parametrised test across #1348 profiles incl. `max_opening_degrees = 70` (valve physically open at 70); "Central heating" risk of the report |

#### Cohérence avec le périmètre du rapport de revue

Cette spécification reprend fidèlement le périmètre inclus/exclus du rapport `issue-1938-review.md` § 4 (incl. `AC mode`, demande brute 100 % convertie sans promesse d'ouverture physique 100 %, thermostat `OFF` sans sollicitation de chaudière, reprise de régulation à la sortie, mises à jour EN/FR/DE/CS/PL, tests listés) et ses exclusions (aucune modification de `over_climate`, de #1348, pas de paramètre supplémentaire, pas d'entité `climate` factice, aucune modification d'état HA).

---

## English version

### 1. Title and metadata

| Field                      | Value                                                                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Name**                   | Sleep Mode for `ThermostatOverValve` (`over_valve`)                                                                                                      |
| **Version**                | 1.1                                                                                                                                                      |
| **Status**                 | Approved, implemented, design-reviewed and manually tested                                                                                               |
| **Date**                   | September 15, 2026                                                                                                                                       |
| **Owner**                  | Versatile Thermostat team                                                                                                                                |
| **Issue reference**        | [jmcollin78/versatile_thermostat#1938](https://github.com/jmcollin78/versatile_thermostat/issues/1938) (open; labels `enhancement`, `Vote needed`, `P1`) |
| **Approved review report** | `documentation/tech-docs/issue-1938-review.md` (review dated September 15, 2026; recommendation: accept)                                                 |

**Sources analysed (verified):** identical to the French version, see § 1 (French) — `base_thermostat.py`, `thermostat_climate_valve.py`, `thermostat_valve.py`, `underlyings.py`, `state_manager.py`, `sensor.py`, `services.yaml`, `const.py`, `tests/test_overclimate_valve.py`, `tests/test_valve.py`, `documentation/*/reference.md`, `documentation/*/over-climate.md`, `documentation/fr/over-valve.md`, `translations/`.

### 2. Context and objectives

#### Problem

The Sleep Mode allows thermostatic radiator valves (TRVs) to be driven to the maximum opening demand without requesting any heating from the central boiler: the VTherm is presented as `off`, `hvac_action` is `off`, and no device is considered active. This feature currently exists only for `over_climate` VTherms with direct valve regulation (class `ThermostatOverClimateValve`).

`over_valve` VTherms directly drive one or more `number` entities (opening degree) when the TRV exposes no `climate` entity. These users have no built-in way to reach the "valves open, no heating demand" state: they must physically remove their TRVs (see discussion [#1937](https://github.com/jmcollin78/versatile_thermostat/discussions/1937)).

#### Expected value

- Provide, through a standard HVAC mode and a dedicated service, a way to open `over_valve` valves without requesting the central boiler.
- Offer a homogeneous experience with the `over_climate` sleep mode: same exposed modes, same attributes, same state semantics.
- Remove the need for external automations or physical TRV removal.

#### Functional scope

See § 4 (requirements) and § 8 (exclusions).

### 3. Actors and use cases

#### Actors

| Actor                            | Description                                                                                                                      |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **End user**                     | Owner of an `over_valve` VTherm who wants valves open without heating (e.g. circuit flushing, gravity circulation, air purging). |
| **Home Assistant automation**    | Scenario calling the `versatile_thermostat.set_hvac_mode_sleep` service / `climate.set_hvac_mode` on the VTherm entity.          |
| **Chaudière centrale**           | Device driven through `NbActiveDeviceForBoilerSensor`; must never be triggered by a sleeping VTherm.                             |
| **Underlying `number` entities** | TRV valves exposing an opening-degree `number` (one to several per VTherm).                                                      |
| **UI (VTherm card / Lovelace)**  | Renders the `off` state, the `is_sleeping` attribute and the `sleep_mode` reason.                                                |

#### Use cases

**UC-001 — Entering sleep from the UI**
- **Trigger**: the user selects the VTherm climate entity's `SLEEP` mode.
- **Nominal flow**: the VTherm switches to the internal `SLEEP` mode; the Home Assistant state shown becomes `off`; `hvac_off_reason` becomes `sleep_mode`; a raw 100% opening demand is calculated; the converted command is sent to each underlying valve.
- **Expected result**: valves open according to the converted command (possibly capped), VTherm `off`, no central boiler request.

**UC-002 — Entering sleep from an automation**
- **Trigger**: a call to the `versatile_thermostat.set_hvac_mode_sleep` service.
- **Nominal flow**: same as UC-001 (the service is registered for all integration entities today — `climate.py` l. 128-141 — but fails with `NotImplementedError` for `over_valve`; it must succeed).
- **Expected result**: `SLEEP` mode selected without error.

**UC-003 — Exiting sleep**
- **Trigger**: selection of another mode (`heat` or `cool`) or `off`.
- **Nominal flow**: the VTherm resumes TPI regulation; target temperature and preset are preserved; the current effective TPI command is resent to the valves.
- **Expected result**: behaviour identical to `over_climate` (reference test step 4: back to the pre-sleep TPI value, target 19 °C and COMFORT preset unchanged).

**UC-004 — Home Assistant restart during sleep**
- **Trigger**: reload/restart with a VTherm in `SLEEP`.
- **Nominal flow**: the `SLEEP` state and `hvac_off_reason = sleep_mode` are restored; the valves again receive the converted 100% raw demand (as `UnderlyingValveRegulation.check_initial_state` does for `over_climate`).
- **Expected result**: sleep state persists, no involuntary return to heating.

**UC-005 — Sleep with multiple valves**
- **Trigger**: putting to sleep a VTherm driving several `number` entities.
- **Expected result**: each valve receives the 100% raw demand, each converted with its own parameters/bounds.

**UC-006 — Sleep in `AC mode`**
- **Trigger**: an `over_valve` VTherm configured with `ac_mode` enabled.
- **Expected result**: exposed modes `cool`, `sleep`, `off`; identical sleep semantics.

### 4. Functional requirements

> Imperative, testable wording. Stable identifiers, identical to the French version.

**FR-001** — The system shall expose, for any `over_valve` VTherm without `AC mode`, the HVAC mode list `heat`, `sleep`, `off`.

**FR-002** — The system shall expose, for any `over_valve` VTherm with `AC mode` enabled, the HVAC mode list `cool`, `sleep`, `off` (consistent with the convention already applied by `ThermostatOverClimateValve.build_hvac_list()`; although atypical for a valve, this case is included because `ac_mode` is offered by the `over_valve` type).

**FR-003** — The system shall make the `versatile_thermostat.set_hvac_mode_sleep` service succeed on an `over_valve` VTherm by selecting the internal `SLEEP` mode, without raising an exception.

**FR-004** — The system shall expose the `is_sleeping` state attribute as `true` for an `over_valve` VTherm whose internal mode is `SLEEP`, and `false` otherwise.

**FR-005** — During the sleep of an `over_valve` VTherm, the system shall present the climate entity in the Home Assistant state `off` (displayed HVAC mode `off` while the internal mode is `SLEEP`), with `hvac_off_reason` equal to `sleep_mode`.

**FR-006** — During the sleep of an `over_valve` VTherm, the system shall set `hvac_action` to `off`.

**FR-007** — During the sleep of an `over_valve` VTherm, the system shall count no active device for this VTherm (`device_actives` empty, `nb_device_actives` = 0), so that the central boiler sensors (`Nb device active for boiler`, `Total power active device for boiler`) do not change due to sleep. This requirement shall be verified by a **parameterised (matrix) unit test** explicitly covering each #1348 opening-parameter profile — including the case `max_opening_degrees = 70` with a valve physically open at 70 — and confirming, for each profile of the matrix, `device_actives = []`, `nb_device_actives = 0` and the absence of any variation or activation of the central boiler sensors/conditions.

**FR-008** — During the sleep of an `over_valve` VTherm, the system shall expose, through the public `valve_open_percent` property, a raw opening demand of 100% for all underlying valves, this value being injected into the existing regulation path (it is not necessarily already computed before the first regulation cycle or the post-restart resumption).

**FR-009** — During sleep, the system shall keep converting the raw demand into the physical command through the existing control path, so that `min_opening_degrees`/`max_opening_degrees`/`max_closing_degree`/`opening_threshold_degree` (#1348 parameters) and each `number` entity's min/max bounds may cap the actually sent command. The system shall not guarantee a 100% physical opening; only the raw demand is 100%.

**FR-010** — Upon exiting sleep (selection of `heat`, `cool` or `off`), the system shall resume proportional TPI regulation: recalculation of `valve_open_percent` from the current target and temperatures, and sending of this effective command to the underlying valves.

**FR-011** — Upon exiting sleep, the system shall preserve the target temperature and the preset selected before entering sleep, and clear `hvac_off_reason` (identical behaviour to `over_climate`).

**FR-012** — After a Home Assistant restart with a sleeping `over_valve` VTherm, the system shall restore the sleep state (internal `SLEEP` mode, `hvac_off_reason = sleep_mode`) and resend the converted raw demand to the valves.

**FR-013** — The system shall apply the 100% raw demand to each underlying `number` entity of a sleeping `over_valve` VTherm, independently from each other (multi-valve).

**FR-014** — The system shall update the `set_hvac_mode_sleep` service description (`services.yaml` and related translations) to cover both `over_climate` with direct valve regulation and `over_valve` types.

**FR-015** — The system documentation shall be updated in the five published languages (EN, FR, DE, CS, PL): type pages (`over-valve.md`), attribute reference pages (`reference.md`) and any page mentioning sleep mode or the modes available per type.

**FR-016** — Entering and exiting sleep shall not modify any VTherm configuration parameter, including the #1348 opening-control parameters (`opening_threshold_degree`, `min_opening_degrees`, `max_opening_degrees`, `max_closing_degree`).

### 5. Business rules

**BR-001** — *Raw demand / heating activity separation.* During sleep, the 100% raw demand and the heating activity are deliberately decoupled: the valves receive the converted command, but `hvac_action`, `should_device_be_active`, `is_device_active`, `device_actives` and the central boiler sensors remain off. Conditions: internal `SLEEP` mode. Exceptions: none. Priority: high.

**BR-002** — *Physical command capping.* The command actually sent to each valve is the result of converting the raw demand (100%) through the existing control path: `calculate_opening_closing_degree` then the `number` entity min/max constraints. Consequently, if `max_opening_degrees` or the entity bounds cap the opening, the physical command is below 100%. The system never promises a 100% physical opening. Conditions: non-neutral #1348 parameters or entity bounds < 100. Exceptions: none — capping is the expected behaviour. Priority: high.

**BR-003** — *Display consistency.* The internal `SLEEP` mode is rendered to Home Assistant as an `off` mode (through the existing state machine), with an explicit `sleep_mode` reason, so that users and automations can distinguish a manual off from sleep. Priority: medium.

**BR-004** — *Target and preset preservation.* Sleep modifies neither the target temperature, nor the preset, nor the parameters. Upon exit, regulation resumes with the values in force before entering sleep. Priority: high.

**BR-005** — *`AC mode` inclusion.* Although atypical for a valve, `ac_mode` is exposed by the `over_valve` type; sleep shall be available there with the `cool`, `sleep`, `off` list and the same semantics. Priority: medium.

**BR-006** — *Non-regression outside sleep.* No existing regulation, conversion or counting path shall change behaviour as long as `SLEEP` is not selected. Existing `over_valve` setups keep behaving as before (besides the addition of `SLEEP` to the exposed list). Priority: high.

**BR-007** — *Independence from the `over_climate` mechanism.* The implementation shall be specific to the `over_valve` path (`UnderlyingValve`) and shall neither reuse nor alter the `UnderlyingValveRegulation` mechanism specific to the `over_climate` architecture, whose lifecycle differs. Priority: high (functional design constraint: behavioural homogeneity, mechanism distinction).

**BR-008** — *Sleep state persistence.* After restart, a sleeping VTherm stays asleep and its valves again receive the converted command, without user intervention. Priority: medium.

**BR-009** — *No central boiler request.* During sleep, the VTherm shall never contribute to central boiler activation, regardless of the number of physically open valves, and **regardless of the #1348 opening-parameter profile** in force (`min_opening_degrees`, `max_opening_degrees`, `max_closing_degree`, `opening_threshold_degree`). A physically open valve — including one open below 100 (e.g. 70 with `max_opening_degrees = 70`) — shall never be interpreted as an active device. This rule shall be covered by a parameterised (matrix) unit test explicitly listing each #1348 profile, including the case `max_opening_degrees = 70` with a valve physically open at 70, and verifying for each profile: `device_actives = []`, `nb_device_actives = 0`, and the absence of any variation or activation of the central boiler sensors and conditions. Priority: high (functional safety: a physically open valve must not be interpreted as an active device — a tricky case since `UnderlyingValve.is_device_active` is currently based on the actual opening; see risks).

### 6. Functional constraints

- **Compatibility**: do not change the existing `over_climate` sleep behaviour (see exclusions).
- **Parameter compatibility**: the #1348 parameters are out of modification scope; they are only tested in interaction with sleep.
- **Documentation / internationalisation**: all related documentation and translations shall be updated in the five published languages (EN, FR, DE, CS, PL). The `translations/` folder includes 10 files; the five published languages at minimum are in scope.
- **Security / privacy**: no new secret, network access or personal data processing (noted in the review report).
- **User experience**: the rendered state must be distinguishable from a plain manual off (`hvac_off_reason = sleep_mode`, `is_sleeping` attributes).
- **Aucune modification d'état Home Assistant pendant la spécification / conception.**

### 7. Acceptance criteria

> Observable scenarios, including edge cases and expected errors. Chaque critère est testable.

**AC-001 (mode availability)** — Given an `over_valve` VTherm without `ac_mode`, its exposed HVAC modes contain exactly `heat`, `sleep`, `off`. Ref. FR-001.

**AC-002 (AC mode availability)** — Given an `over_valve` VTherm with `ac_mode`, its exposed HVAC modes contain exactly `cool`, `sleep`, `off`. Ref. FR-002, BR-005.

**AC-003 (service)** — Calling `versatile_thermostat.set_hvac_mode_sleep` on the `over_valve` entity succeeds without exception and the internal mode becomes `SLEEP`. Ref. FR-003.

**AC-004 (entering sleep from HEAT)** — Given an `over_valve` VTherm in `heat` regulating at 40%, selecting `sleep` causes: internal `SLEEP` mode; Home Assistant state `off`; `is_sleeping = true`; `hvac_action = off`; `hvac_off_reason = sleep_mode`; target and preset unchanged; raw demand `valve_open_percent = 100`. Ref. FR-004 to FR-006, FR-008, BR-003, BR-004. (Scenario modelled on reference test step 3.)

**AC-005 (uncapped command)** — With neutral #1348 parameters and a 0-100 `number` entity, the command actually sent to each valve during sleep is 100. Ref. FR-008, FR-009, BR-002.

**AC-006 (command capped by max_opening_degrees)** — With `max_opening_degrees = 70` and a 0-100 `number` entity, the raw demand is 100 and the physical command sent to the valve is deterministic: **70** (conversion identical to the out-of-sleep one, confirmed by the design analysis of the `over_valve` path through `UnderlyingValve._get_controlled_percent`). Aucune promesse d'une ouverture physique de 100 % n'est faite. Ref. FR-009, BR-002. *(Question ouverte OQ-002 — résolue par la conception.)*

**AC-007 (number entity bounds)** — If the underlying `number` entity has a max below 100 (e.g. max = 90), the converted command is constrained by that max, as for any command outside sleep. Ref. FR-009, BR-002.

**AC-008 (no central boiler request)** — Given a sleeping `over_valve` VTherm with physically open valves, `device_actives` is empty, `nb_device_actives = 0`, and the central boiler sensors/conditions (`Nb device active for boiler`, `Total power active device for boiler`) are unchanged compared to the instant before sleep. Ref. FR-006, FR-007, BR-001, BR-009.

**AC-008.a (parameterised unit test — no boiler impact for any #1348 profile)** — The AC-008 scenario shall be covered by a **parameterised (matrix) unit test** run for each #1348 opening-parameter profile — the case `max_opening_degrees = 70` must appear **explicitly** as a data set of the matrix, not merely implicitly. For each profile of the matrix, the scenario is: (1) an `over_valve` VTherm regulates in `heat`; (2) it enters `SLEEP`; (3) the underlying valves are physically open (for the `max_opening_degrees = 70` profile: the valve is physically open at 70 — cf. AC-006); (4) the test verifies: `device_actives = []`, `nb_device_actives = 0`, no variation of the `Nb device active for boiler` and `Total power active device for boiler` sensors, and no activation of the central boiler control conditions, compared to the instant before sleep. The test fails if any of these points is not observed for any profile of the matrix. Ref. FR-006, FR-007, BR-001, BR-009, AC-006, AC-008.

**AC-009 (exiting sleep)** — Given a sleeping `over_valve` VTherm, selecting `heat` restores: internal `heat` mode; target and preset restored; `is_sleeping = false`; `hvac_off_reason = none`; `valve_open_percent` recalculated by TPI (e.g. 40% under the same pre-sleep conditions) and sent to the valves; `hvac_action = heating` and one active device if TPI requires it. Ref. FR-010, FR-011, BR-004. (Modelled on reference test step 4.)

**AC-010 (exit to OFF)** — From sleep, selecting `off` removes the opening command (valve closed / at its minimal bound) without error. Ref. FR-010.

**AC-011 (multi-valve)** — Given an `over_valve` VTherm driving N valves (`N ≥ 2`), entering sleep sends the converted raw demand to each of the N `number` entities, each with its own parameters; no valve is omitted. Ref. FR-013.

**AC-012 (restart during sleep)** — After integration reload / Home Assistant restart, a sleeping `over_valve` VTherm stays asleep: `is_sleeping = true`, `hvac_off_reason = sleep_mode`, and the valves again receive the converted command. Ref. FR-012, BR-008.

**AC-013 (interaction with #1348)** — Entering/exiting sleep does not modify the value of any `opening_threshold_degree`, `min_opening_degrees`, `max_opening_degrees`, `max_closing_degree` parameter, and the out-of-sleep conversion after wake-up remains conformant to the configured parameters. Ref. FR-016, BR-002, BR-006.

**AC-014 (HEAT/OFF non-regression)** — An existing `over_valve` VTherm that never selected `SLEEP` behaves identically to the current regulation and counting behaviour. Ref. BR-006.

**AC-015 (documentation)** — The `over-valve.md` pages, `reference.md` pages (`is_sleeping` attribute, service description) and related pages exist and describe the `over_valve` sleep mode in the five languages (EN, FR, DE, CS, PL); the `set_hvac_mode_sleep` service description reflects both supported types. Ref. FR-014, FR-015.

**AC-016 (expected error for unsupported types)** — For types not supporting sleep (e.g. `over_switch`, `over_climate` without direct valve regulation), the service call keeps raising `NotImplementedError` / `HomeAssistantError` with a clear message. Ref. exclusion § 8, review report.

### 8. Out of scope (exclusions)

- **Any change to the existing `over_climate` sleep behaviour** with direct valve regulation: out of scope; the reference implementation stays unchanged (rationale: non-regression of a published feature).
- **Any change to the #1348 parameters** (`opening_threshold_degree`, `min_opening_degrees`, `max_opening_degrees`, `max_closing_degree`) — formulae, configuration or defaults: out of scope; interaction tests only (rationale: #1348 scope, already implemented on the branch).
- **Creating a dummy `climate` entity** or manufacturer-specific TRV compatibility: rejected (review report § 6, alternative 1 does not address the need).
- **A new configurable sleep parameter** (e.g. an opening percentage other than 100%): rejected to keep the semantics simple and consistent with `over_climate`.
- **Modifying the VTherm UI Card code**: out of this repository's scope; open question on its mode rendering (OQ-001).
- **Any Home Assistant state modification** during specification and design: excluded.

### 9. Proposed future evolutions

- *Configurable sleep opening percentage* — Dependency: product decision on added value vs complexity. To decide: an optional parameter (default 100%)?
- *Dedicated sleep rendering in the VTherm UI Card* — Dependency: card repository; coordinated update (cf. OQ-001).
- *Time-based sleep selection (duration/scheduling)* — Dependency: alignment with potential evolutions of the timed preset feature (`feature-timed-preset`).
- *Sleep-specific energy statistics* — Dependency: clarifier la sémantique de comptage énergétique d'un VTherm endormi (aujourd'hui aucun comptage car aucun équipement actif).

### 10. Assumptions, open questions and traceability

#### Vocabulary

- **Internal `SLEEP` mode (`VThermHvacMode_SLEEP`)**: mode specific to the integration, selectable by the user/automation; rendered to Home Assistant as an `off` state with reason `sleep_mode`.
- **Raw demand**: the 100% value computed by the thermostat during sleep (exposée via `valve_open_percent`), before conversion.
- **Physical (effective) command**: the value actually sent to the `number` entity after conversion/capping (exposée via `valve_command_percent` / `valve_command_by_valve` / `last_sent_opening_value`).
- **Conversion**: the control path transforming the raw demand into the physical command — `calculate_opening_closing_degree` (#1348 parameters) then the entity min/max constraints (`clamp_sent_value`).
- **`over_valve` / `ThermostatOverValve`**: a VTherm driving one or more `number` entities.
- **`over_climate` valve / `ThermostatOverClimateValve`**: `over_climate` VTherm with direct valve regulation; the sleep reference implementation.

#### Assumptions

- **H-001** — Target and preset persistence across `heat → sleep → heat` is identical to the `over_climate` behaviour (**confirmée par l'analyse de conception**: aucun chemin sommeil n'écrit sur la consigne ou le préréglage ; comportement hérité de la machine d'états commune, déjà testé pour `over_climate`).
- **H-002** — The (generic) `state_manager` handles `SLEEP` correctly for `over_valve` without modification, the `off` rendering and `sleep_mode` reason being already generically implemented (verified `state_manager.py` l. ~150-200).
- **H-003** — The VTherm UI Card already renders an `off` state with reason correctly, or will be updated separately; any card malfunction does not impair the integration-side functional specification.
- **H-004** — L'énergie n'est pas comptabilisée pendant le sommeil (aucun équipement actif), comme pour `over_climate`.

#### Questions ouvertes

- **OQ-001** — La carte VTherm UI Card représente-t-elle le mode `SLEEP` pour un type `over_valve`, ou une mise à jour coordonnée est-elle requise ? (Non déterminable depuis l'issue et le dépôt ; question non bloquante identifiée dans le rapport de revue § 7.)
- **OQ-002** — La conversion exacte de la demande brute 100 % dans le chemin `over_valve` (via `UnderlyingValve._get_controlled_percent`) doit être validée en conception : la sémantique « rigoureusement cohérente avec over_climate » porte sur le *comportement* (demande brute 100 %, puis conversion et plafonnement possibles), pas sur une arithmétique identique ligne à ligne. La valeur physique attendue avec `max_opening_degrees = 70` et des bornes 0-100 est fixée à **70** (critère AC-006).
- **OQ-003** — Do the centralised boiler control conditions have a direct test for a sleeping `over_valve`? The existing coverage shall be verified and completed during design (report § 7); addressed in the design test plan (T-SLEEP-06). This specification now explicitly mandates this test in parameterised form (matrix of #1348 profiles including case 70 — cf. AC-008.a, BR-009, FR-007): the question is now only about the test's location/name, not its existence.

#### Traçabilité exigences ↔ critères ↔ sources traceability

Identical traceability matrix as in the French version (§ 10, French) — same FR/BR/AC identifiers, same sources:

| Requirement            | Criteria                       | Main sources                                                                                                                                                                                                                                                                                                         |
| ---------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-001 / FR-002        | AC-001, AC-002                 | `thermostat_climate_valve.py` `build_hvac_list()`; `base_thermostat.py` `build_hvac_list()`; `test_valve.py` l. 81; `test_overclimate_valve.py` l. 93                                                                                                                                                                |
| FR-003                 | AC-003                         | `base_thermostat.py` `service_set_hvac_mode_sleep()`; `climate.py` service registration                                                                                                                                                                                                                              |
| FR-004, FR-012         | AC-004, AC-012                 | `thermostat_climate_valve.py` `is_sleeping`, `restore_specific_previous_state()`; `base_thermostat.py` `is_sleeping`                                                                                                                                                                                                 |
| FR-005, FR-006, FR-007 | AC-004, AC-008, AC-008.a       | `thermostat_climate_valve.py` `calculate_hvac_action()`, `device_actives`; `state_manager.py` l. ~173; `sensor.py` `calculate_nb_active_devices`                                                                                                                                                                     |
| FR-008, FR-009, FR-013 | AC-005, AC-006, AC-007, AC-011 | `thermostat_climate_valve.py` `recalculate()` (sleep → 100); `underlyings.py` `UnderlyingValveRegulation.check_initial_state()` l. ~1472-1474 and `send_percent_open()` l. ~1519-1543; `UnderlyingValve._get_controlled_percent()`, `clamp_sent_value()`                                                             |
| FR-010, FR-011         | AC-009, AC-010                 | `test_overclimate_valve.py` step 4 (target 19, COMFORT preserved, back to 40%)                                                                                                                                                                                                                                       |
| FR-016                 | AC-013                         | `const.py` l. 146-149; `thermostat_valve.py` `post_init()` (parameters)                                                                                                                                                                                                                                              |
| FR-014, FR-015         | AC-015                         | `services.yaml` l. ~132-140; `documentation/en                                                                                                                                                                                                                                                                       | fr/reference.md`; `documentation/en | fr/over-climate.md` l. 102-104; `documentation/fr/over-valve.md` |
| BR-009                 | AC-008, AC-008.a               | `underlyings.py` `UnderlyingValve.is_device_active` (based on actual opening); `base_thermostat.py` `device_actives`; `sensor.py` `calculate_nb_active_devices`; matrix/parametrised test across #1348 profiles incl. `max_opening_degrees = 70` (valve physically open at 70); "Central heating" risk of the report |

#### Consistency with the review report scope

This specification faithfully follows the included/excluded scope of the `issue-1938-review.md` report § 4 (incl. `AC mode`, 100% raw demand converted with no 100% physical opening promise, `off` thermostat with no boiler request, regulation resumption on exit, EN/FR/DE/CS/PL documentation updates, all listed tests) and its exclusions (no modification of `over_climate`, of #1348, no additional parameter, no dummy `climate` entity, no HA state modification).
