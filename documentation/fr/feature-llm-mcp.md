# Versatile Thermostat + MCP Home Assistant

Cette documentation décrit l'ajout d'outils LLM/MCP à **Versatile Thermostat (VTherm)** via le serveur MCP officiel de Home Assistant.

Le fichier `llm.py` fourni expose :

- 4 outils de lecture/diagnostic et d’historique ;
- 3 outils d'action simples : température, preset et mode HVAC ;
- 2 outils TPI de lecture et 1 outil TPI d’écriture explicite ;
- des descriptions et instructions utilisables en **français et en anglais** ;
- des liens vers la documentation VTherm, le collecteur de logs et l'analyseur de logs pour le dépannage.

> Le fichier ne crée pas son propre serveur MCP. Il utilise la plateforme LLM native de Home Assistant, puis le **Model Context Protocol Server** officiel de Home Assistant publie ces outils aux clients MCP.

---

## 1. Fichier à installer

Copier les quatre fichiers suivants dans le répertoire de l’intégration :

```text
/config/custom_components/versatile_thermostat/llm.py
/config/custom_components/versatile_thermostat/recorder_export.py
/config/custom_components/versatile_thermostat/tpi_history.py
/config/custom_components/versatile_thermostat/tpi_identification.py
```

Arborescence :

```text
/config/custom_components/versatile_thermostat/
├── __init__.py
├── climate.py
├── const.py
├── manifest.json
├── ...
├── llm.py
├── recorder_export.py
├── tpi_history.py
└── tpi_identification.py
```

Il n'est pas nécessaire de modifier `manifest.json` pour déclarer la plateforme `llm`.

Home Assistant recherche les plateformes d'intégration de manière dynamique et charge `llm.py` à la demande lorsqu'une API LLM a besoin des outils de l'intégration.

Après avoir copié le fichier, effectuer un **redémarrage complet de Home Assistant**.

> Attention : si `llm.py` a été ajouté manuellement dans une installation VTherm gérée par HACS, une future mise à jour HACS peut remplacer le répertoire de l'intégration. Conserver une copie du fichier tant qu'il n'est pas intégré au projet VTherm lui-même.

---

## 2. Outils exposés

Avec l'API LLM `assist`, le serveur MCP Home Assistant ajoute le préfixe `assist__` aux outils.

### Lecture seule — niveau 1

```text
assist__versatile_thermostat__list_vtherms
assist__versatile_thermostat__get_status
assist__versatile_thermostat__diagnose
assist__versatile_thermostat__get_history
```

### Actions — niveau 2A

```text
assist__versatile_thermostat__set_temperature
assist__versatile_thermostat__set_preset
assist__versatile_thermostat__set_hvac_mode
```

Les trois premiers outils sont marqués :

```python
read_only=True
destructive=False
idempotent=True
open_world=False
```

Les trois outils d'action sont marqués :

```python
read_only=False
destructive=False
idempotent=True
open_world=False
```

Ils modifient réellement l'état du thermostat, mais uniquement via les services standards Home Assistant `climate.*`.

---

## 3. `list_vtherms`

Cet outil liste uniquement les entités VTherm :

- chargées dans Home Assistant ;
- de domaine `climate` ;
- appartenant à une entrée de configuration Versatile Thermostat ;
- exposées à Assist.

Pour chaque thermostat, il renvoie notamment :

```text
entity_id
name
hvac_mode
hvac_action
preset_mode
current_temperature
target_temperature
target_minus_current
min_temperature
max_temperature
target_temperature_step
hvac_modes
preset_modes
thermostat_type
messages
```

Exemple simplifié :

```json
{
  "entity_id": "climate.thermostat_salon",
  "hvac_mode": "heat",
  "hvac_action": "heating",
  "preset_mode": "comfort",
  "current_temperature": 18.7,
  "target_temperature": 19.5,
  "target_minus_current": 0.8,
  "hvac_modes": ["heat", "off"],
  "preset_modes": ["none", "frost", "eco", "comfort", "boost"]
}
```

---

## 4. `get_status`

`get_status` retourne l'état brut complet de l'entité VTherm :

```text
entity_id
state
last_changed
last_updated
attributes
```

