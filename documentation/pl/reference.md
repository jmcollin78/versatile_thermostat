# Dokumentacja Referencyjna

- [Dokumentacja Referencyjna](#dokumentacja-referencyjna)
  - [Parametry](#parametry)
- [Konfiguracja w trybie eksperckim](#konfiguracja-w-trybie-eksperckim)
  - [Parametry samoregulacji w trybie eksperckim](#parametry-samoregulacji-w-trybie-eksperckim)
  - [Wyłączenie sprawdzania czujnika zewnętrznego w trybie bezpieczeństwa](#wyłączenie-sprawdzania-czujnika-zewnętrznego-w-trybie-bezpieczeństwa)
  - [Maksymalny limit mocy grzewczej](#maksymalny-limit-mocy-grzewczej)
  - [Parametry automatycznej detekcji otwarcia okna](#parametry-automatycznej-detekcji-otwarcia-okna)
  - [Przechowywanie plików dziennika (Log Buffer)](#przechowywanie-plików-dziennika-log-buffer)
- [Sensory](#sensory)
- [Akcje (Usługi)](#akcje-usługi)
  - [Wymuszanie obecności/zajętości](#wymuszanie-obecnościzajętości)
  - [Modyfikacja ustawień bezpieczeństwa](#modyfikacja-ustawień-bezpieczeństwa)
  - [Pomijanie sprawdzania stanu okna](#pomijanie-sprawdzania-stanu-okna)
  - [Zmiana parametrów TPI](#zmiana-parametrów-tpi)
  - [Preset czasowy](#preset-czasowy)
- [Zdarzenia](#zdarzenia)
- [Atrybuty własne](#atrybuty-własne)
  - [For _VTherm_](#for-vtherm)
  - [For central configuration](#for-central-configuration)
  - [Atrybuty własne konfiguracji centralnej](#atrybuty-własne-konfiguracji-centralnej)

## Parametry

| Parametr                                  | Nazwa                                                             | Termostat<br>na<br>Przełączniku | Termostat<br>na<br>Klimacie | Termostat<br>na<br>Zaworze | Konfiguracja<br>Centralna |
| ----------------------------------------- | ----------------------------------------------------------------- | ------------------------------- | --------------------------- | -------------------------- | ------------------------- |
| ``name``                                  | Nazwa                                                             | X                               | X                           | X                          | -                         |
| ``thermostat_type``                       | Typ termostatu                                                    | X                               | X                           | X                          | -                         |
| ``temperature_sensor_entity_id``          | Identyfikator encji sensora temperatury                           | X                               | X (auto-regulacja)          | X                          | -                         |
| ``external_temperature_sensor_entity_id`` | Identyfikator encji sensora temperatury zewnętrznej               | X                               | X (auto-regulacja)          | X                          | X                         |
| ``cycle_min``                             | Czas trwania cyklu (w min.)                                       | X                               | X                           | X                          | -                         |
| ``temp_min``                              | Minimalna dopuszczalna temperatura                                | X                               | X                           | X                          | X                         |
| ``temp_max``                              | Maksymalna dopuszczalna temperatura                               | X                               | X                           | X                          | X                         |
| ``device_power``                          | Moc urządzenia                                                    | X                               | X                           | X                          | -                         |
| ``use_central_mode``                      | Sterowanie centralne aktywne                                      | X                               | X                           | X                          | -                         |
| ``use_window_feature``                    | Z detekcją otwarcia okna                                          | X                               | X                           | X                          | -                         |
| ``use_motion_feature``                    | Z detekcją ruchu                                                  | X                               | X                           | X                          | -                         |
| ``use_power_feature``                     | Z zarządzaniem mocą                                               | X                               | X                           | X                          | -                         |
| ``use_presence_feature``                  | Z detekcją obecności                                              | X                               | X                           | X                          | -                         |
| ``heater_entity1_id``                     | 1-szy grzejnik                                                    | X                               | -                           | -                          | -                         |
| ``heater_entity2_id``                     | 2-gi grzejnik                                                     | X                               | -                           | -                          | -                         |
| ``heater_entity3_id``                     | 3-ci grzejnik                                                     | X                               | -                           | -                          | -                         |
| ``heater_entity4_id``                     | 4-ty grzejnik                                                     | X                               | -                           | -                          | -                         |
| ``heater_keep_alive``                     | Częstość odświerzania stanu                                       | X                               | -                           | -                          | -                         |
| ``proportional_function``                 | Algorytm                                                          | X                               | -                           | -                          | -                         |
| ``climate_entity1_id``                    | 1-szy termostat podstawowy                                        | -                               | X                           | -                          | -                         |
| ``climate_entity2_id``                    | 2-gi termostat podstawowy                                         | -                               | X                           | -                          | -                         |
| ``climate_entity3_id``                    | 3-ci termostat podstawowy                                         | -                               | X                           | -                          | -                         |
| ``climate_entity4_id``                    | 4-ty termostat podstawowy                                         | -                               | X                           | -                          | -                         |
| ``valve_entity1_id``                      | 1-szy zawór podstawowy                                            | -                               | -                           | X                          | -                         |
| ``valve_entity2_id``                      | 2-gi zawór podstawowy                                             | -                               | -                           | X                          | -                         |
| ``valve_entity3_id``                      | 3-ci zawór podstawowy                                             | -                               | -                           | X                          | -                         |
| ``valve_entity4_id``                      | 4-ty zawór podstawowy                                             | -                               | -                           | X                          | -                         |
| ``ac_mode``                               | Tryb AC                                                           | X                               | X                           | X                          | -                         |
| ``tpi_coef_int``                          | Współczynnik delta temperatury wewnętrznej                        | X                               | -                           | X                          | X                         |
| ``tpi_coef_ext``                          | Współczynnik delta temperatury zewnętrznej                        | X                               | -                           | X                          | X                         |
| ``frost_temp``                            | Temperatura antyzamarzania                                        | X                               | X                           | X                          | X                         |
| ``window_sensor_entity_id``               | Identyfikator encji sensora okna                                  | X                               | X                           | X                          | -                         |
| ``window_delay``                          | Zwłoka w wyłączeniu (w sek.)                                      | X                               | X                           | X                          | X                         |
| ``window_auto_open_threshold``            | Górny próg automatycznej detekcji otwarcia okna (°/min)           | X                               | X                           | X                          | X                         |
| ``window_auto_close_threshold``           | Dolny próg automatycznej detekcji zamknięcia okna (°/min)         | X                               | X                           | X                          | X                         |
| ``window_auto_max_duration``              | Maksymalny czas trwania automatycznego wyłączenia (w min.)        | X                               | X                           | X                          | X                         |
| ``motion_sensor_entity_id``               | Identyfikator encji sensora ruchu                                 | X                               | X                           | X                          | -                         |
| ``motion_delay``                          | Zwłoka początku detekcji ruchu (w sek.)                           | X                               | X                           | X                          | -                         |
| ``motion_off_delay``                      | Zwłoka końca detekcji ruchu (w sek.)                              | X                               | X                           | X                          | X                         |
| ``motion_preset``                         | Preset po wykryciu początku ruchu                                 | X                               | X                           | X                          | X                         |
| ``no_motion_preset``                      | Preset po wykryciu końca ruchu                                    | X                               | X                           | X                          | X                         |
| ``power_sensor_entity_id``                | Identyfikator encji sensora mocy                                  | X                               | X                           | X                          | X                         |
| ``max_power_sensor_entity_id``            | Identyfikator encji sensora mocy maksymalnej                      | X                               | X                           | X                          | X                         |
| ``power_temp``                            | Temperatura podczar redukcji mocy                                 | X                               | X                           | X                          | X                         |
| ``presence_sensor_entity_id``             | Identyfikator encji sensora obecności (`true`=obecność)           | X                               | X                           | X                          | -                         |
| ``minimal_activation_delay``              | Minimalna zwłoka aktywacji                                        | X                               | -                           | -                          | X                         |
| ``minimal_deactivation_delay``            | Minimalna zwłoka deaktywacji                                      | X                               | -                           | -                          | X                         |
| ``safety_delay_min``                      | Maksymalna zwłoka między dwoma pomiarami temperatury              | X                               | -                           | X                          | X                         |
| ``safety_min_on_percent``                 | Procent mocy minimalnej do przejścia w tryb bezpieczny            | X                               | -                           | X                          | X                         |
| ``auto_regulation_mode``                  | Tryb samoregulacji                                                | -                               | X                           | -                          | -                         |
| ``auto_regulation_dtemp``                 | Próg samoregulacji                                                | -                               | X                           | -                          | -                         |
| ``auto_regulation_period_min``            | Minimalny czas samoregulacji                                      | -                               | X                           | -                          | -                         |
| ``inverse_switch_command``                | Przełącznk inwersji polecenia (przełączanie przewodem sterującym) | X                               | -                           | -                          | -                         |
| ``auto_fan_mode``                         | Automatyczny tryb wentylacji                                      | -                               | X                           | -                          | -                         |
| ``auto_regulation_use_device_temp``       | Temperatura wewnętrzna (własna) urządzenia                        | -                               | X                           | -                          | -                         |
| ``use_central_boiler_feature``            | Dodanie sterowania kotłem głównym                                 | -                               | -                           | -                          | X                         |
| ``central_boiler_activation_service``     | Usługa aktywacji kotła                                            | -                               | -                           | -                          | X                         |
| ``central_boiler_deactivation_service``   | Usługa deaktywacji kotła                                          | -                               | -                           | -                          | X                         |
| ``central_boiler_activation_delay_sec``   | Opóźnienie załączenia (w sekundach)                               | -                               | -                           | -                          | X                         |
| ``used_by_controls_central_boiler``       | Wskaźnik sterowania kotła termostatem                             | X                               | X                           | X                          | -                         |
| ``use_auto_start_stop_feature``           | Wskażnik załączenia funkcji autoSTART/autoSTOP                    | -                               | X                           | -                          | -                         |
| ``auto_start_stop_level``                 | Poziom detekcji autoSTART/autoSTOP                                | -                               | X                           | -                          | -                         |
# Konfiguracja w trybie eksperckim

Versatile Thermostat umożliwia konfigurację zaawansowanych parametrów bezpośrednio w pliku `configuration.yaml`. Te parametry są zarezerwowane dla zaawansowanych użytkowników i zapewniają dokładną kontrolę nad zachowaniem termostatu.

## Parametry samoregulacji w trybie eksperckim

Gdy _VTherm_ typu `over_climate` używa **trybu eksperckie** samoregulacji, możesz zadeklarować parametry regulacji bezpośrednio w pliku `configuration.yaml`. Pozwala to na precyzyjne dostrojenie zachowania regulacji.

Aby użyć tej funkcji, dodaj następujące wiersze do pliku `configuration.yaml`:

```yaml
versatile_thermostat:
  auto_regulation_expert:
    kp: 0.6
    ki: 0.1
    k_ext: 0.0
    offset_max: 10
    accumulated_error_threshold: 80
    overheat_protection: true
```

Parametry to:

| Parametr                      | Opis                                                                                                                                  | Typ                       | Przykład |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | -------- |
| `kp`                          | Współczynnik proporcjonalny zastosowany do surowego błędu temperatury (różnica między temperaturą docelową a rzeczywistą temperaturą) | Liczba zmiennoprzecinkowa | 0.6      |
| `ki`                          | Współczynnik całkowy stosowany do akumulacji błędów w czasie                                                                          | Liczba zmiennoprzecinkowa | 0.1      |
| `k_ext`                       | Współczynnik stosowany do różnicy między temperaturą wewnętrzną a zewnętrzną. Umożliwia kompensację zmian zewnętrznych                | Liczba zmiennoprzecinkowa | 0.0      |
| `offset_max`                  | Maksymalna korekta (przesunięcie), którą regulacja może zastosować do temperatury zadanej                                             | Liczba zmiennoprzecinkowa | 10       |
| `accumulated_error_threshold` | Maksymalny próg akumulacji błędu. Zapobiega nieskończonej akumulacji błędu                                                            | Liczba zmiennoprzecinkowa | 80       |
| `overheat_protection`         | Aktywuje ochronę przed przegrzaniem poprzez ograniczenie poprawek dodatnich (opcjonalnie)                                             | Wartość logiczna          | true     |

> ![Ważne](images/tips.png) _*Ważna uwaga*_
>
> - Te parametry dotyczą **wszystkich _VTherms_ w trybie eksperckim** w systemie. Nie jest możliwe posiadanie różnych konfiguracji dla różnych termostatów.
> - **Home Assistant musi zostać uruchomiony ponownie**, aby zmiany weszły w życie (lub możesz ponownie załadować integrację Versatile Thermostat za pośrednictwem Narzędzi Programisty).
> - Zapoznaj się z [dokumentacją samoregulacji](self-regulation.md#samoregulacja-w-trybie-eksperckim), aby znaleźć przykłady wstępnie zdefiniowanych konfiguracji.

## Wyłączenie sprawdzania czujnika zewnętrznego w trybie bezpieczeństwa

Domyślnie tryb bezpieczeństwa sprawdza, czy **czujnik temperatury zewnętrznej** regularnie wysyła dane. Jeśli jednak czujnik zewnętrzny nie jest obecny lub nie jest krytyczny dla Twojej instalacji, możesz wyłączyć to sprawdzenie.

Aby to zrobić, dodaj następujące wiersze do pliku `configuration.yaml`:

```yaml
versatile_thermostat:
  safety_mode:
    check_outdoor_sensor: false
```

| Parametr               | Opis                                                                                                                                   | Typ              | Domyślnie |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | --------- |
| `check_outdoor_sensor` | Jeśli `true`, brak danych czujnika zewnętrznego wyzwoli tryb bezpieczeństwa. Jeśli `false`, będzie sprawdzany tylko czujnik wewnętrzny | Wartość logiczna | true      |

> ![Ważne](images/tips.png) _*Ważna uwaga*_
>
> - Ta modyfikacja dotyczy **wszystkich _VTherms_** w systemie
> - Wpływa na detekcję dla wszystkich termostatów w tym samym czasie
> - **Home Assistant musi zostać uruchomiony ponownie**, aby zmiany weszły w życie

## Maksymalny limit mocy grzewczej

Parametr `max_on_percent` pozwala na globalne ograniczenie maksymalnej mocy grzewczej dla całej instalacji. Może to być przydatne dla poszanowania ograniczeń elektrycznych lub regulowania obciążenia systemu.

Aby skonfigurować ten limit, dodaj następujący wiersz do pliku `configuration.yaml`:

```yaml
versatile_thermostat:
  max_on_percent: 0.9
```

| Parametr         | Opis                                                                               | Typ                       | Zakres     | Domyślnie |
| ---------------- | ---------------------------------------------------------------------------------- | ------------------------- | ---------- | --------- |
| `max_on_percent` | Maksymalny procent dozwolonej mocy grzewczej. `1.0` = 100% mocy, `0.9` = 90%, itd. | Liczba zmiennoprzecinkowa | 0.0 do 1.0 | 1.0       |

**Przykłady użycia**:
- `0.8`: ogranicza ogrzewanie do 80% wydajności
- `0.5`: ogranicza do 50% (przydatne w przypadku przeciążenia elektrycznego)
- `1.0`: brak ograniczenia (zachowanie domyślne)

> ![Ważne](images/tips.png) _*Ważna uwaga*_
>
> - To ograniczenie dotyczy **wszystkich _VTherms_** w systemie
> - Jest stosowane natychmiast bez ponownego uruchamiania
> - Wpływa na maksymalną moc obliczaną w każdym cyklu

## Parametry automatycznej detekcji otwarcia okna

Używając automatycznej detekcji otwarcia okna (opartej na spadzie temperatury), możesz dostroić parametry wygładzania temperatury, aby poprawić detekcję.

Aby skonfigurować te parametry, dodaj następujące wiersze do pliku `configuration.yaml`:

```yaml
versatile_thermostat:
  short_ema_params:
    max_alpha: 0.5
    halflife_sec: 300
    precision: 2
```

| Parametr       | Opis                                                                                                                            | Typ                       | Zakres     | Domyślnie |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | ---------- | --------- |
| `max_alpha`    | Maksymalny współczynnik wygładzania (alfa) dla średniej ruchomej wykładniczej. Kontroluje czułość na szybkie zmiany temperatury | Liczba zmiennoprzecinkowa | 0.0 do 1.0 | 0.5       |
| `halflife_sec` | Okres półtrwania w sekundach dla obliczenia średniej ruchomej. Określa, jak szybko stare wartości tracą wagę                    | Liczba całkowita          | > 0        | 300       |
| `precision`    | Liczba miejsc dziesiętnych zachowywanych w obliczeniu średniej ruchomej                                                         | Liczba całkowita          | > 0        | 2         |

**Znaczenie parametrów**:
- **`max_alpha`**: wyższa wartość sprawia, że detekcja jest bardziej reaktywna na nagłe zmiany (szybsza detekcja, ale bardziej wrażliwa na fałsze alarmy)
- **`halflife_sec`**: krótszy czas sprawia, że algorytm szybciej zapomina stare wartości (szybsza detekcja)
- **`precision`**: kontroluje zaokrąglenie obliczenia (rzadko wymaga dostrojenia)

> ![Ostrzeżenie](images/tips.png) _*Te parametry są czułe*_
>
> - Te parametry wpływają na automatyczną detekcję otwarcia okna
> - Dotyczą **wszystkich _VTherms_** w systemie
> - Dostosuj je tylko w przypadku problemów z detekcją (fałsze alarmy lub brak detekcji)
> - Zapoznaj się z [sekcją rozwiązywania problemów](troubleshooting.md#dostosowanie-parametrów-detekcji-otwarcia-okna-w-trybie-automatycznym), aby uzyskać więcej szczegółów

## Przechowywanie plików dziennika (Log Buffer)

Versatile Thermostat przechowuje wewnętrzne dzienniki do rozwiązywania problemów. Można skonfigurować okres przechowywania tych dzienników.

Aby skonfigurować ten czas przechowywania, dodaj następujący wiersz do pliku `configuration.yaml`:

```yaml
versatile_thermostat:
  log_buffer_max_age_hours: 24
```

| Parametr                   | Opis                                                                                                       | Typ              | Zakres | Domyślnie |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------------- | ------ | --------- |
| `log_buffer_max_age_hours` | Maksymalny okres przechowywania dziennika w godzinach. Dzienniki starsze niż to będą automatycznie usuwane | Liczba całkowita | > 0    | 24        |

**Przykłady użycia**:
- `12`: przechowuje dzienniki z ostatnich 12 godzin
- `24`: przechowuje dzienniki przez 24 godziny (1 dzień)
- `72`: przechowuje dzienniki przez 72 godziny (3 dni) dla rozszerzonego rozwiązywania problemów

> ![Ważne](images/tips.png) _*Zarządzanie pamięcią*_
>
> - Dłuższy czas przechowywania zużywa więcej pamięci
> - Ta konfiguracja dotyczy **wszystkich _VTherms_** w systemie
> - Dzienniki są przydatne do rozwiązywania problemów za pośrednictwem punktu końcowego pobierania dziennika
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

## Preset czasowy
Te usługi umożliwiają tymczasowe wymuszenie presetu na termostacie przez określony czas. Szczegóły w [Preset czasowy](feature-timed-preset.md).

Aby aktywować preset czasowy:
```yaml
service: versatile_thermostat.set_timed_preset
data:
  preset: "boost"
  duration_minutes: 30
target:
  entity_id: climate.moj_termostat
```

Aby anulować preset czasowy przed upływem jego czasu:
```yaml
service: versatile_thermostat.cancel_timed_preset
target:
  entity_id: climate.moj_termostat
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
- ``versatile_thermostat_timed_preset_event``: zdarzenie wskazujące aktywację lub dezaktywację presetu czasowego

Jeśli śledziłeś instrukcje, gdy termostat przełącza się w tryb bezpieczny, wyzwalane są 3 zdarzenia:
1. ``versatile_thermostat_temperature_event`` – wskazuje, że termometr przestał odpowiadać,
2. ``versatile_thermostat_preset_event`` – wskazuje przełączenie na ustawienie trybu `bezpiecznego`,
3. ``versatile_thermostat_hvac_mode_event`` – wskazuje potencjalne wyłączenie termostatu.

Każde zdarzenie przechowuje kluczowe wartości zdarzenia (temperatury, aktualne ustawienia, bieżąca moc, ...) oraz stany termostatu.
Możesz łatwo przechwytywać te zdarzenia w automatyzacji, na przykład w celu powiadamiania użytkowników.

# Atrybuty własne

Aby dostosować algorytm, masz dostęp do całego kontekstu widzianego i obliczanego przez termostat za pośrednictwem dedykowanych atrybutów. Możesz przeglądać (i używać) te atrybuty w sekcji `Narzędzia deweloperskie -> Stany` w Home Assistant. Wprowadź swój termostat, a zobaczysz:

![image](images/dev-tools-climate.png)

## For _VTherm_

Atrybuty własne są następujace:

| Atrybut                            | Znaczenie                                                                                                           |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| ``hvac_modes``                     | Lista trybów obsługiwanych przez termostat                                                                          |
| ``temp_min``                       | Temperatura minimana                                                                                                |
| ``temp_max``                       | Temperatura maksymalna                                                                                              |
| ``preset_modes``                   | Preset widoczny dla tego termostatu. Ukryte ustawienia nie są tu wyświetlane.                                       |
| ``temperature_actuelle``           | Aktualna temperatura raportowana przez czujnik                                                                      |
| ``temperature``                    | Temperatura docelowa                                                                                                |
| ``action_hvac``                    | Akcja aktualnie wykonywana przez grzejnik. Może być `idle` lub `heating`.                                           |
| ``preset_mode``                    | Aktualnie wybrany preset. Może być jednym z `preset_modes` lub ukrytym presetem, np. `moc`                          |
| ``[eco/confort/boost]_temp``       | Temperatura skonfigurowana dla presetu `xxx`                                                                        |
| ``[eco/confort/boost]_away_temp``  | Temperatura skonfigurowana dla presetu `xxx`, gdy `obecność` jest wyłączona lub ma wartość `not_home`.              |
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
| ``minimal_activation_delay_sec``   | Minimalne opóźnienie aktywacji (w sek.)                                                                             |
| ``minimal_deactivation_delay_sec`` | Minimalne opóźnienie deaktywacji (w sek.)                                                                           |
| ``last_update_datetime``           | Data i czas tego stanu (w formacie ISO8866)                                                                         |
| ``friendly_name``                  | Przyjazna nazwa termostatu                                                                                          |
| ``supported_features``             | Kombinacja wszystkich funkcji obsługiwanych przez ten termostat. Zobacz dokumentację, aby uzyskać więcej informacji |
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

## For central configuration

## Atrybuty własne konfiguracji centralnej

Atrybuty własne konfiguracji centralnej są dostepne w panelu _Narzędzia deweloperskie -> Stany_ w sensorze `binary_sensor.central_configuration_central_boiler`:

| Atrybut                                     | znaczenie                                                                            |
| ------------------------------------------- | ------------------------------------------------------------------------------------ |
| ``central_boiler_state``                    | The state of the central boiler. Can be `on` or `off`                                |
| ``is_central_boiler_configured``            | Indicates whether the central boiler feature is configured                           |
| ``is_central_boiler_ready``                 | Indicates whether the central boiler is ready                                        |
| **SECTION `central_boiler_manager`**        | ------                                                                               |
| ``is_on``                                   | true if the central boiler is on                                                     |
| ``activation_scheduled``                    | true if a boiler activation is scheduled (see `central_boiler_activation_delay_sec`) |
| ``delayed_activation_sec``                  | The boiler activation delay in seconds                                               |
| ``nb_active_device_for_boiler``             | The number of active devices controlling the boiler                                  |
| ``nb_active_device_for_boiler_threshold``   | The threshold of active devices before activating the boiler                         |
| ``total_power_active_for_boiler``           | The total active power of devices controlling the boiler                             |
| ``total_power_active_for_boiler_threshold`` | The total power threshold before activating the boiler                               |
| **SUB-SECTION `service_activate`**          | ------                                                                               |
| ``service_domain``                          | The domain of the activation service (e.g., switch)                                  |
| ``service_name``                            | The name of the activation service (e.g., turn_on)                                   |
| ``entity_domain``                           | The domain of the entity controlling the boiler (e.g., switch)                       |
| ``entity_name``                             | The name of the entity controlling the boiler                                        |
| ``entity_id``                               | The complete identifier of the entity controlling the boiler                         |
| ``data``                                    | Additional data passed to the activation service                                     |
| **SUB-SECTION `service_deactivate`**        | ------                                                                               |
| ``service_domain``                          | The domain of the deactivation service (e.g., switch)                                |
| ``service_name``                            | The name of the deactivation service (e.g., turn_off)                                |
| ``entity_domain``                           | The domain of the entity controlling the boiler (e.g., switch)                       |
| ``entity_name``                             | The name of the entity controlling the boiler                                        |
| ``entity_id``                               | The complete identifier of the entity controlling the boiler                         |
| ``data``                                    | Additional data passed to the deactivation service                                   |

Example values:

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