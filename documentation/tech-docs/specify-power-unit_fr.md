# Spécification Technique : Unités de puissance/énergie personnalisables et adaptatives (#1671)

## Présentation générale

Ce document spécifie la conception technique nécessaire pour résoudre l'issue #1671. L'objectif est de permettre aux utilisateurs de spécifier explicitement l'unité de puissance pour tous les attributs de puissance et de s'adapter automatiquement aux unités de puissance des capteurs configurés. De plus, cela résout l'issue #2022 où l'entité `TotalPowerActiveDeviceForBoilerSensor` manquait de la propriété `native_unit_of_measurement` malgré une classe d'appareil configurée sur `SensorDeviceClass.POWER`, ce qui générait des erreurs ou des avertissements dans Home Assistant.

## Architecture

Pour prendre en charge des unités personnalisables et adaptatives, la résolution des unités de puissance et d'énergie suit une hiérarchie claire et gère des unités potentiellement hétérogènes entre les thermostats (VTherms) et la configuration centrale :

### 1. Résolution de l'unité de puissance centrale (Niveau Central)
L'unité résolue par le gestionnaire de puissance central sert d'unité de référence pour toutes les opérations globales, les capteurs centraux et les algorithmes de délestage. Elle est résolue comme suit :
- **Surcharge utilisateur** : Si l'utilisateur choisit explicitement une unité de puissance (`W` ou `kW`) dans la configuration centrale, cette unité est strictement respectée.
- **Auto-adaptation du capteur** : Si le paramètre est positionné sur "Auto" (ou non spécifié), l'intégration inspecte l'état de l'entité du capteur de puissance configuré (`power_sensor_entity_id`) pour en extraire dynamiquement son attribut `unit_of_measurement` (valeurs valides : `W` ou `kW`).
- **Repli forcé (Fallback)** : Si l'unité ne peut pas être récupérée au démarrage (capteur indisponible ou état inconnu), l'intégration **force l'unité en Watts (`W`)** pour s'assurer d'éviter des états `None` ou incohérents.

### 3. Calculs internes normalisés (Toujours en Watts)
Plutôt que d'effectuer des conversions d'unités de puissance répétitives et bidirectionnelles au cœur même des calculs et des algorithmes (ce qui alourdirait le code et introduirait un fort risque d'erreurs), **tous les calculs internes de l'intégration s'exécutent strictement en Watts (`W`)**. Ce choix assure une unité de mesure cohérente et robuste pour toutes les évaluations algorithmiques intermédiaires (gestion du délestage, évaluation de la capacité de démarrage, puissance disponible globale, et cumuls de chaudière).
- **Normalisation à l'entrée (Frontière)** :
  - Dès lors que la configuration `device_power` d'un VTherm ou tout autre attribut de puissance est lu, il est normalisé à la volée en Watts (multiplié par 1000 si le VTherm s'avère configuré en `kW`).
  - Dès que la valeur d'état du capteur de puissance principal ou du capteur de puissance maximale est lue, elle est normalisée en Watts (multipliée par 1000 si l'unité déclarée par l'état actuel de l'entité est `kW`).
- **Traitement interne** :
  - Les opérations clés telles que `calculate_shedding()` et `check_power_available()` dans `FeatureCentralPowerManager` manipulent uniquement des Watts bruts. L'algorithme métier est ainsi épuré de toute logique d'unités hétérogènes.
- **Dénormalisation à la sortie (Restitution / Affichage)** :
  - Les valeurs affectées aux capteurs (`MeanPowerSensor`, `EnergySensor`, `TotalPowerActiveDeviceForBoilerSensor`) ou exposées dans les attributs complémentaires (`add_custom_attributes`) sont converties à la volée depuis l'unité de stockage interne (Watts) vers l'unité d'exposition désignée.

### Flux de résolution d'unité centrale

```mermaid
flowchart TD
    Start([Résoudre l'unité centrale]) --> Choice{Est-ce que CONF_POWER_UNIT central est configuré ?}
    Choice -->|L'utilisateur a choisi W| Watts[Retourner W / Wh]
    Choice -->|L'utilisateur a choisi kW| Kilowatts[Retourner kW / kWh]
    Choice -->|L'utilisateur a choisi Auto / Vide| GetSensorState[Obtenir l'état de power_sensor_entity_id]

    GetSensorState --> SensorChoice{Le capteur a-t-il une unité ?}
    SensorChoice -->|W| Watts
    SensorChoice -->|kW| Kilowatts
    SensorChoice -->|Aucune / Invalide| Fallback[Forcer en watts W]

    Fallback --> Watts
```

## Modifications des classes et des attributs

### Schéma de Configuration
Nous introduisons `CONF_POWER_UNIT` comme option de configuration dans les schémas d'intégration.

