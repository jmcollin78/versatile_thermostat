# Log Collector — Technical Architecture

## 1. Objectif

Permettre aux utilisateurs de récupérer les logs passés d'un VTherm spécifique via une action (service) Home Assistant, filtrés par niveau de log et période temporelle, sous forme d'un fichier téléchargeable.

---

## 2. Alternatives étudiées

| Approche                                             | Description                                                                                            | Avantages                                                        | Inconvénients                                                                                                            |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **A. Ring buffer in-memory + service + fichier www** | Handler logging custom qui stocke les logs en mémoire ; service HA écrit un fichier dans `config/www/` | Simple, fichier accessible via HTTP (`/local/...`)               | Nécessite que le dossier `www` existe ; URL pas sécurisée                                                                |
| **B. Ring buffer + endpoint HTTP custom**            | Idem A, mais le fichier est servi via un endpoint HTTP enregistré dans HA                              | URL propre, contrôle d'accès HA intégré                          | Plus complexe ; nécessite `HomeAssistantView`                                                                            |
| **C. Plateforme diagnostics HA**                     | Utiliser le mécanisme natif `diagnostics` de HA                                                        | Intégré dans l'UI HA (Settings > Devices > Download diagnostics) | Conçu pour des dumps d'état, pas pour des logs filtrés ; pas de filtrage par période/niveau ; un seul fichier par device |
| **D. Per-thermostat log buffer**                     | Chaque VTherm stocke ses propres logs dans un buffer interne                                           | Filtrage natif par thermostat                                    | Ne capture pas les logs des modules transverses (managers, algorithmes) ; intrusif dans le code existant                 |
| **E. System Log HA**                                 | Utiliser `homeassistant.components.system_log`                                                         | Zéro code                                                        | Limité à ~50 entrées, global, pas de filtrage par intégration                                                            |

### Choix retenu : **Option A** (Ring buffer in-memory + service + fichier www)

**Justification :**
- Simplicité d'implémentation et de maintenance
- Pas de dépendance à des composants internes HA non stables
- Le dossier `config/www/` est le mécanisme standard HA pour servir des fichiers statiques
- La notification persistante fournit un lien direct à l'utilisateur
- Compatible avec tous les types d'installation HA (HAOS, Docker, Core)

> **Note :** Si la sécurité de l'URL est un enjeu (environnement multi-utilisateurs), l'option B pourra être envisagée ultérieurement. Pour un usage typique (réseau local, utilisateur unique), l'option A est suffisante.

---

## 3. Architecture globale

```
┌─────────────────────────────────────────────────────────────┐
│                     Python logging system                    │
│                                                              │
│   Logger: "custom_components.versatile_thermostat"           │
│      │                                                       │
│      ├── (existing handlers: console, HA)                    │
│      │                                                       │
│      └── VThermLogHandler  ◄── handler custom ajouté         │
│              │                                               │
│              ▼                                               │
│      VThermLogBuffer (collections.deque, thread-safe)        │
│      ┌──────────────────────────────────────┐               │
│      │ LogEntry(timestamp, level, name,     │               │
│      │         message, thermostat_name)    │               │
│      │ ...                                  │               │
│      │ (max 4h OU max N entrées)            │               │
│      └──────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
                         │
                         │  Filtrage (thermostat, niveau, période)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Service: versatile_thermostat.download_logs      │
│                                                              │
│   Paramètres:                                                │
│     - entity_id    : climate.xxx (optionnel, tous si absent) │
│     - log_level    : DEBUG|INFO|WARNING|ERROR (défaut: DEBUG)│
│     - period_start : début extraction (défaut: -60 min)      │
│     - period_end   : fin extraction (défaut: maintenant)     │
│                                                              │
│   1. Filtre les logs du buffer                               │
│   2. Écrit le fichier dans config/www/versatile_thermostat/  │
│   3. Envoie une notification persistante avec le lien        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│   config/www/versatile_thermostat/                           │
│     vtherm_logs_<entity>_<timestamp>.log                     │
│                                                              │
│   Accessible via: /local/versatile_thermostat/xxx.log        │
│                                                              │
│   + Notification persistante avec lien de téléchargement     │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Composants détaillés

### 4.1 `VThermLogHandler` (logging.Handler)

**Fichier :** `custom_components/versatile_thermostat/log_collector.py`

```python
class VThermLogEntry:
    """A single log entry stored in the ring buffer."""
    timestamp: datetime       # UTC timestamp
    level: int                # logging level (DEBUG=10, INFO=20, ...)
    logger_name: str          # e.g. "custom_components.versatile_thermostat.base_thermostat"
    message: str              # formatted message
    thermostat_hint: str | None  # extracted thermostat name if found

