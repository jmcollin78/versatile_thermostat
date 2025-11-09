# Używanie różnych algorytmów

- [Użycie różnych algorytmów](#the-different-algorithms-used)
  - [Algorytm TPI](#the-tpi-algorithm)
    - [Konfigurowanie współczynników algorytmu TPI](#configuring-the-tpi-algorithm-coefficients)
    - [Zasady](#principle)
    - [Minimalna zwłoka aktywacji lub dezaktywacji](#minimum-activation-or-deactivation-delay)
    - [Górne i dolne progi aktywacji algorytmu](#upper-and-lower-activation-thresholds-of-the-algorithm)
  - [Algorytm autoregulacji (bez sterowania zaworem)](#the-self-regulation-algorithm-without-valve-control)
  - [Algorytm autoSTAR i autoSTOP](#the-auto-startstop-function-algorithm)

## Algorytm TPI

### Konfigurowanie współczynników algorytmu TPI

Jeśli wybrałeś typ termostatu `Na Przełączniku`, `Na Zaworze`, lub `Na Klimacie` z trybem autoregulacji  `Bezpośrednie strowanie zaworem` i wybrałeś w menu opcję "TPI", znajdziesz się na tej stronie:

![image](images/config-tpi.png)

Musisz określić:
1. współczynnik `coef_int` algorytmu TPI,
2. współczynnik `coef_ext` algorytmu TPI,
3. minimalny czas aktywacji (w sek.),
4. minimalny czas deaktywacji (w sek.),
5. górny próg odcięcia w °C (lub °K) dla odchylenia temperatury, powyżej którego algorytm zostanie wyłączony,
6. dolny próg ponownej aktywacji w °C (lub °K) dla odchylenia temperatury, poniżej którego algorytm zostanie ponownie włączony.

### Zasady

Algorytm TPI oblicza procent załączenia/wyłączenia grzejnika w każdym cyklu, wykorzystując temperaturę docelową, aktualną temperaturę w pomieszczeniu i aktualną temperaturę zewnętrzną. Algorytm ten ma zastosowanie tylko dla termostatów, działających w trybach `na Przełączniku` lub `na Zaworze`.

Procent ten obliczany jest na podstawie następującej formuły:

    on_percent = coef_int * (target_temperature - current_temperature) + coef_ext * (target_temperature - outdoor_temperature)
    Then, the algorithm ensures that 0 <= on_percent <= 1.

The default values for `coef_int` and `coef_ext` are `0.6` and `0.01`, respectively. These default values are suitable for a standard well-insulated room.

When adjusting these coefficients, keep the following in mind:
1. **If the target temperature is not reached** after stabilization, increase `coef_ext` (the `on_percent` is too low),
2. **If the target temperature is exceeded** after stabilization, decrease `coef_ext` (the `on_percent` is too high),
3. **If reaching the target temperature is too slow**, increase `coef_int` to provide more power to the heater,
4. **If reaching the target temperature is too fast and oscillations occur** around the target, decrease `coef_int` to provide less power to the radiator.

In `over_valve` mode, the `on_percent` value is converted to a percentage (0 to 100%) and directly controls the valve's opening level.

### Minimalna zwłoka aktywacji lub dezaktywacji

The first delay (`minimal_activation_delay_sec`), in seconds, is the minimum acceptable delay to turn on the heater.
When the calculation results in a power-on delay shorter than this value, the heater remains off.
If the activation time is too short, rapid switching will not allow the equipment to reach operating temperature.

Similarly, the second delay (`minimal_deactivation_delay_sec`), also in seconds, defines the minimum acceptable off-time.
If the off-time is shorter than this value, the heater will not be turned off.
This prevents rapid flickering that provides little benefit for temperature regulation.

### Górne i dolne progi aktywacji algorytmu

Since version 7.4, two additional thresholds are available.
They allow you to disable (or re-enable) the TPI algorithm itself, based on the difference between the target setpoint and the current temperature.

- If the temperature rises and the difference is greater than the upper threshold, the heater is switched off (i.e., `on_percent` is forced to 0).
- If the temperature drops and the difference is smaller than the lower threshold, the heater is turned back on (i.e., `on_percent` is calculated by the algorithm as described above).

These two thresholds stop the on/off cycling when the temperature overshoots the target.
A hysteresis prevents rapid toggling.

Examples:
1. Suppose the target setpoint is 20°C, the upper threshold is 2°C, and the lower threshold is 1°C.
2. When the temperature rises above 22°C (setpoint + upper threshold), `on_percent` is forced to 0.
3. When the temperature drops below 21°C (setpoint + lower threshold), `on_percent` is recalculated.

> ![Tip](images/tips.png) _*Notes*_
> 1. Leave both values at 0 if you do not want to use thresholds. This restores the behavior from before version 7.4.
> 2. Both values are required. If you leave one at 0, no threshold will be applied. Indeed, both are necessary for correct operation.
> 3. In cooling mode, the tests are reversed, but the principle remains the same.
> 4. The upper threshold should always be greater than the lower threshold, even in cooling mode.

## Algorytm autoregulacji (bez sterowania zaworem)

The self-regulation algorithm can be summarized as follows:

1. Initialize the target temperature as the VTherm setpoint,
2. If self-regulation is enabled:
   1. Calculate the regulated temperature (valid for a VTherm),
   2. Use this temperature as the target,
3. For each underlying device of the VTherm:
     1. If "Use Internal Temperature" is checked:
          1. Calculate the compensation (`trv_internal_temp - room_temp`),
     2. Add the offset to the target temperature,
     3. Send the target temperature (= regulated_temp + (internal_temp - room_temp)) to the underlying device.

## Algorytm autoSTAR i autoSTOP

The algorithm used in the auto-start/stop function operates as follows:
1. If "Enable Auto-Start/Stop" is off, stop here.
2. If VTherm is on and in Heating mode, when `error_accumulated` < `-error_threshold` -> turn off and save HVAC mode.
3. If VTherm is on and in Cooling mode, when `error_accumulated` > `error_threshold` -> turn off and save HVAC mode.
4. If VTherm is off and the saved HVAC mode is Heating, and `current_temperature + slope * dt <= target_temperature`, turn on and set the HVAC mode to the saved mode.
5. If VTherm is off and the saved HVAC mode is Cooling, and `current_temperature + slope * dt >= target_temperature`, turn on and set the HVAC mode to the saved mode.
6. `error_threshold` is set to `10 (° * min)` for slow detection, `5` for medium, and `2` for fast.

`dt` is set to `30 min` for slow, `15 min` for medium, and `7 min` for fast detection levels.

The function is detailed [here](https://github.com/jmcollin78/versatile_thermostat/issues/585).
