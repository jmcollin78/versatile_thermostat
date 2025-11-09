# Używanie różnych algorytmów

- [Użycie różnych algorytmów](#the-different-algorithms-used)
  - [Algorytm TPI](#the-tpi-algorithm)
    - [Konfigurowanie współczynników algorytmu TPI](#configuring-the-tpi-algorithm-coefficients)
    - [Zasady](#principle)
    - [Minimalna zwłoka aktywacji lub dezaktywacji](#minimum-activation-or-deactivation-delay)
    - [Górne i dolne progi aktywacji algorytmu](#upper-and-lower-activation-thresholds-of-the-algorithm)
  - [Algorytm autoregulacji (bez sterowania zaworem)](#the-self-regulation-algorithm-without-valve-control)
  - [Algorytm autoSTART i autoSTOP](#the-auto-startstop-function-algorithm)

## Algorytm TPI

### Konfigurowanie współczynników algorytmu TPI

Jeśli wybrałeś typ termostatu `Na Przełączniku`, `Na Zaworze`, lub `Na Klimacie` z trybem autoregulacji  `Bezpośrednie strowanie zaworem` i wybrałeś w menu opcję "TPI", znajdziesz się na tej stronie:

![image](images/config-tpi.png)

Musisz tutaj określić:
1. współczynnik `współczynnik delty dla temperatury wewnętrznej` algorytmu TPI,
2. współczynnik `współczynnik delty dla temperatury zewnętrznej` algorytmu TPI,
3. minimalny czas aktywacji (w sek.),
4. minimalny czas deaktywacji (w sek.),
5. górny próg odcięcia w °C (lub °K) dla odchylenia temperatury, powyżej którego algorytm zostanie wyłączony,
6. dolny próg ponownej aktywacji w °C (lub °K) dla odchylenia temperatury, poniżej którego algorytm zostanie ponownie włączony.

### Zasady

Algorytm TPI oblicza procent załączenia/wyłączenia grzejnika w każdym cyklu, wykorzystując temperaturę docelową, aktualną temperaturę w pomieszczeniu i aktualną temperaturę zewnętrzną. Algorytm ten ma zastosowanie tylko dla termostatów, działających w trybach `na Przełączniku` lub `na Zaworze`.

Procent ten obliczany jest na podstawie następującej formuły:

    procent = współczynnik_delty_dla_temperatury_wewnętrznej * (temperatura_docelowa - temperatura_aktuana) + współczynnik_delty_dla_temperatury_zewnętrznej * (temperatura_docelowa - temperatura_zewnętrzna)
    Następnie algorytm sprawdza warunek: 0 <= procent <= 1.

Domyślne wartości  `współczynnika delty dla temperatury wewnętrznej` i `współczynnika delty dla temperatury zewnętrznej` wynoszą odpowiednio `0.6` i `0.01`. Wartości te są odpowiednie dla pomieszczenia o dobrej izolacji termicznej.

Określając wartości współczynników, należy pamiętać, że:
1. **Jeśli docelowa temperatura nie zostanie osiągnięta** po stabilizacji, zwiększ `współczynnik delty dla temperatury wewnętrznej` (wartość procentowa jest zbyt niska),
2. **Jeśli docelowa temperatura zostanie przekroczona** po stabilizacji, zmniejsz `współczynnik delty dla temperatury zewnętrznej` (wartość procentowa jest zbyt wysoka),
3. **Jeśli osiąganie docelowej temperatury jest zbyt wolne**, zwiększ `współczynnik delty dla temperatury wewnętrznej`, aby dostarczyć więcej mocy do ogrzewania,
4. **Jeśli osiąganie docelowej temperatury jest zbyt szybkie** i występują oscylacje wokół celu, zmniejsz `współczynnik delty dla temperatury wewnętrznej`, aby dostarczyć mniej mocy do grzejnika.

W trybie `Termostat na Zaworze`, wartość `procent` jest konwertowana na procent (0 do 100%) i bezpośrednio steruje stopniem otwarcia zaworu.

### Minimalna zwłoka aktywacji lub dezaktywacji

Pierwsze opóźnienie (`minimal_activation_delay_sec`), w sekundach, to minimalne dopuszczalne opóźnienie włączenia ogrzewania. Gdy wynik obliczeń daje czas włączenia krótszy, niż ta wartość, ogrzewanie pozostaje wyłączone. Jeśli czas aktywacji jest zbyt krótki, szybkie przełączanie nie pozwoli urządzeniu osiągnąć temperatury roboczej.

Podobnie, drugie opóźnienie (`minimal_deactivation_delay_sec`), również w sekundach, definiuje minimalny dopuszczalny czas wyłączenia. Jeśli czas wyłączenia jest krótszy, niż ta wartość, ogrzewanie nie zostanie wyłączone. Zapobiega to szybkiemu migotaniu, które przynosi niewielkie korzyści w regulacji temperatury.

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

## Algorytm autoSTART i autoSTOP

The algorithm used in the auto-start/stop function operates as follows:
1. If "Enable Auto-Start/Stop" is off, stop here.
2. If VTherm is on and in Heating mode, when `error_accumulated` < `-error_threshold` -> turn off and save HVAC mode.
3. If VTherm is on and in Cooling mode, when `error_accumulated` > `error_threshold` -> turn off and save HVAC mode.
4. If VTherm is off and the saved HVAC mode is Heating, and `current_temperature + slope * dt <= target_temperature`, turn on and set the HVAC mode to the saved mode.
5. If VTherm is off and the saved HVAC mode is Cooling, and `current_temperature + slope * dt >= target_temperature`, turn on and set the HVAC mode to the saved mode.
6. `error_threshold` is set to `10 (° * min)` for slow detection, `5` for medium, and `2` for fast.

`dt` is set to `30 min` for slow, `15 min` for medium, and `7 min` for fast detection levels.

The function is detailed [here](https://github.com/jmcollin78/versatile_thermostat/issues/585).
