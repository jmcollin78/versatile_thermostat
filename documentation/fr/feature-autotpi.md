# Fonctionnalité Auto TPI


## Introduction

La fonctionnalité **Auto TPI** (ou auto-apprentissage) est une avancée majeure du Versatile Thermostat. Elle permet au thermostat d'ajuster **automatiquement** ses coefficients de régulation (Kp et Ki) en analysant le comportement thermique de votre pièce.

En mode TPI (Time Proportional & Integral), le thermostat calcule un pourcentage d'ouverture ou de temps de chauffe en fonction de l'écart entre la température de consigne et la température intérieure (`Kp`), et de l'influence de la température extérieure (`Ki`).

Trouver les bons coefficients (`tpi_coef_int` et `tpi_coef_ext`) est souvent complexe et nécessite de nombreux essais. **Auto TPI le fait pour vous.**

## Pré-requis

Pour que l'Auto TPI fonctionne efficacement :
1.  **Capteur de température fiable** : Le capteur ne doit pas être influencé directement par la source de chaleur (pas posé sur le radiateur !).
2.  **Capteur de température extérieure** : Une mesure précise de la température extérieure est indispensable.
3.  **Mode TPI activé** : Cette fonctionnalité ne s'applique que si vous utilisez l'algorithme TPI (thermostat sur switch, vanne, ou climate en mode TPI).
4.  **Configuration correcte de la puissance** : Définissez correctement les paramètres liés au temps de chauffe (voir ci-dessous).
5.  **Démarrage Optimal (Important)** : Pour que l'apprentissage démarre efficacement, il est recommandé de l'activer lorsque l'écart entre la température actuelle et la consigne est significatif (**2°C** est suffisant). 
    *   *Astuce* : refroidir la pièce, activez l'apprentissage, puis remettez la consigne de confort.

## Configuration

La configuration de l'Auto TPI est intégrée au flux de configuration du TPI pour **chaque thermostat individuel**.

> **Note** : L'apprentissage Auto TPI ne peut pas être configuré depuis la configuration centrale, car chaque thermostat nécessite son propre apprentissage.

1.  Allez dans la configuration de l'entité Versatile Thermostat (**Configurer**).
2.  Choisissez **Paramètres TPI**.
3.  **Important** : Vous devez décocher l'option **Utiliser la configuration centrale TPI** pour accéder aux paramètres locaux.
4.  Sur l'écran suivant (Attributs TPI), cochez la case **Activer l'apprentissage Auto TPI** tout en bas.

Une fois coché, un assistant de configuration dédié s'affiche en plusieurs étapes :

### Étape 1 : Général

