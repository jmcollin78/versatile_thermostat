# Télécharger les logs passés - Diagnostic et dépannage

- [Télécharger les logs passés - Diagnostic et dépannage](#télécharger-les-logs-passés---diagnostic-et-dépannage)
  - [Pourquoi récupérer les logs ?](#pourquoi-récupérer-les-logs-)
  - [Comment accéder à cette fonction](#comment-accéder-à-cette-fonction)
  - [Appeler l'action depuis Home Assistant](#appeler-laction-depuis-home-assistant)
    - [Option 1 : Depuis l'interface utilisateur (UI)](#option-1--depuis-linterface-utilisateur-ui)
    - [Option 2 : Depuis un script ou une automatisation](#option-2--depuis-un-script-ou-une-automatisation)
  - [Paramètres disponibles](#paramètres-disponibles)
    - [Explication des niveaux de log](#explication-des-niveaux-de-log)
  - [Recevoir et télécharger le fichier](#recevoir-et-télécharger-le-fichier)
  - [Format et contenu du fichier de logs](#format-et-contenu-du-fichier-de-logs)
  - [Exemples pratiques](#exemples-pratiques)
    - [Exemple 1 : Déboguer une température anormale sur 30 minutes](#exemple-1--déboguer-une-température-anormale-sur-30-minutes)
    - [Exemple 2 : Valider qu'une présence est correctement détectée](#exemple-2--valider-quune-présence-est-correctement-détectée)
    - [Exemple 3 : Verifier tous les thermostats sur une courte période](#exemple-3--verifier-tous-les-thermostats-sur-une-courte-période)
  - [Configuration avancée](#configuration-avancée)
  - [Conseils d'utilisation](#conseils-dutilisation)

## Pourquoi récupérer les logs ?

Les logs (_journal des événements_) du Versatile Thermostat enregistrent tous les changements et les actions effectuées par le thermostat. Ils sont utiles pour :

- **Diagnostiquer un dysfonctionnement** : Comprendre pourquoi le thermostat ne se comporte pas comme prévu
- **Analyser un comportement anormal** : Vérifier les décisions du thermostat sur une période donnée
- **Déboguer une configuration** : Valider que les capteurs et les actions sont bien détectés
- **Signaler un problème** : Fournir un historique aux développeurs pour aider au débogage

La fonction de **téléchargement de logs** offre un moyen simple de récupérer les logs d'une période spécifique, filtrés selon votre besoin.

**Conseil utile** : Lors d'une demande de support, vous devrez fournir les logs du moment où votre problème s'est produit. L'utilisation de cette fonction est recommandée puisque les logs sont collectés indépendamment du niveau de log configuré dans Home Assistant (contrairement au système de logs natif de HA).

## Comment accéder à cette fonction

L'action `versatile_thermostat.download_logs` est disponible dans Home Assistant via :

1. **Les automatisations** (Scripts > Automations)
2. **Les scripts** (Scripts > Scripts)
3. **Les contrôles Développeur** (Settings > Developer Tools > Services)
4. **L'interface de contrôle de certaines intégrations** (selon votre version de Home Assistant)

## Appeler l'action depuis Home Assistant

### Option 1 : Depuis l'interface utilisateur (UI)

Pour appeler l'action depuis les Outils de développement :

1. Allez dans **Settings** (Paramètres) → **Developer Tools** (Outils de développement)
2. Onglet **Actions** (anciennement nommé **Services**) → sélectionnez `versatile_thermostat: Download logs`
3. Remplissez les paramètres désirés (voir section ci-dessous)
4. Cliquez sur **Call Service**

Une **notification persistante** s'affichera alors avec un lien de téléchargement du fichier.

### Option 2 : Depuis un script ou une automatisation

Exemple d'appel dans une automatisation ou un script YAML :

```yaml
action: versatile_thermostat.download_logs
metadata: {}
data:
  entity_id: climate.salon        # Optionnel : remplacer par votre thermostat
  log_level: INFO                 # Optionnel : DEBUG (défaut), INFO, WARNING, ERROR
  period_start: "2025-03-14T08:00:00"   # Optionnel : format ISO (datetime)
  period_end: "2025-03-14T10:00:00"     # Optionnel : format ISO (datetime)
```

## Paramètres disponibles

| Paramètre      | Requis ? | Valeurs possibles                   | Défaut                      | Description                                                                    |
| -------------- | -------- | ----------------------------------- | --------------------------- | ------------------------------------------------------------------------------ |
| `entity_id`    | Non      | `climate.xxx` ou absent             | Tous les VTherm             | Thermostat spécifique ciblé. Si absent, inclut tous les thermostats.           |
| `log_level`    | Non      | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `DEBUG`                     | Niveau minimum de gravité. Tous les logs à ce niveau et au-dessus sont inclus. |
| `period_start` | Non      | ISO datetime (ex: `2025-03-14...`)  | 60 minutes avant maintenant | Début de la période d'extraction. Format ISO avec date et heure.               |
| `period_end`   | Non      | ISO datetime (ex: `2025-03-14...`)  | Maintenant (heure actuelle) | Fin de la période d'extraction. Format ISO avec date et heure.                 |

### Explication des niveaux de log

- **DEBUG** : Messages de diagnostic détaillés (vitesse du calcul TPI, valeurs intermédiaires, etc.). Très verbeux.
- **INFO** : Informations générales (changements d'état, décisions du thermostat, activations de fonctionnalités).
- **WARNING** : Avertissements (préconditions non remplies, valeurs anormales détectées).
- **ERROR** : Erreurs (défaillances capteur, exception non rattrapée).

**Conseil** : Commencez par `INFO` pour une première analyse, puis passez à `DEBUG` si vous avez besoin de plus de détails.

## Recevoir et télécharger le fichier

Après l'appel de l'action, une **notification persistante** s'affiche contenant :

- Un résumé de l'export (thermostat, période, niveau, nombre d'entrées)
- Une **URL de téléchargement** à copier/coller dans votre navigateur

L'URL est un **lien signé absolu** (avec un jeton d'authentification valable 24 heures). En raison d'une limitation du frontend Home Assistant, **le lien ne peut pas être cliqué directement** depuis la notification — vous devez le **copier et le coller** dans un nouvel onglet de navigateur pour déclencher le téléchargement.

Le fichier téléchargé est un fichier `.log` nommé par exemple :
```
vtherm_logs_salon_20250314_102500.log
```

Le fichier est stocké temporairement sur votre serveur Home Assistant dans le dossier accessible sur le réseau local (sous `config/www/versatile_thermostat/`).

> **Note** : Les anciens fichiers de logs (> 24 h) sont automatiquement supprimés du serveur.

> **Important** : Pour que l'URL de téléchargement soit correcte, vous devez configurer votre URL interne ou externe dans **Paramètres > Système > Réseau** dans Home Assistant. Sinon, l'URL peut contenir l'adresse IP interne du conteneur Docker.

## Format et contenu du fichier de logs

Le fichier contient :

1. **Un en-tête** avec les informations de l'export :
   ```
   ================================================================================
   Versatile Thermostat - Log Export
   Thermostat : Salon (climate.salon)
   Period     : 2025-03-14 08:00:00 → 2025-03-14 10:00:00 UTC
   Level      : INFO and above
   Entries    : 342
   Generated  : 2025-03-14 10:25:03 UTC
   ================================================================================
   ```

2. **Les entrées de logs**, une par ligne, avec :
   - Horodatage (date + heure UTC)
   - Niveau (`[INFO]`, `[DEBUG]`, `[WARNING]`, `[ERROR]`)
   - Nom du module Python (où le log a été générée)
   - Message

Exemple d'entrée :
```
2025-03-14 08:25:12.456 INFO    [base_thermostat    ] Salon - Current temperature is 20.5°C
2025-03-14 08:30:00.001 INFO    [prop_algo_tpi      ] Salon - TPI calculated on_percent=0.45
2025-03-14 08:30:00.123 WARNING [safety_manager     ] Salon - No temperature update for 35 min
```

Vous pouvez alors **analyser ce fichier** avec :
- Un éditeur de texte classique
- Un script Python pour traiter les données
- Un outil comme `grep`, `awk`, `sed`, etc. pour filtrer manuellement

## Exemples pratiques

### Exemple 1 : Déboguer une température anormale sur 30 minutes

**Objectif** : Comprendre pourquoi le thermostat Salon gère mal sa température.

**Action à appeler** :
```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.salon
  log_level: DEBUG              # On veut tous les détails
  period_start: "2025-03-14T14:00:00"
  period_end: "2025-03-14T14:30:00"
```

**Analyse du fichier** :
- Cherchez « Current temperature », « Target temperature » pour voir l'évolution
- Cherchez « TPI calculated » pour voir le calcul du pourcentage d'activation
- Cherchez « WARNING » ou « ERROR » pour identifier des anomalies

---

### Exemple 2 : Valider qu'une présence est correctement détectée

**Objectif** : Vérifier que le capteur de présence a bien changé l'état du thermostat.

**Action à appeler** :
```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.bureau
  log_level: INFO
  period_start: "2025-03-15T12:00:00"      # Début de la période (format ISO)
  period_end: "2025-03-15T14:00:00"        # Fin de la période
```

**Analyse du fichier** :
- Cherchez les messages contenant « presence » ou « motion »
- Vérifiez que les changements de preset sont correctement enregistrés

---

### Exemple 3 : Verifier tous les thermostats sur une courte période

**Objectif** : Récupérer un historique global de tous les thermostats pendant une heure, filtré aux avertissements et erreurs.

**Action à appeler** :
```yaml
action: versatile_thermostat.download_logs
data:
  log_level: WARNING            # Pas d'entity_id → tous les VTherm
  period_start: "2025-03-15T13:00:00"
  period_end: "2025-03-15T14:00:00"
```

**Analyse du fichier** :
- Le fichier inclura tous les logs WARNING et ERROR de tous les thermostats
- Utile pour vérifier qu'aucune alerte anormale n'est survenue

---

## Configuration avancée

Par défaut, les logs sont conservés en mémoire sur **4 heures** sur votre serveur Home Assistant. Vous pouvez ajuster cette durée dans `configuration.yaml` :

```yaml
versatile_thermostat:
  log_buffer_max_age_hours: 6   # Garder les logs pendant 6 heures au lieu de 4
```

Vous pouvez spécifier **n'importe quel entier positif** (en heures) selon vos besoins. Voici quelques exemples avec une estimation de la consommation mémoire :

| Durée    | Scénario 10 VTherm  | Scénario 20 VTherm  |
| -------- | ------------------- | ------------------- |
| **1 h**  | ~0.5-1 Mo           | ~2-5 Mo             |
| **2 h**  | ~1-2 Mo             | ~4-10 Mo            |
| **4 h**  | ~2-5 Mo             | ~8-20 Mo            |
| **6 h**  | ~3-7 Mo             | ~12-30 Mo           |
| **8 h**  | ~4-10 Mo            | ~16-40 Mo           |
| **24 h** | Plafonné à 40-50 Mo | Plafonné à 40-50 Mo |

> **Note** : Augmenter la durée de rétention consomme plus de mémoire sur votre serveur. Un garde-fou automatique limite la consommation totale à ~40-50 Mo maximum.

---

## Conseils d'utilisation

1. **Commencez par un niveau INFO** : Moins de bruit, plus facile à lire
2. **Cibler un thermostat spécifique** : Plus de pertinence que tous les VTherm
3. **Réduire la période** : Plutôt que 24h, téléchargez juste la période problématique
4. **Utilisez le site pour l'analyse**: le [site web Versatile Thermostat](https://www.versatile-thermostat.org/fr/debugger/) permet d'analyser vos logs et de tracer des courbes. Il est le complément indispensable à cette fonction
5. **Utilisez des outils de traitement** : `grep`, `sed`, `awk` ou Python pour analyser les gros fichiers
6. **Conservez l'en-tête** : Utile pour fournir du contexte en cas de signalement de problème

---
