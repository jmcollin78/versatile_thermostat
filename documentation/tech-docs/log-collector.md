# Log Collector — Technical Architecture

## 1. Objectif

Permettre aux utilisateurs de récupérer les logs passés d'un VTherm spécifique via une action (service) Home Assistant, filtrés par niveau de log et période temporelle, sous forme d'un fichier téléchargeable.

---

## 2. Alternatives étudiées

| Approche                                             | Description                                                                                            | Avantages                                                        | Inconvénients                                                                                                            |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **A. Ring buffer in-memory + service + fichier www** | Handler logging custom qui stocke les logs en mémoire ; service HA écrit un fichier dans `config/www/` | Simple, fichier accessible via HTTP (`/local/...`)               | Nécessite que le dossier `www` existe ; URL pas sécurisée                                                                |
| **B. Ring buffer + endpoint HTTP custom** (✓ ACTUEL) | Idem A, mais le fichier est servi via un endpoint HTTP enregistré dans HA                              | URL propre, compatible reverse proxy, contrôle d'accès HA intégré | Un peu plus complexe ; nécessite `HomeAssistantView`                                                                     |
| **C. Plateforme diagnostics HA**                     | Utiliser le mécanisme natif `diagnostics` de HA                                                        | Intégré dans l'UI HA (Settings > Devices > Download diagnostics) | Conçu pour des dumps d'état, pas pour des logs filtrés ; pas de filtrage par période/niveau ; un seul fichier par device |
| **D. Per-thermostat log buffer**                     | Chaque VTherm stocke ses propres logs dans un buffer interne                                           | Filtrage natif par thermostat                                    | Ne capture pas les logs des modules transverses (managers, algorithmes) ; intrusif dans le code existant                 |
| **E. System Log HA**                                 | Utiliser `homeassistant.components.system_log`                                                         | Zéro code                                                        | Limité à ~50 entrées, global, pas de filtrage par intégration                                                            |

### Choix retenu : **Option B** (Ring buffer in-memory + endpoint HTTP custom)

**Justification :**
- Simplicité et maintenabilité (basée sur Option A)
- Pas de dépendance à des composants internes HA non stables
- **Fonctionne avec les reverse proxies et domaines externes** (contrairement à `/local/`)
- Le dossier `config/www/` est le mécanisme standard HA pour stocker les fichiers
- La notification persistante fournit un lien direct via `/api/versatile_thermostat/logs/<filename>`
- Compatible avec tous les types d'installation HA (HAOS, Docker, Core)

---

## 3. Architecture globale

```
┌─────────────────────────────────────────────────────────────┐
│                     Python logging system                    │
│                                                              │
│   VThermLogger (sous-classe Logger, isEnabledFor=True)       │
│      │                                                       │
│      ├── callHandlers → VThermLogHandler (ring buffer)       │
│      │         ↕ toujours (tous niveaux)                     │
│      │                                                       │
│      └── callHandlers → handlers HA normaux                  │
│                ↕ uniquement si level ≥ niveau configuré      │
│                                                              │
│      VThermLogBuffer (collections.deque, thread-safe)        │
│      ┌──────────────────────────────────────┐                │
│      │ LogEntry(timestamp, level, name,     │                │
│      │         message, thermostat_hint)    │                │
│      │ ...                                  │                │
│      │ (max N heures OU max N entrées)      │                │
│      └──────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────┘
                         │
                         │  Filtrage (thermostat, niveau, période)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Service: versatile_thermostat.download_logs     │
│                                                              │
│   Paramètres:                                                │
│     - entity_id    : climate.xxx (optionnel, tous si absent) │
│     - log_level    : DEBUG|INFO|WARNING|ERROR (défaut: DEBUG)│
│     - period_start : début extraction (défaut: -60 min)      │
│     - period_end   : fin extraction (défaut: maintenant)     │
│                                                              │
│   1. Filtre les logs du buffer                               │
│   2. Écrit le fichier dans config/www/versatile_thermostat/  │
│   3. Envoie une notification persistante avec le lien API    │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│   config/www/versatile_thermostat/                          │
│     vtherm_logs_<entity>_<timestamp>.log                    │
│                                                             │
│   Accessible via: /api/versatile_thermostat/logs/           │
│                   vtherm_logs_<entity>_<timestamp>.log       │
│                                                             │
│   ✓ Fonctionne avec reverse proxies                         │
│   ✓ Fonctionne sur domaines externes                        │
│   ✓ Endpoint HTTP sécurisé                                  │
│   + Notification persistante avec lien de téléchargement    │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Composants détaillés

### 4.1 `VThermLogger` + `VThermLogHandler`

**Fichier :** `custom_components/versatile_thermostat/log_collector.py`

#### Problème de niveau de log

Le pipeline Python logging standard est :
```
logger.debug(msg)
  → isEnabledFor(DEBUG) ?  ← retourne False si logger configuré à WARNING → record jamais créé
  → sinon : crée LogRecord → callHandlers() → handler.emit()
