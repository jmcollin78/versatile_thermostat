# Dokumentacja Referencyjna

- [Dokumentacja Referencyjna](#reference-documentation)
  - [Parametry](#parameter-summary)
- [Sensory](#sensors)
- [Akcje (Usługi)](#actions-services)
  - [Wymuszanie obecności/zajętości](#force-presenceoccupation)
  - [Modykacja wstępnych ustawień temperatury](#modify-the-preset-temperature)
  - [Modify ustawień bezpieczeństwa](#modify-security-settings)
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
| ``motion_preset``                         | Ustawienie wstępne po wykryciu początku ruchu               | X             | X                   | X            | X                       |
| ``no_motion_preset``                      | Ustawienie wstępne po wykryciu końca ruchu                  | X             | X                   | X            | X                       |
| ``power_sensor_entity_id``                | Identyfikator encji sensora mocy                            | X             | X                   | X            | X                       |
| ``max_power_sensor_entity_id``            | Identyfikator encji sensora mocy maksymalnej                | X             | X                   | X            | X                       |
| ``power_temp``                            | Temperatura podczar redukcji mocy                           | X             | X                   | X            | X                       |
| ``presence_sensor_entity_id``             | Identyfikator encji sensora obecności (`true`=obecność)     | X             | X                   | X            | -                       |
| ``minimal_activation_delay``              | Minimalna zwłoka aktywacji                                  | X             | -                   | -            | X                       |
| ``minimal_deactivation_delay``            | Minimalna zwłoka deaktywacji                                | X             | -                   | -            | X                       |
| ``safety_delay_min``                      | Maksymalna zwłoka między dwoma pomiarami temperatury        | X             | -                   | X            | X                       |
| ``safety_min_on_percent``                 | Procent mocy minimalnej do przejścia w tryb bezpieczeństwa  | X             | -                   | X            | X                       |
| ``auto_regulation_mode``                  | Tryb samoregulacji                                          | -             | X                   | -            | -                       |
| ``auto_regulation_dtemp``                 | Próg samoregulacji                                          | -             | X                   | -            | -                       |
| ``auto_regulation_period_min``            | Minimalny czas samoregulacji                                | -             | X                   | -            | -                       |
| ``inverse_switch_command``                | Przełącznk inwersji polecenia (przełączanie pilotem)        | X             | -                   | -            | -                       |
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

## Modykacja wstępnych ustawień temperatury
This service is useful if you want to dynamically change the preset temperature. Instead of switching presets, some use cases require modifying the temperature of the preset. This way, you can keep the scheduler unchanged to manage the preset while adjusting the preset temperature.
If the modified preset is currently selected, the target temperature change is immediate and will be applied in the next calculation cycle.

You can modify one or both temperatures (when present or absent) of each preset.

Use the following code to set the preset temperature:
```yaml
service: versatile_thermostat.set_preset_temperature
data:
    preset: boost
    temperature: 17.8
    temperature_away: 15
target:
    entity_id: climate.my_thermostat
```

Or, to change the preset for the Air Conditioning (AC) mode, add the `_ac` prefix to the preset name like this:
```yaml
service: versatile_thermostat.set_preset_temperature
data:
    preset: boost_ac
    temperature: 25
    temperature_away: 30
target:
    entity_id: climate.my_thermostat
```

> ![Tip](images/tips.png) _*Notes*_
>
>    - After a restart, presets are reset to the configured temperature. If you want your change to be permanent, you need to modify the preset temperature in the integration configuration.

## Modify ustawień bezpieczeństwa
This service allows you to dynamically modify the security settings described here [Advanced Configuration](#advanced-configuration).
If the thermostat is in ``security`` mode, the new settings are applied immediately.

To change the security settings, use the following code:
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
This service allows you to enable or disable a bypass for the window check.
It allows the thermostat to continue heating even if the window is detected as open.
When set to ``true``, changes to the window's status will no longer affect the thermostat. When set to ``false``, the thermostat will be disabled if the window is still open.

To change the bypass setting, use the following code:
```yaml
service: versatile_thermostat.set_window_bypass
data:
    bypass: true
target:
    entity_id: climate.my_thermostat
```

# Zdarzenia
The key events of the thermostat are notified via the message bus.
The following events are notified:

- ``versatile_thermostat_security_event``: the thermostat enters or exits the ``security`` preset
- ``versatile_thermostat_power_event``: the thermostat enters or exits the ``power`` preset
- ``versatile_thermostat_temperature_event``: one or both temperature measurements of the thermostat haven't been updated for more than `safety_delay_min`` minutes
- ``versatile_thermostat_hvac_mode_event``: the thermostat is turned on or off. This event is also broadcast at the thermostat's startup
- ``versatile_thermostat_preset_event``: a new preset is selected on the thermostat. This event is also broadcast at the thermostat's startup
- ``versatile_thermostat_central_boiler_event``: an event indicating a change in the boiler's state
- ``versatile_thermostat_auto_start_stop_event``: an event indicating a stop or restart made by the auto-start/stop function

If you've followed along, when a thermostat switches to security mode, 3 events are triggered:
1. ``versatile_thermostat_temperature_event`` to indicate that a thermometer is no longer responding,
2. ``versatile_thermostat_preset_event`` to indicate the switch to the ``security`` preset,
3. ``versatile_thermostat_hvac_mode_event`` to indicate the potential shutdown of the thermostat

Each event carries the event's key values (temperatures, current preset, current power, ...) as well as the thermostat's states.

You can easily capture these events in an automation, for example, to notify users.

# Atrybuty własne

To adjust the algorithm, you have access to the entire context seen and calculated by the thermostat via dedicated attributes. You can view (and use) these attributes in the "Developer Tools / States" section of HA. Enter your thermostat and you will see something like this:
![image](images/dev-tools-climate.png)

The custom attributes are as follows:


| Attrybut                          | Znaczenie                                                                                                                           |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| ``hvac_modes``                    | Lista trybów obsługiwanych przez termostat                                                                                          |
| ``temp_min``                      | Temperatura minimana                                                                                                                |
| ``temp_max``                      | Temperatura maksymalna                                                                                                              |
| ``preset_modes``                  | Ustawienia wstępne widoczne dla tego termostatu. Ukryte ustawienia nie są tu wyświetlane                                            |
| ``temperature_actuelle``          | Aktualna temperatura raportowana przez czujnik                                                                                      |
| ``temperature``                   | Temperatura docelowa                                                                                                                |
| ``action_hvac``                   | Akcja aktualnie wykonywana przez grzejnik. Może być `idle` lub `heating`.                                                           |
| ``preset_mode``                   | Aktualnie wybrane ustawienie wstępne. Może być jednym z `preset_modes` lub ukrytym ustawieniem wstępnym, np. `moc`                  |
| ``[eco/confort/boost]_temp``      | Temperatura skonfigurowana dla ustawienia wstępnego `xxx`                                                                           |
| ``[eco/confort/boost]_away_temp`` | Temperatura skonfigurowana dla ustawienia wstępnego `xxx`, gdy `obrcność` jest wyłączona lub jest `not_home`.                       |
| ``temp_power``                    | Temperatura używana podczas wykrywania utraty sygnału                                                                               |
| ``on_percent``                    | Obliczony procent włączenia przez algorytm TPI                                                                                      |
| ``on_time_sec``                   | Okres załączenia (w sek.). Powinien wynosić ```on_percent * cycle_min```                                                            |
| ``off_time_sec``                  | Okres wyłączenia (w sek.). Powinien wynosić ```(1 - on_percent) * cycle_min```                                                      |
| ``cycle_min``                     | Cykl obliczeniowy (w min.)                                                                                                          |
| ``function``                      | Algorytm używany do obliczeń cyklu                                                                                                  |
| ``tpi_coef_int``                  | Wartość `współczynnika delty dla temperatury wewnętrznej` algorytmu TPI                                                             |
| ``tpi_coef_ext``                  | Wartość `współczynnika delty dla temperatury zewnętrznej` algorytmu TPI                                                             |
| ``saved_preset_mode``             | Ostatnio użyte ustawienie wstępne przed automatycznym przełączeniem                                                                 |
| ``saved_target_temp``             | Ostatnia temperatura użyta przed automatycznym przełączeniem                                                                        |
| ``window_state``                  | Ostatni znany stan czujnika okna. `Brak`, jeśli czujnik nie jest skonfigurowany                                                     |
| ``is_window_bypass``              | `True`, jeśli pomijanie detekcji otwartego okna jest załączone                                                                      |
| ``motion_state``                  | Ostatni znany stan czujnika ruchu. `Brak`, jeśli detekcja ruchu nie jest skonfigurowana                                             |
| ``overpowering_state``            | Ostatni znany stan czujnika przeciążenia. `Brak`, jeśli zarządzanie energią nie jest skonfigurowane                                 |
| ``presence_state``                | Ostatni znany stan czujnika obecności. `Brak`, jeśli detekcja obecności nie jest skonfigurowana                                     |
| ``safety_delay_min``              | Zwłoka w aktywacji trybu bezpieczeństwa, gdy jeden z dwóch czujników temperatury przestaje wysyłać pomiary                          |
| ``safety_min_on_percent``         | Procent grzania, poniżej którego termostat nie przełączy się w tryb bezpieczeństwa                                                  |
| ``safety_default_on_percent``     | Procent grzania używany, gdy termostat pracuje w trybie bezpieczeństwa                                                              |
| ``last_temperature_datetime``     | Data i czas ostatniego odczytu temperatury wewnętrznej (w formacie ISO8866)                                                         |
| ``last_ext_temperature_datetime`` | Data i czas ostatniego odczytu temperatury zewnętrznej (w formacie ISO8866)                                                         |
| ``security_state``                | Stan bezpieczeństwa. `True` lub `false`                                                                                             |
| ``minimal_activation_delay_sec``  | Minimalne opóźnienie aktywacji (w sek.)                                                                                             |
| ``minimal_deactivation_delay_sec``| Minimalne opóźnienie deaktywacji (w sek.)                                                                                           |
| ``last_update_datetime``          | Data i czas tego stanu (w formacie ISO8866)                                                                                         |
| ``friendly_name``                 | Przyjazna nazwa termostatu                                                                                                          |
| ``supported_features``            | Kombinacja wszystkich funkcji obsługiwanych przez ten termostat. Zobacz dokumentację, aby uzyskać więcej informacji                 |
| ``valve_open_percent``            | Procent otwarcia zaworu                                                                                                             |
| ``regulated_target_temperature``  | Temperatura docelowa obliczona przez samoregulację                                                                                  |
| ``is_inversed``                   | `True`, jeśli sterowanie jest odwrócone (pilot przewodowy)                                                                          |
| ``is_controlled_by_central_mode`` | `True`, jeśli termostat może być sterowany centralnie                                                                               |
| ``last_central_mode``             | Ostatni użyty tryb centralny (`None`, jeśli termostat nie jest sterowany centralnie)                                                |
| ``is_used_by_central_boiler``     | Wskazuje, czy termostat może sterować centralnym kotłem                                                                             |
| ``auto_start_stop_enable``        | Wskazuje, czy termostat może pracować w trybie autoSTART/autoSTOP                                                                   |
| ``auto_start_stop_level``         | Wskazuje poziom autoSTAR/autoSTOP                                                                                                   |
| ``hvac_off_reason``               | Wskazuje powód wyłączenia termostatu (`hvac_off`). Może to być `Window`, `AutoSTART/autoSTOP` lub `Manual`                          |
| ``last_change_time_from_vtherm``  | Data i czas ostatniej zmiany dokonanej przez termostat                                                                              |
| ``nb_device_actives``             | Liczba urządzeń podrzędnych widocznych jako aktywne                                                                                 |
| ``device_actives``                | Lista urządzeń podrzędnych widocznych jako aktywne                                                                                  |


