# Nouvelle Structure de `ThermostatProp` (Refactor)

Ce document détaille la nouvelle architecture de la classe `ThermostatProp` et de ses composants associés suite aux récents refactorings. L'objectif principal était de centraliser la logique de sécurité et de "clamping" (limitation) dans la classe parente et d'introduire un mécanisme de feedback vers les algorithmes.

## Changements Principaux

1.  **Centralisation de la Sécurité et du Clamping** :
    *   Auparavant, chaque algorithme (TPI, SmartPI) gérait sa propre logique de sécurité (mode "safe") et de limitation (`max_on_percent`).
    *   Désormais, **`ThermostatProp`** est le seul responsable de l'application de ces contraintes via sa propriété `on_percent`. L'algorithme propose une valeur brute, et `ThermostatProp` la modifie si nécessaire.

2.  **Mécanisme de Feedback (`update_realized_power`)** :
    *   Puisque l'algorithme ne connait plus la valeur finale utilisée (car modifiée par `ThermostatProp` ou par des contraintes temporelles), une méthode `update_realized_power(val)` a été ajoutée.
    *   `ThermostatProp` appelle cette méthode pour informer l'algorithme de la puissance *réellement* appliquée. C'est crucial pour les algorithmes d'apprentissage (comme SmartPI ou AutoTPI) qui doivent "savoir" ce qui s'est réellement passé.

3.  **Encapsulation via `Handler`** :
    *   La logique spécifique à chaque type (TPI vs SmartPI) est déléguée à un **Handler** (ex: `TPIHandler`).
    *   Le Handler interagit désormais via les **propriétés publiques** de `BaseThermostat` (ex: `self.thermostat.tpi_coef_int`) au lieu d'accéder aux attributs privés protégés (`_tpi_coef_int`), améliorant la maintenabilité.

4.  **Utilitaires de Temps (`timing_utils`)** :
    *   Le calcul des temps de cycle (`on_time_sec`, `off_time_sec`) a été extrait dans `timing_utils.calculate_cycle_times`.
    *   Ce calcul retourne désormais un indicateur `forced_by_timing` si les contraintes de temps (min_on/off) ont forcé une modification de la puissance. Cela déclenche également le feedback vers l'algorithme.

## Schéma d'Architecture (Mermaid)

```mermaid
classDiagram
    class BaseThermostat {
        +tpi_coef_int
        +tpi_coef_ext
        +on_percent
        +current_temperature
    }

    class ThermostatProp {
        -AlgorithmHandler _algo_handler
        -Algorithm _prop_algorithm
        +has_prop()
        +on_percent()
        +recalculate()
    }

    class ThermostatOverSwitch {
        +updates_attributes()
        +control_heating()
    }

    class TPIHandler {
        +init_algorithm()
        +control_heating()
        +update_attributes()
    }

    class TpiAlgorithm {
        +calculate()
        +on_percent
        +update_realized_power(power_percent)
    }

    BaseThermostat <|-- ThermostatProp
    ThermostatProp <|-- ThermostatOverSwitch
    ThermostatProp *-- TPIHandler : _algo_handler
    ThermostatProp *-- TpiAlgorithm : _prop_algorithm
    TPIHandler ..> TpiAlgorithm : Configures & Updates

    note for ThermostatProp "Responsable de :<br/>1. Demander on_percent à l'Algo<br/>2. Appliquer Safety<br/>3. Appliquer MaxOnPercent<br/>4. Feedback vers l'Algo"
```

## Flux de Données (Calcul de la Puissance)

Le diagramme suivant montre comment la puissance est calculée et comment le feedback est renvoyé.

```mermaid
sequenceDiagram
    participant Call as Caller (Cycle/Update)
    participant Prop as ThermostatProp
    participant Algo as TpiAlgorithm
    participant Handler as TPIHandler

    Call->>Prop: on_percent (Property)
    
    activate Prop
    Prop->>Algo: on_percent (Getter)
    Algo-->>Prop: Valeur calculée (ex: 0.5)
    
    rect rgb(200, 220, 240)
        note right of Prop: Application des contraintes
        Prop->>Prop: Check Safety (Si actif -> default_on_percent)
        Prop->>Prop: Check MaxOnPercent
    end
    
    alt Valeur modifiée ?
        Prop->>Algo: update_realized_power(nouvelle_valeur)
        note left of Algo: L'algo apprend/s'ajuste<br/>avec la vraie valeur
    end
    
    Prop-->>Call: Valeur Finale
    deactivate Prop

    opt Lors du cycle de chauffe (TPIHandler)
        Call->>Handler: control_heating()
        Handler->>Prop: on_percent
        Prop-->>Handler: Puissance
        Handler->>Handler: calculate_cycle_times(Puissance)
        
        alt Forced by Timing?
            Handler->>Algo: update_realized_power(realized_percent)
            note left of Algo: Feedback si les temps min/max<br/>ont modifié la puissance
        end
    end
```
