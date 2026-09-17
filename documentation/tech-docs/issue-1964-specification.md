# Spécification fonctionnelle / Functional specification — External Humidity Sensor Support (Issue #1964)

- **Fichier / File** : `documentation/tech-docs/issue-1964-specification.md`
- **Issue** : [jmcollin78/versatile_thermostat#1964](https://github.com/jmcollin78/versatile_thermostat/issues/1964) — [Feature Request] External Humidity Sensor Support
- **Version** : 1.0 · **Statut** : Draft (en attente de validation utilisateur / Pending user validation)
- **Date** : 2026-09-17 · **Propriétaire / Owner** : Équipe Versatile Thermostat
- **Sources analysées / Sources analyzed** :
  - Rapport de revue validé / Validated review report : `documentation/tech-docs/issue-1964-review.md`
  - `custom_components/versatile_thermostat/thermostat_climate.py` — `current_humidity` (~ligne 1159 : lecture depuis `underlying_entity(0)`), `async_set_humidity` (~ligne 1233, humidité cible — hors périmètre)
  - `custom_components/versatile_thermostat/underlyings.py` — `current_humidity` (~ligne 987, via `get_underlying_attribute`), `set_humidity`
  - `custom_components/versatile_thermostat/base_thermostat.py` — listeners `sensor_entity_id` / `external_temp_sensor_entity_id` (`async_track_state_change_event` dans `async_added_to_hass`), gestionnaires `_async_update_temp`, `_async_update_ext_temp` (~ligne 2193) — modèle direct
  - `custom_components/versatile_thermostat/config_flow.py` — `async_step_menu` (~ligne 611), étapes `window` / `motion` / `presence` / `sync_device_internal_temp`, `validate_input`, `check_config_complete`
  - `custom_components/versatile_thermostat/config_schema.py`, `const.py`, `strings.json` / `translations/`
  - Issue GitHub #1964 (consultée dans le cadre de la revue)

---

# Partie 1 — Version française

## 1. Titre et métadonnées

**Spécification fonctionnelle : Prise en charge d'un capteur d'humidité externe pour Versatile Thermostat.** Permet d'alimenter l'attribut standard Home Assistant `current_humidity` d'une entité VTherm à partir d'un capteur d'humidité externe (configuré explicitement ou auto-détecté), au lieu de — ou à défaut de — la valeur exposee par l'entité climate sous-jacente. Version 1.0, statut Draft, 2026-09-17, sources listées en tête de document.

## 2. Contexte et objectifs

En type `over_climate`, `current_humidity` est aujourd'hui lu directement depuis l'entité climate sous-jacente (`thermostat_climate.py`, `current_humidity` : `self.underlying_entity(0).current_humidity`). De nombreux équipements (clims IR, vannes radiateur, intégrations tierces) n'exposent aucune humidité : l'attribut reste alors `None`. À l'inverse, beaucoup d'utilisateurs disposent d'un capteur d'humidité mieux placé (centre de pièce).

**Valeur attendue** : visibilité immédiate de l'humidité sur la carte thermostat Lovelace et via les intégrations lisant l'attribut standard (`current_humidity`, ex. HomeKit `CurrentRelativeHumidity`), pour tous les types de VTherm.

**Objectifs** :
1. Permettre d'affecter un capteur d'humidité externe à tout VTherm (`over_switch`, `over_valve`, `over_climate`) — décision D2.
2. Offrir une auto-détection « zéro configuration » : si rien n'est spécifié, chercher un capteur d'humidité sur le même appareil (`device_id`) que le capteur de température configuré — décision D3.
3. Préserver strictement la compatibilité ascendante : sans configuration et sans détection, comportement identique à l'existant — décision D4.

**Périmètre fonctionnel inclus** (conforme au rapport §4) : clé de configuration optionnelle disponible pour tous les types ; auto-détection via le registre d'entités HA (`device_class == humidity`, même `device_id` que le capteur de température) ; priorité capteur explicite > auto-détecté > entité climate sous-jacente (`over_climate` uniquement) > `None` ; page dédiée « Humidité » dans le config flow ; listener + lecture initiale + gestion des états invalides ; tests ; documentation et traductions.

**Périmètre exclu** : tout contrôle d'humidité (setpoint, déshumidification) ; modification de `async_set_humidity` / `set_humidity` ; entité datetime « dernière mesure d'humidité » (décision D6) ; historique/statistiques ; capteur de diagnostic dédié.

## 3. Acteurs et cas d'utilisation

**Acteurs** :
- **Utilisateur final** : configure et utilise le VTherm via l'UI Home Assistant (config flow), consulte l'humidité sur la carte climate ou via HomeKit/Lovelace.
- **VTherm (intégration)** : résout la source d'humidité, écoute le capteur, expose `current_humidity`.
- **Registre d'entités Home Assistant** : source de l'auto-détection (appareil et `device_class` des entités).
- **Intégrations tierces** : consommatrices de l'attribut standard `current_humidity`.

**Cas d'utilisation** :

- **UC-1 — Configuration automatique (zéro configuration)** : l'utilisateur crée/modifie un VTherm sans visiter la page « Humidité ». Le VTherm détecte automatiquement un capteur d'humidité sur le même appareil que le capteur de température ; `current_humidity` est alimenté. Déclencheur : fin du config flow / démarrage de l'entité.
- **UC-2 — Configuration explicite** : l'utilisateur visite l'option de menu « Humidité », active l'utilisation de l'humidité, voit le sélecteur pré-rempli avec le capteur auto-détecté (s'il existe), sélectionne ou remplace le capteur, valide. Le capteur explicite prime sur toute détection.
- **UC-3 — VTherm existant sans configuration** : VTherm créé avant cette version, sans capteur d'humidité configuré. Si l'auto-détection ne trouve rien : comportement strictement identique à l'actuel (lecture depuis l'entité sous-jacente en `over_climate`, `None` sinon). Si l'auto-détection trouve un candidat, l'humidité est alimentée (le comportement « s'enrichit » sans action utilisateur — conforme à D3/D4 : sans détection, aucune différence).
- **UC-4 — Consultation** : l'utilisateur consulte l'humidité courante sur la carte thermostat, Lovelace ou HomeKit ; la valeur suit le capteur en temps réel.
- **UC-5 — Désactivation explicite** : depuis la page « Humidité », l'utilisateur désactive l'utilisation de l'humidité ; le VTherm cesse d'utiliser le capteur (retour au comportement de repli).

## 4. Exigences fonctionnelles

- **FR-001** : Le système doit permettre de configurer, pour chaque VTherm de tout type (`over_switch`, `over_valve`, `over_climate`), un capteur d'humidité externe optionnel identifié par son `entity_id`.
- **FR-002** : Le système doit exposer l'humidité via l'attribut standard `current_humidity` de l'entité climate VTherm, quelle que soit la source retenue (capteur explicite, capteur auto-détecté, entité sous-jacente).
- **FR-003** : Le système doit lire la valeur du capteur retenu au démarrage de l'entité (lecture initiale) et à chaque changement d'état du capteur (listener), conformément au pattern existant de la température (`_async_update_temp` / `_async_update_ext_temp` dans `base_thermostat.py`).
- **FR-004** : Le système doit auto-détecter un capteur d'humidité lorsque aucun capteur n'est explicitement configuré, en recherchant, via le registre d'entités Home Assistant, les entités de domaine `sensor` avec `device_class == humidity` attachées au même appareil (`device_id`) que le capteur de température configuré dans le VTherm.
- **FR-005** : Lorsque plusieurs candidats sont trouvés par l'auto-détection, le système doit retenir le premier candidat dans l'ordre du registre d'entités et consigner un log informatif listant tous les candidats trouvés.
- **FR-006** : Lorsqu'aucun candidat n'est trouvé et qu'aucun capteur n'est configuré, le système doit consigner un log informatif (sans erreur) et se replier selon FR-008.
- **FR-007** : Le système doit offrir dans le config flow une option de menu dédiée « Humidité » (pattern des options existantes : `window`, `motion`, `presence`, `sync_device_internal_temp`), facultative, proposant : l'activation/désactivation de l'utilisation de l'humidité et un sélecteur de capteur pré-rempli avec le capteur auto-détecté le cas échéant.
- **FR-008** : Le système doit résoudre la source d'humidité selon la priorité : capteur explicite > capteur auto-détecté > entité climate sous-jacente (`over_climate` uniquement) > `None`.
- **FR-009** : Le système doit garantir que, sans capteur configuré et sans candidat détecté, le comportement de `current_humidity` est strictement identique au comportement actuel (lecture depuis l'entité sous-jacente en `over_climate` ; `None` pour les autres types).
- **FR-010** : Le système doit gérer les états `unavailable`, `unknown` et les valeurs non numériques (y compris `NaN`/`Inf`) du capteur sans crash, en **propageant l'invalidité** (valeur invalide/explicite, cf. FR-017 et BR-003) plutôt qu'en conservant une valeur obsolète.
- **FR-011** : Le système doit effectuer l'auto-détection (ou sa re-détection) au démarrage de l'entité et après toute modification de la configuration via le config flow.
- **FR-012** : Le système ne doit apporter aucune modification aux algorithmes de régulation ni au traitement de l'humidité cible (`async_set_humidity` / `set_humidity`) : l'humidité est purement informative.
- **FR-013** : Le système doit valider l'entity_id saisi dans le config flow (cohérence avec `validate_input`) et rester cohérent avec `check_config_complete`.
- **FR-014** : Le système doit fournir la documentation utilisateur dans **toutes les langues du dépôt** (**CS, DE, EN, FR, PL — obligatoires**) et des traductions UI complètes dans toutes les langues (`strings.json` / `translations/`) pour la page et l'option de menu « Humidité ». Fichiers concernés : `documentation/{cs,de,en,fr,pl}/`, `strings.json` et tous les fichiers de `translations/`, ainsi que les `README{,-cs,-de,-fr,-pl}.md`.
- **FR-015** : Le paragraphe « Quoi de neuf ? » annonçant la **release 10.4** de chaque README (`README.md`, `README-fr.md`, `README-cs.md`, `README-de.md`, `README-pl.md`) doit être **complété** avec la fonctionnalité « capteur d'humidité externe », dans la langue du README concerné.
- **FR-016** : The config flow page listing the "features" (checkboxes) **does not change**: no "Humidity" checkbox is added there. The "Humidity" menu option is **always present** in the menu, **regardless** of the choices made in the "features" page (unlike conditional options such as `window`, `motion` or `presence`). Enabling/disabling humidity is done only through the toggle on the "Humidité" page itself (user decision of 2026-09-17).
- **FR-017** : On invalid humidity (`unavailable`, `unknown`, non-numeric, `NaN`/`Inf`), the VTherm does **not** keep the last valid value: `current_humidity` takes an **explicit invalid value** (`None` by default, or the entity's `unavailable` state if the `ClimateEntity` API allows — to be validated during design) to faithfully reflect the sensor state (user decision of 2026-09-17, settles Q2; see BR-003).
- **FR-018** : At startup the humidity sensor may be temporarily unavailable (HA sensor loading order, frequent case): the system shall **retry later** (read/detection retries) and report humidity as **undefined** (`None`) until the sensor is available (user decision of 2026-09-17, settles Q4).

## 5. Règles métier

- **BR-001 — Résolution de la source d'humidité** : À la résolution de l'entité (démarrage, modification de config), la source est déterminée selon FR-008. Condition : un capteur explicite, s'il existe, est toujours prioritaire et désactive toute détection. Exception : si le capteur explicite est supprimé de la configuration, une nouvelle auto-détection a lieu.
- **BR-002 — Auto-détection** : La détection s'applique uniquement si aucun capteur explicite n'est configuré (D4). Elle se base sur le `device_id` du capteur de température configuré (`sensor_entity_id` key). Si le VTherm n'a pas de capteur de température configuré, ou que celui-ci n'est rattaché à aucun appareil, aucune détection n'a lieu (log informatif). Plusieurs candidats → premier retenu (ordre du registre), log listant tous les candidats (D3). Aucun candidat → `None`, log informatif, pas d'erreur.
- **BR-003 — États invalides du capteur** : Si le capteur retenu passe à `unavailable`/`unknown` ou expose une valeur non convertible en nombre (dont `NaN`/`Inf`) : le VTherm ne conserve **pas** la dernière valeur valide ; `current_humidity` prend une valeur invalide/explicite — `None` par défaut, ou state `unavailable` de l'entité si l'API `ClimateEntity` le permet (décision utilisateur du 2026-09-17 : la valeur invalide doit être **propagée** et « forçable » via VTherm) — sans crash ni exception non gérée. Un log est émis. Au retour d'une valeur valide, le capteur reprend immédiatement la priorité.
- **BR-004 — Redémarrage et modification de configuration** : Au redémarrage de Home Assistant / rechargement de l'entité, la source est re-résolue (config explicite d'abord, puis détection). Si le capteur ou sa valeur n'est pas encore disponible au démarrage (ordre de chargement HA), des **re-tentatives** ont lieu plus tard (FR-018) et l'humidité reste **indéfinie** (`None`) en attendant. Une modification de la page « Humidité » (activation/désactivation/changement de capteur) prend effet après validation et rechargement de l'entité, sans redémarrage complet requis.
- **BR-005 — Désactivation explicite** : Si l'utilisateur désactive l'utilisation de l'humidité depuis la page « Humidité », le VTherm ne doit utiliser ni capteur configuré ni auto-détection ; `current_humidity` suit le repli (entité sous-jacente en `over_climate`, sinon `None`). Priorité : la désactivation explicite prime sur l'auto-détection.
- **BR-006 — Compatibilité ascendante** : Aucune configuration existante ne doit être impactée : le champ est optionnel, aucune migration n'est requise, et sans champ + sans détection le comportement est inchangé.
- **BR-007 — Humidité purement informative** : Aucune règle, aucun algorithme, aucun calcul de régulation ne doit consommer l'humidité courante. Priorité : alignement sur D7.
- **BR-008 — Types de VTherm** : La fonctionnalité s'applique aux trois types ; pour `over_switch`/`over_valve` il n'existe pas d'entité climate sous-jacente exposant l'humidité — seuls les niveaux « capteur explicite », « auto-détecté » et `None` de la priorité s'appliquent.

## 6. Contraintes fonctionnelles

- **Compatibilité ascendante** : stricte (FR-009, BR-006) — vérifiable par les tests de non-régression existants.
- **Performances** : l'auto-détection est une opération ponctuelle (démarrage / rechargement / modification de config) sur le registre d'entités ; le listener supplémentaire est optionnel et marginal (coût équivalent à un listener de température). Aucun polling.
- **UX** : la page « Humidité » est facultative ; l'auto-détection rend la fonctionnalité « zéro configuration » ; le sélecteur pré-rempli évite l'effet « boîte noire » (affichage explicit de ce qui a été détecté).
- **Documentation / traductions** : conventions du dépôt (`documentation/` par langue, `strings.json` + `translations/`) — **toutes les langues obligatoires (CS, DE, EN, FR, PL)**, y compris la mise à jour du paragraphe « Release 10.4 » de tous les README (`README{,-cs,-de,-fr,-pl}.md`).
- **Sécurité/confidentialité** : néant de particulier — lecture d'un capteur local, aucune donnée externe.
- **Modèle de données** : le capteur est supposé être une entité `sensor` avec `device_class: humidity` (hypothèse H1).

## 7. Critères d'acceptation

Chaque scénario doit être vérifiable par test unitaire ou inspection manuelle documentée.

- **AC-1 (capteur explicite, temps réel)** : VTherm `over_climate` avec capteur configuré → `current_humidity` reflète la valeur du capteur ; le capteur change d'état → `current_humidity` est mis à jour au cycle suivant. Idem `over_switch` et `over_valve`.
- **AC-2 (persistance au redémarrage)** : après rechargement/redémarrage, la lecture initiale fournit la valeur du capteur sans attendre un changement d'état.
- **AC-3 (auto-détection — un candidat)** : VTherm sans capteur configuré, capteur de température rattaché à un appareil comportant exactement un `sensor` `humidity` → ce capteur est retenu ; `current_humidity` alimenté ; log informatif émis. Applicable aux trois types.
- **AC-4 (auto-détection — plusieurs candidats)** : appareil comportant plusieurs capteurs `humidity` → le premier (ordre du registre) est retenu ; log listant tous les candidats.
- **AC-5 (auto-détection — aucun candidat)** : aucun capteur `humidity` sur l'appareil → log informatif ; comportement identique à l'existant (AC-6).
- **AC-6 (compatibilité ascendante)** : VTherm existant, aucun capteur configuré, aucun candidat détecté → `over_climate` : `current_humidity` = valeur de l'entité sous-jacente (régression nulle par rapport au comportement de `thermostat_climate.py` actuel, ligne ~1159) ; `over_switch`/`over_valve` : `current_humidity` = `None`. Aucun crash, aucun log d'erreur.
- **AC-7 (états invalides)** : capteur `unavailable`/`unknown`/`NaN`/`Inf` → pas d'exception ; `current_humidity` prend la valeur invalide/explicite définie en BR-003 (`None` ou état `unavailable`) — **pas de conservation** de l'ancienne valeur ; retour à la normale dès valeur valide ; au démarrage avec capteur non encore chargé, re-tentatives effectuées et humidité `None` en attendant (FR-017/FR-018).
- **AC-8 (config flow)** : le menu propose **toujours** l'option « Humidité » (quels que soient les choix de la page « features », qui reste inchangée) ; la page permet activation/désactivation et sélection du capteur ; le sélecteur est pré-rempli avec le capteur auto-détecté (AC-3/AC-4) ; l'entity_id invalide est rejeté avec message d'erreur ; la configuration est modifiable ; `check_config_complete` reste cohérent ; l'utilisateur peut finaliser sans visiter la page « Humidité ».
- **AC-9 (re-détection)** : modification de la config — ajout d'un capteur explicite → il prime sur la détection ; suppression du capteur explicite → nouvelle détection ; désactivation → repli (BR-005).
- **AC-10 (non-régression algorithmes)** : avec/sans capteur d'humidité, les sorties des algorithmes de régulation (TPI, prog, sécurité, etc.) sont identiques ; `async_set_humidity`/`set_humidity` inchangés en comportement.
- **AC-11 (montée en charge)** : un VTherm (idéalement l'ensemble des entités d'une instance de test) avec capteurs d'humidité actifs ne provoque ni crash ni erreur récurrente dans les logs sur une durée représentative (ex. suite de tests complète + vérification manuelle).
- **AC-12 (documentation/traductions)** : documentation à jour dans **toutes** les langues (CS, DE, EN, FR, PL) ; clés `strings.json`/`translations` présentes **dans toutes les langues** pour la page « Humidité » ; paragraphe « Release 10.4 » de **tous** les README (`README.md`, `README-cs.md`, `README-de.md`, `README-fr.md`, `README-pl.md`) complété avec la fonctionnalité humidité dans la langue concernée.

## 8. Fonctions non prises en compte

- Contrôle d'humidité (consigne, déshumidification, humidification) — hors périmètre ; `async_set_humidity` reste inchangé.
- Entité datetime « dernière mesure d'humidité » — refusée (D6) : aucun usage dans les algorithmes (confirmation faite : aucun symbole existant ne consomme l'humidité courante à des fins de régulation ; voir « Traçabilité »).
- Historique, statistiques, capteur de diagnostic dédié pour l'humidité — possible extension future (rapport §4 exclusions).
- Auto-détection basée sur d'autres critères que le `device_id` du capteur de température (zone/pièce, nom, proximité) — non prévu.

## 9. Évolutions futures proposées

- Capteur de diagnostic/historique d'humidité si un besoin utilisateur émerge.
- Auto-détection étendue (zone/piece, capteurs `hygrostat`), choix interactif en cas de candidats multiples.
- Usage de l'humidité dans des algorithmes futurs (confort, condensation) — supposerait d'ajouter alors l'entité datetime et de revoir D6/D7 ; questions à trancher à ce moment-là.

## 10. Hypothèses, questions ouvertes et traçabilité

**Hypothèses (H)** :
- **H1** : le capteur d'humidité est une entité du domaine `sensor` avec `device_class: humidity` (issue/rapport).
- **H2** : l'auto-détection sur le `device_id` du capteur de température est suffisante (le capteur de température est obligatoire dans la configuration d'un VTherm).
- **H3** : l'accès au registre d'entités HA (entity registry) permet de retrouver le `device_id` d'une entité et les entités d'un appareil avec leur `device_class` — pattern disponible dans Home Assistant.
- **H4** : l'ordre « du registre » est stable au sein d'un même démarrage (suffisant pour le choix du premier candidat).

**Questions ouvertes (Q)** :
- **Q1** : **Tranché (2026-09-17)** : **non**, pas de log d'écrasement. Si un capteur externe est explicitement spécifié, l'utilisateur sait ce qu'il a configuré — aucun log (ni info ni warning) de l'écrasement de l'humidité sous-jacente en `over_climate`.
- **Q2** : **Tranché (2026-09-17)** : à état invalide, il faut pouvoir **forcer une valeur invalide** via VTherm — retourner `None` ou un état tel que `unavailable` si l'API `ClimateEntity` le permet (à valider techniquement en conception : faisabilité d'exposer un état invalide). Ne pas conserver la dernière valeur valide (voir FR-017/BR-003).
- **Q3** : la page « Humidité » doit-elle apparaître dans le menu dès la création du VTherm (avant toute activation), ou uniquement après activation d'un toggle « use humidity » quelque part ? **Tranché (2026-09-17)** : l'option de menu « Humidité » est **toujours présente**, indépendamment de la page « features » qui **ne change pas** (pas de case humidité à cocher) ; l'activation/désactivation se fait par le toggle de la page « Humidité » elle-même (voir FR-016).
- **Q4** : **Tranché (2026-09-17)** : au démarrage, le capteur peut être momentanément indisponible (ordre de chargement des capteurs par HA) — il faut donc **réessayer plus tard** (re-tentatives de lecture/détection) et remonter l'humidité comme **indéfinie** (`None`) tant que le capteur n'est pas disponible (voir FR-018).