`attributes` contient les attributs Home Assistant et les attributs spécifiques VTherm disponibles sur l'entité.

Cet outil est utile lorsque l'agent a besoin d'une donnée qui n'a pas été extraite dans le diagnostic structuré.

---

## 5. `diagnose`

`diagnose` est l'outil à privilégier pour les demandes telles que :

- « Pourquoi mon thermostat ne chauffe pas ? »
- « Pourquoi est-il en idle ? »
- « Est-il délesté ? »
- « Y a-t-il un problème avec une fenêtre ? »
- « Pourquoi VTherm s'est arrêté ? »
- « Debug the living-room thermostat. »
- « Diagnose why this VTherm is not heating. »

Il renvoie notamment :

### État courant

```text
hvac_mode
hvac_action
preset_mode
current_temperature
target_temperature
target_minus_current
hvac_modes
preset_modes
```

### Raisons VTherm

Le fichier privilégie les informations calculées par VTherm lui-même :

```text
specific_states.messages
hvac_off_reason
hvac_mode_reason
should_device_be_active
device_actives
unavailable_underlying_entities
temperature_slope
is_sleeping
is_recalculate_scheduled
```

L'objectif est d'éviter que le modèle invente une cause à partir de la seule différence entre température actuelle et consigne.

### Sections de diagnostic

Lorsqu'elles existent, les sections suivantes sont renvoyées intégralement :

```text
configuration
current_state
requested_state
specific_states
preset_temperatures
presence_manager
motion_manager
power_manager
window_manager
safety_manager
auto_start_stop_manager
lock_manager
heating_failure_detection
vtherm_over_switch
vtherm_over_climate
vtherm_over_valve
```

Une section absente de l'entité n'est simplement pas renvoyée.

---

## 6. Documentation et dépannage VTherm

Le résultat de `diagnose` contient également `support_resources` avec les ressources françaises **et** anglaises :

```text
documentation_fr
documentation_en
reference_fr
reference_en
log_collector_fr
log_collector_en
log_analyzer
official_repository
log_download_action
```

Liens principaux :

- Documentation FR : https://www.versatile-thermostat.org/fr/
- Documentation EN : https://www.versatile-thermostat.org/en/
- Référence FR : https://www.versatile-thermostat.org/fr/docs/reference/
- Référence EN : https://www.versatile-thermostat.org/en/docs/reference/
- Collecteur de logs FR : https://www.versatile-thermostat.org/fr/docs/feature-logs-collector/
- Collecteur de logs EN : https://www.versatile-thermostat.org/en/docs/feature-logs-collector/
- Analyseur de logs : https://www.versatile-thermostat.org/fr/debugger/
- Dépôt officiel VTherm : https://github.com/jmcollin78/versatile_thermostat

Le prompt fourni au LLM lui demande, pour un debug complexe :

1. d'utiliser d'abord les informations renvoyées par VTherm ;
2. de ne pas inventer une cause non présente dans les données ;
3. de consulter la documentation FR ou EN adaptée à la langue de la demande si le client dispose d'un accès Web ;
4. de proposer le collecteur puis l'analyseur de logs si l'état instantané ne permet pas de conclure.

### Important

`llm.py` **ne télécharge pas lui-même les pages Web**.

Il fournit les URLs et les instructions au client LLM. Si le client utilisé (Codex, Gemini, Claude, etc.) dispose d'un accès Web, il peut consulter la documentation. Sinon, il peut au minimum fournir les liens à l'utilisateur.

Le site versatile-thermostat.org indique lui-même être un site communautaire et précise que la source officielle du projet reste le dépôt GitHub VTherm.

---

## 7. Collecteur de logs

VTherm fournit l'action :

```text
versatile_thermostat.download_logs
```

Le fichier `llm.py` n'exécute pas cette action automatiquement ; il la signale comme ressource de dépannage.

Exemple Home Assistant :

```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.thermostat_salon
  log_level: DEBUG
```

Le fichier obtenu peut ensuite être chargé dans l'analyseur :

```text
https://www.versatile-thermostat.org/fr/debugger/
```

---

# Niveau 2 — actions

## 8. `set_temperature`

Utilise :

```text
climate.set_temperature
```

