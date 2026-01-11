# Użycie różnych algorytmów

- [Użycie różnych algorytmów](#użycie-różnych-algorytmów)
  - [Algorytm TPI](#algorytm-tpi)
    - [Konfigurowanie współczynników algorytmu TPI](#konfigurowanie-współczynników-algorytmu-tpi)
    - [Zasady](#zasady)
    - [Minimalna zwłoka aktywacji lub dezaktywacji](#minimalna-zwłoka-aktywacji-lub-dezaktywacji)
    - [Górne i dolne progi aktywacji algorytmu](#górne-i-dolne-progi-aktywacji-algorytmu)
  - [Algorytm autoregulacji (bez sterowania zaworem)](#algorytm-autoregulacji-bez-sterowania-zaworem)
  - [Algorytm autoSTART i autoSTOP](#algorytm-autostart-i-autostop)

## Algorytm TPI

TPI is applicable only for _VTherm_ which does the regulation itself. This kind of _VTherm_ is concerned:
1. `over_switch`,
2. `over_valve`,
3. `over_climate` with direct valve control.

`over_climate` with self-regulation that doesn't control the valve directly don't have any TPI algorithm embedded and thus this chapter is not applicable for them.

### Konfigurowanie współczynników algorytmu TPI

Jeśli wybrałeś typ termostatu `Na Przełączniku`, `Na Zaworze`, lub `Na Klimacie` z trybem autoregulacji  `Bezpośrednie sterowanie zaworem` i wybrałeś w menu opcję "TPI", znajdziesz się na tej stronie:

![image](images/config-tpi.png)

Musisz tutaj określić:

| Parametr | Opis | Nazwa atrybutu |
|----------|------|----------------|
| **Wewnętrzny współczynnik** | Współczynnik `współczynnik delty dla temperatury wewnętrznej` algorytmu TPI. | `tpi_coef_int` |
| **Zewnętrzny współczynnik** | Współczynnik `współczynnik delty dla temperatury zewnętrznej` algorytmu TPI. | `tpi_coef_ext` |
| **Opóźnienie aktywacji** | Minimalny czas aktywacji w sekundach. | `minimal_activation_delay` |
| **Opóźnienie deaktywacji** | Minimalny czas deaktywacji w sekundach. | `minimal_deactivation_delay` |
| **Górny próg** | Odchylenie temperatury (°C lub K), powyżej którego algorytm zostanie wyłączony. | `tpi_threshold_high` |
| **Dolny próg** | Odchylenie temperatury (°C lub K), poniżej którego algorytm zostanie ponownie włączony. | `tpi_threshold_low` |

### Zasady

Algorytm TPI oblicza procent załączenia/wyłączenia grzejnika w każdym cyklu, wykorzystując temperaturę docelową, aktualną temperaturę w pomieszczeniu i aktualną temperaturę zewnętrzną.

Procent ten obliczany jest na podstawie następującej formuły:

    procent = współczynnik_delty_dla_temperatury_wewnętrznej * (temperatura_docelowa - temperatura_aktuana) + współczynnik_delty_dla_temperatury_zewnętrznej * (temperatura_docelowa - temperatura_zewnętrzna)
    Następnie algorytm sprawdza warunek: 0 <= procent <= 1.

Domyślne wartości  `współczynnika delty dla temperatury wewnętrznej` i `współczynnika delty dla temperatury zewnętrznej` wynoszą odpowiednio `0.6` i `0.01`. Wartości te są odpowiednie dla pomieszczenia o dobrej izolacji termicznej.

Określając wartości współczynników, należy pamiętać, że:
1. **Jeśli docelowa temperatura nie zostanie osiągnięta** po stabilizacji, zwiększ `współczynnik delty dla temperatury wewnętrznej` (wartość procentowa jest zbyt niska),
2. **Jeśli docelowa temperatura zostanie przekroczona** po stabilizacji, zmniejsz `współczynnik delty dla temperatury zewnętrznej` (wartość procentowa jest zbyt wysoka),
3. **Jeśli osiąganie docelowej temperatury jest zbyt wolne**, zwiększ `współczynnik delty dla temperatury wewnętrznej`, aby dostarczyć więcej mocy do ogrzewania,
4. **Jeśli osiąganie docelowej temperatury jest zbyt szybkie** i występują oscylacje wokół celu, zmniejsz `współczynnik delty dla temperatury wewnętrznej`, aby dostarczyć mniej mocy do grzejnika.

Wartość `on_percent` jest konwertowana na procent (0 do 100%) i bezpośrednio steruje stopniem otwarcia zaworu.

### Minimalna zwłoka aktywacji lub dezaktywacji

Pierwsze opóźnienie (`minimal_activation_delay_sec`), w sekundach, to minimalne dopuszczalne opóźnienie włączenia ogrzewania. Gdy wynik obliczeń daje czas włączenia krótszy, niż ta wartość, grzejnik pozostaje wyłączony. Jeśli czas aktywacji jest zbyt krótki, szybkie przełączanie nie pozwoli urządzeniu osiągnąć temperatury roboczej.

Podobnie, drugie opóźnienie (`minimal_deactivation_delay_sec`), również w sekundach, definiuje minimalny dopuszczalny czas wyłączenia. Jeśli czas wyłączenia jest krótszy, niż ta wartość, grzejnik nie zostanie wyłączony. Zapobiega to szybkiemu migotaniu, które przynosi niewielkie korzyści w regulacji temperatury.

### Górne i dolne progi aktywacji algorytmu

Od wersji 7.4 dostępne są dwa dodatkowe progi aktywacji algorytmów. Pozwalają one wyłączyć (lub ponownie załączyć) sam algorytm TPI, w zależności od różnicy między temperaturą docelową a temperaturą aktualną.

- Jeśli temperatura rośnie i różnica jest większa, niż górny próg, grzejnik zostaje wyłączony (tj. `on_percent` ma wymuszoną wartość 0).
- Jeśli temperatura spada i różnica jest mniejsza, niż dolny próg, grzejnik zostaje ponownie załączony (tj. `on_percent` jest obliczany przez algorytm zgodnie z opisem powyżej).

Te dwa progi zatrzymują cykliczne włączanie/wyłączanie, gdy temperatura przekracza wartość docelową. Histereza zapobiega szybkiemu przełączaniu.

Przykłady:
1. Załóżmy, że docelowa temperatura ustawiona jest na 20°C, górny próg to 2°C, a dolny próg to 1°C.
2. Gdy temperatura wzrośnie powyżej 22°C (`temperatura docelowa` + `górny próg`), to `on_percent` ma wymuszoną wartość 0.
3. Gdy temperatura spadnie poniżej 21°C (`temperatura docelowa` + `dolny próg`), to `on_percent` zostaje ponownie obliczony przez algorytm.

> ![Tip](images/tips.png) _*Wskazówka*_
> 1. Pozostaw obie wartości równe 0, jeśli nie chcesz używać progów. Przywraca to zachowanie sprzed wersji 7.4.
> 2. Obie wartości są wymagane. Jeśli jedna pozostanie równa 0, żaden próg nie zostanie zastosowany. Faktycznie obie wartości są niezbędne do prawidłowego działania.
> 3. W trybie chłodzenia testy są odwrócone, ale zasada pozostaje taka sama.
> 4. Górny próg powinien zawsze być większy niż dolny próg, nawet w trybie chłodzenia.

## Algorytm autoregulacji (bez sterowania zaworem)

Algorytm samoregulacji można podsumować w następujący sposób:

1. Zainicjalizuj temperaturę docelową na termostacie VTherm,
2. Jeśli samoregulacja jest załączona:
    1. Oblicz temperaturę regulowaną (istotną dla teostatu VTherm),
    2. Użyj tej temperatury jako wartości docelowej,
3. Dla każdego urządzenia powiązanego z termostatem VTherm:
    1. Jeśli zaznaczono „Użyj temperatury wewnętrznej”:
        1. Oblicz kompensację (`trv_internal_temp` - `room_temp`),
    2. Dodaj offset do temperatury docelowej,
    3. Ustaw temperaturę docelową (= `regulated_temp` + (`internal_temp` - `room_temp`)) na urządzeniu powiązanym.

## Algorytm autoSTART i autoSTOP

Algorytm używany w funkcji autoSTART/STOP działa w następujący sposób:

1. Jeśli „AutoSTART/AutoSTOP” jest wyłączony, działanie funkcji zatrzymuje się.
2. Jeśli termostat VTherm jest załączony i pracuje w trybie ogrzewania, gdy `error_accumulated` < `-error_threshold` → wyłącz i zapisz tryb HVAC.
3  Jeśli termostat VTherm jest załączony i pracuje w trybie chłodzenia, gdy `error_accumulated` > `error_threshold` → wyłącz i zapisz tryb HVAC.
4. Jeśli termostat VTherm jest wyłączony, a zapisany tryb HVAC to `grzanie`, i `aktualna temperatura` + `slope` * `dt` <= `temperatura docelowa`, załącz i ustaw tryb HVAC jako zapisany.
5. Jeśli termostat VTherm jest wyłączony, a zapisany tryb HVAC to `chłodzenie`, i `aktuana temperatura` + `slope` * `dt` >= `temperatura docelowa`, załącz i ustaw tryb HVAC jako zapisany.
6. `error_threshold` jest ustawiony na `10 (° * min)` dla powolnej detekcji, `5` dla średniej detekcji oraz `2` dla szybkiej detekcji.

Parametr `dt` jest ustawiony na `30 minut` dla powolnego, na `15 minut` dla średniego, oraz na `7 minut` dla szybkiego tempa detekcji.

Szczegóły tej funkcji opisane są [tutaj](https://github.com/jmcollin78/versatile_thermostat/issues/585).