```

Si l'utilisateur configure `custom_components.versatile_thermostat: warning` dans `logger.yaml`, les messages DEBUG ne sont jamais créés et ne peuvent donc pas être capturés.

#### Solution : `VThermLogger` (sous-classe de `logging.Logger`)

```python
class VThermLogger(logging.Logger):
    _collector: ClassVar[VThermLogHandler | None] = None

    def isEnabledFor(self, level: int) -> bool:
        """Always return True so that LogRecords are always created."""
        return True

    def callHandlers(self, record: logging.LogRecord) -> None:
        """Send to collector unconditionally; to other handlers only if level allows."""
        if VThermLogger._collector is not None:
            VThermLogger._collector.emit(record)          # always → ring buffer
        if record.levelno >= self.getEffectiveLevel():
            super().callHandlers(record)                  # only if level OK → HA logs

def get_vtherm_logger(name: str) -> VThermLogger:
    """Factory : remplace le Logger standard dans le Manager par un VThermLogger."""
    ...
```

Tous les modules du composant utilisent `_LOGGER = get_vtherm_logger(__name__)` au lieu de `logging.getLogger(__name__)`.

#### `VThermLogHandler` et `VThermLogEntry`

```python
class VThermLogEntry:
    timestamp: datetime       # UTC timestamp
    level: int                # logging level (DEBUG=10, INFO=20, ...)
    logger_name: str          # e.g. "custom_components.versatile_thermostat.base_thermostat"
    message: str              # formatted message
    thermostat_hint: str | None  # extracted thermostat name if found

class VThermLogHandler(logging.Handler):
    def __init__(self, max_age_hours: int = 4, max_entries: int = 100_000):
        # Registers itself as VThermLogger._collector on init
        VThermLogger._collector = self
        ...

    def emit(self, record: logging.LogRecord):
        """Store the record in the buffer (thread-safe). Called directly by VThermLogger."""

    def get_entries(self, thermostat_name=None, min_level=DEBUG, start=None, end=None):
        """Return filtered entries from the ring buffer."""

    def purge(self):
        """Remove entries older than max_age_hours."""
```

**Points clés :**
- `VThermLogHandler` ne dépend plus du niveau configuré sur le logger : c'est `VThermLogger.callHandlers()` qui l'appelle directement, avant le filtrage de niveau HA.
- Le buffer `max_age_hours` est configurable via `configuration.yaml` (voir section 5).
- **Thread-safety** : `threading.Lock` sur le `deque`.
- **Purge automatique** : toutes les 1 000 insertions.

### 4.2 Extraction du nom de thermostat depuis les logs

La quasi-totalité des logs VTherm suivent le pattern :
```
"%s - Some message", self._name
```

**Stratégie d'extraction :**
```python
import re
THERMOSTAT_PATTERN = re.compile(r"^(.+?) - ")

def extract_thermostat_hint(message: str) -> str | None:
    match = THERMOSTAT_PATTERN.match(message)
    return match.group(1) if match else None
