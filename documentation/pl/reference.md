# Dokumentacja Referencyjna

- [Dokumentacja Referencyjna](#dokumentacja-referencyjna)
  - [Parametry](#parametry)
- [Sensory](#sensory)
- [Akcje (Usługi)](#akcje-usługi)
  - [Wymuszanie obecności/zajętości](#wymuszanie-obecnościzajętości)
  - [Modyfikacja presetów temperatury](#modyfikacja-presetów-temperatury)
  - [Modyfikacja ustawień bezpieczeństwa](#modyfikacja-ustawień-bezpieczeństwa)
  - [Pomijanie sprawdzania stanu okna](#pomijanie-sprawdzania-stanu-okna)
  - [Zmiana parametrów TPI](#zmiana-parametrów-tpi)
- [Zdarzenia](#zdarzenia)
- [Atrybuty własne](#atrybuty-własne)

## Parametry

| Parametr                                  | Nazwa                                                             | Termostat<br>na<br>Przełączniku | Termostat<br>na<br>Klimacie | Termostat<br>na<br>Zaworze | Konfiguracja<br>Centralna |
| ----------------------------------------- | ----------------------------------------------------------------- | ------------------------------ | -------------------------- | ------------------------- | --------------------------- |
| ``name``                                  | Nazwa                                                             | X                              | X                          | X                         | -                           |
| ``thermostat_type``                       | Typ termostatu                                                    | X                              | X                          | X                         | -                           |
| ``temperature_sensor_entity_id``          | Identyfikator encji sensora temperatury                           | X                              | X (auto-regulacja)         | X                         | -                           |
| ``external_temperature_sensor_entity_id`` | Identyfikator encji sensora temperatury zewnętrznej               | X                              | X (auto-regulacja)         | X                         | X                           |
| ``cycle_min``                             | Czas trwania cyklu (w min.)                                       | X                              | X                          | X                         | -                           |
| ``temp_min``                              | Minimalna dopuszczalna temperatura                                | X                              | X                          | X                         | X                           |
| ``temp_max``                              | Maksymalna dopuszczalna temperatura                               | X                              | X                          | X                         | X                           |
| ``device_power``                          | Moc urządzenia                                                    | X                              | X                          | X                         | -                           |
| ``use_central_mode``                      | Sterowanie centralne aktywne                                      | X                              | X                          | X                         | -                           |
| ``use_window_feature``                    | Z detekcją otwarcia okna                                          | X                              | X                          | X                         | -                           |
| ``use_motion_feature``                    | Z detekcją ruchu                                                  | X                              | X                          | X                         | -                           |
| ``use_power_feature``                     | Z zarządzaniem mocą                                               | X                              | X                          | X                         | -                           |
| ``use_presence_feature``                  | Z detekcją obecności                                              | X                              | X                          | X                         | -                           |
| ``heater_entity1_id``                     | 1-szy grzejnik                                                    | X                              | -                          | -                         | -                           |
| ``heater_entity2_id``                     | 2-gi grzejnik                                                     | X                              | -                          | -                         | -                           |
| ``heater_entity3_id``                     | 3-ci grzejnik                                                     | X                              | -                          | -                         | -                           |
| ``heater_entity4_id``                     | 4-ty grzejnik                                                     | X                              | -                          | -                         | -                           |
| ``heater_keep_alive``                     | Częstość odświerzania stanu                                       | X                              | -                          | -                         | -                           |
| ``proportional_function``                 | Algorytm                                                          | X                              | -                          | -                         | -                           |
| ``climate_entity1_id``                    | 1-szy termostat podstawowy                                        | -                              | X                          | -                         | -                           |
| ``climate_entity2_id``                    | 2-gi termostat podstawowy                                         | -                              | X                          | -                         | -                           |
| ``climate_entity3_id``                    | 3-ci termostat podstawowy                                         | -                              | X                          | -                         | -                           |
| ``climate_entity4_id``                    | 4-ty termostat podstawowy                                         | -                              | X                          | -                         | -                           |
| ``valve_entity1_id``                      | 1-szy zawór podstawowy                                            | -                              | -                          | X                         | -                           |
| ``valve_entity2_id``                      | 2-gi zawór podstawowy                                             | -                              | -                          | X                         | -                           |
| ``valve_entity3_id``                      | 3-ci zawór podstawowy                                             | -                              | -                          | X                         | -                           |
| ``valve_entity4_id``                      | 4-ty zawór podstawowy                                             | -                              | -                          | X                         | -                           |
| ``ac_mode``                               | Tryb AC                                                           | X                              | X                          | X                         | -                           |
| ``tpi_coef_int``                          | Współczynnik delta temperatury wewnętrznej                        | X                              | -                          | X                         | X                           |
| ``tpi_coef_ext``                          | Współczynnik delta temperatury zewnętrznej                        | X                              | -                          | X                         | X                           |
| ``frost_temp``                            | Temperatura antyzamarzania                                        | X                              | X                          | X                         | X                           |
| ``window_sensor_entity_id``               | Identyfikator encji sensora okna                                  | X                              | X                          | X                         | -                           |
| ``window_delay``                          | Zwłoka w wyłączeniu (w sek.)                                      | X                              | X                          | X                         | X                           |
| ``window_auto_open_threshold``            | Górny próg automatycznej detekcji otwarcia okna (°/min)           | X                              | X                          | X                         | X                           |
| ``window_auto_close_threshold``           | Dolny próg automatycznej detekcji zamknięcia okna (°/min)         | X                              | X                          | X                         | X                           |
| ``window_auto_max_duration``              | Maksymalny czas trwania automatycznego wyłączenia (w min.)        | X                              | X                          | X                         | X                           |
| ``motion_sensor_entity_id``               | Identyfikator encji sensora ruchu                                 | X                              | X                          | X                         | -                           |
| ``motion_delay``                          | Zwłoka początku detekcji ruchu (w sek.)                           | X                              | X                          | X                         | -                           |
| ``motion_off_delay``                      | Zwłoka końca detekcji ruchu (w sek.)                              | X                              | X                          | X                         | X                           |
| ``motion_preset``                         | Preset po wykryciu początku ruchu                                 | X                              | X                          | X                         | X                           |
| ``no_motion_preset``                      | Preset po wykryciu końca ruchu                                    | X                              | X                          | X                         | X                           |
| ``power_sensor_entity_id``                | Identyfikator encji sensora mocy                                  | X                              | X                          | X                         | X                           |
| ``max_power_sensor_entity_id``            | Identyfikator encji sensora mocy maksymalnej                      | X                              | X                          | X                         | X                           |
| ``power_temp``                            | Temperatura podczas redukcji mocy                                 | X                              | X                          | X                         | X                           |
| ``presence_sensor_entity_id``             | Identyfikator encji sensora obecności (`true`=obecność)           | X                              | X                          | X                         | -                           |
| ``minimal_activation_delay``              | Minimalna zwłoka aktywacji                                        | X                              | -                          | -                         | X                           |
| ``minimal_deactivation_delay``            | Minimalna zwłoka deaktywacji                                      | X                              | -                          | -                         | X                           |
| ``safety_delay_min``                      | Maksymalna zwłoka między dwoma pomiarami temperatury              | X                              | -                          | X                         | X                           |
| ``safety_min_on_percent``                 | Procent mocy minimalnej do przejścia w tryb bezpieczny            | X                              | -                          | X                         | X                           |
| ``auto_regulation_mode``                  | Tryb samoregulacji                                                | -                              | X                          | -                         | -                           |
| ``auto_regulation_dtemp``                 | Próg samoregulacji                                                | -                              | X                          | -                         | -                           |
| ``auto_regulation_period_min``            | Minimalny czas samoregulacji                                      | -                              | X                          | -                         | -                           |
| ``inverse_switch_command``                | Przełącznk inwersji polecenia (przełączanie przewodem sterującym) | X                              | -                          | -                         | -                           |
| ``auto_fan_mode``                         | Automatyczny tryb wentylacji                                      | -                              | X                          | -                         | -                           |
| ``auto_regulation_use_device_temp``       | Temperatura wewnętrzna (własna) urządzenia                        | -                              | X                          | -                         | -                           |
| ``use_central_boiler_feature``            | Dodanie sterowania kotłem głównym                                 | -                              | -                          | -                         | X                           |
| ``central_boiler_activation_service``     | Usługa aktywacji kotła                                            | -                              | -                          | -                         | X                           |
| ``central_boiler_deactivation_service``   | Usługa deaktywacji kotła                                          | -                              | -                          | -                         | X                           |
| ``central_boiler_activation_delay_sec``   | Zwłoka załączenia (w sekundach)                                   | -                              | -                          | -                         | X                           |
| ``used_by_controls_central_boiler``       | Wskaźnik sterowania kotła termostatem                             | X                              | X                          | X                         | -                           |
| ``use_auto_start_stop_feature``           | Wskażnik załączenia funkcji autoSTART/autoSTOP                    | -                              | X                          | -                         | -                           |
| ``auto_start_stop_level``                 | Poziom detekcji autoSTART/autoSTOP                                | -                              | X                          | -                         | -                           |

# Sensory

W termostacie dostępne są sensory wizualizujące alerty i stan wewnętrzny samego termostatu. Są one dostępne w encjach urządzenia powiązanych z termostatem:

![image](images/thermostat-sensors.png)

Są to kolejno:
1. główna encja `climate` do sterowania termostatem,
2. encja umożliwiająca funkcję autoSTART/autoSTOP,
3. encja umożliwiająca termostatowi śledzenie zmian w urządzeniu głównym,
4. energia zużyta przez termostat (wartość stale rosnąca),
5. czas ostatniego odczytu temperatury zewnętrznej,
6. czas ostatniego odczytu temperatury wewnętrznej,
7. średnia moc urządzenia w cyklu (tylko dla TPI),
8. czas trwania stanu wyłączenia podczas cyklu (tylko TPI),
9. czas trwania stanu załączenia podczas cyklu (tylko TPI),
10. stan redukcji obciążenia,
11. procent mocy w trakcie cyklu (tylko TPI),
12. stan obecności (jeśli skonfigurowano zarządzanie obecnością),
13. stan bezpieczeństwa,
14. stan okna (jeśli skonfigurowano zarządzanie oknem),
15. stan ruchu (jeśli skonfigurowano zarządzanie ruchem),
16. procent otwarcia zaworu (dla typu `termostat na zaworze`),

Dostępność tych encji zależy od tego, czy odpowiednia funkcja została załączona.

Aby nadać kolory poszczególnym sensorom, w pliku `configuration.yaml` dodaj poniższe linie kodu , dostosowując je według własnych potrzeb:

```yaml
frontend:
  themes:
    versatile_thermostat_theme:
      state-binary_sensor-safety-on-color: "#FF0B0B"
      state-binary_sensor-power-on-color: "#FF0B0B"
      state-binary_sensor-window-on-color: "rgb(156, 39, 176)"
      state-binary_sensor-motion-on-color: "rgb(156, 39, 176)"
      state-binary_sensor-presence-on-color: "lightgreen"
      state-binary_sensor-running-on-color: "orange"
```

...i wybierz motyw ```versatile_thermostat_theme``` w panelu konfiguracyjnym, a otrzymasz następujący (lub podobny) efekt:

![image](images/colored-thermostat-sensors.png)

# Akcje (Usługi)

Ta niestandardowa implementacja oferuje określone akcje (usługi), ułatwiające integrację z innymi komponentami Home Assistanta.

## Wymuszanie obecności/zajętości
Ta usługa umożliwia wymuszenie stanu obecności niezależnie od czujnika obecności. Może to być przydatne, jeśli chcesz zarządzać obecnością za pośrednictwem usługi, a nie czujnika. Na przykład, możesz użyć alarmu do wymuszenia nieobecności, gdy ten jest włączony.

Kod wywołujący tę akcję jest następujący:

```yaml
service : versatile_thermostat.set_presence
Les données:
    présence : "off"
cible:
    entity_id : climate.my_thermostat
```

## Modyfikacja presetów temperatury
Ta usługa jest przydatna, jeśli chcesz dynamicznie zmieniać temperaturę w presecie. Zamiast przełączać ustawienia, w niektórych przypadkach konieczne jest modyfikowanie temperatury w samym ustawieniu. Dzięki temu możesz pozostawić harmonogram bez zmian, aby zarządzał presetem, jednocześnie dostosowując jego temperaturę. Jeśli zmodyfikowane ustawienie jest aktualnie wybrane, zmiana temperatury docelowej następuje natychmiast i zostanie uwzględniona w następnym cyklu obliczeniowym.

Możesz zmodyfikować jedną lub obie temperatury (dla obecności lub nieobecności) każdego z ustawień.

Użyj poniższego kodu, aby ustawić temperaturę:
```yaml
service: versatile_thermostat.set_preset_temperature
data:
    preset: boost
    temperature: 17.8
    temperature_away: 15
target:
    entity_id: climate.my_thermostat
```

...lub, aby zmienić ustawienie dla trybu `AC`, dodaj sufiks `_ac` do nazwy ustawienia, jak w przykładzie:
```yaml
service: versatile_thermostat.set_preset_temperature
data:
    preset: boost_ac
    temperature: 25
    temperature_away: 30
target:
    entity_id: climate.my_thermostat
```

> ![Tip](images/tips.png) _*Wskazówki*_
>
>    - Po ponownym uruchomieniu presety zostaną zresetowane do skonfigurowanej temperatury. Aby zmiana była trwała, należy zmodyfikować presety w konfiguracji integracji.

## Modyfikacja ustawień bezpieczeństwa
Usługa ta umożliwia dynamiczną modyfikację ustawień bezpieczeństwa, opisanych tutaj: [Zaawansowana konfiguracja](#advanced-configuration).
Jeśli termostat jest w trybie ``bezpiecznym``, nowe ustawienia zostaną zastosowane natychmiast.

Aby zmienić ustawienia bezpieczeństwa, zastosuj poniższy kod:
```yaml
service: versatile_thermostat.set_safety
data:
    min_on_percent: "0.5"
    default_on_percent: "0.1"
    delay_min: 60
target:
    entity_id: climate.my_thermostat
```

## Pomijanie sprawdzania stanu okna
Usługa ta umożliwia dynamiczne załączanie i wyłączanie funkcji pomijania stanu otwarcia okien (lub drzwi). To z kolei pozwala termostatom kontynuować grzanie nawet w sytuacji wykrycia otwarcia okna.
Przy wartości ``true``, zmiany stanu okna nie będą wpływały na termostat. Przy wartości ``false``, termostat zostanie wyłączony, jeśli okno będzie nadal otwarte.

Aby zmienić ustawienie pomijania stanu otwarcia okna, zastosuj poniższy kod:
```yaml
service: versatile_thermostat.set_window_bypass
data:
    bypass: true
target:
    entity_id: climate.my_thermostat
```

## Zmiana parametrów TPI
Wszystkie konfigurowalne parametry TPI mogą być modyfikowane poprzez wywołanie akcji (usługi): `versatile_thermostat.set_tpi_parameters`. Zmiany te są trwałe i pozostają zachowane także po ponownym uruchomieniu. Są one stosowane niezwłocznie, a aktualizacja termostatu jest wykonywana natychmiast, w chwili zmiany wartości któregokolwiek z tych parametrów.

Każdy parametr jest opcjonalny. Jeśli któryś z parametrów nie zostanie podany, zachowywana jest jego dotychczasowa wartość.

Oto przykładowy kod zmiany parametrów TPI za pomoca wspomnianej akcji (usługi):

```yaml
action: versatile_thermostat.set_tpi_parameters
data:
  tpi_coef_int: 0.5
  tpi_coef_ext: 0.01
  minimal_activation_delay: 10
  minimal_deactivation_delay: 10
  tpi_threshold_low: -2
  tpi_threshold_high: 5
target:
  entity_id: climate.sonoff_trvzb
```

# Zdarzenia
Kluczowe zdarzenia z udziałem termostatów wywołują pojawienie się powiadomień za pośrednictwem magistrali komunikacyjnej.
Powiadomienia dotyczą następujących zdarzeń:

- ``versatile_thermostat_safety_event``: termostat wchodzi lub wychodzi z ustawień `bezpieczeństwo`
- ``versatile_thermostat_power_event``: termostat wchodzi lub wychodzi z ustawień `moc`
- ``versatile_thermostat_temperature_event``: co najmniej jeden z pomiarów temperatury termostatu nie został zaktualizowany przez ponad `safety_delay_min` minut.
- ``versatile_thermostat_hvac_mode_event``: termostat jest włączany lub wyłączany. To zdarzenie jest również raportowane podczas uruchamiania termostatu.
- ``versatile_thermostat_preset_event``: w termostacie wybrano nowy preset. To zdarzenie jest również raportowane podczas uruchamiania termostatu.
- ``versatile_thermostat_central_boiler_event``: zdarzenie zmiany stanu kotła
- ``versatile_thermostat_auto_start_stop_event``: zdarzenie zatrzymania lub ponownego uruchomienia wykonane przez funkcję autoSTART/autoSTOP

Gdy termostat przełącza się w tryb bezpieczny, wyzwalane są 3 zdarzenia:
1. ``versatile_thermostat_temperature_event`` – wskazuje, że termometr przestał odpowiadać,
2. ``versatile_thermostat_preset_event`` – wskazuje przełączenie na ustawienie trybu `bezpiecznego`,
3. ``versatile_thermostat_hvac_mode_event`` – wskazuje potencjalne wyłączenie termostatu.

Każde zdarzenie przechowuje kluczowe wartości zdarzenia (temperatury, aktualne ustawienia, bieżącą moc) oraz stany termostatu.
Możesz łatwo przechwytywać te zdarzenia w automatyzacji, na przykład w celu powiadamiania użytkowników.

# Atrybuty własne

Aby dostosować algorytm, masz dostęp do całego kontekstu widzianego i obliczanego przez termostat za pośrednictwem dedykowanych atrybutów. Możesz przeglądać (i używać) te atrybuty w sekcji `Narzędzia deweloperskie -> Stany` w Home Assistant. Wprowadź swój termostat, a zobaczysz:

![image](images/dev-tools-climate.png)

### Atrybuty własne są następujace:

| Atrybut                            | Znaczenie                                                                                                           |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| ``hvac_modes``                     | Lista trybów obsługiwanych przez termostat                                                                          |
| ``temp_min``                       | Temperatura minimana                                                                                                |
| ``temp_max``                       | Temperatura maksymalna                                                                                              |
| ``target_temp_step``               | Krok temperatury docelowej                                                                                          |
| ``preset_modes``                   | Preset dostępny dla termostatu. Ukryte ustawienia nie są tu wyświetlane.                                            |
| ``current_temperature``            | Aktualna temperatura raportowana przez czujnik                                                                      |
| ``temperature``                    | Temperatura docelowa                                                                                                |
| ``action_hvac``                    | Akcja aktualnie wykonywana przez grzejnik. Może być `idle` lub `heating`.                                           |
| ``preset_mode``                    | Aktualnie wybrany preset. Może być jednym z `preset_modes` lub ukrytym presetem, np. `moc`                          |
| ``hvac_mode``                      | Aktualnie wybrany tryb. Może być jednym z następujących: `heat`, `cool`, `fan_only`, lub `off`                      |
| ``friendly_name``                  | Przyjazna nazwa termostatu                                                                                          |
| ``supported_features``             | Wszystkie funkcjonalności tego termostatu. Sprawdź oficjalną integrację `climate`, aby dowiedzieć się więcej        |
| ``is_presence_configured``         | Wskaźnik konfiguracji detekcji obecności                                                                            |
| ``is_power_configured``            | Wskaźnik konfiguracji funkcji redukcji mocy                                                                         |
| ``is_motion_configured``           | Wskaźnik konfiguracji detekcji ruchu                                                                                |
| ``is_window_configured``           | Wskaźnik konfiguracji detekcji okna przez sensor                                                                    |
| ``is_window_auto_configured``      | Wskaźnik konfiguracji detekcji okna przez spadek temperatury                                                        |
| ``is_safety_configured``           | Wskaźnik konfiguracji detekcji spadku temperatury                                                                   |
| ``is_auto_start_stop_configured``  | Wskaźnik konfiguracji funkcji autoSTART / autoSTOP (tylko dla `termostatu na klimacie`)                             |
| ``is_over_switch``                 | Wskaźnik typu termostatu VTherm `termostat na przełączniku`                                                         |
| ``is_over_valve``                  | Wskaźnik typu termostatu VTherm `termostat na zaworze`                                                              |
| ``is_over_climate``                | Wskaźnik typu termostatu VTherm `termostat na klimacie`                                                          |
| ``is_over_climate_valve``          | Wskaźnik typu termostatu VTherm `termostat na klimacie` z kontrolą zaworu        |
| **SEKCJA `specyficzne stany`**     | ------                                                                                                              |
| ``is_on``                                       | `prawda` jeśli termostat jest załączony (stan `hvac_mode` inny niż `Off`)                              |
| ``last_central_mode``                           | Ostatnio użyty tryb centralnego starowania (`brak` jeśli termostat nie jest sterowany centralnie)      |
| ``last_update_datetime``                        | Data i czas w formacie ISO8866 dla trybu centralnego sterowania                                        |
| ``ext_current_temperature``                     | Aktualna temperatura zewnętrzna                                                                        |
| ``last_temperature_datetime``                   | Data i czas w formacie ISO8866 dla ostatniego odczytu temperatury wewnętrznej                          |
| ``last_ext_temperature_datetime``               | Data i czas w formacie ISO8866 dla ostatniego odczytu temperatury zewnętrznej                          |
| ``is_device_active``                            | `prawda`, jeśli urządzenie jest aktywne                                                                |
| ``device_actives``                              | Lista aktualnie aktywnych urządzeń                                                                     |
| ``nb_device_actives``                           | Ilość aktualnie aktywnych urządzeń                                                                     |
| ``ema_temp``                                    | Bieżąca temperatura uśredniona, obliczana jako ruchoma średnia wykładnicza z poprzednich wartości. Służy do obliczania kąta nachylenia krzywej temperatur.  |
| ``temperature_slope``                           | Kąt nachylenia aktualnej temperatury w `°/godz`                                                                                                                                                                         |
| ``hvac_off_reason``                             | Przyczyna wyłączenia termostatu (`hvac_off`). Może być to: `okno`, `AutoSTART/autoSTOP` lub `Manual`     |
| ``total_energy``                                | Łączna energia zużyta przez termostat VTherm                                               |
| ``last_change_time_from_vtherm``                | Data i czas ostatniej zmiany dokonanej przez termostat VTherm                                          |
| ``messages``                                    | Lista komunikatów wyjaśniających obliczenie aktualnej wartości. Patrz: [Komunikaty](#state-messages)    |
| ``is_sleeping``                                 | Wskaźnik trybu uśpienia termostatu (tylko dla `termostatu na klimacie` z kontrolą zaworu)              |
| ``is_recalculate_scheduled``                    | Wskaźnik zwłoki dla powtórnych obliczeń wartości, spowodowanego przez filtrowanie czasu w celu ograniczenia liczby interakcji z urządzeniem   |
| **SEKCJA `konfiguracje`**                       | ------                                                                                                 |
| ``ac_mode``                                     | `prawda` jeśli urządzenie wspiera tryb `chłodzenia` oraz `grzania`                                     |
| ``type``                                        | Typ termostatu VTherm (`termostat na przełączniku, termostat na zaworze, termostat na klimacie`, czy `termostat na klimacie z kontrolą zaworu`) |
| ``is_controlled_by_central_mode``               | `prawda`, jeśli termostat jest sterowany centralnie                                                    |
| ``target_temperature_step``                     | Krok temperatury docelowej (tożsame z `target_temp_step`)                                              |
| ``minimal_activation_delay_sec``                | Minimalna zwłoka aktywacji (w sek.). Używana jest tylko w TPI                                          |
| ``minimal_deactivation_delay_sec``              | Minimalna zwłoka deaktywacji (w sek.) Używana test tylko w TPI                                         |
| ``timezone``                                    | Strefa czasowa używana w znacznikach czasu                                                             |
| ``temperature_unit``                            | Jednostka temperatury                                                                                  |
| ``is_used_by_central_boiler``                   | Wskaźnik sterowania kotłem centralnym przez termostat VTherm                                           |
| ``max_on_percent``                              | Maksymalny procent mocy. Używany tylko w TPI                                                           |
| ``have_valve_regulation``                       | Wskaźnik regulacji termostatu zaworem (`termostat na klimacie` ze sterowaniem zaworu)                  |
| ``cycle_min``                                   | Czas trwania cyklu (w min.)                                                                            |
| **SEKCJA `presety temperatur`**                 | ------                                                                                                 |
| ``[eco/confort/boost]_temp``       | Temperatura skonfigurowana dla wybranego presetu                                                                    |
| ``[eco/confort/boost]_away_temp``  | Temperatura skonfigurowana dla wybranego presetu , gdy `obecność` jest wyłączona lub ma wartość `not_home`.         |
| ``temp_power``                     | Temperatura używana podczas wykrywania utraty sygnału                                                               |
| ``on_percent``                     | Obliczony procent włączenia przez algorytm TPI                                                                      |
| ``on_time_sec``                    | Okres załączenia (w sek.). Powinien wynosić ```on_percent * cycle_min```                                            |
| ``off_time_sec``                   | Okres wyłączenia (w sek.). Powinien wynosić ```(1 - on_percent) * cycle_min```                                      |
| ``cycle_min``                      | Cykl obliczeniowy (w min.)                                                                                          |
| ``function``                       | Algorytm używany do obliczeń cyklu                                                                                  |
| ``tpi_coef_int``                   | Wartość `współczynnika delty dla temperatury wewnętrznej` algorytmu TPI                                             |
| ``tpi_coef_ext``                   | Wartość `współczynnika delty dla temperatury zewnętrznej` algorytmu TPI                                             |
| ``saved_preset_mode``              | Ostatnio użyty preset przed automatycznym przełączeniem                                                             |
| ``saved_target_temp``              | Ostatnia temperatura użyta przed automatycznym przełączeniem                                                        |
| ``window_state``                   | Ostatni znany stan czujnika okna. `Brak`, jeśli czujnik nie jest skonfigurowany                                     |
| ``is_window_bypass``               | `True`, jeśli pomijanie detekcji otwartego okna jest załączone                                                      |
| ``motion_state``                   | Ostatni znany stan czujnika ruchu. `Brak`, jeśli detekcja ruchu nie jest skonfigurowana                             |
| ``overpowering_state``             | Ostatni znany stan czujnika przeciążenia. `Brak`, jeśli zarządzanie energią nie jest skonfigurowane                 |
| ``presence_state``                 | Ostatni znany stan czujnika obecności. `Brak`, jeśli detekcja obecności nie jest skonfigurowana                     |
| ``safety_delay_min``               | Zwłoka w aktywacji trybu bezpiecznego, gdy jeden z dwóch czujników temperatury przestaje wysyłać pomiary            |
| ``safety_min_on_percent``          | Procent grzania, poniżej którego termostat nie przełączy się w tryb bezpieczny                                      |
| ``safety_default_on_percent``      | Procent grzania używany, gdy termostat pracuje w trybie bezpiecznym                                                 |
| ``last_temperature_datetime``      | Data i czas ostatniego odczytu temperatury wewnętrznej (w formacie ISO8866)                                         |
| ``last_ext_temperature_datetime``  | Data i czas ostatniego odczytu temperatury zewnętrznej (w formacie ISO8866)                                         |
| ``safety_state``                   | Stan bezpieczny. `True` lub `false`                                                                                 |
| ``minimal_activation_delay_sec``   | Minimalna zwłoka aktywacji (w sek.)                                                                             |
| ``minimal_deactivation_delay_sec`` | Minimalna zwłoka deaktywacji (w sek.)                                                                           |
| ``last_update_datetime``           | Data i czas wartości stanu (w formacie ISO8866)                                                                         |
| ``friendly_name``                  | Przyjazna nazwa termostatu                                                                                          |
| ``supported_features``             | Lista wszystkich funkcji obsługiwanych przez termostat. Zobacz dokumentację, aby uzyskać więcej informacji |
| ``valve_open_percent``             | Procent otwarcia zaworu                                                                                             |
| ``regulated_target_temperature``   | Temperatura docelowa obliczona przez samoregulację                                                                  |
| ``is_inversed``                    | `True`, jeśli sterowanie jest odwrócone (dotyczy sterowania przewodowego z diodą)                                   |
| ``is_controlled_by_central_mode``  | `True`, jeśli termostat może być sterowany centralnie                                                               |
| ``last_central_mode``              | Ostatni użyty tryb centralny (`None`, jeśli termostat nie jest sterowany centralnie)                                |
| ``is_used_by_central_boiler``      | Wskazuje, czy termostat może sterować centralnym kotłem                                                             |
| ``auto_start_stop_enable``         | Wskazuje, czy termostat może pracować w trybie autoSTART/autoSTOP                                                   |
| ``auto_start_stop_level``          | Wskazuje poziom autoSTAR/autoSTOP                                                                                   |
| ``hvac_off_reason``                | Wskazuje powód wyłączenia termostatu (`hvac_off`). Może to być `Window`, `AutoSTART/autoSTOP` lub `Manual`          |
| ``last_change_time_from_vtherm``   | Data i czas ostatniej zmiany dokonanej przez termostat                                                              |
| ``nb_device_actives``              | Liczba urządzeń podrzędnych widocznych jako aktywne                                                                 |
| ``device_actives``                 | Lista urządzeń podrzędnych widocznych jako aktywne                                                                  |


## Atrybuty własne dla konfiguracji centralnej

Atrybuty własne w konfiguracji centralnej są dostepne w panelu _Narzędzia deweloperskie -> Stany_ w sensorze `binary_sensor.central_boiler`:

| Atrybut                                     | znaczenie                                                                            |
| ------------------------------------------- | ------------------------------------------------------------------------------------ |
| ``central_boiler_state``                    | Stan kotła centralnego. Może być `on` lub `off`                                      |
| ``is_central_boiler_configured``            | Wkaźnik konfiguracji funkcji kotła centralnego                           |
| ``is_central_boiler_ready``                 | Wskaźnik gotowości kotła centralnego                                        |
| **SEKCJA `zarządzanie kotłem centralnym`**  | ------                                                                               |
| ``is_on``                                   | `prawda` jeśli kocioł centralny jest załączony                                       |
| ``activation_scheduled``                    | `prawda` jeśli aktywacja kotła centralnego została ustawiona (patrz: `central_boiler_activation_delay_sec`) |
| ``delayed_activation_sec``                  | Zwłoka aktywacji kotła centralnego (w sek.)                                              |
| ``nb_active_device_for_boiler``             | Liczba aktywnych urządzeń sterujących kotłem centralnym                              |
| ``nb_active_device_for_boiler_threshold``   | Próg ilości aktywnych urządzeń przed aktywacją kotła centralnego                     |
| ``total_power_active_for_boiler``           | Łączna moc wszystkich urządzeń sterujących kotłem centralnym                           |
| ``total_power_active_for_boiler_threshold`` | Próg łącznej mocy urządzeń przed aktywacją kotła centralnego                         |
| **SEKCJA `aktywacja usług`**                | ------                                                                               |
| ``service_domain``                          | Domena urządzenia aktywującego (np. `switch`)                                  |
| ``service_name``                            | Nazwa usługi aktywującej (np. `turn_on`)                                   |
| ``entity_domain``                           | Domena sensora kontrolującego kocioł centralny (np. `switch`)                       |
| ``entity_name``                             | Nazwa sensora kontrolującego kocioł centralny                                        |
| ``entity_id``                               | Identyfikator encji kontrolującej kocioł centralny                         |
| ``data``                                    | Dodatkowe dane przesyłane do usługi aktywującej                                     |
| **SEKCJA `deaktywacja usług`**              | ------                                                                               |
| ``service_domain``                          | Domena urządzenia deaktywującego (np. `switch`)                                |
| ``service_name``                            | Nazwa usługi deaktywującej (np. `turn_off`)                                  |
| ``entity_domain``                           | Domena sensora kontrolującego kocioł centralny (np. `switch`)                       |
| ``entity_name``                             | Nazwa sensora kontrolującego kocioł centralny                                        |
| ``entity_id``                               | Identyfikator encji kontrolującej kocioł centralny                       |
| ``data``                                    | Dodatkowe dane przesyłane do usługi deaktywującej                                   |

Przykładowe warości:

```yaml
central_boiler_state: "off"
is_central_boiler_configured: true
is_central_boiler_ready: true
central_boiler_manager:
  is_on: false
  activation_scheduled: false
  delayed_activation_sec: 10
  nb_active_device_for_boiler: 1
  nb_active_device_for_boiler_threshold: 3
  total_power_active_for_boiler: 50
  total_power_active_for_boiler_threshold: 500
  service_activate:
    service_domain: switch
    service_name: turn_on
    entity_domain: switch
    entity_name: controle_chaudiere
    entity_id: switch.controle_chaudiere
    data: {}
  service_deactivate:
    service_domain: switch
    service_name: turn_off
    entity_domain: switch
    entity_name: controle_chaudiere
    entity_id: switch.controle_chaudiere
    data: {}
device_class: running
icon: mdi:water-boiler-off
friendly_name: Central boiler
```

Te atrybuty należy podać w przypadku prośby o pomoc techniczną.

# Komunikaty

Sensor `specific_states.messages` zawiera listę kodów komunikatów, wyjaśniających aktualny stan. Oto lista możliwych komunikatów:

| Code                                | Meaning                                                                             |
| ----------------------------------- | ----------------------------------------------------------------------------------- |
| `overpowering_detected`             | Wykryto przekroczenie mocy                                                          |
| `safety_detected`                   | Błąd pomiaru temperatury skutkujący przejściem do trybu _bezpiecznego_             |
| `target_temp_window_eco`            | Preset `Eko` zmieniający temperaturę docelową, wymuszony detekcją otwarcia okna     |
| `target_temp_window_frost`          | Preset `Mróz` zmieniający temperaturę docelową, wymuszony detekcją otwarcia okna    |
| `target_temp_power`                 | Redukcja mocy wymuszona temperaturą docelową skonfigurowaną dla potrzeb redukcji mocy |
| `target_temp_central_mode`          | Wymuszenie temperatury doceowej przez tryb centralny                                   |
| `target_temp_activity_detected`     | Wymuszenie temperatury doceowej detekcją ruchu                                      |
| `target_temp_activity_not_detected` | Wymuszenie temperatury doceowej detekcją braku ruchu                                |
| `target_temp_absence_detected`      | Wymuszenie temperatury doceowej brakiem obecności                                   |

> ![Tip](images/tips.png) _*Wskazówka*_
>
>    Komunikaty te są widoczne na karcie [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card) pod ikoną informacyjną.
> 