Paramètres MCP :

```json
{
  "entity_id": "climate.thermostat_salon",
  "temperature": 19.5
}
```

Avant l'appel, l'outil vérifie :

- que le VTherm est exposé à Assist ;
- qu'un utilisateur Home Assistant authentifié est associé à l'appel ;
- que l'utilisateur a le droit de contrôler cette entité ;
- que la température demandée reste comprise entre les valeurs min/max du thermostat lorsqu'elles sont disponibles.

Le résultat contient :

```text
success
action
requested
state_after_call
note
```

`state_after_call` permet au modèle de vérifier l'état juste après la commande.

VTherm peut ensuite modifier l'état effectif selon ses propres règles : mode central, fenêtre, délestage, sécurité, preset, auto-start/stop, régulation, etc.

---

## 9. `set_preset`

Utilise :

```text
climate.set_preset_mode
```

Paramètres :

```json
{
  "entity_id": "climate.thermostat_salon",
  "preset": "comfort"
}
```

Avant l'action, le preset demandé doit apparaître dans :

```text
preset_modes
```

de l'entité ciblée.

Un modèle ne peut donc pas demander arbitrairement un preset qui n'est pas disponible sur ce thermostat.

---

## 10. `set_hvac_mode`

Utilise :

```text
climate.set_hvac_mode
```

Paramètres :

```json
{
  "entity_id": "climate.thermostat_salon",
  "hvac_mode": "heat"
}
```

Le mode doit être présent dans :

```text
hvac_modes
```

Pour éteindre un thermostat lorsque `off` est supporté :

```json
{
  "entity_id": "climate.thermostat_salon",
  "hvac_mode": "off"
}
```

Le fichier n'expose volontairement aucun outil `toggle` : l'état souhaité doit être explicite.

---

## 11. Sécurité des actions

Les trois actions climate ci-dessus appliquent plusieurs garde-fous (l’action TPI est décrite séparément) :

1. uniquement des VTherm exposés à Assist ;
2. contexte utilisateur Home Assistant obligatoire pour une écriture ;
3. vérification de la permission `CONTROL` ;
4. validation des presets et modes HVAC contre l'entité réelle ;
5. validation de la plage de température ;
6. utilisation uniquement des services standards `climate.*` ;
7. aucune modification de la configuration interne VTherm ;
8. aucun changement de TPI, délestage, fenêtre, sécurité ou algorithme.

Les actions sont marquées `read_only=False`, ce qui permet au serveur MCP Home Assistant de les masquer lorsque son option **Read only** est activée.

---

# Installation du serveur MCP officiel Home Assistant

## 12. Activer le serveur MCP

Dans Home Assistant :

```text
Paramètres
→ Système
→ IA
→ Model Context Protocol
```

Activer le serveur MCP si nécessaire.

Il est également possible de passer par :

```text
Paramètres
→ Appareils et services
→ Ajouter une intégration
→ Model Context Protocol Server
```

Home Assistant fournit ensuite une URL MCP, typiquement en local :

```text
http://homeassistant.local:8123/api/mcp
```

---

## 13. Configuration recommandée du serveur MCP

Dans les options de **Model Context Protocol Server** :

```text
Expose all LLM APIs      : OFF (recommandé pour limiter la surface)
Control Home Assistant   : Assist / Device control
Require administrator    : ON
Read only                : OFF pour utiliser le niveau 2
```

### Si `Read only` est activé

Les outils d'action :

```text
set_temperature
set_preset
set_hvac_mode
set_tpi_coefficients
```

sont filtrés du catalogue MCP car ils sont déclarés `read_only=False`.

Les outils de diagnostic restent disponibles.

C'est utile si l'on souhaite temporairement revenir à un fonctionnement niveau 1 sans modifier `llm.py`.

---

## 14. Exposer les VTherm à Assist

Les outils n'accèdent qu'aux thermostats exposés à Assist.

Dans Home Assistant, exposer les entités nécessaires, par exemple :

```text
climate.thermostat_salon
climate.thermostat_cuisine
climate.thermostat_salle
```

Il n'est pas nécessaire d'exposer tous les équipements de la maison.

---

# Connexion à Codex