**Divergences avec le rapport de revue** : aucune. Conformité D1–D7 vérifiée : réimplémentation interne (D1), tous types (D2), auto-détection sur `device_id` avec premier candidat + log (D3), priorité des sources et compatibilité ascendante (D4), page dédiée facultative pré-remplie (D5), pas d'entité datetime — l'analyse n'a mis en évidence aucun usage de l'humidité courante dans les algorithmes, donc aucune divergence à la D6 (D6), humidité purement informative (D7).

**Traçabilité (symboles vérifiés)** :
- `thermostat_climate.py` : `current_humidity` (lecture `underlying_entity(0)`, ~l. 1159 — comportement actuel confirmé), `async_set_humidity` (~l. 1233, inchangé).
- `base_thermostat.py` : `async_set_humidity` (~l. 1589), `await self._async_update_ext_temp(...)` (~l. 599, 2151), `async def _async_update_ext_temp` (~l. 2193 — reusable state-handling pattern).
- `underlyings.py` : `current_humidity` (~l. 987, via `get_underlying_attribute`), `set_humidity`.
- `config_flow.py` : `async_step_menu` (~l. 611) dynamically building `menu_options` (conditional options `window`, `motion`, `presence`, `power`, `sync_device_internal_temp`, etc. — pattern for adding an option), `async_step_main`/`async_step_spec_main`, `window`/`motion` steps.
- Tests : `tests/test_config_flow.py` (`menu_options` assertions), `tests/commons.py` (`current_humidity` mocks).