*   **Activer l'Auto TPI** : Permet d'activer ou désactiver l'apprentissage.
*   **Notification** : Si activé, une notification sera envoyée **uniquement** lorsque l'apprentissage est considéré comme terminé (50 cycles par coefficient).
*   **Mise à jour de la configuration** : Si cette option est cochée, les coefficients TPI appris seront **automatiquement** enregistrés dans la configuration du thermostat **uniquement lorsque l'apprentissage est considéré comme terminé**. Si cette option est décochée, les coefficients appris sont utilisés pour la régulation TPI en cours, mais ne sont pas enregistrés dans la configuration.
*   **Apprentissage Continu** (`auto_tpi_continuous_learning`): Si activé, l'apprentissage se poursuivra indéfiniment, même après l'achèvement des 50 cycles initiaux. Cela permet au thermostat de s'adapter en continu aux changements progressifs de l'environnement thermique (ex: changements saisonniers, vieillissement de la maison). Si cette option est cochée, les paramètres appris seront sauvegardés dans la configuration (si **Mise à jour de la configuration** est également cochée) à la fin de chaque cycle une fois le modèle considéré comme "stable" (ex: après les 50 premiers cycles).
    *   **Robustesse aux Échecs** : En mode continu, les échecs consécutifs n'arrêtent pas l'apprentissage. Le système ignore les cycles fautifs et continue son adaptation.
    *   **Détection de Changement de Régime** : Lorsque l'apprentissage continu est activé, le système surveille les erreurs d'apprentissage récentes. Si un **biais systématique** est détecté (par exemple, dû à un changement de saison, d'isolation ou de système de chauffage), le taux d'apprentissage (alpha) est **temporairement boosté** (jusqu'à 3x la valeur de base, plafonné à 15%) pour accélérer l'adaptation. Cette fonctionnalité permet au thermostat de s'adapter rapidement aux nouvelles conditions thermiques sans intervention manuelle.
*   **Conserver l'apprentissage du coefficient externe** (`auto_tpi_keep_ext_learning`): Si activé, le coefficient extérieur (`Kext`) continuera son apprentissage même après avoir atteint 50 cycles, tant que le coefficient intérieur (`Kint`) n'a pas atteint la stabilité.
**Note :** La persistance à la configuration ne se fait que quand les deux coefficients sont stables.
*   **Temps de chauffe/refroidissement** : Définissez l'inertie de votre radiateur ([voir Configuration Thermique](#configuration-thermique-critique)).
*   **Plafond Coefficient Intérieur** : Limites de sécurité pour le coefficient Interieur (`max 3.0`). **Remarque** : En cas de modification de cette limite dans le flux de configuration, la nouvelle valeur est **immédiatement** appliquée aux coefficients appris si ces derniers sont supérieurs à la nouvelle limite (ce qui nécessite un rechargement de l'intégration, ce qui est le cas après avoir enregistré une modification via les options).

*   **Taux de chauffe** (`auto_tpi_heating_rate`): Taux cible de montée en température en °C/h. ([voir Configuration des Taux](#configuration-des-taux-de-chauffe) )

    *Note: On ne veut pas forcément utiliser le taux de chauffe maximal. Vous pouvez tout à fait utiliser une valeur inférieure selon le dimensionnement du chauffage, **et c'est très conseillé**.
    Plus vous serez proche de la capacité maximale, plus le coefficient Kint trouvé lors de l'apprentissage sera elevé.*

    *Donc une fois votre capacité définie par le service action dédié à ça , ou estimée manuellement, vous devriez  utiliser un taux de chauffe raisonnable.
   **Le plus important étant de ne pas être au dessus de ce que votre radiateur peut fournir dans cette pièce.**
    ex: Votre capacité adiabatique mesurée est de 1.5°/h, 1°/h est une constante standard et raisonable à utiliser.*

### Étape 2 : Méthode

Choisissez l'algorithme d'apprentissage :
*   **Moyenne (Average)** : Moyenne pondérée simple. Idéale pour un apprentissage rapide et unique (se réinitialise facilement).
*   **EMA (Exponential Moving Average)** : Moyenne mobile exponentielle. Fortement recommandée pour l'apprentissage continu et le réglage fin, car elle favorise les valeurs récentes.

### Étape 3 : Paramètres de la méthode

Configurez les paramètres spécifiques à la méthode choisie :
*   **Moyenne** : Poids initial.
*   **EMA** : Alpha initial et Taux de décroissance (Decay).


### Configuration Thermique (Critique)

L'algorithme a besoin de comprendre la réactivité de votre système de chauffage.

#### `heater_heating_time` (Temps de réponse thermique)
C'est le temps total nécessaire pour que le système commence à avoir un effet mesurable sur la température ambiante.

Il doit inclure :
*   Le temps de chauffe du radiateur (inertie matérielle).
*   Le temps de propagation de la chaleur dans la pièce jusqu'au capteur.

**Valeurs suggérées :**

| Type de chauffage | Valeur suggérée |
|---|---|
| Radiateur électrique (convecteur), capteur proche | 2-5 min |
| Radiateur à inertie (bain d'huile, fonte), capteur proche | 5-10 min |
| Chauffage au sol, ou grande pièce avec capteur éloigné | 10-20 min |

> Une valeur incorrecte peut fausser le calcul de l'efficacité et empêcher l'apprentissage.

#### `heater_cooling_time` (Temps de refroidissement du radiateur)
Temps nécessaire pour que le radiateur devienne froid après l'arrêt. Utilisé pour estimer si le radiateur est "chaud" ou "froid" au début d'un cycle via le `cold_factor`. Le `cold_factor` permet de corriger l'inertie du radiateur, et il sert de **filtre** : si le temps de chauffe est trop court par rapport au temps de réchauffement estimé, l'apprentissage pour ce cycle sera ignoré (pour éviter le bruit).

### Apprentissage Automatique de la Capacité Thermique ⚡

La capacité thermique (taux de montée en température en °C/h) est maintenant **apprise automatiquement** pendant l'apprentissage initial grâce au **bootstrap**.

#### Comment ça fonctionne ?

Le système démarre avec des **coefficients TPI agressifs** pour les 3 premiers cycles afin de provoquer une montée en température significative et mesurer la capacité réelle de votre chauffage. Ensuite, il passe automatiquement en mode TPI normal.

#### Les 2 Stratégies de Démarrage

1. **Mode Automatique (Recommandé)** ✅ :
   - Laissez `auto_tpi_heating_rate` à **0** (défaut)
   - Le système détecte automatiquement que la capacité est inconnue
   - Il effectue 3 cycles avec des **coefficients TPI agressifs** (200.0/5.0) pour provoquer une montée en température et mesurer la capacité
   - **C'est le mode recommandé pour un démarrage sans configuration**

2. **Mode Manuel** :
   - Définissez `auto_tpi_heating_rate` avec une valeur connue (ex: 1.5°C/h)
   - Le bootstrap est totalement sauté
   - Le système démarre immédiatement en TPI avec cette capacité
   - Utilisez ce mode si vous connaissez déjà votre capacité

#### Configuration

Dans l'étape 1 de configuration Auto TPI :
- **Taux de chauffe** (`auto_tpi_heating_rate`) : Laissez à **0** pour activer le bootstrap automatique

> 💡 **Astuce** : Pour un démarrage optimal du bootstrap, activez l'apprentissage lorsque l'écart entre la température actuelle et la consigne est d'au moins 2°C.

#### Service de calibration (optionnel)

Si vous souhaitez tout de même estimer la capacité à partir de l'historique sans attendre le bootstrap :

```yaml
service: versatile_thermostat.auto_tpi_calibrate_capacity
target:
  entity_id: climate.my_thermostat
data:
  save_to_config: true
```

Ce service analyse l'historique et estime la capacité en identifiant les moments de chauffe à pleine puissance.

## Fonctionnement

L'Auto TPI fonctionne de manière cyclique :

1.  **Observation** : À chaque cycle (ex: toutes les 10 min), le thermostat (qui est en mode `HEAT`) mesure la température au début et à la fin, ainsi que la puissance utilisée.
2.  **Validation** : Il vérifie si le cycle est valide pour l'apprentissage :
    *   L'apprentissage est basé sur le mode `HEAT` du thermostat, indépendamment de l'état actuel de l'émetteur de chaleur (`heating`/`idle`).
    *   La puissance n'était pas saturée (entre 0% et 100% exclu).
    *   L'écart de température est significatif.
    *   Le système est stable (pas d'échecs consécutifs).
    *   Le cycle n'a pas été interrompu par un délestage de puissance (Power Shedding), ou une ouverture de fenêtre.
    *   **Panne détectée** : L'apprentissage est suspendu si une anomalie de chauffage ou climatisation est détectée (ex: température ne monte pas malgré la chauffe), pour éviter d'apprendre des coefficients erronés.
    *   **Chaudière Centrale** : Si le thermostat dépend d'une chaudière centrale, l'apprentissage est suspendu si la chaudière n'est pas activée (même si le thermostat est en demande).
3.  **Calcul (Apprentissage)** :
    *   **Cas 1 : Coefficient Intérieur**. Si la température a évolué dans le bon sens de manière significative (> 0.05°C), il calcule le ratio entre l'évolution réelle **(sur l'ensemble du cycle, inertie incluse)** et l'évolution théorique attendue (corrigée par la capacité calibrée). Il ajuste `CoeffInt` pour réduire l'écart.
    *   **Cas 2 : Coefficient Extérieur**. Si l'apprentissage intérieur n'a pas été possible et que l'écart de température est significatif (> 0.1°C), il ajuste `CoeffExt` pour compenser les pertes.
        *   **Important** : L'apprentissage du coefficient extérieur est **bloqué** si l'écart de température est trop important (> 0.5°C). Cela garantit que `Kext` (qui représente les pertes à l'équilibre) n'est pas faussé par des problèmes de dynamique de montée en température (qui relèvent de `Kint`).
    *   **Cas 3 : Corrections Rapides (Boost/Deboost)**. En parallèle, le système surveille les anomalies critiques :
        *   **Boost Kint** : Si la température stagne malgré une demande de chauffe, le coefficient intérieur est boosté. (Optionnel via `allow_kint_boost_on_stagnation`)
        *   **Deboost Kext** : Si la température dépasse la consigne et ne redescend pas, le coefficient extérieur est réduit. (Optionnel via `allow_kext_compensation_on_overshoot`)
        *   *Ces corrections sont pondérées par la confiance du modèle : plus le système a d'historique (cycles d'apprentissage), plus les corrections sont modérées pour éviter de déstabiliser un modèle fiable.*
4.  **Mise à jour** : Les nouveaux coefficients sont lissés et sauvegardés pour le cycle suivant.

### Sécurité d'Activation
Pour éviter des activations involontaires :
1.  Le service `set_auto_tpi_mode` refuse d'activer l'apprentissage si la case "Activer l'apprentissage Auto TPI" n'est pas cochée dans la configuration du thermostat.
2.  Si vous décochez cette case dans la configuration alors que l'apprentissage était actif, celui-ci sera automatiquement arrêté au rechargement de l'intégration.

## Attributs et Capteurs

Un capteur dédié `sensor.<nom_thermostat>_auto_tpi_learning_state` permet de suivre l'état de l'apprentissage.

**Attributs disponibles :**

*   `active` : L'apprentissage est activé.
*   `heating_cycles_count` : Nombre total de cycles observés.
*   `coeff_int_cycles` : Nombre de fois où le coefficient intérieur a été ajusté.
*   `coeff_ext_cycles` : Nombre de fois où le coefficient extérieur a été ajusté.
*   `model_confidence` : Indice de confiance (0.0 à 1.0) sur la qualité des réglages. Plafonné à 100% après 50 cycles pour chaque coefficient (même si l'apprentissage continue).
*   `last_learning_status` : Raison du dernier succès ou échec (ex: `learned_indoor_heat`, `power_out_of_range`).
*   `calculated_coef_int` / `calculated_coef_ext` : Valeurs actuelles des coefficients.
*   `learning_start_dt`: Date et heure du début de l'apprentissage (utile pour les graphiques).
*   `allow_kint_boost_on_stagnation` : Indique si le boost de Kint en cas de stagnation est activé.
*   `allow_kext_compensation_on_overshoot` : Indique si la correction de Kext en cas d'overshoot est activée.
*   `capacity_heat_status` : Statut de l'apprentissage de la capacité thermique (`learning` ou `learned`).
*   `capacity_heat_value` : La valeur de la capacité thermique apprise (en °C/h).
*   `capacity_heat_count` : Le nombre de cycles de bootstrap effectués pour l'apprentissage de la capacité.

## Services

### Service de Calibration (`versatile_thermostat.auto_tpi_calibrate_capacity`)


Ce service permet d'estimer la **Capacité Adiabatique** de votre système (`max_capacity` en °C/h) en analysant l'historique des capteurs.

**Principe :** Le service utilise l'historique des **capteurs** `temperature_slope` et `power_percent` pour identifier les moments où le chauffage était à pleine puissance. Il utilise le **75ème percentile** (plus proche de l'adiabatique que la médiane) et applique une **correction Kext** : `Capacity = P75 + Kext_config × ΔT`.

```yaml
service: versatile_thermostat.auto_tpi_calibrate_capacity
target:
  entity_id: climate.my_thermostat
data:
  start_date: "2023-11-01T00:00:00+00:00" # Optionnel. Par défaut, 30 jours avant "end_date".
  end_date: "2023-12-01T00:00:00+00:00"   # Optionnel. Par défaut, maintenant.
  min_power_threshold: 95          # Optionnel. Seuil de puissance en % (0-100). Défaut 95.
  capacity_safety_margin: 20       # Optionnel. Marge de sécurité en % (0-100) à retirer de la capacité calculée. Défaut 20.
  save_to_config: true             # Optionnel. Enregistrer la capacité recommandée (après marge) dans la configuration. Défaut false.
```

> **Résultat** : La valeur de la Capacité Adiabatique (`max_capacity_heat`) est mise à jour dans les attributs du capteur d'état d'apprentissage avec la **valeur recommandée** (Capacité calculée - marge de sécurité).
>
> Le service retourne également les informations suivantes pour analyser la qualité de la calibration :
> *   **`max_capacity`** : La capacité adiabatique estimée brute (en °C/h).
> *   **`recommended_capacity`** : La capacité recommandée après application de la marge de sécurité (en °C/h). C'est cette valeur qui est sauvegardée.
> *   **`margin_percent`** : La marge de sécurité appliquée (en %).
> *   **`observed_capacity`** : Le 75ème percentile brut (avant correction Kext).
> *   **`kext_compensation`** : La valeur de correction appliquée (Kext × ΔT).
> *   **`avg_delta_t`** : Le ΔT moyen utilisé pour la correction.
> *   **`reliability`** : Indice de fiabilité (en %) basé sur le nombre d'échantillons et la variance.
> *   **`samples_used`** : Nombre d'échantillons utilisés après filtrage.
> *   **`outliers_removed`** : Nombre d'outliers éliminés.
> *   **`min_power_threshold`** : Seuil de puissance utilisé.
> *   **`period`** : Nombre de jours d'historique analysés.
>
> Les coefficients TPI (`Kint`/`Kext`) sont ensuite appris ou ajustés par la boucle d'apprentissage normale en utilisant cette capacité comme référence.

### Activer/Désactiver l'apprentissage (`versatile_thermostat.set_auto_tpi_mode`)

Ce service permet de contrôler l'apprentissage Auto TPI sans passer par la configuration du thermostat.

#### Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `auto_tpi_mode` | boolean | - | Active (`true`) ou désactive (`false`) l'apprentissage |
| `reinitialise` | boolean | `true` | Contrôle la réinitialisation des données lors de l'activation |
| `allow_kint_boost_on_stagnation` | boolean | `false` | Autorise le boost de Kint en cas de stagnation de température |
| `allow_kext_compensation_on_overshoot` | boolean | `false` | Autorise la compensation de Kext en cas de dépassement (overshoot) |

#### Comportement du paramètre `reinitialise`

Le paramètre `reinitialise` détermine comment les données d'apprentissage existantes sont traitées lors de l'activation :

- **`reinitialise: true`** (défaut) : Efface toutes les données d'apprentissage (coefficients et compteurs) et recommence l'apprentissage à zéro. Les capacités calibrées (`max_capacity_heat`/`cool`) sont conservées.
- **`reinitialise: false`** : Reprend l'apprentissage avec les données existantes sans les effacer. Les coefficients et compteurs précédents sont conservés et l'apprentissage continue à partir de ces valeurs.

**Cas d'usage :** Permet de désactiver temporairement l'apprentissage (par exemple lors d'une période de vacances ou de travaux) puis de le réactiver sans perdre les progrès déjà réalisés.

#### Exemples

**Démarrer un nouvel apprentissage (réinitialisation complète) :**
```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.mon_thermostat
data:
  auto_tpi_mode: true
  reinitialise: true  # ou omis car c'est le défaut
```

**Reprendre l'apprentissage sans perdre les données :**
```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.mon_thermostat
data:
  auto_tpi_mode: true
  reinitialise: false
```

**Arrêter l'apprentissage :**

Lorsque l'apprentissage est arrêté :

- L'apprentissage est **désactivé** mais les données apprises restent **visibles** dans les attributs de l'entité **auto_tpi_learning_state**
- La régulation utilise les coefficients de **configuration** (pas les coefficients appris)


## Méthode de calcul Moyenne Pondérée

La méthode **Moyenne Pondérée** (Average) est une approche simple et efficace pour l'apprentissage des coefficients TPI. Elle est particulièrement adaptée pour un apprentissage rapide et unique, ou lorsque vous souhaitez réinitialiser facilement les coefficients.

### Comportement

La méthode Moyenne Pondérée calcule une moyenne pondérée entre les coefficients existants et les nouvelles valeurs calculées. Comme la méthode EMA, elle réduit progressivement l'influence des nouveaux cycles au fur et à mesure de l'apprentissage, mais utilise une approche différente.

**Caractéristique clé** : Plus le nombre de cycles augmente, plus le poids du coefficient existant devient important par rapport au nouveau coefficient. Cela signifie que l'influence des nouveaux cycles diminue progressivement au fur et à mesure de l'apprentissage.

### Paramètres

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Poids initial** (`avg_initial_weight`) | Poids initial donné aux coefficients de configuration au démarrage | 1 |

### Formule

```
avg_coeff = ((old_coeff × weight_old) + coeff_new) / (weight_old + 1)
```

Où :
- `old_coeff` est le coefficient actuel
- `coeff_new` est le nouveau coefficient calculé pour ce cycle
- `weight_old` est le nombre de cycles d'apprentissage déjà effectués (avec un minimum de 1)

**Exemple d'évolution du poids** :
- Cycle 1 : weight_old = 1 → nouveau coefficient a un poids de 50%
- Cycle 10 : weight_old = 10 → nouveau coefficient a un poids de ~9%
- Cycle 50 : weight_old = 50 → nouveau coefficient a un poids de ~2%
- Cycle 100+ : weight_old = 50 (plafonné) → nouveau coefficient a encore un poids ~2% pour assurer la réactivité

### Caractéristiques principales

1. **Simplicité** : La méthode est facile à comprendre
2. **Réinitialisation facile** : Les coefficients peuvent être facilement réinitialisés en redémarrant l'apprentissage
3. **Apprentissage progressif** : L'influence des nouveaux cycles diminue au fur et à mesure, stabilisant progressivement les coefficients
4. **Convergence rapide** : La méthode atteint une stabilité après environ 50 cycles

### Comparaison avec EMA

| Aspect | Moyenne Pondérée | EMA |
|--------|------------------|-----|
| **Complexité** | Simple | Plus complexe |
| **Mécanisme de réduction** | Poids basé sur le nombre de cycles | Alpha adaptatif avec décroissance |
| **Stabilité** | Stable après 50 cycles | Stable après 50 cycles avec décroissance alpha |
| **Adaptation continue** | Moins adaptée | Plus adaptée (meilleure pour les changements progressifs) |
| **Réinitialisation** | Très facile | Facile |

### Recommandations d'utilisation

- **Apprentissage initial** : La méthode Moyenne Pondérée est excellente pour un premier apprentissage rapide
- **Réglages ponctuels** : Idéale lorsque vous souhaitez ajuster les coefficients une seule fois
- **Environnements stables** : Bien adaptée aux environnements thermiques relativement stables

### Exemple de progression

| Cycle | Poids ancien | Poids nouveau | Nouveau coefficient | Résultat |
|-------|--------------|---------------|---------------------|----------|
| 1 | 1 | 1 | 0.15 | (0.10 × 1 + 0.15 × 1) / 2 = 0.125 |
| 2 | 2 | 1 | 0.18 | (0.125 × 2 + 0.18 × 1) / 3 = 0.142 |
| 10 | 10 | 1 | 0.20 | (0.175 × 10 + 0.20 × 1) / 11 = 0.177 |
| 50 | 50 | 1 | 0.19 | (0.185 × 50 + 0.19 × 1) / 51 = 0.185 |

**Note** : Après 50 cycles, le coefficient est considéré comme stable et l'apprentissage s'arrête (sauf si l'apprentissage continu est activé). À ce stade, le nouveau coefficient n'a plus qu'un poids d'environ 2% dans la moyenne.

## Méthode de calcul EMA Adaptatif

La méthode EMA (Exponential Moving Average) utilise un coefficient **alpha** qui détermine
l'influence de chaque nouveau cycle sur les coefficients appris.

### Comportement

Au fil des cycles, **alpha décroît progressivement** pour stabiliser l'apprentissage :

| Cycles | Alpha (avec α₀=0.2, k=0.1) | Influence du nouveau cycle |
|--------|----------------------------|---------------------------|
| 0 | 0.20 | 20% |
| 10 | 0.10 | 10% |
| 50 | 0.033 | 3.3% |
| 100 | 0.033 | 3.3% (plafonné à 50 cycles) |

### Paramètres

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Alpha initial** (`ema_alpha`) | Influence au démarrage | 0.2 (20%) |
| **Taux de décroissance** (`ema_decay_rate`) | Vitesse de stabilisation | 0.1 |

### Formule

```
alpha(n) = alpha_initial / (1 + decay_rate × n)
```

Où `n` est le nombre de cycles d'apprentissage (plafonné à 50).

### Cas particuliers

- **decay_rate = 0** : Alpha reste fixe (comportement EMA classique)
- **decay_rate = 1, alpha = 1** : Équivalent à la méthode "Moyenne Pondérée"

### Recommandations

| Situation | Alpha (`ema_alpha`) | Taux de Décroissance (`ema_decay_rate`) |
|---|---|---|
| **Apprentissage initial** | `0.15` | `0.08` |
| **Apprentissage fin** | `0.08` | `0.12` |
| **Apprentissage continu** | `0.05` | `0.02` |

**Explications:**

- **Apprentissage initial:**

  *Alpha:* 0.15 (15% de poids initial)

  *Avec ces paramètres, le système garde en tête principalement les 20 derniers cycles*

  * Cycle 1: α = 0.15 (forte réactivité initiale)
  * Cycle 10: α = 0.083 (commence à stabiliser)
  * Cycle 25: α = 0.050 (filtrage accru)
  * Cycle 50: α = 0.036 (robustesse finale)


  *Taux de décroissance:* 0.08

  Décroissance modérée permettant une adaptation rapide aux 10 premiers cycles
  Balance optimale entre vitesse (éviter stagnation) et stabilité (éviter sur-ajustement)

- **Apprentissage fin**

  *Alpha:* 0.08 (8% de  poids initial)

  *Avec ces paramètres, le système garde en tête principalement les 50 derniers cycles*

  Démarrage conservateur (coefficients déjà bons)
  Évite les sur-corrections brutales

  * Cycle 1 : α = 0.08
  * Cycle 25 : α = 0.024
  * Cycle 50+ : α = 0.013 (plafonné)


  *Taux de décroissance:*: 0.12

  Décroissance plus rapide que l'apprentissage initial
  Converge vers un filtrage très fort (stabilité)
  Adaptation majoritaire dans les 15 premiers cycles

- **Apprentissage continu**
  
  *Alpha* = 0.05 (5% de poids initial)

  *Avec ces paramètres, le système garde en tête principalement les 100 derniers cycles*

  Très conservateur pour éviter dérive
  Réactivité modérée aux changements graduels

  * Cycle 1 : α = 0.05
  * Cycle 50 : α = 0.025
  * Cycle 100+ : α = 0.025 (plafonné)


  *Taux de décroissance:* = 0.02

  Décroissance très lente (apprentissage à long terme)
  Maintient une capacité d'adaptation même après des centaines de cycles
  Adapté aux variations saisonnières (hiver/été)