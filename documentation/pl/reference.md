# Dokumentacja Referencyjna

- [Dokumentacja Referencyjna](#reference-documentation)
  - [Parametry](#parameter-summary)
- [Sensory](#sensors)
- [Akcje (Usługi)](#actions-services)
  - [Wymuszanie obecności/zajętości](#force-presenceoccupation)
  - [Modykacja presetów temperatury](#modify-the-preset-temperature)
  - [Modikacja ustawień bezpieczeństwa](#modify-security-settings)
  - [Pomijanie sprawdzania stanu okna](#bypass-window-check)
- [Zdarzenia](#events)
- [Atrybuty własne](#custom-attributes)

## Parametry

| Parametr                                  | Nazwa                                                       | "Termostat<br>na Przełączniku" | "Termostat<br>na<br>Klimacie"      | "Termostat<br>na Zaworze" | "Główna<br>konfiguracja" |
| ----------------------------------------- | ----------------------------------------------------------- | ------------- | ------------------- | ------------ | ----------------------- |
| ``name``                                  | Nazwa                                                       | X             | X                   | X            | -                       |
| ``thermostat_type``                       | Typ termostatu                                              | X             | X                   | X            | -                       |
| ``temperature_sensor_entity_id``          | Identyfikator encji sensora temperatury                     | X             | X (auto-regulacja) | X            | -                       |
| ``external_temperature_sensor_entity_id`` | Identyfikator encji sensora temperatury zewnętrznej         | X             | X (auto-regulacja) | X            | X                       |
| ``cycle_min``                             | Czas trwania cyklu (w min.)                                 | X             | X                   | X            | -                       |
| ``temp_min``                              | Minimalna dopuszczalna temperatura                          | X             | X                   | X            | X                       |
| ``temp_max``                              | Maksymalna dopuszczalna temperatura                         | X             | X                   | X            | X                       |
| ``device_power``                          | Moc urządzenia                                              | X             | X                   | X            | -                       |
| ``use_central_mode``                      | Sterowanie centralne aktywne                                | X             | X                   | X            | -                       |
| ``use_window_feature``                    | Z detekcją otwarcia okna                                    | X             | X                   | X            | -                       |
| ``use_motion_feature``                    | Z detekcją ruchu                                            | X             | X                   | X            | -                       |
| ``use_power_feature``                     | Z zarządzaniem mocą                                         | X             | X                   | X            | -                       |
| ``use_presence_feature``                  | Z detekcją obecności                                        | X             | X                   | X            | -                       |
| ``heater_entity1_id``                     | 1-szy grzejnik                                              | X             | -                   | -            | -                       |
| ``heater_entity2_id``                     | 2-gi grzejnik                                               | X             | -                   | -            | -                       |
| ``heater_entity3_id``                     | 3-ci grzejnik                                               | X             | -                   | -            | -                       |
| ``heater_entity4_id``                     | 4-ty grzejnik                                               | X             | -                   | -            | -                       |
| ``heater_keep_alive``                     | Częstość odświerzania stanu                                 | X             | -                   | -            | -                       |
| ``proportional_function``                 | Algorytm                                                    | X             | -                   | -            | -                       |
| ``climate_entity1_id``                    | 1-szy termostat podstawowy                                  | -             | X                   | -            | -                       |
| ``climate_entity2_id``                    | 2-gi termostat podstawowy                                   | -             | X                   | -            | -                       |
| ``climate_entity3_id``                    | 3-ci termostat podstawowy                                   | -             | X                   | -            | -                       |
| ``climate_entity4_id``                    | 4-ty termostat podstawowy                                   | -             | X                   | -            | -                       |
| ``valve_entity1_id``                      | 1-szy zawór podstawowy                                      | -             | -                   | X            | -                       |
| ``valve_entity2_id``                      | 2-gi zawór podstawowy                                       | -             | -                   | X            | -                       |
| ``valve_entity3_id``                      | 3-ci zawór podstawowy                                       | -             | -                   | X            | -                       |
| ``valve_entity4_id``                      | 4-ty zawór podstawowy                                       | -             | -                   | X            | -                       |
| ``ac_mode``                               | Tryb AC                                                     | X             | X                   | X            | -                       |
| ``tpi_coef_int``                          | Współczynnik delta temperatury wewnętrznej                  | X             | -                   | X            | X                       |
| ``tpi_coef_ext``                          | Współczynnik delta temperatury zewnętrznej                  | X             | -                   | X            | X                       |
| ``frost_temp``                            | Temperatura antyzamarzania                                  | X             | X                   | X            | X                       |
| ``window_sensor_entity_id``               | Identyfikator encji sensora okna                            | X             | X                   | X            | -                       |
| ``window_delay``                          | Zwłoka w wyłączeniu (w sek.)                                | X             | X                   | X            | X                       |
| ``window_auto_open_threshold``            | Górny próg automatycznej detekcji otwarcia okna (°/min)     | X             | X                   | X            | X                       |
| ``window_auto_close_threshold``           | Dolny próg automatycznej detekcji zamknięcia okna (°/min)   | X             | X                   | X            | X                       |
| ``window_auto_max_duration``              | Maksymalny czas trwania automatycznego wyłączenia (w min.)  | X             | X                   | X            | X                       |
| ``motion_sensor_entity_id``               | Identyfikator encji sensora ruchu                           | X             | X                   | X            | -                       |
| ``motion_delay``                          | Zwłoka początku detekcji ruchu (w sek.)                     | X             | X                   | X            | -                       |
| ``motion_off_delay``                      | Zwłoka końca detekcji ruchu (w sek.)                        | X             | X                   | X            | X                       |
| ``motion_preset``                         | Preset po wykryciu początku ruchu                           | X             | X                   | X            | X                       |
| ``no_motion_preset``                      | Preset po wykryciu końca ruchu                              | X             | X                   | X            | X                       |
| ``power_sensor_entity_id``                | Identyfikator encji sensora mocy                            | X             | X                   | X            | X                       |
| ``max_power_sensor_entity_id``            | Identyfikator encji sensora mocy maksymalnej                | X             | X                   | X            | X                       |
| ``power_temp``                            | Temperatura podczar redukcji mocy                           | X             | X                   | X            | X                       |
| ``presence_sensor_entity_id``             | Identyfikator encji sensora obecności (`true`=obecność)     | X             | X                   | X            | -                       |
| ``minimal_activation_delay``              | Minimalna zwłoka aktywacji                                  | X             | -                   | -            | X                       |
| ``minimal_deactivation_delay``            | Minimalna zwłoka deaktywacji                                | X             | -                   | -            | X                       |
| ``safety_delay_min``                      | Maksymalna zwłoka między dwoma pomiarami temperatury        | X             | -                   | X            | X                       |
| ``safety_min_on_percent``                 | Procent mocy minimalnej do przejścia w tryb bezpieczny  | X             | -                   | X            | X                       |
| ``auto_regulation_mode``                  | Tryb samoregulacji                                          | -             | X                   | -            | -                       |
| ``auto_regulation_dtemp``                 | Próg samoregulacji                                          | -             | X                   | -            | -                       |
| ``auto_regulation_period_min``            | Minimalny czas samoregulacji                                | -             | X                   | -            | -                       |
| ``inverse_switch_command``                | Przełącznk inwersji polecenia (przełączanie przewodem sterującym)        | X             | -                   | -            | -                       |
| ``auto_fan_mode``                         | Automatyczny tryb wentylacji                                | -             | X                   | -            | -                       |
| ``auto_regulation_use_device_temp``       | Temperatura wewnętrzna (własna) urządzenia                  | -             | X                   | -            | -                       |
| ``use_central_boiler_feature``            | Dodanie sterowania kotłem głównym                           | -             | -                   | -            | X                       |
| ``central_boiler_activation_service``     | Usługa katyewacji kotła                                     | -             | -                   | -            | X                       |
| ``central_boiler_deactivation_service``   | Usługa deaktywacji kotła                                    | -             | -                   | -            | X                       |
| ``used_by_controls_central_boiler``       | Wskaźnik sterowania kotła termostatem                       | X             | X                   | X            | -                       |
| ``use_auto_start_stop_feature``           | Wskażnik załączenia funkcji autoSTART/autoSTOP              | -             | X                   | -            | -                       |
| ``auto_start_stop_level``                 | Poziom detekcji autoSTART/autoSTOP                          | -             | X                   | -            | -                       |

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

Aby pokolorować sensory dodaj w pliku `configuration.yaml` poniższe linie kodu , dostosowując je według własnych potrzeb:

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

...i wybierz motyw ```versatile_thermostat_theme``` w panelu konfiguracyjnym. Otrzymasz coś podobnego do tego:

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

...lub aby zmienić ustawienie dla trybu `AC`, dodaj prefiks `_ac` do nazwy ustawienia, jak w przykładzie:
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
Usługa ta umożliwia dynamiczne załączanie i wyłączanie funkcji pomijania stanu otwarcia okien (lub drzwi). To z kolei pozwala termostatom kontunuować grzanie nawet w sytuacji wykrycia otwarcia okna.
Przy wartości ``true``, zmiany stanu okna nie będą wpływały na termostat. Przy wartości ``false``, termostat zostanie wyłączony, jeśli okno będzie nadal otwarte.

Aby zmienić ustawienie pomijania stanu otwarcia okna, zastosuj poniższy kod:
```yaml
service: versatile_thermostat.set_window_bypass
data:
    bypass: true
target:
    entity_id: climate.my_thermostat
```

# Zdarzenia
Kluczowe zdarzenia z udziałem termostatów wywołują pojawienie się powiadomień za pośrednictwem magistrali komunikacyjnej.
Powiadomienia dotyczą następujących zdarzeń:

- ``versatile_thermostat_security_event``: termostat wchodzi lub wychodzi z ustawień `bezpieczeństwo`
- ``versatile_thermostat_power_event``: termostat wchodzi lub wychodzi z ustawień `moc`
- ``versatile_thermostat_temperature_event``: co najmniej jeden z pomiarów temperatury termostatu nie został zaktualizowany przez ponad `safety_delay_min` minut.
- ``versatile_thermostat_hvac_mode_event``: termostat jest włączany lub wyłączany. To zdarzenie jest również raportowane podczas uruchamiania termostatu.
- ``versatile_thermostat_preset_event``: w termostacie wybrano nowy preset. To zdarzenie jest również raportowane podczas uruchamiania termostatu.
- ``versatile_thermostat_central_boiler_event``: zdarzenie zmiany stanu kotła
- ``versatile_thermostat_auto_start_stop_event``: zdarzenie zatrzymania lub ponownego uruchomienia wykonane przez funkcję autoSTART/autoSTOP

Jeśli śledziłeś instrukcje, gdy termostat przełącza się w tryb bezpieczny, wyzwalane są 3 zdarzenia:
1. ``versatile_thermostat_temperature_event`` – wskazuje, że termometr przestał odpowiadać,
2. ``versatile_thermostat_preset_event`` – wskazuje przełączenie na ustawienie trybu `bezpiecznego`,
3. ``versatile_thermostat_hvac_mode_event`` – wskazuje potencjalne wyłączenie termostatu.

Każde zdarzenie przechowuje kluczowe wartości zdarzenia (temperatury, aktualne ustawienia, bieżąca moc, ...) oraz stany termostatu.
Możesz łatwo przechwytywać te zdarzenia w automatyzacji, na przykład w celu powiadamiania użytkowników.

# Atrybuty własne

Aby dostosować algorytm, masz dostęp do całego kontekstu widzianego i obliczanego przez termostat za pośrednictwem dedykowanych atrybutów. Możesz przeglądać (i używać) te atrybuty w sekcji `Narzędzia developerskie -> Stany` w Home Assistant. Wprowadź swój termostat, a zobaczysz coś takiego:

![image](images/dev-tools-climate.png)

Atrybuty własne są następujace:

| Attrybut                          | Znaczenie                                                                                                                           |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| ``hvac_modes``                    | Lista trybów obsługiwanych przez termostat                                                                                          |
| ``temp_min``                      | Temperatura minimana                                                                                                                |
| ``temp_max``                      | Temperatura maksymalna                                                                                                              |
| ``preset_modes``                  | Preset widoczny dla tego termostatu. Ukryte ustawienia nie są tu wyświetlane.                                                       |
| ``temperature_actuelle``          | Aktualna temperatura raportowana przez czujnik                                                                                      |
| ``temperature``                   | Temperatura docelowa                                                                                                                |
| ``action_hvac``                   | Akcja aktualnie wykonywana przez grzejnik. Może być `idle` lub `heating`.                                                           |
| ``preset_mode``                   | Aktualnie wybrany preset. Może być jednym z `preset_modes` lub ukrytym presetem, np. `moc`                                          |
| ``[eco/confort/boost]_temp``      | Temperatura skonfigurowana dla presetu `xxx`                                                                                        |
| ``[eco/confort/boost]_away_temp`` | Temperatura skonfigurowana dla presetu `xxx`, gdy `obecność` jest wyłączona lub ma wartość `not_home`.                              |
| ``temp_power``                    | Temperatura używana podczas wykrywania utraty sygnału                                                                               |
| ``on_percent``                    | Obliczony procent włączenia przez algorytm TPI                                                                                      |
| ``on_time_sec``                   | Okres załączenia (w sek.). Powinien wynosić ```on_percent * cycle_min```                                                            |
| ``off_time_sec``                  | Okres wyłączenia (w sek.). Powinien wynosić ```(1 - on_percent) * cycle_min```                                                      |
| ``cycle_min``                     | Cykl obliczeniowy (w min.)                                                                                                          |
| ``function``                      | Algorytm używany do obliczeń cyklu                                                                                                  |
| ``tpi_coef_int``                  | Wartość `współczynnika delty dla temperatury wewnętrznej` algorytmu TPI                                                             |
| ``tpi_coef_ext``                  | Wartość `współczynnika delty dla temperatury zewnętrznej` algorytmu TPI                                                             |
| ``saved_preset_mode``             | Ostatnio użyty preset przed automatycznym przełączeniem                                                                             |
| ``saved_target_temp``             | Ostatnia temperatura użyta przed automatycznym przełączeniem                                                                        |
| ``window_state``                  | Ostatni znany stan czujnika okna. `Brak`, jeśli czujnik nie jest skonfigurowany                                                     |
| ``is_window_bypass``              | `True`, jeśli pomijanie detekcji otwartego okna jest załączone                                                                      |
| ``motion_state``                  | Ostatni znany stan czujnika ruchu. `Brak`, jeśli detekcja ruchu nie jest skonfigurowana                                             |
| ``overpowering_state``            | Ostatni znany stan czujnika przeciążenia. `Brak`, jeśli zarządzanie energią nie jest skonfigurowane                                 |
| ``presence_state``                | Ostatni znany stan czujnika obecności. `Brak`, jeśli detekcja obecności nie jest skonfigurowana                                     |
| ``safety_delay_min``              | Zwłoka w aktywacji trybu bezpiecznego, gdy jeden z dwóch czujników temperatury przestaje wysyłać pomiary                          |
| ``safety_min_on_percent``         | Procent grzania, poniżej którego termostat nie przełączy się w tryb bezpieczny                                                |
| ``safety_default_on_percent``     | Procent grzania używany, gdy termostat pracuje w trybie bezpiecznym                                                              |
| ``last_temperature_datetime``     | Data i czas ostatniego odczytu temperatury wewnętrznej (w formacie ISO8866)                                                         |
| ``last_ext_temperature_datetime`` | Data i czas ostatniego odczytu temperatury zewnętrznej (w formacie ISO8866)                                                         |
| ``security_state``                | Stan bezpieczny. `True` lub `false`                                                                                             |
| ``minimal_activation_delay_sec``  | Minimalne opóźnienie aktywacji (w sek.)                                                                                             |
| ``minimal_deactivation_delay_sec``| Minimalne opóźnienie deaktywacji (w sek.)                                                                                           |
| ``last_update_datetime``          | Data i czas tego stanu (w formacie ISO8866)                                                                                         |
| ``friendly_name``                 | Przyjazna nazwa termostatu                                                                                                          |
| ``supported_features``            | Kombinacja wszystkich funkcji obsługiwanych przez ten termostat. Zobacz dokumentację, aby uzyskać więcej informacji                 |
| ``valve_open_percent``            | Procent otwarcia zaworu                                                                                                             |
| ``regulated_target_temperature``  | Temperatura docelowa obliczona przez samoregulację                                                                                  |
| ``is_inversed``                   | `True`, jeśli sterowanie jest odwrócone (dotyczy sterowania przewodowego z diodą)                                                                          |
| ``is_controlled_by_central_mode`` | `True`, jeśli termostat może być sterowany centralnie                                                                               |
| ``last_central_mode``             | Ostatni użyty tryb centralny (`None`, jeśli termostat nie jest sterowany centralnie)                                                |
| ``is_used_by_central_boiler``     | Wskazuje, czy termostat może sterować centralnym kotłem                                                                             |
| ``auto_start_stop_enable``        | Wskazuje, czy termostat może pracować w trybie autoSTART/autoSTOP                                                                   |
| ``auto_start_stop_level``         | Wskazuje poziom autoSTAR/autoSTOP                                                                                                   |
| ``hvac_off_reason``               | Wskazuje powód wyłączenia termostatu (`hvac_off`). Może to być `Window`, `AutoSTART/autoSTOP` lub `Manual`                          |
| ``last_change_time_from_vtherm``  | Data i czas ostatniej zmiany dokonanej przez termostat                                                                              |
| ``nb_device_actives``             | Liczba urządzeń podrzędnych widocznych jako aktywne                                                                                 |
| ``device_actives``                | Lista urządzeń podrzędnych widocznych jako aktywne                                                                                  |