# Partie 2 — English version

## 1. Title and metadata

- **File**: `documentation/tech-docs/issue-1964-specification.md`
- **Version**: 1.1, status Draft, 2026-09-17
- **Sources**: issue #1964, review report `issue-1964-review.md`, technical design `issue-1964-design.md`, verified code symbols.

## 2. Scope, constraints and acceptance criteria (summary)

**Functional scope included** (per review report §4): optional configuration key available for all VTherm types; auto-detection via the HA entity registry (`device_class == humidity`, same `device_id` as the configured temperature sensor, first candidate if several); source priority: explicit sensor > auto-detected sensor > underlying climate entity (`over_climate` only) > `None`; dedicated optional "Humidity" menu page in the config flow (toggle + sensor selector pre-filled with the auto-detected sensor); listener + initial read + invalid-state handling (keep last valid value); no entity or algorithm change for humidity control (`async_set_humidity` unchanged); no datetime humidity entity.

**Key functional requirements**:
- **FR-014**: The system shall provide user documentation in **all repository languages** (**CS, DE, EN, FR, PL — mandatory**, per user decision of 2026-09-17) and complete UI translations in **all languages** (`strings.json` / `translations/`) for the "Humidity" page and menu option. Concerned files: `documentation/{cs,de,en,fr,pl}/`, `strings.json`, all files in `translations/`, and `README{,-cs,-de,-fr,-pl}.md`.
- **FR-015**: The "What's new?" paragraph announcing **release 10.4** in each README (`README.md`, `README-fr.md`, `README-cs.md`, `README-de.md`, `README-pl.md`) shall be **updated** with the "external humidity sensor" feature, in the language of the relevant README.

**Documentation / translations constraint**: repository conventions (`documentation/` per language, `strings.json` + `translations/`) — **all languages mandatory (CS, DE, EN, FR, PL)**, including the update of the "Release 10.4" paragraph in **all** READMEs.

**Acceptance criteria (summary; full list in the French part)**: AC-1 to AC-11 cover all VTherm types, resolution priorities, auto-detection (none/one/several candidates), invalid states, restart, re-detection, non-regression of algorithms and `async_set_humidity`, and resilience.
- **AC-12 (documentation/translations)**: documentation up to date in **all** languages (CS, DE, EN, FR, PL); `strings.json`/`translations` keys present in **all** languages for the "Humidité" page; "Release 10.4" paragraph in **all** READMEs (`README.md`, `README-cs.md`, `README-de.md`, `README-fr.md`, `README-pl.md`) updated with the humidity feature in the relevant language.

La version française (Partie 1) fait autorité en cas de divergence entre les deux parties.
