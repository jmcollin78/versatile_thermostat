# Spécification fonctionnelle — Parité du contrôle de vanne pour `over_valve` / Functional specification — Valve control parity for `over_valve`

- **Référence :** [issue #1348](https://github.com/jmcollin78/versatile_thermostat/issues/1348) — [discussion #1339](https://github.com/jmcollin78/versatile_thermostat/discussions/1339)
- **Version :** 1.1
- **Statut :** Proposée / Proposed
- **Date :** 14 septembre 2026
- **Propriétaire :** Équipe Versatile Thermostat (rédaction : agent de spécification)
- **Documents sources :**
  - `documentation/tech-docs/issue-1348-review.md` (rapport de revue, lu intégralement)
  - `documentation/tech-docs/issue-1348-design.md` (conception technique v1.0, lue intégralement ; constats intégrés dans cette version 1.1)
  - `custom_components/versatile_thermostat/opening_degree_algorithm.py` (`OpeningClosingDegreeCalculation.calculate_opening_closing_degree`)
  - `custom_components/versatile_thermostat/thermostat_valve.py` (`ThermostatOverValve`, `valve_open_percent`)
  - `custom_components/versatile_thermostat/thermostat_climate_valve.py` (`ThermostatOverClimateValve`)
  - `custom_components/versatile_thermostat/underlyings.py` (`UnderlyingValve`, `UnderlyingValveRegulation`)
  - `custom_components/versatile_thermostat/config_flow.py` (validations de la régulation directe, `async_step_valve_regulation` et validation de données, lignes ~285-330)
  - `custom_components/versatile_thermostat/config_schema.py` (`valve_regulation_schema`), `const.py` (`CONF_MIN_OPENING_DEGREES`, `CONF_MAX_OPENING_DEGREES`, `CONF_MAX_CLOSING_DEGREE`, `CONF_OPENING_THRESHOLD_DEGREE`)
  - `custom_components/versatile_thermostat/translations/en.json`, `fr.json`, et fichiers de traduction existants
  - `documentation/en/over-valve.md`, `documentation/en/self-regulation.md`, `README-fr.md`
  - `tests/test_valve.py`, `tests/test_overclimate_valve.py`, `tests/test_config_flow.py`, `tests/test_vtherm_api_opening_degree*.py`

> Documents sources referenced above were inspected read-only. Les numéros de ligne ne sont pas cités comme preuve ; seuls les fichiers et symboles réellement lus sont référencés. / Source documents were inspected read-only. Line numbers are not cited as proof; only files and symbols actually read are referenced.

---

## 1. Contexte et objectifs / Context and objectives

### FR
Un thermostat `over_valve` de Versatile Thermostat commande directement une ou plusieurs entités `number` représentant l'ouverture de vannes, en leur transmettant le pourcentage issu de l'algorithme TPI. Or certains corps de chauffe ne produisent aucune chaleur en dessous d'un certain pourcentage d'ouverture. Le cas d'origine (discussion #1339) est une vanne Plugwise Tom qui ne chauffe pas sous 20 % alors que le TPI peut commander 19 % : l'appareil n'expose aucune entité `climate`, c'est donc bien `over_valve` qui est concerné. Aujourd'hui, les paramètres permettant de contraindre la commande (seuil d'ouverture, ouverture minimale, fermeture maximale, ouverture maximale) n'existent que pour `over_climate` avec régulation directe de vanne (`ThermostatOverClimateValve`). L'objectif est d'apporter une **parité complète du contrôle de vanne** entre `over_valve` et `over_climate` (régulation directe), en **mutualisant** strictement le calcul et les règles de validation entre les deux variantes. La valeur réputée non fonctionnelle (performance, observabilité hors attributs de diagnostic) est hors périmètre.