- **Fichiers** : [custom_components/versatile_thermostat/const.py](custom_components/versatile_thermostat/const.py), [custom_components/versatile_thermostat/config_schema.py](custom_components/versatile_thermostat/config_schema.py)
- **Constante** : `CONF_POWER_UNIT = "power_unit"`
- **Schéma** :
  - Ajouter `CONF_POWER_UNIT` dans `STEP_CENTRAL_POWER_DATA_SCHEMA` et `STEP_NON_CENTRAL_POWER_DATA_SCHEMA`. Il présente un menu déroulant avec les choix : `W`, `kW` et `Auto` (valeur par défaut : `Auto`, soit `None` en interne).
  - Ajouter `CONF_POWER_UNIT` dans `STEP_MAIN_DATA_SCHEMA` ou le schéma principal du VTherm où `CONF_DEVICE_POWER` est configuré. Il présente un menu déroulant avec les choix : `W` et `kW` (valeur par défaut : `W`).

### Gestionnaire Central de Puissance (Central Power Feature Manager)
Le gestionnaire de puissance central fait office de source de vérité pour déterminer les unités de puissance et d'énergie actives de la configuration centrale et gère les conversions d'unités de puissance.

- **Fichier** : [custom_components/versatile_thermostat/feature_central_power_manager.py](custom_components/versatile_thermostat/feature_central_power_manager.py)
- **Propriétés** :
  - Propriété `power_unit` : résout l'unité soit depuis la configuration utilisateur centrale `CONF_POWER_UNIT`, soit depuis l'attribut d'unité du capteur `power_sensor_entity_id`, soit retourne par défaut `W`.
- **Méthodes d'aide à la normalisation** :
  - Ajouter des helpers pour convertir à l'entrée et à la sortie :
    ```python
    def to_watts(self, power: float, unit: str) -> float:
        """Convertit une valeur de puissance en Watts."""
        if unit == "kW":
            return power * 1000.0
        return power

    def from_watts(self, power_w: float, target_unit: str) -> float:
        """Convertit une valeur de Watts vers l'unité de restitution cible."""
        if target_unit == "kW":
            return power_w / 1000.0
        return power_w
    ```
- **Prise en compte dans l'algorithme** :
  - Dans tous les calculs internes de délestage (p. ex. `calculate_shedding()`), normaliser d'abord toutes les entrées en Watts :
    - Établir `current_power_w = self.to_watts(self.current_power, self.power_unit)`
    - Établir `max_power_w = self.to_watts(self.current_max_power, self.power_unit)`
    - Pour chaque VTherm, évaluer `device_power_w = self.to_watts(vtherm.device_power, vtherm.power_unit)`
  - Réaliser l'intégralité du calcul avec ces valeurs brutes exemptes d'unités hétérogènes.

### Capteurs (Sensors)

#### MeanPowerSensor & EnergySensor
Ces capteurs utilisent strictement l'unité de puissance configurée pour leur VTherm parent respectif, évitant les sauts d'unités indésirables d'un thermostat à l'autre.

- **Fichier** : [custom_components/versatile_thermostat/sensor.py](custom_components/versatile_thermostat/sensor.py)
- **Propriétés** :
  - `native_unit_of_measurement` de la classe `MeanPowerSensor` :
    - Retourne directement l'unité `power_unit` configurée sur le VTherm (choix : `W` ou `kW`, valeur par défaut : `W`).
  - `native_unit_of_measurement` de la classe `EnergySensor` :
    - Retourne `UnitOfEnergy.WATT_HOUR` si l'unité de puissance du VTherm est `W`, ou `UnitOfEnergy.KILO_WATT_HOUR` si elle est configurée sur `kW`.
- **Restitution des valeurs** :
  - Bien que calculées en Watts / Watt-heures en interne, les valeurs affectées à `_attr_native_value` lors de l'appel à `async_my_climate_changed()` sont converties à la volée d'après l'unité locale du VTherm à l'aide de la méthode `from_watts()` ou équivalent.

#### TotalPowerActiveDeviceForBoilerSensor
Ce capteur manquait auparavant de la propriété `native_unit_of_measurement`. Nous l'exposons directement, et elle s'aligne sur l’unité du gestionnaire de puissance central.

- **Fichier** : [custom_components/versatile_thermostat/sensor.py](custom_components/versatile_thermostat/sensor.py)
- **Propriétés** :
  - `native_unit_of_measurement` :
    - Retourne l'unité résolue par le gestionnaire de puissance central (se replie sur `W` si indisponible).
- **Calcul global de cumul** :
  - Lors des cycles d'évaluation dans `calculate_total_power()`, normaliser la puissance de chaque VTherm actif en Watts (via `to_watts(vtherm.device_power, vtherm.power_unit)`) avant de calculer leur cumul brut en Watts.
  - Convertir ce cumul brut en Watts dans l'unité centrale cible via `from_watts()` avant d'assigner l'état final à `_attr_native_value`.

### Attributs d'état additionnels (Extra State Attributes)
Exposer les unités résolues dans les attributs d'état supplémentaires pour faciliter le dépannage et le rendu dans l'interface utilisateur.

- **Fichier** : [custom_components/versatile_thermostat/feature_power_manager.py](custom_components/versatile_thermostat/feature_power_manager.py)
- **Mises à jour** : Ajouter les valeurs `power_unit` et `energy_unit` issues de la configuration de chaque VTherm dans le dictionnaire `power_manager` dans `add_custom_attributes`. Ajouter optionnellement `central_power_unit` pointant vers l'unité centrale si elle est configurée/résolue.

