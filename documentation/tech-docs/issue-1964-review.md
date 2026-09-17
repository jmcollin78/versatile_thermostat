# Revue de l'issue #1964 — External Humidity Sensor Support

- **Issue** : [jmcollin78/versatile_thermostat#1964](https://github.com/jmcollin78/versatile_thermostat/issues/1964)
- **Titre** : [Feature Request] - External Humidity Sensor Support
- **Auteur** : @BTopbas (ouvert le 12 mai) · **Étiquette** : `enhancement` · **État** : Open, non assignée, pas de PR liée
- **Date de revue** : 2026-09-17 · **Mise à jour** : 2026-09-17 (décisions utilisateur intégrées)

## 1. Résumé fidèle de l'issue

Demande de fonctionnalité : permettre d'affecter un **capteur d'humidité externe** à une entité Versatile Thermostat (type `over_climate`), afin que `current_humidity` soit alimenté par ce capteur plutôt que par l'entité climate sous-jacente.

- **Motivation** : en `over_climate`, `current_humidity` est lu directement depuis l'entité sous-jacente (pompe à chaleur, clim…). Beaucoup d'utilisateurs disposent d'un capteur d'humidité mieux placé (centre de pièce). Par ailleurs, certains équipements (clims IR, vannes radiateur, intégrations tierces) n'exposent aucune valeur d'humidité : `current_humidity` est alors toujours `None` sans possibilité de la renseigner.
- **Comportement proposé** : nouveau champ optionnel `humidity_sensor_entity_id` ; si configuré, `current_humidity` retourne la valeur du capteur ; sinon comportement existant (lecture depuis l'entité climate sous-jacente). Exposition via l'attribut standard HA `current_humidity` (carte thermostat Lovelace, Apple Home/HomeKit `CurrentRelativeHumidity`, etc.).
- **Notes d'implémentation fournies par l'auteur** (implémentation locale fonctionnelle, testée 2 jours en production) :
  - `const.py` : `CONF_HUMIDITY_SENSOR = "humidity_sensor_entity_id"`
  - `base_thermostat.py` : suivi des changements d'état du capteur, lecture initiale au démarrage, stockage dans `_cur_humidity`, `_attr_current_humidity`, `_humidity`
  - `thermostat_climate.py` : surcharge de `current_humidity` pour préférer le capteur externe, avec repli sur `underlying_entity(0).current_humidity`
- **Réaction du mainteneur** (@jmcollin78, 13 mai) : invite l'auteur à soumettre une PR avec tests et documentation. L'auteur précise que le code a été assisté par IA et demande une revue attentive. **Aucune PR n'est liée à ce jour.**

## 2. Sources et éléments vérifiés

- Issue #1964 (description complète, commentaires, étiquettes, métadonnées) — consultée le 2026-09-17.
- Dépôt local (branche courante `1348-...`, base `main`) :
  - `custom_components/versatile_thermostat/thermostat_climate.py` : `current_humidity` (vers ligne 1159) retourne `self.underlying_entity(0).current_humidity` — confirme le comportement décrit dans l'issue.
  - `custom_components/versatile_thermostat/underlyings.py` : `current_humidity` lu via `get_underlying_attribute("current_humidity")` (ligne ~987) ; `set_humidity` vs `SERVICE_SET_HUMIDITY` (traitement de l'humidité **cible**, à distinguer de l'humidité **courante**).
  - `custom_components/versatile_thermostat/base_thermostat.py` : motifs existants pour `sensor_entity_id` / `external_temp_sensor_entity_id` / `last_seen` (listeners `async_track_state_change_event` dans `async_added_to_hass`, gestionnaires `_async_update_temp`, `_async_update_ext_temp`, etc.) — modèle direct pour l'humidité.
  - `config_flow.py` / `config_schema.py` : mécanismes de validation des entity_ids (`validate_input`) et schémas par étape — un nouveau champ devra y être ajouté.
  - `sensor.py` : capteurs additionnels de diagnostic (dates de dernière mesure, etc.).
  - Tests existants (`tests/test_sensors.py`, `tests/test_config_flow.py`, `tests/test_bugs.py`) : patterns de tests réutilisables.

## 3. Analyse de pertinence

**Recommandation : RETENIR** (avec périmètre cadré).

- **Problème réel** : oui. Aucune alternative dans VTherm aujourd'hui pour peupler `current_humidity` quand l'entité sous-jacente ne l'expose pas ou qu'un capteur mieux placé existe.
- **Cohérence avec le projet** : forte. La priorité « capteur dédié > valeur de l'entité sous-jacente » est déjà le pattern appliqué pour la température ambiante et la température extérieure. L'humidité est le chaînon manquant.
- **Valeur attendue** : correcte et immédiate (visibilité HomeKit/Lovelace, compatibilité intégrations lisant l'attribut standard).
- **Faisabilité** : élevée. L'issue propose une approche alignée sur l'existant ; les motifs de listener et de config sont déjà en place.
- **Doublons / travaux liés** : pas de PR liée à l'issue ; pas de doublon identifié dans le code consulté.

## 4. Périmètre proposé

**Inclus** (mis à jour après décisions utilisateur du 2026-09-17) :
1. Nouvelle clé de configuration optionnelle (par ex. `CONF_HUMIDITY_SENSOR` / `humidity_sensor_entity_id`), disponible pour **tous les types de VTherm** (pas seulement `over_climate`).
2. **Auto-détection** : si l'utilisateur n'a rien spécifié, tenter de trouver automatiquement un capteur d'humidité sur le **même appareil** (`device_id`) que le capteur de température fourni dans la configuration (via le registre d'entités HA, `device_class == humidity`). L'auto-détection n'intervient **que** si aucun capteur n'est explicitement configuré. Si **plusieurs candidats** sont trouvés, on **prend le premier** (ordre du registre d'entités HA ; cas rare mais possible) — avec un log informatif listant tous les candidats trouvés à des fins de diagnostic.
3. **Priorité des sources** : capteur explicite > capteur auto-détecté > entité climate sous-jacente (`over_climate` uniquement) > `None`.
4. Configuration via `config_flow.py` + `config_schema.py` : le capteur d'humidité est configuré dans une **option de menu dédiée « Humidité »** du menu du config flow (pattern existant : `window`, `motion`, `presence`, `sync_device_internal_temp`…). Sur cette page : possibilité d'activer/désactiver l'utilisation de l'humidité, sélecteur de capteur **pré-rempli avec le capteur auto-détecté** (donc l'utilisateur voit ce qui a été trouvé en automatique — pas de boîte noire), et validation de l'entity_id. Cohérence avec `check_config_complete`. L'auto-détection reste opérationnelle même si l'utilisateur ne visite jamais cette page (l'option de menu est optionnelle, la fonctionnalité reste « zéro configuration »).
5. `base_thermostat.py` : listener de changement d'état + lecture initiale, stockage interne, gestion `unavailable`/`unknown`/valeurs non numériques (NaN/Inf) conformément au pattern température ; re-détection dynamique au démarrage et à la modification de la config.
6. `thermostat_climate.py` : `current_humidity` privilégie le capteur externe (explicite ou auto-détecté), repli sur l'entité sous-jacente.
7. Tests unitaires : config flow avec/sans capteur, auto-détection (candidat trouvé / plusieurs candidats / aucun), mise à jour d'état, repli, valeurs invalides, tous types de VTherm.
8. Documentation (`documentation/`, au minimum EN/FR, idéalement CS/DE/PL) + traductions UI (`strings.json` / `translations`).

**Exclus** :
- Tout contrôle d'humidité (setpoint, déshumidification) : hors périmètre ; `async_set_humidity` existant reste inchangé.
- Historique/statistiques d'humidité ou capteur de diagnostic dédié (possible extension future).

## 5. Impacts et risques

| Risque                                                                                                      | Gravité | Probabilité | Commentaire                                                                                                                                                                       |
| ----------------------------------------------------------------------------------------------------------- | ------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Régression de `current_humidity` pour les VTherm sans capteur configuré                                     | Moyenne | Faible      | Repli obligatoire sur le comportement actuel ; testé                                                                                                                              |
| Conflit de nommage interne (`_humidity` déjà utilisé ? sémantique ambiguë entre humidité courante et cible) | Moyenne | Moyenne     | Vérifier précisément les attributs existants ; l'issue mentionne `_cur_humidity`, `_attr_current_humidity`, `_humidity` sans clarification — point d'attention pour la conception |
| Qualité du code fourni par l'auteur (assisté par IA, l'auteur lui-même demande une revue)                   | Moyenne | Moyenne     | Pas de PR soumise : réimplémentation propre nécessaire dans le cadre du projet ; on reprend l'idée, pas le code                                                                   |
| Prolifération de capteurs externes à écouter (coût runtime marginal)                                        | Faible  | Faible      | Un listener supplémentaire optionnel                                                                                                                                              |
| Documentation/traductions incomplètes (众多 langues)                                                        | Faible  | Moyenne     | Prévoir mise à jour minimale conforme aux conventions                                                                                                                             |
| Compatibilité/migration config existante                                                                    | Faible  | Faible      | Champ optionnel, pas de migration requise                                                                                                                                         |

**Sécurité/confidentialité** : néant de particulier (lecture d'un capteur local).
**Exploitation** : logs cohérents avec le pattern température recommandés.

## 6. Alternatives examinées

- **Template sensor / `current_humidity` écrasé via personnalisation HA** : contournement imparfait (pas d'attribut standard exposé par VTherm, fragile). Écarté.
- **Exposer l'humidité via un capteur dédié VTherm plutôt que l'attribut climate** : ne répond pas au besoin HomeKit/Lovelace sur l'entité climate elle-même. Écarté.
- **Appliquer aussi aux types `over_switch`/`over_valve`** : possible mais sans sous-jacent气候 ; à différer.

## 7. Hypothèses, décisions nécessaires et questions ouvertes

- **Décisions tranchées par l'utilisateur (2026-09-17)** :
  1. La PR de l'auteur de l'issue a été refusée : **réimplémentation interne**, on n'attend pas l'auteur.
  2. L'humidité est proposée pour **tous les types de VTherm** (pas seulement `over_climate`).
  3. **Auto-détection** : chercher un capteur d'humidité sur le même appareil que le capteur de température configuré ; si trouvé, l'utiliser.
  4. L'utilisateur peut **spécifier explicitement** un capteur ; l'auto-détection ne s'applique que si rien n'est spécifié → **compatibilité ascendante préservée** (aucune configuration existante n'est impactée). Si plusieurs candidats sont trouvés en auto-détection, **le premier est retenu** (décision du 2026-09-17).
  5. UX config flow : **option de menu dédiée « Humidité »** plutôt que champ sur la page du capteur de température (qui ne permettrait pas d'afficher le résultat de l'auto-détection). L'option est facultative : l'auto-détection fonctionne même sans visiter cette page (décision du 2026-09-17).
  6. **Pas d'entité datetime pour l'humidité** : l'humidité est purement **affichée** (aucun usage à ce jour dans les algorithmes de VTherm), donc une entité « date de dernière mesure d'humidité » n'est **pas nécessaire** — à confirmer en spécification/conception (décision du 2026-09-17).
- **Hypothèses restantes** : le capteur est un entity_id de domaine `sensor` (device_class humidity) ; l'humidité est purement informative pour VTherm (aucun usage dans les algorithmes de régulation actuels) ; si aucun candidat n'est trouvé en auto-détection → `None` (log informatif), pas d'erreur.
- **Questions ouvertes** : aucune bloquante. Point de contrôle en spécification/conception : confirmer l'inutilité d'une entité datetime humidité (orientation actuelle : non nécessaire).

## 8. Proposition de suite du processus et critères de passage au développement

1. Accord utilisateur sur le présent rapport et le périmètre proposé.
2. Rédaction de la **spécification fonctionnelle** (sous-agent `Rédacteur de spécifications`) : règles, critères d'acceptation, périmètre, exclusions.
3. **Conception technique** (sous-agent `Conception logicielle détaillée`) : composants affectés (`const.py`, `base_thermostat.py`, `thermostat_climate.py`, `config_flow.py`, `config_schema.py`, `strings.json`), flux d'états, erreurs, tests.
4. Convergence des deux documents (max 3 cycles).
5. Validation utilisateur finale, puis délégation au développement (`Développement d’intégrations Home Assistant`).

**Critères d'acceptation proposés (préliminaires)** :
- Avec capteur configuré : `current_humidity` reflète la valeur du capteur en temps réel (y compris après redémarrage).
- Sans capteur : comportement strictement identique à l'existant.
- Capteur `unavailable`/`unknown`/valeur invalide : pas de crash, repli maîtrisé (à définir en spécification).
- Config flow : champ optionnel validé, configuration modifiable.
- Tests unitaires couvrant les cas ci-dessus ; documentation et traductions à jour.

## 9. Inconnus assumés

- Le contenu exact de l'implémentation locale de l'auteur (non publié — pas de PR) : seules ses notes d'implémentation sont connues.
- L'existence d'éventuelles branches locales/travaux privés en cours sur ce sujet dans le dépôt (non détectés).
- L'état exact de l'attribut `_humidity` mentionné dans l'issue (vérification à faire en conception).