```

- Ce pattern couvre la majorité des logs dans `base_thermostat.py`, tous les `feature_*_manager.py`, `thermostat_*.py`, etc.
- Les logs sans ce pattern (modules utilitaires comme `ema.py`, `pi_algorithm.py`) seront inclus sans filtre thermostat (car ils sont transverses).
- En mode "tous les thermostats" (pas de filtre entity_id), tous les logs sont retournés.

### 4.3 Service `download_logs`

**Enregistrement :** dans `climate.py`, via `platform.async_register_entity_service()` pour la variante ciblée, **ET** dans `__init__.py` via `hass.services.async_register()` pour la variante globale (tous les VTherm).

**Définition services.yaml :**
```yaml
download_logs:
    name: Download logs
    description: Collect and download filtered logs for a VTherm entity.
    target:
        entity:
            integration: versatile_thermostat
    fields:
        log_level:
            name: Log level
            description: Minimum log level to include
            required: false
            default: "DEBUG"
            selector:
                select:
                    options:
                        - "DEBUG"
                        - "INFO"
                        - "WARNING"
                        - "ERROR"
        period_start:
            name: Period start
            description: Start of the extraction period
            required: false
            selector:
                datetime:
        period_end:
            name: Period end
            description: End of the extraction period
            required: false
            selector:
                datetime:
```

### 4.4 Flux d'exécution du service

```
Appel service download_logs(entity_id=climate.salon, log_level=INFO,
                           period_start=2025-03-14 08:00, period_end=2025-03-14 10:00)
      │
      ▼
1. Résoudre le nom du thermostat depuis entity_id
      │
      ▼
2. VThermLogHandler.get_entries(
       thermostat_name="Salon",
       min_level=logging.INFO,
       start=datetime(2025,3,14,8,0),
       end=datetime(2025,3,14,10,0)
   )
      │
      ▼
3. Formater les entrées en texte :
   "2025-03-14 10:23:45.123 [INFO] base_thermostat - Salon - Temperature changed to 21.5°C"
      │
      ▼
4. Créer le dossier config/www/versatile_thermostat/ si nécessaire
      │
      ▼
5. Écrire le fichier :
   config/www/versatile_thermostat/vtherm_logs_salon_20250314_102500.log
      │
      ▼
6. Nettoyer les anciens fichiers de logs (> 24h) dans ce dossier
      │
      ▼
7. Envoyer persistent_notification :
   "VTherm Log Export - Copy/paste the link below into your browser to download the log file:
    http://<ha_url>/api/versatile_thermostat/logs/vtherm_logs_salon_20250314_102500.log?authSig=..."
```

### 4.5 Endpoint HTTP de téléchargement

**Fichier :** `custom_components/versatile_thermostat/log_collector.py` → `async_register_log_download_endpoint()`

**Enregistrement :** dans `async_setup()` de `__init__.py`, une fois le `VThermLogHandler` créé.

**URL :**
```
GET /api/versatile_thermostat/logs/{filename}
```

**Exemple :**
```
GET /api/versatile_thermostat/logs/vtherm_logs_salon_20250314_102500.log
```

**Avantages de cet endpoint par rapport à `/local/...` :**
- ✅ **Fonctionne avec reverse proxies** : l'endpoint est serveur par Home Assistant via son système de routing HTTP intégré
- ✅ **Fonctionne sur domaines externes** : pas de dépendance à un chemin de fichier statique
- ✅ **Sécurité** : validation du nom de fichier (regex) et du chemin (resolve + relative_to pour éviter path traversal)
- ✅ **Intégration native HA** : hérite du mécanisme d'authentification et de l'architecture HTTP de HA

**Authentification :**
- `requires_auth = True` : l'endpoint est **protégé par l'authentification HA**
- L'accès est autorisé via un **token signé** (`authSig`) ajouté à l'URL au moment de l'export
- Le token est généré par `async_sign_path()` de `homeassistant.components.http.auth` avec une durée de validité de 24 h (= `OLD_FILE_MAX_AGE_HOURS`)
- La notification persistante contient l'URL complète (absolue + token signé) que l'utilisateur doit copier/coller dans un navigateur
- **Note** : le lien ne peut pas être cliqué directement dans la notification HA car le frontend SPA intercepte les clics et tente de router en interne

**Construction de l'URL de téléchargement :**
1. Le chemin brut est : `/api/versatile_thermostat/logs/{filename}`
2. `async_sign_path(hass, path, timedelta(hours=24))` ajoute un paramètre `?authSig=<jwt>` au chemin
3. Le préfixe de base est résolu dans cet ordre :
   - `hass.config.external_url` (URL externe configurée par l'utilisateur)
   - `hass.config.internal_url` (URL interne configurée par l'utilisateur)
   - `get_url(hass)` en fallback (auto-détection, peut retourner l'IP Docker)
4. L'URL finale est : `{base_url}{signed_path}`

> **Important** : pour que l'URL soit correcte, l'utilisateur doit configurer son URL interne ou externe dans **Paramètres > Système > Réseau** dans Home Assistant.

**Sécurité :**
- Validation du filename : `^vtherm_logs_[a-z0-9_]+_\d{8}_\d{6}\.log$`
- Vérification du chemin : le fichier doit être dans `config/www/versatile_thermostat/`
- Pas de path traversal possible (ex: `../../../etc/passwd`)
- Le fichier doit exister physiquement (pas de création à la volée)

**Corps de la réponse :**
- Content-Type : `text/plain; charset=utf-8`
- Header : `Content-Disposition: attachment; filename="..."`
- Body : contenu du fichier de log

### 4.6 Format du fichier de sortie

```
================================================================================
Versatile Thermostat - Log Export
Thermostat : Salon (climate.salon)
Period     : 2025-03-14 08:00:00 → 2025-03-14 10:00:00 UTC
Level      : INFO and above
Entries    : 342
Generated  : 2025-03-14 10:25:03 UTC
================================================================================