class VThermLogHandler(logging.Handler):
    """Custom handler that stores log records in an in-memory ring buffer."""

    def __init__(self, max_age_hours=4, max_entries=100_000):
        ...

    def emit(self, record: logging.LogRecord):
        """Store the record in the buffer (thread-safe)."""
        ...

    def get_entries(self, thermostat_name=None, min_level=DEBUG,
                    start=None, end=None):
        """Return filtered entries from the buffer.
        start: datetime UTC, defaults to now - 60 min
        end:   datetime UTC, defaults to now
        """
        ...

    def purge_old_entries(self):
        """Remove entries older than max_age_hours."""
        ...
```

**Points clés :**
- Le handler est attaché au logger `custom_components.versatile_thermostat` (le logger racine de l'intégration).
- **Niveau du handler** : `DEBUG` en permanence — il capture tout, indépendamment du niveau configuré dans HA.
- **Thread-safety** : Utilisation de `threading.Lock` pour protéger le `deque`.
- **Purge automatique** : À chaque `emit()`, les entrées trop anciennes sont purgées (pas à chaque appel pour limiter le coût, mais toutes les N insertions ou via un timer).
- **Taille mémoire** : `max_entries=100_000` comme garde-fou (~50 Mo estimé max). Configurable.

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
   "VTherm logs ready: [Download](/local/versatile_thermostat/vtherm_logs_salon_20250314_102500.log)"
```

### 4.5 Format du fichier de sortie

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
Créer VThermLogHandler (singleton via hass.data[DOMAIN])
      │
      ▼
Attacher le handler au logger "custom_components.versatile_thermostat"
  → logger.addHandler(log_handler)
  → logger.setLevel(min(logger.level, DEBUG))  # S'assurer que DEBUG passe
      │
      ▼
Stocker la référence : hass.data[DOMAIN]["log_handler"] = log_handler
      │
      ▼
Enregistrer le service "download_logs"
```

**Attention au niveau du logger :**
Le logger `custom_components.versatile_thermostat` a un niveau effectif qui dépend de la configuration HA (`logger:` dans `configuration.yaml`). Si le niveau est `WARNING`, les messages `DEBUG` et `INFO` ne seront jamais émis et donc jamais capturés.

**Solution :** Forcer le niveau du logger VTherm à `DEBUG` quand le handler est actif. Cela n'impacte PAS les autres handlers (console, fichier HA) car ceux-ci ont leur propre niveau de filtrage. Le handler HA standard filtre indépendamment.

```python
vtherm_logger = logging.getLogger("custom_components.versatile_thermostat")
vtherm_logger.setLevel(logging.DEBUG)  # Allow all levels to reach our handler
log_handler = VThermLogHandler(max_age_hours=4, max_entries=100_000)
log_handler.setLevel(logging.DEBUG)
vtherm_logger.addHandler(log_handler)
```

> **Impact :** Le logging HA standard possède ses propres handlers avec leurs propres niveaux. Abaisser le level du logger parent n'affecte pas le filtrage des handlers existants — chaque handler filtre indépendamment. Cependant, cela signifie que les messages DEBUG seront maintenant créés par Python (même si les handlers HA les ignorent), ce qui a un coût CPU léger.

---

## 6. Gestion de la mémoire

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

## 7. Fichiers impactés

| Fichier                | Modification                                                                        |
| ---------------------- | ----------------------------------------------------------------------------------- |
| `log_collector.py`     | **Créer** — `VThermLogHandler`, `VThermLogEntry`, logique de filtrage et d'export   |
| `__init__.py`          | Initialiser le handler dans `async_setup()`, enregistrer le service `download_logs` |
| `climate.py`           | Enregistrer le service entity-level `download_logs` via la plateforme               |
| `services.yaml`        | Ajouter la définition du service `download_logs`                                    |
| `const.py`             | Ajouter `SERVICE_DOWNLOAD_LOGS = "download_logs"`                                   |
| `strings.json`         | Ajouter les traductions EN pour le service                                          |
| `translations/fr.json` | Ajouter les traductions FR                                                          |
| `translations/en.json` | Ajouter les traductions EN                                                          |

---

## 8. Tests

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

## 9. Limites et évolutions possibles

- **Limite** : Les logs DEBUG ne sont capturés que si le handler est actif. Si l'intégration est rechargée, le buffer est vidé.
- **Limite** : L'extraction du thermostat est pattern-based — les logs qui ne suivent pas `"%s - ..."` ne pourront pas être filtrés par thermostat.
- **Évolution possible** : Ajouter une option de configuration pour activer/désactiver la capture (économie de mémoire pour les installations légères).
- **Évolution possible** : Option B (endpoint HTTP custom) pour un contrôle d'accès plus fin.
- **Évolution possible** : Export en JSON structuré en plus du texte brut.