---

## Plan de validation et de test

### Tests unitaires et d'intégration

1. **Vérification de la cohérence des unités et conversions** :
   - Ajout de tests de classe dans [tests/test_sensors.py](tests/test_sensors.py) pour s'assurer que la modification de la configuration `power_unit` d'un VTherm met à jour ses entités de mesure en `W` ou en `kW` de façon transparente.
   - Écriture d'un test unitaire valider les fonctions de normalisation `to_watts` et `from_watts` dans `FeatureCentralPowerManager`.
   - Entériner que si le mode est `Auto` sans état de capteur, l'unité centrale par défaut est bien forcée à `W`.

2. **Délestage et comportement face à des unités hétérogènes** :
   - Ajouter de nouveaux scénarios de test dans [tests/test_power.py](tests/test_power.py) et [tests/test_central_power_manager.py](tests/test_central_power_manager.py) dans lesquels le capteur de puissance globale est configuré en `W` mais certains chauffages possèdent un `device_power` en `kW` et d'autres en `W`. Vérifier que les calculs de délestage et de récupération de charge demeurent parfaitement corrects grâce au traitement unifié en Watts.

3. **Conformité et somme du capteur chaudière globale** :
   - Suite de tests dans [tests/test_central_boiler.py](tests/test_central_boiler.py) pour confirmer que `TotalPowerActiveDeviceForBoilerSensor` expose un attribut d'unité de mesure conforme, et que le calcul de la somme totale d'équipements actifs d'unités mixtes (par exemple un chauffage de 1500W et un second de 2.0kW actif) effectue bien les conversions appropriées (somme calculée valant 3500W ou 3.5kW selon l'unité de référence).
    - Retourne `UnitOfEnergy.WATT_HOUR` si l'unité de puissance du VTherm est `W`, ou `UnitOfEnergy.KILO_WATT_HOUR` si elle est configurée sur `kW`.

#### TotalPowerActiveDeviceForBoilerSensor
Ce capteur manquait auparavant de la propriété `native_unit_of_measurement`. Nous l'exposons directement, et elle s'aligne sur l’unité du gestionnaire de puissance central.

- **Fichier** : [custom_components/versatile_thermostat/sensor.py](custom_components/versatile_thermostat/sensor.py)
- **Propriétés** :
  - `native_unit_of_measurement` :
    - Retourne l'unité résolue par le gestionnaire de puissance central (se replie sur `W` si indisponible).
- **Calcul global de cumul** :
  - Lors des cycles d'évaluation dans `calculate_total_power()`, obtenir l'unité de puissance individuelle de chaque VTherm actif afin de convertir son `device_power` dans l'unité cible du capteur de chaudière centrale avant de faire la somme finale.

### Attributs d'état additionnels (Extra State Attributes)
Exposer les unités résolues dans les attributs d'état supplémentaires pour faciliter le dépannage et le rendu dans l'interface utilisateur.

- **Fichier** : [custom_components/versatile_thermostat/feature_power_manager.py](custom_components/versatile_thermostat/feature_power_manager.py)
- **Mises à jour** : Ajouter les valeurs `power_unit` et `energy_unit` issues de la configuration de chaque VTherm dans le dictionnaire `power_manager` dans `add_custom_attributes`. Ajouter optionnellement `central_power_unit` pointant vers l'unité centrale si elle est configurée/résolue.

---

## Plan de validation et de test

### Tests unitaires et d'intégration

1. **Vérification de la cohérence des unités et conversions** :
   - Ajout de tests de classe dans [tests/test_sensors.py](tests/test_sensors.py) pour s'assurer que la modification de la configuration `power_unit` d'un VTherm met à jour ses entités de mesure en `W` ou en `kW` de façon transparente.
   - Écriture d'un test unitaire valider la fonction de conversion `convert_power_to_central_unit` avec différentes variations d'unités de puissance.
   - Entériner que si le mode est `Auto` sans état de capteur, l'unité centrale par défaut est bien forcée à `W`.

2. **Délestage et comportement face à des unités hétérogènes** :
   - Ajouter de nouveaux scénarios de test dans [tests/test_power.py](tests/test_power.py) et [tests/test_central_power_manager.py](tests/test_central_power_manager.py) dans lesquels le capteur de puissance globale est configuré en `W` mais certains chauffages possèdent un `device_power` en `kW` et d'autres en `W`. Vérifier que les calculs de délestage et de récupération de charge demeurent corrects (grace aux conversions).

3. **Conformité et somme du capteur chaudière globale** :
   - Suite de tests dans [tests/test_central_boiler.py](tests/test_central_boiler.py) pour confirmer que `TotalPowerActiveDeviceForBoilerSensor` expose un attribut d'unité de mesure conforme, et que le calcul de la somme totale d'équipements actifs d'unités mixtes (par exemple un chauffage de 1500W et un second de 2.0kW actif) effectue bien les conversions appropriées (somme calculée valant 3500W ou 3.5kW selon l'unité de référence).