2025-03-14 08:25:12.456 [INFO   ] base_thermostat    | Salon - Current temperature is 20.5°C
2025-03-14 08:25:12.458 [INFO   ] base_thermostat    | Salon - Target temperature is 21.0°C
2025-03-14 08:30:00.001 [INFO   ] prop_algo_tpi      | Salon - TPI calculated on_percent=0.45
2025-03-14 08:30:00.123 [WARNING] safety_manager     | Salon - No temperature update for 35 min
...
```

---

## 5. Cycle de vie et initialisation

```
async_setup() dans __init__.py
      │
      ▼
Lire vtherm_config = config.get(DOMAIN)  (configuration.yaml)
      │
      ▼
Lire max_age_hours = vtherm_config.get("log_buffer_max_age_hours", 4)
      │
      ▼
Créer VThermLogHandler(max_age_hours=max_age_hours)  →  VThermLogger._collector = handler
      │
      ▼
Attacher le handler au logger "custom_components.versatile_thermostat"
  → logger.addHandler(log_handler)
  → logger.setLevel(DEBUG)   ← garantit que les LogRecords sont créés pour les modules
                                qui utilisent encore logging.getLogger() directement
      │
      ▼
Stocker la référence : hass.data[DOMAIN]["log_handler"] = log_handler
      │
      ▼
Enregistrer le service "download_logs"
```

**Configuration `configuration.yaml` :**

```yaml
versatile_thermostat:
  log_buffer_max_age_hours: 6   # optionnel, défaut 4
```

L'option accepte un entier positif (heures). Si absente, la valeur par défaut (`DEFAULT_MAX_AGE_HOURS = 4`) est utilisée.

---

## 6. Configuration — `log_buffer_max_age_hours`

### Déclaration dans `configuration.yaml`

```yaml
versatile_thermostat:
  log_buffer_max_age_hours: 6   # optionnel — entier positif, défaut : 4
