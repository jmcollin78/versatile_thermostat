# Funkcja Auto TPI


## Wstęp

Funkcja **Auto TPI** (lub samouczenia) stanowi istotny postęp w rozwoju integracji _*Termostat VTherm*_. Umożliwia ona termostatowi **automatyczny** dobór współczynników regulacji (`Kp` i `Ki`) poprzez analizę zachowania termicznego pomieszczenia.

W trybie TPI _*(Time Proportional & Integral)*_ termostat oblicza procent otwarcia lub czas grzania na podstawie różnicy między temperaturą docelową a temperaturą wewnętrzną (`Kp`) oraz wpływu temperatury zewnętrznej (`Ki`).

Znalezienie odpowiednich współczynników (`tpi_coef_int` i `tpi_coef_ext`) jest często skomplikowane i wymaga wielu prób. Od teraz **Auto TPI robi to za Ciebie.**

## Wymagania wstępne

Aby funkcja _*Auto TPI*_ działała efektywnie, potrzebne są:
1. **Niezawodny czujnik temperatury**: Czujnik nie może być narażony na bezpośredni wpływ źródła ciepła (nie umieszczaj go na grzejniku!).
2. **Czujnik temperatury zewnętrznej**: Dokładny pomiar temperatury zewnętrznej jest niezbędny.
3. **Włączony tryb TPI**: Ta funkcja ma zastosowanie tylko w przypadku korzystania z algorytmu TPI (`termostat na przełączniku`, `termostat na zaworze` lub `termostat na klimacie` w trybie TPI).
4. **Prawidłowa konfiguracja zasilania**: Prawidłowo zdefiniuj parametry związane z czasem grzania (patrz poniżej).
5. **Optymalny rozruch (ważne)**: Aby funkcja uczenia się działała efektywnie, zaleca się jej włączenie, gdy różnica między aktualną temperaturą a temperaturą docelową jest znacząca (**co najmniej 2°C**).
* *Wskazówka*: ochłodź pomieszczenie, włącz funkcję uczenia się, a następnie przywróć żądane ustawienie komfortowe.

## Prerequisites

For Auto TPI to work effectively:
1.  **Reliable Temperature Sensor**: The sensor must not be directly influenced by the heat source (do not place it on the radiator!).
2.  **Outdoor Temperature Sensor**: Accurate measurement of the outdoor temperature is essential.
3.  **TPI Mode Enabled**: This feature only applies if you use the TPI algorithm (thermostat over switch, valve, or climate in TPI mode).
4.  **Correct Power Configuration**: Correctly define the parameters related to heating time (see below).
5.  **Optimal Startup (Important)**: For learning to start effectively, it is recommended to enable it when the gap between the current temperature and the target is significant (**2°C is sufficient**).
    *   *Tip*: cool the room, enable learning, then restore the comfort setpoint.

## Konfiguracja

Automatyczna konfiguracja TPI jest zintegrowana z procesem konfiguracji TPI dla **każdego termostatu**.

> **Uwaga**: Automatycznego uczenia się TPI nie można skonfigurować z poziomu konfiguracji centralnej, ponieważ każdy termostat wymaga własnych parametrów uczenia się.

1. Przejdź do konfiguracji jednostki VTherm (**Konfiguracja**).
2. Wybierz **Parametry TPI**.
3. **Ważne**: Aby uzyskać dostęp do parametrów lokalnych, należy wyłączyć opcję **Użyj centralnej konfiguracji TPI**.
4. Na następnym ekranie (Atrybuty TPI) zaznacz pole wyboru **Włącz uczenie się Auto TPI** na samym dole.

Po tym zaznaczeniu pojawi się dedykowany kreator konfiguracji, składający się z kilku kroków:

## Configuration

Auto TPI configuration is integrated into the TPI configuration flow for **each individual thermostat**.

> **Note** : Auto TPI learning cannot be configured from the central configuration, as each thermostat requires its own learning parameters.