## 15. Ajouter le serveur MCP

```bash
codex mcp add homeassistant \
  --url http://homeassistant.local:8123/api/mcp
```

Codex ouvre Home Assistant dans le navigateur pour l'authentification OAuth.

Vérification :

```bash
codex mcp list
```

Exemple :

```text
homeassistant  http://homeassistant.local:8123/api/mcp  enabled
```

Pour installer et configurer le serveur MCP officiel de Home Assistant, consulter la [documentation de référence Home Assistant](https://www.home-assistant.io/integrations/mcp_server/).

---

## 16. Vérifier les outils VTherm

Prompt :

```text
Utilise uniquement le serveur MCP homeassistant.
Liste tous les outils disponibles sur ce serveur dont le nom contient
versatile_thermostat. N'effectue aucune action.
```

Avec le niveau 2A, on doit retrouver :

```text
assist__versatile_thermostat__list_vtherms
assist__versatile_thermostat__get_status
assist__versatile_thermostat__diagnose
assist__versatile_thermostat__get_history
assist__versatile_thermostat__set_temperature
assist__versatile_thermostat__set_preset
assist__versatile_thermostat__set_hvac_mode
assist__versatile_thermostat__check_tpi_optimization
assist__versatile_thermostat__analyze_tpi_coefficients
assist__versatile_thermostat__set_tpi_coefficients
```

Le catalogue complet contient six outils de lecture et quatre d’écriture. Avec **Read only**, seuls les six outils de lecture restent visibles.

---

# Exemples de questions

## 17. Français — lecture et diagnostic

```text
Liste mes Versatile Thermostat et donne-moi leur température actuelle,
leur consigne et leur état de chauffe.
```

```text
Diagnostique climate.thermostat_salon et explique pourquoi il ne chauffe pas.
N'invente aucune cause non présente dans les données VTherm.
```

```text
Pourquoi le thermostat du salon est-il idle alors que la température est
inférieure à la consigne ? Regarde aussi le délestage, la sécurité et les fenêtres.
```

```text
Fais un diagnostic de climate.thermostat_salon. Si les données ne suffisent pas,
indique quelle documentation VTherm consulter et rappelle-moi comment utiliser
le collecteur et l'analyseur de logs.
```

---

## 18. Français — actions

```text
Mets la consigne du thermostat du salon à 19,5 °C.
```

```text
Passe climate.thermostat_salon en preset comfort.
```

```text
Passe climate.thermostat_salon en mode HVAC off.
```

```text
Remets climate.thermostat_salon en mode heat puis affiche son état.
```

---

## 19. English — read and diagnose

```text
List my Versatile Thermostats and show their current temperature,
target temperature and HVAC action.
```

```text
Diagnose climate.thermostat_salon and explain why it is not heating.
Do not infer a cause that is not supported by the VTherm diagnostic data.
```

```text
Debug climate.thermostat_salon. Check power shedding, safety, window detection,
auto start/stop and unavailable underlying entities.
```

```text
If the current diagnostic data is not enough, tell me which VTherm documentation
page or log-analysis workflow I should use next.
```

---

## 20. English — actions

```text
Set climate.thermostat_salon to 19.5 °C.
```

```text
Set climate.thermostat_salon preset to comfort.
```

```text
Set climate.thermostat_salon HVAC mode to off.
```

---

# Dépannage

## 21. Aucun outil VTherm n'apparaît

Vérifier :

1. le fichier existe bien ici :

   ```text
   /config/custom_components/versatile_thermostat/llm.py
/config/custom_components/versatile_thermostat/recorder_export.py
/config/custom_components/versatile_thermostat/tpi_history.py
/config/custom_components/versatile_thermostat/tpi_identification.py
   ```

2. Home Assistant a été redémarré ;
3. VTherm est chargé normalement ;
4. au moins un `climate` VTherm est exposé à Assist ;
5. l'API Assist/Device control est exposée par le serveur MCP ;
6. le client MCP s'est reconnecté après le redémarrage.

La plateforme `llm.py` est chargée à la demande : l'absence de message au démarrage de Home Assistant ne signifie pas nécessairement qu'elle n'a pas été détectée.

---

## 22. Les outils de lecture apparaissent mais pas les actions

Vérifier l'option :

```text
Model Context Protocol Server → Read only
```

Pour le niveau 2A :

```text
Read only = OFF
```

---

## 23. Une action est refusée

Le résultat de l'outil indique normalement la raison :

- absence de contexte utilisateur authentifié ;
- permission insuffisante ;
- température hors plage ;
- preset inexistant ;
- mode HVAC non supporté ;
- erreur renvoyée par le service Home Assistant.

Utiliser `list_vtherms` ou `get_status` pour récupérer les valeurs réellement supportées par l'entité.

---

# Optimisation des coefficients TPI par historique

Une demande simple suffit, par exemple : « Tu regardes si les coefficients du thermostat chambre parents sont optimaux ? » ou « Mes coefficients sont-ils bien réglés ? ». Les descriptions des outils guident l'assistant vers la vérification puis le calcul TPI en lecture seule, avec résolution du nom de pièce si nécessaire. Aucun nom d'outil ni `entity_id` n'est requis dans la question, et l'accès au tableau de bord n'est pas un préalable. Le connecteur utilisé doit toutefois exposer `check_tpi_optimization` et `analyze_tpi_coefficients` : une formulation différente ne rend pas disponibles des outils absents. Le résultat reste une estimation exploratoire, pas la preuve d'un optimum.

Trois outils complètent les outils existants :

| Outil (suffixe `versatile_thermostat__…`) | Accès | Étape |
| --- | --- | --- |
| `check_tpi_optimization` | Lecture seule | 1/3 — vérification |
| `analyze_tpi_coefficients` | Lecture seule | 2/3 — analyse |
| `set_tpi_coefficients` | Écriture explicite | 3/3 — application éventuelle |

Les outils de lecture prennent uniquement `entity_id`. Le client annonce chaque étape avant l'appel ; aucun traitement en arrière-plan n'est simulé. Chaque réponse contient `stage`, `stage_number`, `stage_total` et `state_changed`.

L'analyse concerne uniquement le TPI classique (`proportional_function=tpi`), sans Auto-TPI configuré, apprentissage actif ou compensation extérieure continue. Cette première version accepte les VTherm `over_switch` utilisant un ou plusieurs switches physiques. Leurs fractions ON sont intégrées à partir des transitions Recorder, puis moyennées selon la convention VTherm de parts égales `device_power / N`. Les phases décalées et transitions inférieures à une minute sont prises en compte. La puissance absolue n'est pas obligatoire. Cette convention ne mesure pas des puissances individuelles différentes.

Pour `over_climate`, `over_valve` et climate avec régulation de valve, la réponse indique explicitement `eligible: false`, `supported: false`, `reason: unsupported_thermostat_type` : l'analyse n'est pas encore disponible pour ce type. Les commandes virtuelles ambiguës sont également refusées ; aucun fallback aveugle sur `hvac_action` n'est utilisé.

Recorder fournit au maximum les **14 derniers jours**. Au moins **7 jours de minutes réellement exploitables** sont nécessaires après exclusions. Les capteurs intérieur et extérieur proviennent de la configuration effective VTherm, configuration centrale incluse. La réponse détaille `sources`, `history_requested_days`, `history_available_days`, `history_usable_days`, les exclusions et les réglages actuels. Aucune durée de conservation Recorder n'est supposée.

La réponse contient `applicability_note` (FR/EN) : les coefficients sont des estimations exploratoires issues de la période analysée, sans validité établie dans d'autres conditions. Relancer l'analyse sur une période représentative si les conditions de chauffage ou l'usage du logement changent sensiblement, ou si la régulation se dégrade, avant d'envisager un ajustement. Une variation de température extérieure seule n'impose pas de nouveau calcul.

La comparaison Kalman est désactivée dans la réponse MCP : les simulations montrent que des coefficients dans les bornes peuvent encore être inexacts. `experimental_estimator` indique `unavailable`, avec la raison `experimental_model_not_validated_for_application`, sans calcul ni coefficients Kalman. L'estimateur reste disponible pour les essais hors ligne avec refus des valeurs hors `[0, 10]` (intérieur) et `[0, 1]` (extérieur), des données insuffisamment excitantes et des estimations instables. Aucun écrêtage ne transforme un échec en résultat utilisable. Ces contrôles ne prouvent pas la fiabilité ; l'OLS reste exploratoire et aucune application n'est automatique. Les intervalles bootstrap restent non calibrés et ne sont pas tronqués aux bornes du service.

La température est reconstruite sur une grille d'une minute, par maintien causal limité à 60 minutes. Contrairement à l'interpolation extérieure du script de référence, aucune mesure future n'est utilisée. Les états binaires HA persistent jusqu'à leur prochain événement ; un état `unknown`/`unavailable` invalide l'intervalle. Les capteurs physiques et binaires de sécurité, délestage et fenêtre sont lus via Recorder : les sections de diagnostic du climate sont souvent exclues de l'enregistrement. Une source de filtrage nécessaire absente entraîne un refus. Les périodes HVAC hors `heat`, protections actives, fenêtres ouvertes et données manquantes sont exclues. Le nombre de cycles exclus pour fenêtre figure dans chaque résolution. L'analyse de cette version exige une configuration VTherm en °C ; les capteurs source en °F sont convertis en °C.

Le modèle conserve `ΔT = g × (T_ext - T_int) + B × u + q`, `coef_ext = g/B`, `A = 1-g` et `coef_int = (A-exp(-dt/tau_cl))/B`. La convergence préférée reste **6 h** ; la table 3/4/5/6/8/10/12 h est retournée. Le cycle réel `cycle_min` est prioritaire, avec essais 10/20/30/60 minutes et repli explicite sur la résolution valide la plus proche. Chaque résolution exige 40 cycles, 80 % de minutes valides et les bornes physiques du script. Un intervalle manquant ne devient jamais un cycle plus long caché.

Validation chronologique 70 % apprentissage / 30 % validation, OLS `numpy.linalg.lstsq`, MAE, RMSE, R² sur ΔT et conditionnement sont conservés. Le bootstrap temporel utilise 1000 répétitions, des blocs de 24 h et la seed `20261030` ; les trous ne compriment pas les blocs. Il retourne des IC95 approximatifs. Moins de 30 réplications physiques acceptées entraîne `bootstrap_failed`. Un modèle non physique ou un conditionnement ≥1000 est refusé ; entre 100 et 1000, prudence. Un faible R² seul n'entraîne pas de rejet. Une étendue relative de `coef_ext` supérieure à 25 %, moins de trois résolutions ou un IC large produisent des avertissements. `recommendation_reliable: false` interdit de présenter le candidat comme fiable. Aucun CSV, graphique, rapport ou autre fichier n'est nécessaire ou généré ; aucune dépendance pandas/matplotlib n'est ajoutée.

L'analyse **n'applique jamais** les coefficients. Présenter le résultat, ses limites et la comparaison, puis attendre la décision utilisateur. Une modification directe explicite ne nécessite ni historique ni analyse :

```json
{"entity_id": "climate.thermostat_salon", "coef_int": 0.35, "coef_ext": 0.025}
```

Au moins un coefficient doit être fourni ; mise à jour partielle possible. Plages du service VTherm : `0 <= coef_int <= 10`, `0 <= coef_ext <= 1`, valeurs finies uniquement. L'outil vérifie de nouveau l'exposition Assist, le TPI classique, l'utilisateur authentifié et la permission `CONTROL`, puis appelle uniquement `versatile_thermostat.set_tpi_parameters` avec son contexte. La configuration centrale et le verrouillage restent soumis au service existant. Le service peut persister ces paramètres ; l'outil ne modifie jamais directement une ConfigEntry.

Un changement est `large_change` si l'écart absolu atteint **0.15 pour coef_int**, **0.01 pour coef_ext**, ou si l'écart relatif atteint **50 %** (depuis zéro, tout changement est important). Ces seuils sont des seuils de confirmation, pas des garanties de sûreté thermique. L'outil renvoie `large_change_confirmation_required`, `confirmation_required: true`, la comparaison et un `confirmation_token`, sans écriture. Après une confirmation utilisateur supplémentaire, rappeler les mêmes valeurs avec `confirm_large_change: true` et ce jeton. Il expire après 10 minutes et ne vaut que pour cet utilisateur, ce thermostat et cette comparaison ; il devient invalide si les réglages changent.

Après l'appel, les valeurs sont relues sur l'objet VTherm chargé, y compris après rechargement : `previous`, `requested`, `applied`. Un échec après appel retourne `state_changed: null` et demande une vérification ; il ne prétend pas qu'aucun changement n'a eu lieu. Les refus avant appel indiquent qu'aucun coefficient n'a été modifié. Ne jamais contourner un refus par un service générique.

Le mode MCP **Read only** conserve les deux outils d'analyse et masque `set_tpi_coefficients`, comme les autres actions.

---

# Références techniques

- Home Assistant — Model Context Protocol Server  
  https://www.home-assistant.io/integrations/mcp_server/

- Home Assistant Core — plateforme LLM `climate`  
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/climate/llm.py

- Home Assistant Core — API `Tool`, `ToolResult`, `ToolAnnotations`  
  https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/llm.py

- Home Assistant Core — services `climate`  
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/climate/

- Home Assistant Core — configuration MCP Server (`read_only`, `require_admin`)  
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/mcp_server/config_flow.py

- Versatile Thermostat — dépôt officiel  
  https://github.com/jmcollin78/versatile_thermostat

- Versatile Thermostat — documentation de référence  
  https://www.versatile-thermostat.org/fr/docs/reference/

- Versatile Thermostat — collecteur de logs  
  https://www.versatile-thermostat.org/fr/docs/feature-logs-collector/

- Versatile Thermostat — analyseur de logs  
  https://www.versatile-thermostat.org/fr/debugger/


---

## Historique Recorder : exports CSV et graphiques

Pour « Fais-moi un graphe pro du thermostat de la cuisine annoté sur 48 h », l'assistant est guidé vers `get_history`, puis la création du graphe côté client après récupération de toutes les pages. Une carte ApexCharts/Lovelace en YAML n'est proposée que sur demande explicite de configuration du tableau de bord. SmartPI peut être représenté par son historique climate même si l'analyse des coefficients TPI lui est refusée. Les annotations doivent venir des événements enregistrés ; l'outil n'expose pas l'historique de puissance SmartPI ni celui des relais physiques. Une valeur actuelle ne permet pas de reconstruire ces séries. Si `get_history` manque au catalogue du connecteur, l'assistant doit signaler cette limite.

L'outil de lecture `versatile_thermostat__get_history` transmet au client MCP l'historique enregistré de l'entité climate VTherm : état, température mesurée, consigne, action HVAC et preset, lorsque ces attributs sont enregistrés. Il fonctionne pour tous les types de VTherm, indépendamment de l'analyse TPI. Il ne donne pas accès à tout le Recorder ni aux historiques des capteurs et relais associés.

Le client (ChatGPT, Claude, Gemini, Codex, etc.) récupère les données et crée le CSV ou le graphique selon ses capacités. Exemples : « Exporte l'historique du salon sur une semaine en CSV » ou « Trace température et consigne du bureau sur deux jours ».

Paramètres : `entity_id`, `start_time`, `end_time` (ISO 8601 avec fuseau horaire), `offset` (0 par défaut) et `limit` (500 par défaut, maximum 500). Une période couvre au maximum 14 jours ; découper les périodes plus longues. Récupérer chaque page avec `next_offset`, en conservant exactement les mêmes bornes, jusqu'à `null`. Les résultats contiennent `rows`, `total_rows`, `next_offset`, `pagination_complete`, des dates UTC et les attributs historiques disponibles. La pagination ne constitue pas un instantané figé du Recorder.

Seuls les VTherm encore exposés à Assist sont accessibles, avec un utilisateur authentifié ayant le droit de lecture. Les points sont des changements enregistrés, pas un échantillonnage régulier ; Recorder peut fournir un état reporté au début de la période. Les champs absents restent `null`, et `unknown`/`unavailable` restent explicites. La rétention, les exclusions et les interruptions peuvent limiter les données ; une pagination terminée ne garantit pas la complétude de l'historique. Le client doit signaler ces limites et ne pas inventer les valeurs manquantes. Aucune configuration n'est modifiée.