```

| Attribut  | Valeur                                   |
| --------- | ---------------------------------------- |
| Clé YAML  | `log_buffer_max_age_hours`               |
| Constante | `CONF_LOG_BUFFER_MAX_AGE_HOURS`          |
| Type      | entier positif (`cv.positive_int`)       |
| Défaut    | `4` (exposé via `DEFAULT_MAX_AGE_HOURS`) |
| Unité     | heures                                   |

### Effect sur le buffer

Cette valeur contrôle la durée de rétention des entrées dans le ring buffer. Les entrées plus vieilles que `max_age_hours` sont supprimées lors de la purge automatique (toutes les 1 000 insertions).

> **Note :** La durée de rétention du buffer doit être supérieure ou égale à la fenêtre temporelle `period_start`/`period_end` utilisée lors d'un export. Si le buffer ne couvre pas la période demandée, les entrées manquantes ne pourront pas être retrouvées.

### Impact mémoire selon la valeur choisie

| Valeur | Scénario 10 VTherm (~50 logs/min) | Scénario 20 VTherm (~200 logs/min) |
| ------ | --------------------------------- | ---------------------------------- |
| 1 h    | ~3 000 entrées — ~1 Mo            | ~12 000 entrées — ~5 Mo            |
| 4 h    | ~12 000 entrées — ~5 Mo           | ~48 000 entrées — ~20 Mo           |
| 8 h    | ~24 000 entrées — ~10 Mo          | ~96 000 entrées — ~40 Mo           |
| 24 h   | ~72 000 entrées — ~30 Mo          | plafonné par `max_entries=100 000` |

Le garde-fou `max_entries=100_000` (~40–50 Mo) s'applique toujours, quelle que soit la durée configurée.

---

## 7. Gestion de la mémoire

### Estimation de consommation

| Scénario                    | Logs/minute (estimé) | Entrées en 4h | Mémoire estimée |
| --------------------------- | -------------------- | ------------- | --------------- |
| 1 VTherm, activité normale  | ~5 DEBUG/min         | ~1 200        | ~0.5 Mo         |
| 10 VTherm, activité normale | ~50 DEBUG/min        | ~12 000       | ~5 Mo           |
| 20 VTherm, haute activité   | ~200 DEBUG/min       | ~48 000       | ~20 Mo          |
| Garde-fou max_entries       | —                    | 100 000       | ~40-50 Mo       |

### Stratégie de purge

1. **Par âge** : Toutes les 1000 insertions, supprimer les entrées > `max_age_hours`.
2. **Par taille** : Le `deque(maxlen=max_entries)` évicte automatiquement les plus anciennes.
3. **Fichiers de sortie** : Nettoyage des fichiers `.log` > 24h dans `config/www/versatile_thermostat/` à chaque appel du service.

---

## 8. Fichiers impactés

| Fichier                | Modification                                                                                                                |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `log_collector.py`     | `VThermLogger`, `get_vtherm_logger`, `VThermLogHandler`, `VThermLogEntry`, filtrage, export, `async_register_log_download_endpoint()` |
| `__init__.py`          | Initialiser le handler dans `async_setup()`, lire `log_buffer_max_age_hours`, service `download_logs`, enregistrer endpoint HTTP    |
| `climate.py`           | Enregistrer le service entity-level `download_logs` via la plateforme                                                        |
| `const.py`             | `CONF_LOG_BUFFER_MAX_AGE_HOURS`, `SERVICE_DOWNLOAD_LOGS`                                                                     |
| `*.py` (44 fichiers)   | `_LOGGER = get_vtherm_logger(__name__)` au lieu de `logging.getLogger(__name__)`                                             |
| `services.yaml`        | Ajouter la définition du service `download_logs`                                                                             |
| `strings.json`         | Ajouter les traductions EN pour le service                                                                                  |
| `translations/fr.json` | Ajouter les traductions FR                                                                                                  |
| `translations/en.json` | Ajouter les traductions EN                                                                                                  |

---

## 9. Tests

| Test                              | Description                                                    |
| --------------------------------- | -------------------------------------------------------------- |
| `test_log_collector_buffer`       | Insertion, purge par âge, purge par taille, thread-safety      |
| `test_log_collector_filter`       | Filtrage par thermostat, par niveau, par période (start/end)   |
| `test_log_collector_extract_hint` | Extraction du nom de thermostat depuis les messages            |
| `test_log_collector_service`      | Appel du service, vérification du fichier généré, notification |
| `test_log_collector_no_match`     | Aucun log trouvé → notification appropriée                     |
| `test_log_collector_file_cleanup` | Nettoyage des anciens fichiers dans www/                       |

**Framework :** `pytest` + `pytest-homeassistant-custom-component` (existant dans le projet).
---

## 10. Limites et évolutions possibles

- **Limite** : Les logs DEBUG ne sont capturés que si le handler est actif. Si l'intégration est rechargée, le buffer est vidé.
- **Limite** : L'extraction du thermostat est pattern-based — les logs qui ne suivent pas `"%s - ..."` ne pourront pas être filtrés par thermostat.
- **Évolution possible** : Option B (endpoint HTTP custom) pour un contrôle d'accès plus fin.
- **Évolution possible** : Export en JSON structuré en plus du texte brut.