### EN
An `over_valve` thermostat in Versatile Thermostat directly drives one or more `number` entities representing valve opening, sending them the percentage produced by the TPI algorithm. However, some heating bodies produce no heat below a certain opening percentage. The originating case (discussion #1339) is a Plugwise Tom valve that does not heat below 20 % while TPI may command 19 %; the device exposes no `climate` entity, so `over_valve` is the relevant type. Today, the parameters constraining the command (opening threshold, minimum opening, maximum closing, maximum opening) exist only for `over_climate` with direct valve regulation (`ThermostatOverClimateValve`). The objective is to bring **full valve-control parity** between `over_valve` and direct-regulation `over_climate`, by **strictly sharing** the calculation and validation rules between the two variants. Non-functional product qualities (update throughput, « ghost » retention, etc.) are out of scope.

### Valeur attendue / Expected value
- Chauffe effective dès qu'un besoin de chauffage existe, malgré un seuil physique de vanne (cas Plugwise).
- Un seul comportement de contrôle de vanne, quel que soit le type de thermostat, réduisant divergence et maintenance.

## 2. Acteurs et cas d'utilisation / Actors and use cases

**Acteurs / Actors**
- **Utilisateur/propriétaire** : configure un VTherm `over_valve`, règle les quatre paramètres de contrôle de vanne.
- **Utilisateur/owner** : configures an `over_valve` VTherm and sets the four valve-control parameters.
- **Intégrateur/développeur HA** : écrit des automatisations/dashboards lisant les états VTherm ; s'appuie sur les attributs de diagnostic et la documentation.
- **HA integrator/developer** : writes automations/dashboards reading VTherm states; relies on diagnostic attributes and documentation.
- **Tests** : fixtures pytest (`tests/test_valve.py`, `tests/test_overclimate_valve.py`) vérifiant le comportement décrit.
- **Tests** : pytest fixtures verifying the described behaviour.

**Cas d'utilisation nominal / Nominal use case**
- **Déclencheur** : un utilisateur configure ou reconfigure un VTherm de type `over_valve` avec des vannes dont le seuil physique est 20 %.
- **Déroulement** : l'utilisateur renseigne les paramètres de contrôle de vanne ; le système valide la configuration ; au calcul du cycle TPI, le pourcentage brut est transformé en commande effective selon les règles de l'issue ; la commande effective est envoyée aux vannes ; les attributs de diagnostic sont mis à jour.
- **Résultat attendu** : la vanne ne reçoit jamais une commande inférieure à son ouverture minimale tant que le besoin brut dépasse le seuil ; en dessous du seuil, elle reçoit `100 - max_closing_degree`.

**Cas d'utilisation secondaires / Secondary use cases**
1. VTherm `over_valve` multi-vannes : listes CSV avec une valeur par vanne, discrimination locale et groupée (voir FR-004).
2. Non-régression : VTherm `over_valve` existant sans paramètres modifiés — comportement inchangé (FR-008).
3. Discrimination physique : l'utilisateur règle `opening_threshold_degree` au plus près du seuil physique réel mesuré.
4. Multi-valve VTherm: CSV lists with one value per valve, local and grouped discrimination (see FR-004).
5. Non-regression: existing `over_valve` VTherm without modified parameters — unchanged behaviour (FR-008).

## 3. Exigences fonctionnelles / Functional requirements

### Champ « exigence » / Note on requirement scope
FR-001..FR-007, FR-009 portent sur `over_valve`. Le terme « Le système » y désigne le composant Versatile Thermostat ; l'entité `climate` du VTherm `over_valve` reste inchangée dans son exposition publique de base. FR-008 s'applique à toute la famille VTherm. / FR-001..FR-007, FR-009 target `over_valve`. « The system » means the Versatile Thermostat component; the public base exposure of the `over_valve` VTherm `climate` entity is otherwise unchanged. FR-008 applies to the whole VTherm family.

### FR-001 — Exposition des quatre options de configuration en `over_valve`
FR :
- Le système **doit** exposer, pour un VTherm de type `over_valve`, les quatre options de configuration suivantes : `opening_threshold_degree`, `min_opening_degrees`, `max_closing_degree`, `max_opening_degrees`.
- Le système **doit** exposer ces options dans le flux de configuration `over_valve` (setup et options flow) et dans le schéma YAML `over_valve`.
- Le système **doit** appliquer strictement les mêmes sémantiques que `over_climate` (régulation directe) :
  - `opening_threshold_degree` : entier, global au thermostat ; échelle 0–100 ; en dessous du seuil la vanne est considérée fermée ;
  - `min_opening_degrees` : liste de nombres sous forme de chaîne CSV (une valeur par vanne sous-jacente) ; ouverture minimale appliquée dès que le besoin dépasse le seuil ;
  - `max_opening_degrees` : liste de nombres sous forme de chaîne CSV (une valeur par vanne sous-jacente) ; plafonne la commande envoyée à la vanne ;
  - `max_closing_degree` : entier unique, échelle 0–100, global à toutes les vannes du thermostat ; définit la commande « fermée » via $100 - \text{max\_closing\_degree}$.
- Le système **doit** proposer les valeurs par défaut suivantes : `opening_threshold_degree = 0`, `min_opening_degrees = ""` (liste vide → `0` par vanne), `max_opening_degrees = ""` (liste vide → max de l'entité `number` sous-jacente si exposé, sinon `100`), `max_closing_degree = 100`.
- `min_opening_degrees` et `max_opening_degrees` **doivent** rester des chaînes CSV (« séparées par des virgules »), sans changement du format persisté.

EN :
- The system **shall** expose, for an `over_valve` VTherm, the four configuration options `opening_threshold_degree`, `min_opening_degrees`, `max_closing_degree`, `max_opening_degrees`.
- The system **shall** expose them in the `over_valve` config flow (setup and options flow) and in the `over_valve` YAML schema.
- The system **shall** strictly apply the same semantics as `over_climate` (direct regulation):
  - `opening_threshold_degree`: integer, thermostat-wide; scale 0–100; below the threshold the valve is considered closed;
  - `min_opening_degrees`: list of numbers as a CSV string (one value per underlying valve); minimum opening applied as soon as need exceeds the threshold;
  - `max_opening_degrees`: list of numbers as a CSV string (one value per underlying valve); caps the command sent to the valve;
  - `max_closing_degree`: single integer, scale 0–100, global to all valves of the thermostat; defines the "closed" command as $100 - \text{max\_closing\_degree}$.
- The system **shall** provide the following defaults: `opening_threshold_degree = 0`, `min_opening_degrees = ""` (empty → `0` per valve), `max_opening_degrees = ""` (empty → underlying `number` entity max if exposed, else `100`), `max_closing_degree = 100`.
- `min_opening_degrees` and `max_opening_degrees` **shall** remain CSV strings, with no persisted-format change.

### FR-002 — Transformation du pourcentage brut TPI en commande effective
FR :
- Pour un VTherm `over_valve`, le système **doit** transformer le pourcentage brut TPI calculé en une commande effective, avant envoi aux entités `number` sous-jacentes.
- La commande effective **doit** être calculée pour chaque vanne sous-jacente à partir du même pourcentage brut TPI et des paramètres effectifs de cette vanne ; les vannes d'un même VTherm partagent le seuil et la fermeture maximale, mais peuvent recevoir des commandes différentes si leurs minima/maxima effectifs diffèrent.
- La formule **doit** être strictement identique à celle utilisée pour `over_climate` (régulation directe) ; aucune copie ni variante de formule ne **doit** être introduite (voir FR-005).

EN :
- For an `over_valve` VTherm, the system **shall** transform the raw TPI percentage into an effective command before sending to the underlying `number` entities.
- The effective command **shall** be calculated for each underlying valve from the same raw TPI percentage and that valve's effective parameters; valves of one VTherm share the threshold and maximum closing, but may receive different commands if their effective minima/maxima differ.
- The formula **shall** be strictly identical to the one used for `over_climate` (direct regulation); no copy or variant **shall** be introduced (see FR-005).

### FR-003 — Comportement de contrôle : seuil, min, max, fermeture maximale
FR :
- Le système **doit** utiliser, pour l'ensemble des vannes du VTherm, les paramètres combinés suivants :
  - le seuil global `opening_threshold_degree` ;
  - le minimum effectif de la vanne (valeur de `min_opening_degrees[vanne]`, défaut `0`) ;
  - le maximum effectif de la vanne (valeur de `max_opening_degrees[vanne]`, défaut le max de l'entité `number` sous-jacente si disponible, sinon `100`) ;
  - la fermeture maximale globale `max_closing_degree`.
- Quand le pourcentage brut TPI est **inférieur strictement** au seuil (ou est nul), la commande effective **doit** être égale à $100 - \text{max\_closing\_degree}$.
- Quand le pourcentage brut est **supérieur ou égal** au seuil, la commande effective **doit** être le résultat de l'interpolation linéaire entre le minimum et le maximum effectifs de la vanne, calibrée pour atteindre le maximum effectif à $100\%$ de besoin brut.
- À $100\%$ de besoin brut, la commande **doit** être égale au maximum effectif.
- La commande effective **doit** être un entier 0–100, borné par le minimum et le maximum effectifs de la vanne quand le besoin brut est au-dessus du seuil.

EN : mirror.
- The system **shall** use, for all valves of the VTherm, the combined parameters: global `opening_threshold_degree`; effective valve minimum (`min_opening_degrees[valve]`, default `0`); effective valve maximum (`max_opening_degrees[valve]`, default underlying entity max if available, else `100`); global `max_closing_degree`.
- When raw TPI need is **strictly below** the threshold (or equals zero), the effective command **shall** be $100 - \text{max\_closing\_degree}$.
- When raw need is **at or above** the threshold, the effective command **shall** be the linear interpolation between the valve's effective minimum and maximum, calibrated so that $100\%$ raw need reaches the effective maximum.
- At $100\%$ raw need the command **shall** equal the effective maximum.
- The effective command **shall** be an integer 0–100, bounded by the valve's effective minimum and maximum when raw need is at/above the threshold.

### FR-004 — Sources des paramètres, comportement multi-vannes, et priorité
FR :
- Pour un VTherm `over_valve` à une seule vanne, le minimum effectif **doit** être la valeur de `min_opening_degrees` pour cette vanne si définie, sinon `0` ; le maximum effectif **doit** être la valeur de `max_opening_degrees` pour cette vanne si définie, sinon le max de l'entité `number` sous-jacente si disponible, sinon `100`.
- Pour un VTherm `over_valve` multi-vannes, `min_opening_degrees` et `max_opening_degrees` **doivent** être des chaînes CSV où la i-ème valeur s'applique à la i-ème vanne sous-jacente. Une liste plus courte ou absente **doit** être tolérée sans erreur : les vannes sans valeur reçoivent le défaut (`0` ou max de l'entité) ; une liste plus longue **doit** être rejetée par la validation (voir FR-007).
- Le seuil `opening_threshold_degree` et la fermeture maximale `max_closing_degree` **doivent** rester des réglages globaux, uniques pour toutes les vannes du VTherm : ils **ne doivent pas** être traités comme des listes par vanne.
- Source des paramètres : configuration locale du VTherm ; à défaut, les défauts FR-001 s'appliquent. La configuration centrale (`central_configuration`) **ne fournit aucun** de ces quatre paramètres pour quelque variante que ce soit (constat de conception §3.4 : aucun schéma `STEP_CENTRAL_*` ne les contient, y compris pour `over_climate`) ; par parité, elle est **hors périmètre** de cette issue (voir §8 évolution 2).

EN :
- For a single-valve `over_valve` VTherm, the effective minimum **shall** be that valve's `min_opening_degrees` value if set, else `0`; the effective maximum **shall** be that valve's `max_opening_degrees` value if set, else the underlying `number` entity max if available, else `100`.
- For a multi-valve `over_valve` VTherm, `min_opening_degrees` and `max_opening_degrees` **shall** be CSV strings where the i-th value applies to the i-th underlying valve. A shorter or absent list **shall** be tolerated without error: valves without a value receive the default; an overly long list **shall** be rejected by validation (see FR-007).
- `opening_threshold_degree` and `max_closing_degree` **shall** remain global settings, unique for all valves of the VTherm: they **shall not** be treated as per-valve lists.
- Parameter source: local VTherm config; otherwise FR-001 defaults apply. Central configuration (`central_configuration`) provides **none** of these four parameters for any variant (design finding §3.4: no `STEP_CENTRAL_*` schema contains them, including for `over_climate`); for parity it is **out of scope** for this issue (see §8 future evolution 2).

### FR-005 — Utilisation d'une seule implémentation de calcul (mutualisation obligatoire)
FR :
- Le calcul de la commande effective **doit** être réalisé par une unique implémentation partagée par `over_valve` et `over_climate` (régulation directe), basée sur l'algorithme existant (`OpeningClosingDegreeCalculation.calculate_opening_closing_degree`).
- Le système **doit** garantir l'absence de duplication de formule : `over_valve` réutilise le point de calcul unique et les règles de validation mutualisées, sans copie ni variante locale.
- Les résultats du calcul **doivent** être déterministes et identiques pour les mêmes entrées, paramètres et vannes, quels que soient le type de VTherm (`over_valve` ou `over_climate` régulation directe) à paramètres équivalents.

EN : ...

### FR-006 — Attributs de diagnostic
FR :
- Le système **doit** exposer, pour un VTherm `over_valve` avec contrôle de vanne actif (`opening_threshold_degree > 0` ou `min_opening_degrees` non vide ou `max_opening_degrees` non vide ou `max_closing_degree != 100`), des attributs de diagnostic distincts :
  - un attribut `valve_open_percent` conservant le pourcentage TPI brut tel que calculé par l'algorithme TPI, avant transformation ;
  - une représentation **par vanne** de la commande effective envoyée à chaque vanne sous-jacente (après transformation, arrondie à l'entier) — par exemple un attribut `valve_command_percent` (échelle normalisée 0-100) accompagné, en multi-vannes, d'une représentation par vanne distincte (p.ex. une liste `underlying_valves` avec la commande effective de chaque vanne).
- L'attribut `valve_open_percent` **doit** conserver sa sémantique et sa stabilité actuelles (« pourcentage TPI brut », un seul scalaire) : en multi-vannes, il ne **doit pas** être redéfini pour représenter des commandes distinctes par vanne. Si un attribut scalaire `valve_command_percent` est exposé en multi-vannes, sa valeur agrégée **doit** être documentée sans prétendre représenter chaque commande individuelle ; la représentation fidèle par vanne reste l'exigence.
- Le changement de nom des attributs existants **doit** être évité pendant la période de transition, pour ne pas casser les dashboards existants.

EN : mirror — `valve_open_percent` = raw TPI percent (scalar, unchanged semantics and stability); a **per-valve** representation of the effective command sent to each underlying valve is required (e.g. a `valve_command_percent` scalar on the normalized 0-100 scale plus, for multi-valve VTherms, a per-valve representation such as an `underlying_valves` list with each valve's effective command). In multi-valve setups a scalar `valve_command_percent` **shall not** be presented as representing each individual command; a documented aggregate is acceptable, but the per-valve representation is the requirement. Existing attribute names stable during transition.

### FR-007 — Validation de la configuration
FR :
- Le système **doit** rejeter, à la sauvegarde de la configuration `over_valve` (YAML ou UI), toute combinaison invalide :
  - entier hors 0–100 pour `opening_threshold_degree` ou `max_closing_degree` ;
  - CSV de `min_opening_degrees` ou `max_opening_degrees` contenant une valeur non entière, négative ou supérieure à 100 ;
  - `max_opening_degrees[i] <= min_opening_degrees[i]` pour un même indice i (quand les deux listes sont définies) ;
  - liste de longueur supérieure au nombre de vannes sous-jacentes.
- Ces validations **doivent** être implémentées dans les mêmes règles de validation que `over_climate` (mutualisées), sans duplication. La règle de cardinalité des listes trop longues est **nova** dans le pipeline mutualisé (constat de conception : aucune validation de longueur CSV n'existe aujourd'hui dans `config_flow.py`) ; elle **doit** être ajoutée une seule fois, partagée par les deux variantes, y compris pour `over_climate` pour lequel les listes trop longues sont aujourd'hui silencieusement tolérées. Ce renforcement appliqué aussi à `over_climate` est assumé : rejeter une liste incohérente ne peut pas casser une configuration existante valide.

EN :
- The system **shall** reject, on `over_valve` config save (YAML or UI), any invalid combination: out-of-range integers for `opening_threshold_degree` or `max_closing_degree`; non-integer, negative, or >100 CSV values in `min_opening_degrees` or `max_opening_degrees`; `max_opening_degrees[i] <= min_opening_degrees[i]` at a same index i (when both lists are provided); lists longer than the number of underlying valves.
- These validations **shall** be implemented in the same validation rules as `over_climate` (shared), without duplication. The overly-long-list cardinality rule is **new** in the shared pipeline (design finding: no CSV-length validation exists today in `config_flow.py`); it **shall** be added once, shared by both variants, including for `over_climate` where overly long lists are currently silently tolerated. This strengthening applied to `over_climate` as well is deliberate: rejecting an inconsistent list cannot break a valid existing configuration.

### FR-008 — Protection du comportement par défaut (non-régression et exclusions de bout en bout)
FR :
- Avec la configuration par défaut (`opening_threshold_degree = 0`, `min = 0`, `max_closing = 100`, `max = max de l'entité ou 100`), la commande effective **doit** être exactement égale au pourcentage TPI brut, pour garantir la non-régression des installations `over_valve` existantes.
- Le comportement du `over_climate` (régulation directe) **ne doit pas** être modifié par ce changement.
- Le comportement du VTherm `over_valve` sans les nouveaux paramètres configurés **ne doit pas** être modifié.

EN : mirror.

### FR-009 — Documentation, traductions et neutralité des formulations
FR :
- Le système **doit** supprimer, dans les libellés, descriptions et documentations (`config_flow.py`, `translations/*.json`, `documentation/*/over-valve.md`, `README-*.md`), les formulations garantissant une compatibilité universelle avec toutes les vannes, et les remplacer par des formulations neutres à l'échelle de l'entité pilotée (entité `number` compatible).
- Le système **doit** utiliser la même terminologie dans toutes les langues publiées.

EN :
- The system **shall** remove, in labels, descriptions and documentation (`config_flow.py`, `translations/*.json`, `documentation/*/over-valve.md`, `README-*.md`), wording guaranteeing universal valve compatibility, replacing it with neutral wording scoped to the driven entity (compatible `number` entity).
- The system **shall** use the same terminology across all published languages.

## 4. Règles métier / Business rules

Les quatre paramètres sont des réglages physiques de la vanne. Ils ne **doivent** pas être confondus avec les paramètres de l'algorithme TPI (kp, ki, etc.). / These four parameters are physical valve settings; they **must not** be confused with TPI algorithm parameters (kp, ki, etc.).

### BR-001 (Priorité haute / High)
**Règle / Rule** : En `over_valve`, un besoin de chauffage brut inférieur au seuil d'ouverture (`opening_threshold_degree`) est interprété comme une absence de chauffage : la vanne reçoit `100 - max_closing_degree` (fermeture maximale autorisée). / In `over_valve`, a raw heating need below the opening threshold is interpreted as no heating: the valve receives `100 - max_closing_degree` (maximum allowed closing).
**Condition** : pourcentage brut TPI < seuil, ou pourcentage brut nul. Exception : si `max_closing_degree = 100`, la vanne reçoit `0` (comportement actuel préservé).
**Priority rationale** : garantit le zéro-chauffe sous le seuil physique.

### BR-002 (Priorité haute / High)
**Règle / Rule** : Au-dessus du seuil, la vanne **doit** toujours recevoir au moins son ouverture minimale (`min_opening_degrees`), bornée par son maximum effectif. / Above threshold, the valve **shall** always receive at least its minimum opening (`min_opening_degrees`), bounded by its effective maximum.
**Condition** : pourcentage brut ≥ seuil et > 0. Exception : si la valeur listée est absente pour cette vanne, le défaut s'applique (`0` ou maximum de l'entité).
**Priority rationale** : garantit un chauffage effectif dès qu'un besoin existe (cas Plugwise).

### BR-003 (Priorité moyenne / Medium)
**Règle / Rule** : La commande est plafonnée par le maximum effectif de la vanne (`max_opening_degrees[vanne]` ou défaut). / The command is capped by the valve's effective maximum.
**Condition** : toujours. Exception : en mode « sous le seuil » (BR-001), la commande est `100 - max_closing_degree`, qui peut dépasser le maximum d'ouverture seulement si `max_closing_degree < 0` — impossible (FR-007).
**Priority rationale** : protège les corps de chauffe à ouverture partielle maximale utile.

### BR-004 (Priorité haute / High)
**Règle / Rule** : Les paramètres proviennent exclusivement de la configuration locale du VTherm ; en absence de configuration locale, les défauts FR-001 s'appliquent. La configuration centrale (`central_configuration`) ne fournit aucune valeur pour ces paramètres et **ne doit pas** être consultée pour eux : ni `over_valve` ni `over_climate` (régulation directe) ne centralise ces quatre paramètres aujourd'hui, et la parité exige de ne pas l'ajouter (voir §8 évolution 2). / Parameters come exclusively from the local VTherm configuration; absent local configuration, FR-001 defaults apply. Central configuration provides no value for these parameters and **shall not** be consulted for them: neither `over_valve` nor direct-regulation `over_climate` centralizes these four parameters today, and parity requires not adding it (see §8 future evolution 2).
**Condition** : à la lecture des paramètres au démarrage. Pas d'exception.

### BR-005 (Priorité moyenne / Medium)
**Règle / Rule** : Un réglage global unique (`max_closing_degree` au singulier) s'applique à toutes les vannes d'un même VTherm. / A single global setting (`max_closing_degree`, singular) applies to all valves of one VTherm.
**Condition** : toujours en `over_valve` comme `over_climate` (régulation directe). Pas d'exception.

### BR-006 (Priorité haute / High)
**Règle / Rule** : Dans un VTherm multi-vannes, la i-ème valeur de `min_opening_degrees` (resp. `max_opening_degrees`) s'applique à la i-ème vanne sous-jacente ; un manque de valeur pour une vanne donne la valeur par défaut (pas d'erreur). / In a multi-valve VTherm, the i-th value of `min_opening_degrees` (resp. `max_opening_degrees`) applies to the i-th underlying valve; a missing value yields the default (no error).
**Condition** : listes CSV de longueur inférieure ou égale au nombre de vannes. Exception : une liste plus longue (voir FR-007 pour l'orientation de validation) ; la validation partagée (FR-007) **doit** rejeter les listes plus longues.

### BR-007 (Priorité moyenne / Medium)
**Règle / Rule** : Les paramètres de contrôle de vanne ne **peuvent pas** être réglés via l'entité `number` de commande : ils sont modifiés par le flux de configuration (options flow), pas par une entité de service ni par la configuration centrale. / Valve-control parameters **cannot** be set through command entities: they are edited through the config flow (options flow), not through service entities or central configuration.
**Condition** : toujours (parité avec `over_climate`). Pas d'exception.

### BR-008 (Priorité haute / High)
**Règle / Rule** : La transformation dépend uniquement du pourcentage brut TPI courant et des quatre paramètres ; elle est déterministe, sans mémoire, et **ne doit pas** dépendre du temps ni de l'historique. / The transformation depends only on the current raw TPI percentage and the four parameters; it is stateless, deterministic, and **shall not** depend on time or history.
**Condition** : chaque cycle de calcul. Pas d'exception.

## 5. Contraintes fonctionnelles / Functional constraints

### FC-001 — Compatibilité configuration
- La configuration YAML existante de `over_valve` **doit** rester valide sans les nouveaux paramètres (aucune migration forcée). / Existing `over_valve` YAML config **shall** remain valid without new parameters (no forced migration).
- Les noms YAML/UI des paramètres **doivent** être identiques à ceux d'`over_climate` (`opening_threshold_degree`, `min_opening_degrees`, `max_closing_degree`, `max_opening_degrees`). / Parameter YAML/UI names **shall** be identical to `over_climate`'s.
- `min_opening_degrees` et `max_opening_degrees` **doivent** rester chaînes CSV. / ... **shall** remain CSV strings.
- `max_closing_degree` **doit** rester un réglage unique global. / ... **shall** remain a single global setting.

### FC-002 — Non-régression des installations existantes
- (FR-008) Le comportement des VTherms `over_valve` et `over_climate` existants **ne doit pas** changer tant que les nouveaux paramètres ne sont pas réglés. / Existing VTherms' behaviour **shall** not change while new parameters are unset.
- Les entités, services et attributs publics (`valve_open_percent` inclus) **doivent** rester stables et compatibles. / Public entities, services and attributes (incl. `valve_open_percent`) **shall** stay stable and compatible.

### FC-003 — Mutualisation obligatoire du calcul
- (FR-005) Aucune duplication de formule/calcul entre `over_valve` et `over_climate` n'est admise. / No formula/calculation duplication between `over_valve` and `over_climate` is allowed.

### FC-004 — Compatibilité environnement HA / HA environment compatibility
- La fonctionnalité **doit** s'exécuter dans l'environnement Home Assistant existant, avec les versions core HA supportées par le dépôt (voir `pyproject.toml`/`requirements_*`), sans nouvelle dépendance. / … **shall** run within the existing Home Assistant environment, repository-supported HA core versions, with no new dependency.
- **Doit** rester compatible avec les types de vannes sous-jacents supportés via entités `number` (Plugwise Tom en tête, mais tout `number` compatible). / … **shall** remain compatible with underlying valve types driven via `number` entities (Plugwise Tom first, but any compatible `number`).

### FC-005 — Expérience utilisateur
- Les messages d'erreur de validation **doivent** être explicites, orientés utilisateur, disponibles dans toutes les langues publiées. / Validation error messages **shall** be explicit, user-oriented, and available in all published languages.
- Les libellés UI **doivent** être cohérents avec ceux d'`over_climate` pour faciliter la compréhension croisée. / UI labels **shall** be consistent with `over_climate`'s for cross-understanding.

## 6. Critères d'acceptation / Acceptance criteria

### Cas nominal / Nominal case
**AC-001 (exigences FR-001, FR-002, FR-003, FR-005, FR-006, FR-007)**
Étant donné un VTherm `over_valve` avec une vanne, `opening_threshold_degree = 20`, `max_closing_degree = 100`, `min_opening_degrees = "30"`, `max_opening_degrees = "80"`, pourcentage brut TPI = 25 :
- la commande effective **doit** être comprise entre 30 et 80 ; précisément $30 + (80-30) \times \frac{25-20}{100-20} = 33$ (arrondie à l'entier) ;
- l'attribut `valve_open_percent` **doit** valoir 25 ; l'attribut `valve_command_percent` **doit** valoir 33.
EN : Given a single-valve `over_valve` VTherm, threshold 20, max_closing 100, min 30, max 80, raw TPI 25 %: effective command must be 33 (interpolation), `valve_open_percent` = 25, `valve_command_percent` = 33.

### Cas limites / Edge cases
**AC-002 (FR-003, BR-001)** : pourcentage brut = 19, seuil = 20, `max_closing_degree = 100` → commande = 0 ; avec `max_closing_degree = 90` → commande = 10.

**AC-003 (FR-003)** : pourcentage brut = 0 → commande = $100 - \text{max\_closing\_degree}$, quel que soit le seuil.

**AC-004 (FR-003, BR-002)** : pourcentage brut = 100, max effectif = 80 → commande = 80 ; max effectif = 100 → commande = 100.

**AC-005 (FR-003, BR-002, min > max protection)** : si `min_opening_degrees = 50` et `max_opening_degrees = "30"` pour une même vanne, la validation de config **doit** rejeter la configuration (FR-007, erreur `ValveRegulationMinMaxOpeningDegreesIncorrect` ou équivalent mutualisé).

**AC-006 (FR-004, BR-006, multi-vannes)** : VTherm à 3 vannes, `min_opening_degrees = "10,20"`, `max_opening_degrees = ""` → vanne 1 : min 10, max défaut ; vanne 2 : min 20, max défaut ; vanne 3 : min 0 (défaut), max défaut. Aucune erreur résiduelle.

**AC-007 (FR-004)** : VTherm à 2 vannes, listes plus longues (`min_opening_degrees = "10,20,30"`) → la validation **doit** rejeter (règle mutualisée de cardinalité).

**AC-008 (FR-008, non-régression)** : VTherm `over_valve` avec paramètres par défaut et pourcentage brut TPI = 19 → commande = 19, identique au comportement pré-changement ; pourcentage = 63 → commande = 63.

**AC-009 (FR-008)** : VTherm `over_climate` avec régulation directe de vanne, avant/après déploiement du changement : comportement, commandes et attributs **doivent** être strictement identiques.

**AC-010 (FR-006)** : les deux attributs `valve_open_percent` (brut) et `valve_command_percent` (effectif) **doivent** être présents et distincts dès qu'un contrôle de vanne est actif ; la valeur de `valve_open_percent` doit rester le pourcentage TPI brut non transformé.

**AC-011 (FR-007)** : valeur hors bornes (`opening_threshold_degree = -1` ou `101`, `max_closing_degree = 0`, CSV contenant `-5` ou `150`, CSV non numérique `"a,b"`) → rejet à la sauvegarde avec message d'erreur explicite, sans crash.

**AC-012 (FR-005, mutualisation)** : des tests de table (paramètres → commande) **doivent** s'exécuter sur le point de calcul unique partagé et être rejoués à l'identique pour `over_valve` et `over_climate` ; toute divergence de résultat à paramètres équivalents **doit** faire échouer le test.

**AC-013 (retiré — configuration centrale hors périmètre) / (removed — central configuration out of scope)** : la configuration centrale ne fournissant aucun des quatre paramètres pour quelque variante que ce soit (constat de conception §3.4), aucun critère d'acceptation de configuration centrale n'est applicable à cette issue. L'éligibilité centrale est traitée en évolution future (voir §8 évolution 2).

### Résultats d'erreurs attendus / Expected error outcomes
- Sauvegarde YAML/UI avec paramètres invalides : message d'erreur de validation, configuration non enregistrée. / Invalid save: validation error, config not stored.
- Listes CSV trop longues : erreur de cardinalité mutualisée. / Overly long CSV lists: shared cardinality error.
- Min ≥ max par vanne : erreur mutualisée. / Min ≥ max per valve: shared error.

## 7. Fonctions non prises en charge / Out of scope

- **Modification du comportement `over_climate`** — exclu pour préserver la non-régression ; l'implémentation existante reste la référence de calcul à mutualiser.
- **Exigence d'une entité `climate` ou contournement par fausse entité** — exclu : le cas d'usage est « pas d'entité `climate` » ; le contournement documenté dans la discussion #1339 n'est pas reconduit.
- **Support spécifique du modèle Plugwise Tom** — exclu : le mécanisme reste générique pour toute entité `number` de position de vanne.
- **Changement du format persisté des listes** (vrais champs de liste UI, remplacement du CSV) — exclu pour cette issue ; le CSV persiste (voir revue, §4 Exclusions et §7).
- **Réglage des paramètres par entité de service** — exclu (BR-007) : flux de configuration uniquement.
- **Migration de données** — non nécessaire : aucun équivalent `over_valve` n'existe aujourd'hui, les paramètres absents retombent sur les défauts neutres.
- **Modifications non fonctionnelles** (performance observée, métriques) — hors périmètre.
- **Langues** : toutes les langues publiées du dépôt sont mises à jour dans le même changement (périmètre confirmé, ex-OC-001) ; aucune traduction « probable » hors dépôt.
- **Éligibilité à la configuration centrale des quatre paramètres** — exclue de cette issue : aucun schéma `STEP_CENTRAL_*` ne les contient, ni pour `over_valve` ni pour `over_climate` (régulation directe) ; la parité interdit de l'ajouter pour `over_valve` seule. Voir §8 évolution 2.

## 8. Évolutions futures proposées / Proposed future evolutions

1. **Remplacer la saisie CSV par de vrais champs de liste UI** — dépendance : évolution du schéma de config et du format persisté ; question à trancher : migration des installations existantes. Exclu de cette issue pour ne pas mélanger UX et évolution fonctionnelle.
2. **Étendre la configuration centrale** aux quatre paramètres de contrôle de vanne — état des lieux : la configuration centrale ne centralise ces paramètres pour **aucune** variante aujourd'hui (y compris `over_climate`, régulation directe — constat de conception §3.4 : les schémas `STEP_CENTRAL_*` ne les contiennent pas). Cette issue ne les ajoute pas, la parité interdisant d'ajouter à `over_valve` une éligibilité centrale qu'`over_climate` n'a pas. Une extension future **devrait** couvrir les deux variantes simultanément pour préserver la parité (BR-004 amendé en v1.1). Dépendances : élargissement de `central_configuration` (nouveaux schémas `STEP_CENTRAL_*`), hiérarchie locale > centrale à définir ; à trancher : périmètre exact et ordre de priorité.
3. **Auto-calibration du seuil physique** : mesure du seuil réel de chauffage par vanne — dépendance : capteur de température différentielle ou log d'analyse ; hors périmètre actuel.
4. **Réglage à chaud des paramètres** (entités `number` de réglage) — dépendance : décision de franchir BR-007 ; question : compatibilité avec verrou d'activation (à trancher).
5. **Publication des commandes par vanne dans l'API VTherm** (`vtherm_api`) — dépendance : demande d'évolution séparée ; question : besoins réels des utilisateurs d'API.

**Aucune de ces évolutions n'est une exigence actuelle.** / None of these is a current requirement.

## 9. Hypothèses, questions ouvertes et traçabilité / Assumptions, open questions and traceability

### Hypothèses / Assumptions
- **AS-001** : L'échelle de tous les paramètres est 0–100 (échelle normalisée), identique à `over_climate`.
- **AS-002** : La valeur brute TPI reste exposée telle quelle (`valve_open_percent`); la commande envoyée est la valeur transformée.
- **AS-003** : `max_closing_degree` garde le nom et la sémantique existants (singulier, global).
- **AS-004** : Les traductions publiées du dépôt (celles présentes dans `translations/`) constituent l'ensemble exact des langues à mettre à jour — périmètre confirmé en v1.1 (ex-OC-001).
- **AS-005** : Le point de calcul unique existant (`OpeningClosingDegreeCalculation`) est, restera ou deviendra l'unique point de conversion brute→effective pour les deux variantes.
- **AS-006** : Les VTherms `over_valve` multi-vannes pilotent une seule zone de chauffe avec une commande commune (confirmé comme base de conception par le rapport de revue, §4 « Multi-vannes »).

### Questions ouvertes / Open questions
- **OC-001** (résolu, convention à confirmer par le mainteneur) : les traductions **doivent** être mises à jour dans **toutes les langues publiées du dépôt** dans le même changement — c'est le périmètre confirmé (FR-009, FC-005). Les langues publiées sont celles présentes dans `translations/` du dépôt (actuellement : `cs`, `de`, `en`, `fr`, `pl`, au minimum — à recenser exhaustivement au moment du développement). Aucune traduction « probable » : seules les langues réellement présentes sont mises à jour.
- **OC-003** (résolu en conception, décision D3) : les attributs de diagnostic (`valve_open_percent` brut, représentation effective par vanne) **doivent** être exposés **uniquement quand un contrôle de vanne est actif** (un des 4 paramètres ≠ défaut), pour alléger l'état des VTherms non concernés ; AC-010 est formulé en conséquence.
- **OC-004** (non bloquant, résolu) : aucune migration d'options n'est nécessaire — aucun équivalent `over_valve` n'existe, les paramètres absents retombent sur les défauts neutres (conception §7.3).
- ~~**OC-002**~~ (résolu v1.1, retiré) : l'éligibilité centrale des paramètres est **hors périmètre** (aucune variante ne les centralise ; parité = ne pas ajouter). Voir §8 évolution 2.
- ~~**OC-005**~~ (résolu v1.1, retiré) : la validation des listes trop longues **est entérinée** comme exigence (FR-007/AC-007) — règle mutualisée ajoutée une fois, appliquée aussi à `over_climate` (constat C3, décision D2 de la conception).

### Traçabilité / Traceability
| Exigence               | Fichier(s)/symbole(s) source                                                                                                     | Commentaire                                         |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| FR-001..FR-007, FR-009 | `opening_degree_algorithm.py`; `thermostat_climate_valve.py`; `underlyings.py`; `config_flow.py`; `config_schema.py`; `const.py` | implantation existante à étendre avec mutualisation |
| FR-008                 | `thermostat_valve.py` (comportement actuel `valve_open_percent`), `tests/test_valve.py` (comportement protégé par tests)         | AC-008/AC-009 exigés pour la protection             |
| FR-009                 | `translations/*.json`; `documentation/*/over-valve.md`; `README-*.md`                                                            | formulations à harmoniser                           |
| Tous                   | `documentation/tech-docs/issue-1348-review.md`                                                                                   | document d'entrée structurant                       |

Fichiers vérifiés en lecture seule : `custom_components/versatile_thermostat/opening_degree_algorithm.py`, `thermostat_climate_valve.py` (lignes 50-160), `thermostat_valve.py` (`valve_open_percent`), `underlyings.py` (UnderlyingValve et ValveRegulation), `config_flow.py` (validations ~lignes 270-330), `config_schema.py`, `const.py`, `translations/en.json`, `fr.json`, `tests/test_overclimate_valve.py`, `tests/test_config_flow.py`, `documentation/en/over-valve.md`, `documentation/en/self-regulation.md`, `documentation/tech-docs/vtherm-overclimate-valve.md`, `README-fr.md`, et [l'issue #1348](https://github.com/jmcollin78/versatile_thermostat/issues/1348).

**Aucun code, configuration, dépendance ou environnement Home Assistant n'a été modifié.** / No code, configuration, dependency, or Home Assistant environment was modified.