1.  Go to the Versatile Thermostat entity configuration (**Configure**).
2.  Choose **TPI Parameters**.
3.  **Important**: You must uncheck **Use TPI central configuration** to access local parameters.
4.  On the next screen (TPI Attributes), check the **Enable Auto TPI Learning** box at the very bottom.

Once checked, a dedicated configuration wizard appears in several steps:

### Krok 1: Informacje ogólne

* **Włącz Auto TPI**: Umożliwia załączenie lub wyłączenie uczenia się.
* **Powiadomienie**: Jeśli ta opcja jest włączona, powiadomienie zostanie wysłane **tylko** po uznaniu procesu uczenia się za zakończony (50 cykli na współczynnik).
* **Aktualizuj konfigurację**: Jeśli ta opcja jest zaznaczona, zapamiętane współczynniki TPI zostaną **automatycznie** zapisane w konfiguracji termostatu **tylko po uznaniu procesu uczenia się za zakończony**. Jeśli ta opcja jest odznaczona, zapamiętane współczynniki są używane do bieżącej regulacji TPI, ale nie są zapisywane w konfiguracji.
* **Ciągłe uczenie się** (`auto_tpi_continuous_learning`): Jeśli ta opcja jest włączona, uczenie się będzie kontynuowane w nieskończoność, nawet po zakończeniu początkowych 50 cykli. Pozwala to termostatowi na ciągłe dostosowywanie się do stopniowych zmian temperatury otoczenia (np. zmian sezonowych, starzenia się budynku). Jeśli ta opcja jest zaznaczona, zapamiętane parametry zostaną zapisane w konfiguracji (jeśli zaznaczona jest również opcja **Aktualizuj konfigurację**) na koniec każdego cyklu, gdy model zostanie uznany za stabilny (np. po pierwszych 50 cyklach).
* **Wykrywanie zmian w reżimie**: Po włączeniu ciągłego uczenia się system monitoruje ostatnie błędy uczenia się. W przypadku wykrycia **systematycznego błędu** (np. spowodowanego zmianą pory roku, izolacji lub systemu grzewczego), szybkość uczenia się (alfa) jest **tymczasowo zwiększana** (do 3x, z ograniczeniem do 15%) w celu przyspieszenia adaptacji. Ta funkcja pomaga termostatowi szybko dostosować się do nowych warunków termicznych bez konieczności ręcznej interwencji.
* **Zapis wyuczonego współczynnika zewnętrznego** (`auto_tpi_keep_ext_learning`): Po włączeniu, współczynnik zewnętrzny (`Kext`) będzie kontynuował uczenie się nawet po osiągnięciu 50 cykli, dopóki współczynnik wewnętrzny (`Kint`) nie osiągnie stabilności.
**Uwaga:** Konfiguracja jest zachowywana tylko wtedy, gdy oba współczynniki są stabilne.
* **Czas grzania/chłodzenia**: Zdefiniuj bezwładność grzejnika ([patrz: Konfiguracja termiczna](#thermal-configuration-critical)).
* **Próg współczynnika temperatury wewnętrznej**: Limity bezpieczeństwa dla współczynnika temperatury wewnętrznej (maks. 3,0). **Uwaga**: Jeśli ten limit zostanie zmieniony w procesie konfiguracji, nowa wartość zostanie **natychmiast** zastosowana do zapamiętanych współczynników, jeśli przekroczą one nowy limit (wymaga to ponownego uruchomienia integracji, co ma miejsce po zapisaniu modyfikacji za pomocą opcji).

* **Szybkość grzania** (`auto_tpi_heating_rate`): Docelowa szybkość wzrostu temperatury w °C/h. ([patrz: Konfiguracja parametrów](#heating-cooling-rate-configuration))
* **Szybkość chłodzenia** (`auto_tpi_cooling_rate`): Docelowa szybkość spadku temperatury w °C/h. ([patrz: Konfiguracja parametrów](#heating-cooling-rate-configuration))

*Uwaga: Niekoniecznie należy używać maksymalnej szybkości grzania/chłodzenia. Można bez problemu użyć niższej wartości, w zależności od rozmiaru systemu ogrzewania, **co jest zdecydowanie zalecane**.
Im bliżej maksymalnej wydajności, tym wyższy będzie współczynnik `Kint`, określony podczas procesu uczenia.*

*Dlatego po zdefiniowaniu wydajności za pomocą usługi dedykowanej lub ręcznego jej oszacowania, należy użyć niższej szybkości grzania/chłodzenia.
**Najważniejsze, aby nie przekraczać wydajności grzejnika w tym pomieszczeniu.**
Np.: Zmierzona wydajność adiabatyczna wynosi 1,5°/h. Wobec tego 1°/h to standardowa i rozsądna stała.*

### Step 1: General

*   **Enable Auto TPI**: Allows enabling or disabling learning.
*   **Notification**: If enabled, a notification will be sent **only** when learning is considered complete ( 50 cycles per coefficient ).
*   **Update Configuration**: If this option is checked, the learned TPI coefficients will be **automatically** saved to the thermostat's configuration **only when learning is considered complete**. If this option is unchecked, the learned coefficients are used for the ongoing TPI regulation but are not saved to the configuration.
*   **Continuous Learning** (`auto_tpi_continuous_learning`): If enabled, learning will continue indefinitely, even after the initial 50 cycles are completed. This allows the thermostat to continuously adapt to gradual changes in the thermal environment (e.g., seasonal changes, house aging). If this option is checked, learned parameters will be saved to config (if **Update Configuration** is also checked) at the end of every cycle once the model is considered "stable" (e.g., after the first 50 cycles).
    *   **Regime Change Detection**: When continuous learning is enabled, the system monitors recent learning errors. If a **systematic bias** is detected (e.g., due to a change in season, insulation, or heating system), the learning rate (alpha) is **temporarily boosted** (up to 3x, capped at 15%) to accelerate adaptation. This feature helps the thermostat quickly adjust to new thermal conditions without manual intervention.
*   **Keep external coefficient learning** (`auto_tpi_keep_ext_learning`): If enabled, the external coefficient (`Kext`) will continue learning even after reaching 50 cycles, as long as the internal coefficient (`Kint`) has not reached stability.  
**Note:** Persistence to the configuration only occurs when both coefficients are stable.
*   **Heating/Cooling Time**: Define your radiator's inertia ([see Thermal Configuration](#thermal-configuration-critical)).
*   **Indoor Coefficient Cap**: Safety limits for indoor coefficient (`max 3.0`). **Note**: If this limit is changed in the configuration flow, the new value is **immediately** applied to the learned coefficients if they exceed the new limit (which requires an integration reload, which is the case after saving a modification via options).

*   **Heating Rate** (`auto_tpi_heating_rate`): Target rate of temperature increase in °C/h. ([see rates Configuration](#heating-cooling-rate-configuration))
*   **Cooling Rate** (`auto_tpi_cooling_rate`): Target rate of temperature decrease in °C/h. ([see rates Configuration](#heating-cooling-rate-configuration))

    *Note: You don’t necessarily want to use the maximum heating/cooling rate. You can perfectly well use a lower value depending on the heating/AC system sizing, **and it is highly recommended**.
    The closer you are to the maximum capacity, the higher the Kint coefficient determined during the learning process will be.*

    *So once your capacity is defined by the dedicated service action, or estimated manually, you should use a lower heating/cooling rate.
   **The most important thing is not to be above what your radiator can provide in this room.**
    ex: Your measured adiabatic capacity is 1.5°/h, 1°/h is a standard and reasonable constant to use.*

### Step 2: Method

Choose the learning algorithm:
*   **Average**: Simple weighted average. Ideal for fast, one-time learning (resets easily).
*   **EMA (Exponential Moving Average)**: Exponential moving average. Highly recommended for continuous, long-term learning and fine-tuning, as it favors recent values.


### Step 3: Method Parameters

Configure the specific parameters for the chosen method:
*   **Average**: Initial weight.
*   **EMA**: Initial Alpha and Decay Rate.

### Thermal Configuration (Critical)

The algorithm needs to understand the responsiveness of your heating system.

#### `heater_heating_time` (Thermal Response Time)
This is the total time required for the system to have a measurable effect on the room temperature.

It must include:
*   The heating time of the radiator (material inertia).
*   The heat propagation time in the room to the sensor.

**Suggested Values:**

| Heater Type | Suggested Value |
|---|---|
| Electric radiator (convector), sensor nearby | 2-5 min |
| Inertia radiator (oil-filled, cast iron), sensor nearby | 5-10 min |
| Underfloor heating, or large room with distant sensor | 10-20 min |

> An incorrect value can skew the efficiency calculation and prevent learning.

#### `heater_cooling_time` (Cooling Time)
Time required for the radiator to become cold after stopping. Used to estimate if the radiator is "hot" or "cold" at the start of a cycle via the `cold_factor`. The `cold_factor` corrects the radiator's inertia and acts as a **filter**: if the heating time is too short compared to the estimated warm-up time, learning for that cycle will be ignored (to prevent noise).

### Heating-Cooling Rate Configuration

The algorithm uses the **Heating/Cooling Rate** (`auto_tpi_heating_rate`/`cooling_rate` in °C/h) as a reference for calculating the indoor coefficient (`Kint`). This value should represent the **desired** or **achievable** rate of temperature increase or decrease when regulation is at 100% power.

> **Calibration** : This value can be automatically learned using the Calibrate capacity service from the thermostat’s HA history.

If you're not using the service above, you must manually define them:

We want an estimate of the so-called **"adiabatic"** value (without heat loss).

To estimate it yourself, the method is quite simple (example for heating):

***I - First, we need the cooling coefficient*** (which should be quite close to the Ext Coeff of the TPI regulation).

1) We will cool the room by turning off the heating for a period of time (1 hour for example) and measure the temperature variation that we will call **ΔTcool = Tend - Tstart** (e.g., we go from 19°C to 18°C in 1h, ΔTcool = -1).
We also note the time elapsed between the two measurements that we call **Δtcool** (in hours)
1) We calculate the cooling rate:
**Rcool = ΔTcool / Δtcool** (will be negative)
1) Then the Cooling Coefficient:
Tavg = the average between the 2 measured temperatures
Text = outdoor temperature (keep the average if it varied during the measurement)

**k ≃ -(Rcool / (Tavg - Text))**

note: you can also use this k value as the starting External Coefficient in the TPI configuration

***II - We can now calculate the adiabatic capacity***

1) We heat for the same duration as the cooling with the thermostat at 100% power.
    
    ***Important:** the heater must already be hot, so run a heating cycle first to bring it up to its maximum temperature.*

    To ensure that we have the full capacity of the radiator throughout the measurement, we raise the setpoint well above.

    Note the starting temperature, the arrival temperature, and the measurement time.

2) We calculate Rheat, which is the observed temperature variation:

- **ΔTheat = Tend - Tstart**
- **Δtheat: the time elapsed between the 2 measurements**
- **Rheat = ΔTheat / Δtheat**
  
3) We can finally find our adiabatic capacity:
- **Radiab = Rheat + k(Tavg − Text)**

## How it Works

Auto TPI operates cyclically:

1.  **Observation**: At each cycle (e.g., every 10 min), the thermostat (which is in `HEAT` or `COOL` mode) measures the temperature at the start and end, as well as the power used.
2.  **Validation**: It checks if the cycle is valid for learning:
    *   Learning is based on the thermostat's `hvac_mode` (`HEAT` or `COOL`), regardless of the current state of the heat emitter (`heating`/`idle`).
    *   Power was not saturated (between 0% and 100% excluded).
    *   The temperature difference is significant.
    *   The system is stable (no consecutive failures).
    *   The cycle was not interrupted by power shedding or by a window being opened.
3.  **Calculation (Learning)**:
    *   **Case 1: Indoor Coefficient**. If the temperature moved in the right direction significantly (> 0.05°C), it calculates the ratio between the real evolution **(over the full cycle, including inertia)** and the expected theoretical evolution (corrected by the calibrated capacity). It adjusts `CoeffInt` to reduce the gap.
    *   **Case 2: Outdoor Coefficient**. If indoor learning was not possible (conditions not met or failure) and outdoor learning is relevant (significant temperature gap > 0.1°C), it adjusts `CoeffExt` **progressively** to compensate for thermal losses. The formula allows this coefficient to increase or decrease as needed to reach equilibrium.
4.  **Update**: The new coefficients are smoothed and saved for the next cycle.

### Activation Safety
To avoid unintended activation:
1.  The `set_auto_tpi_mode` service refuses to enable learning if the "Enable Auto TPI Learning" checkbox is not checked in the thermostat configuration.
2.  If you uncheck this box in the configuration while learning was active, it will be automatically stopped upon reloading the integration.

## Attributes and Sensors

A dedicated sensor `sensor.<thermostat_name>_auto_tpi_learning_state` allows tracking the learning status.

**Available Attributes:**

*   `active`: Learning is enabled.
*   `heating_cycles_count`: Total number of observed cycles.
*   `coeff_int_cycles`: Number of times the indoor coefficient has been adjusted.
*   `coeff_ext_cycles`: Number of times the outdoor coefficient has been adjusted.
*   `model_confidence`: Confidence index (0.0 to 1.0) in the quality of the settings. Capped at 100% after 50 cycles for each coefficient (even if learning continues).
*   `last_learning_status`: Reason for the last success or failure (e.g., `learned_indoor_heat`, `power_out_of_range`).
*   `calculated_coef_int` / `calculated_coef_ext`: Current values of the coefficients.
*   `learning_start_dt`: Date and time when learning started (useful for graphs).

## Services

### Calibration Service (`versatile_thermostat.auto_tpi_calibrate_capacity`)

This service estimates the **Adiabatic Capacity** of your system (`max_capacity` in °C/h) by analyzing sensor histories.

**Principle:** The service uses the history of **sensors** `temperature_slope` and `power_percent` to identify moments when heating was at full power. It uses the **75th percentile** (closer to adiabatic than median) and applies a **Kext correction**: `Capacity = P75 + Kext_config × ΔT`.

```yaml
service: versatile_thermostat.auto_tpi_calibrate_capacity
target:
  entity_id: climate.my_thermostat
data:
  start_date: "2023-11-01T00:00:00+00:00" # Optional. Default is 30 days before "end_date".
  end_date: "2023-12-01T00:00:00+00:00"   # Optional. Default is now.
  hvac_mode: heat                  # Required. 'heat' or 'cool'.
  min_power_threshold: 0.95        # Optional. Power threshold (0.0-1.0). Default 0.95 (100%).
  save_to_config: true             # Optional. Save calculated capacity to config. Default false.
```

> **Result** : The Adiabatic Capacity value (`max_capacity_heat`/`cool`) is updated in the learning state sensor attributes.
>
> The service also returns the following information to analyze the calibration quality:
> *   **`capacity`**: The estimated adiabatic capacity (in °C/h).
> *   **`observed_capacity`**: The raw 75th percentile (before Kext correction).
> *   **`kext_compensation`**: The correction value applied (Kext × ΔT).
> *   **`avg_delta_t`**: The average ΔT used for correction.
> *   **`reliability`**: Reliability index (in %) based on sample count and variance.
> *   **`samples_used`**: Number of samples used after filtering.
> *   **`outliers_removed`**: Number of outliers eliminated.
> *   **`min_power_threshold`**: Power threshold used.
> *   **`period`**: Number of days of history analyzed.
>
> The TPI coefficients (`Kint`/`Kext`) are then learned or adjusted by the normal learning loop using this capacity as a reference.

### Enable/Disable Learning (`versatile_thermostat.set_auto_tpi_mode`)

This service allows controlling Auto TPI learning without going through the thermostat configuration.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `auto_tpi_mode` | boolean | - | Enables (`true`) or disables (`false`) learning |
| `reinitialise` | boolean | `true` | Controls data reset when enabling learning |

#### Behavior of the `reinitialise` parameter

The `reinitialise` parameter determines how existing learning data is handled when enabling learning:

- **`reinitialise: true`** (default): Clears all learning data (coefficients and counters) and restarts learning from scratch. Calibrated capacities (`max_capacity_heat`/`cool`) are preserved.
- **`reinitialise: false`**: Resumes learning with existing data without clearing it. Previous coefficients and counters are preserved and learning continues from these values.

**Use case:** Allows temporarily disabling learning (for example during a vacation or renovation period) and then reactivating it without losing already achieved progress.

#### Examples

**Start new learning (complete reset):**
```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.my_thermostat
data:
  auto_tpi_mode: true
  reinitialise: true  # or omitted since it's the default
```

**Resume learning without losing data:**
```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.my_thermostat
data:
  auto_tpi_mode: true
  reinitialise: false
```

**Stop learning:**

When learning is stopped:

- Learning is **disabled** but learned data stays **visible** in the auto_tpi_learning_state entity attributes.
- Regulation uses **configuration** coefficients (not learned coefficients)



## Weighted Average Calculation Method

The **Weighted Average** method is a simple and effective approach for learning TPI coefficients. It is particularly well-suited for quick, one-time learning, or when you want to easily reset coefficients.

### Behavior

The Weighted Average method calculates a weighted average between existing coefficients and newly calculated values. Like the EMA method, it gradually reduces the influence of new cycles as learning progresses, but uses a different approach.

**Key characteristic**: As the number of cycles increases, the weight of the existing coefficient becomes more important compared to the new coefficient. This means that the influence of new cycles gradually decreases as learning progresses.

### Parameters

| Parameter | Description | Default |
|-----------|-------------|--------|
| **Initial Weight** (`avg_initial_weight`) | Initial weight given to configuration coefficients at startup | 1 |

### Formula

```
avg_coeff = ((old_coeff × weight_old) + coeff_new) / (weight_old + 1)
```

Where:
- `old_coeff` is the current coefficient
- `coeff_new` is the new coefficient calculated for this cycle
- `weight_old` is the number of learning cycles already performed (with a minimum of 1)

**Weight evolution example**:
- Cycle 1: weight_old = 1 → new coefficient has a weight of 50%
- Cycle 10: weight_old = 10 → new coefficient has a weight of ~9%
- Cycle 50: weight_old = 50 → new coefficient has a weight of ~2%

### Main Characteristics

1. **Simplicity**: The method is easy to understand
2. **Easy Reset**: Coefficients can be easily reset by restarting learning
3. **Progressive Learning**: The influence of new cycles decreases over time, gradually stabilizing coefficients
4. **Rapid Convergence**: The method reaches stability after about 50 cycles

### Comparison with EMA

| Aspect | Weighted Average | EMA |
|--------|------------------|-----|
| **Complexity** | Simple | More complex |
| **Reduction Mechanism** | Weight based on number of cycles | Adaptive alpha with decay |
| **Stability** | Stable after 50 cycles | Stable after 50 cycles with alpha decay |
| **Continuous Adaptation** | Less suitable | More suitable (better for gradual changes) |
| **Reset** | Very easy | Easy |

### Usage Recommendations

- **Initial Learning**: The Weighted Average method is excellent for fast initial learning
- **One-time Adjustments**: Ideal when you want to adjust coefficients only once
- **Stable Environments**: Well-suited for relatively stable thermal environments

### Progression Example

| Cycle | Old Weight | New Weight | New Coefficient | Result |
|-------|--------------|---------------|---------------------|----------|
| 1 | 1 | 1 | 0.15 | (0.10 × 1 + 0.15 × 1) / 2 = 0.125 |
| 2 | 2 | 1 | 0.18 | (0.125 × 2 + 0.18 × 1) / 3 = 0.142 |
| 10 | 10 | 1 | 0.20 | (0.175 × 10 + 0.20 × 1) / 11 = 0.177 |
| 50 | 50 | 1 | 0.19 | (0.185 × 50 + 0.19 × 1) / 51 = 0.185 |

**Note**: After 50 cycles, the coefficient is considered stable and learning stops (unless continuous learning is enabled). At this stage, the new coefficient has only about 2% weight in the average.

## Adaptive EMA Calculation Method

The EMA (Exponential Moving Average) method uses an **alpha** coefficient that determines 
the influence of each new cycle on the learned coefficients.

### Behavior

Over cycles, **alpha decreases gradually** to stabilize learning:

| Cycles | Alpha (with α₀=0.2, k=0.1) | Influence of new cycle |
|--------|----------------------------|------------------------|
| 0 | 0.20 | 20% |
| 10 | 0.10 | 10% |
| 50 | 0.033 | 3.3% |
| 100 | 0.018 | 1.8% |

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| **Initial Alpha** (`ema_alpha`) | Influence at startup | 0.2 (20%) |
| **Decay Rate** (`ema_decay_rate`) | Stabilization speed | 0.1 |

### Formula

```
alpha(n) = alpha_initial / (1 + decay_rate × n)
```

Where `n` is the number of learning cycles.

### Special Cases

- **decay_rate = 0**: Alpha remains fixed (classic EMA behavior)
- **decay_rate = 1, alpha = 1**: Equivalent to the "Weighted Average" method

### Recommendations

| Situation | Alpha (`ema_alpha`) | Decay Rate (`ema_decay_rate`) |
|---|---|---|
| **Initial Learning** | `0.15` | `0.08` |
| **Fine-tuning Learning** | `0.08` | `0.12` |
| **Continuous Learning** | `0.05` | `0.02` |

**Explanations:**

- **Initial Learning:**

  *Alpha:* 0.15 (15% initial weight)

  *With these parameters, the system mainly keeps the last 20 cycles in mind*

  * Cycle 1: α = 0.15 (strong initial reactivity)
  * Cycle 10: α = 0.083 (starts to stabilize)
  * Cycle 25: α = 0.050 (increased filtering)
  * Cycle 50: α = 0.036 (final robustness)


  *Decay Rate:* 0.08

  Moderate decay allowing rapid adaptation to the first 10 cycles
  Optimal balance between speed (avoid stagnation) and stability (avoid over-adjustment)

- **Fine-tuning Learning**

  *Alpha:* 0.08 (8% initial weight)

  With these parameters, the system mainly keeps the last 50 cycles in mind*

  Conservative startup (coefficients already good)
  Avoids brutal over-corrections

  * Cycle 1 : α = 0.08
  * Cycle 25 : α = 0.024
  * Cycle 50 : α = 0.013


  *Decay Rate:* 0.12

  Faster decay than initial learning
  Converges towards very strong filtering (stability)
  Major adaptation in the first 15 cycles

- **Continuous Learning**
  
  *Alpha* = 0.05 (5% initial weight)

  With these parameters, the system mainly keeps the last 100 cycles in mind*

  Very conservative to prevent drift
  Moderate reactivity to gradual changes

  * Cycle 1 : α = 0.05
  * Cycle 50 : α = 0.025
  * Cycle 100 : α = 0.017
  * Cycle 200 : α = 0.011


  *Decay Rate:* 0.02

  Very slow decay (long-term learning)
  Maintains an ability to adapt even after hundreds of cycles
  Suitable for seasonal variations (winter/summer)
