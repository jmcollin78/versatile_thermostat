# Wykrywanie awarii ogrzewania

- [Wykrywanie awarii ogrzewania](#wykrywanie-awarii-ogrzewania)
  - [Dlaczego ta funkcja?](#dlaczego-ta-funkcja)
  - [Zasada działania](#zasada-działania)
    - [Wykrywanie awarii ogrzewania](#wykrywanie-awarii-ogrzewania-1)
    - [Wykrywanie awarii chłodzenia](#wykrywanie-awarii-chłodzenia)
  - [Konfiguracja](#konfiguracja)
  - [Parametry](#parametry)
  - [Udostępniane atrybuty](#udostępniane-atrybuty)
  - [Czujnik binarny](#czujnik-binarny)
  - [Zdarzenia](#zdarzenia)
  - [Przykłady automatyzacji](#przykłady-automatyzacji)
    - [Trwałe powiadomienie w przypadku awarii ogrzewania](#trwałe-powiadomienie-w-przypadku-awarii-ogrzewania)
    - [Trwałe powiadomienie dla wszystkich typów awarii](#trwałe-powiadomienie-dla-wszystkich-typów-awarii)
    - [Automatyczne usuwanie powiadomienia po rozwiązaniu awarii](#automatyczne-usuwanie-powiadomienia-po-rozwiązaniu-awarii)

## Dlaczego ta funkcja?

Wykrywanie awarii ogrzewania pozwala monitorować poprawność działania systemu grzewczego. Wykrywa dwie nienormalne sytuacje:

1. **Awaria ogrzewania**: termostat żąda dużej mocy (wysoki `on_percent`), ale temperatura nie rośnie. Może to wskazywać na:
   - uszkodzony lub wyłączony grzejnik,
   - zablokowany zawór termostatyczny,
   - niewykryte otwarte okno,
   - problem z cyrkulacją ciepłej wody (centralne ogrzewanie).

2. **Awaria chłodzenia**: termostat nie żąda mocy (`on_percent` równe 0), ale temperatura nadal rośnie. Może to wskazywać na:
   - grzejnik, który pozostaje włączony pomimo polecenia wyłączenia,
   - przekaźnik zablokowany w pozycji "włączony",
   - urządzenie podrzędne, które przestało reagować.

> ![Wskazówka](../../images/tips.png) _*Ważne*_
>
> Ta funkcja **nie zmienia zachowania termostatu**. Wysyła jedynie zdarzenia, aby ostrzec Cię o nienormalnej sytuacji. To do Ciebie należy stworzenie niezbędnych automatyzacji, aby zareagować na te zdarzenia (powiadomienia, alerty itp.).

## Zasada działania

Ta funkcja dotyczy tylko termostatów _VTherm_ używających algorytmu TPI (over_switch, over_valve lub over_climate z regulacją zaworem). Zatem termostaty _VTherm_ `over_climate`, które sterują na przykład pompą ciepła, nie są objęte tą funkcją. W takim przypadku decyzję o ogrzewaniu lub nie podejmuje samo urządzenie podrzędne, co uniemożliwia dostęp do wiarygodnych informacji.

Ta funkcja dotyczy tylko trybu Ogrzewania (`hvac_mode=heat`). W trybie klimatyzacji (`hvac_mode=cool`) nie przeprowadza się żadnego wykrywania, aby uniknąć fałszywych alarmów.

### Wykrywanie awarii ogrzewania

1. _VTherm_ jest w trybie ogrzewania,
2. `on_percent` jest większy lub równy skonfigurowanemu progowi (domyślnie 90%),
3. Ta sytuacja trwa dłużej niż opóźnienie wykrywania (domyślnie 15 minut),
4. Temperatura nie wzrosła w tym okresie.

➡️ Zdarzenie `versatile_thermostat_heating_failure_event` jest emitowane z `failure_type: heating` i `type: heating_failure_start`.

Gdy sytuacja wróci do normy (temperatura rośnie lub `on_percent` spada), emitowane jest zdarzenie z `type: heating_failure_end`.

### Wykrywanie awarii chłodzenia

1. _VTherm_ jest w trybie ogrzewania,
2. `on_percent` jest mniejszy lub równy skonfigurowanemu progowi (domyślnie 0%),
3. Ta sytuacja trwa dłużej niż opóźnienie wykrywania (domyślnie 15 minut),
4. Temperatura nadal rośnie.

➡️ Zdarzenie `versatile_thermostat_heating_failure_event` jest emitowane z `failure_type: cooling` i `type: cooling_failure_start`.

Gdy sytuacja wróci do normy, emitowane jest zdarzenie z `type: cooling_failure_end`.

## Konfiguracja

Podobnie jak wiele funkcji _VTherm_, tę funkcję można skonfigurować **w konfiguracji centralnej**, aby współdzielić parametry. Aby zastosować ją do wybranych termostatów _VTherm_, użytkownik musi dodać funkcję (patrz menu "Funkcje") i wybrać użycie wspólnych parametrów konfiguracji centralnej lub określić nowe, które będą miały zastosowanie tylko do tego termostatu _VTherm_.

Aby uzyskać dostęp:
1. Przejdź do konfiguracji swojego _VTherm_ typu "Konfiguracja Centralna"
2. W menu wybierz "Heating failure detection" (Wykrywanie awarii ogrzewania)
3. Następnie przejdź do konfiguracji odpowiednich termostatów _VTherm_,
4. Wybierz menu "Funkcje",
5. Zaznacz funkcję "Wykrywanie awarii ogrzewania",
6. Wybierz użycie parametrów konfiguracji centralnej lub określ nowe.

![Konfiguracja](../../images/config-heating-failure-detection.png)

## Parametry

| Parametr                                 | Opis                                                                                                                    | Wartość domyślna |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **Aktywuj wykrywanie awarii ogrzewania** | Włącza lub wyłącza funkcję                                                                                              | Wyłączone        |
| **Próg awarii ogrzewania**               | Procent `on_percent`, powyżej którego ogrzewanie powinno powodować wzrost temperatury. Wartość między 0 a 1 (0.9 = 90%) | 0.9 (90%)        |
| **Próg awarii chłodzenia**               | Procent `on_percent`, poniżej którego temperatura nie powinna rosnąć. Wartość między 0 a 1 (0 = 0%)                     | 0.0 (0%)         |
| **Opóźnienie wykrywania (minuty)**       | Czas oczekiwania przed zgłoszeniem awarii. Pozwala uniknąć fałszywych alarmów spowodowanych normalnymi wahaniami        | 15 minut         |
| **Tolerancja zmiany temperatury (°C)**   | Minimalna zmiana temperatury w stopniach, aby została uznana za znaczącą. Pozwala filtrować szum czujników              | 0.5°C            |

> ![Wskazówka](../../images/tips.png) _*Porady dotyczące ustawień*_
>
> - **Próg ogrzewania**: Jeśli masz fałszywe alarmy (wykrycie awarii, gdy wszystko działa), zwiększ ten próg do 0.95 lub 1.0.
> - **Próg chłodzenia**: Jeśli chcesz wykryć grzejnik, który pozostaje włączony nawet przy niskim `on_percent`, zwiększ ten próg do 0.05 lub 0.1.
> - **Opóźnienie wykrywania**: Zwiększ to opóźnienie, jeśli masz pomieszczenia o dużej bezwładności cieplnej (duże pokoje, ogrzewanie podłogowe itp.). Możesz sprawdzić krzywe grzewcze (patrz [dodatki](../../additions.md#courbes-de-régulattion-avec-plotly)) i zobaczyć, po jakim czasie termometr rośnie po włączeniu ogrzewania. Ten czas powinien być minimum dla tego parametru.
> - **Tolerancja**: Jeśli masz niedokładne lub zaszumione czujniki, zwiększ tę wartość (np. 0.8°C). Wiele czujników ma dokładność ±0.5°C.

## Udostępniane atrybuty

Termostaty _VTherm_ z TPI udostępniają następujące atrybuty:

```yaml
is_heating_failure_detection_configured: true
heating_failure_detection_manager:
  heating_failure_state: "off"      # "on", "off", "unknown", "unavailable"
  cooling_failure_state: "off"      # "on", "off", "unknown", "unavailable"
  heating_failure_threshold: 0.9
  cooling_failure_threshold: 0.0
  detection_delay_min: 15
  temperature_change_tolerance: 0.5
  heating_tracking:                 # Śledzenie wykrywania awarii ogrzewania
    is_tracking: true               # Wykrywanie w toku?
    initial_temperature: 19.5       # Temperatura na początku śledzenia
    current_temperature: 19.7       # Aktualna temperatura
    remaining_time_min: 8.5         # Pozostałe minuty do alarmu
    elapsed_time_min: 6.5           # Minuty upływające od początku
  cooling_tracking:                 # Śledzenie wykrywania awarii chłodzenia
    is_tracking: false
    initial_temperature: null
    current_temperature: null
    remaining_time_min: null
    elapsed_time_min: null
```

## Czujnik binarny

Gdy wykrywanie awarii ogrzewania jest włączone, automatycznie tworzony jest czujnik binarny dla każdego odpowiedniego termostatu _VTherm_:

| Encja                                         | Opis                                                   |
| --------------------------------------------- | ------------------------------------------------------ |
| `binary_sensor.<nazwa>_heating_failure_state` | Wskazuje, czy wykryto awarię ogrzewania lub chłodzenia |

Wyświetlana nazwa czujnika jest tłumaczona zgodnie z językiem Twojego Home Assistant "Stan awarii ogrzewania".

Ten czujnik jest:
- **ON**, gdy wykryto awarię (ogrzewania lub chłodzenia)
- **OFF**, gdy system działa normalnie

Cechy:
- **Device class**: `problem` (umożliwia natywne alerty Home Assistant)
- **Ikony**:
  - `mdi:radiator-off`, gdy wykryto awarię
  - `mdi:radiator`, gdy wszystko działa

Ten czujnik binarny może być używany bezpośrednio w Twoich automatyzacjach jako wyzwalacz lub do tworzenia alertów za pomocą natywnych powiadomień Home Assistant.

## Zdarzenia

Zdarzenie `versatile_thermostat_heating_failure_event` jest emitowane po wykryciu lub zakończeniu awarii.

Dane zdarzenia:
| Pole                     | Opis                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `entity_id`              | Identyfikator _VTherm_                                                                                        |
| `name`                   | Nazwa _VTherm_                                                                                                |
| `type`                   | Typ zdarzenia: `heating_failure_start`, `heating_failure_end`, `cooling_failure_start`, `cooling_failure_end` |
| `failure_type`           | Typ awarii: `heating` lub `cooling`                                                                           |
| `on_percent`             | Procent żądanej mocy w momencie wykrycia                                                                      |
| `temperature_difference` | Różnica temperatur zaobserwowana w okresie wykrywania                                                         |
| `current_temp`           | Aktualna temperatura                                                                                          |
| `target_temp`            | Temperatura docelowa                                                                                          |
| `threshold`              | Skonfigurowany próg, który wyzwolił wykrywanie                                                                |
| `detection_delay_min`    | Skonfigurowane opóźnienie wykrywania                                                                          |
| `state_attributes`       | Wszystkie atrybuty encji w momencie zdarzenia                                                                 |

## Przykłady automatyzacji

### Trwałe powiadomienie w przypadku awarii ogrzewania

Ta automatyzacja tworzy trwałe powiadomienie po wykryciu awarii ogrzewania:

```yaml
alias: "Alert awarii ogrzewania"
description: "Tworzy trwałe powiadomienie w przypadku awarii ogrzewania"
trigger:
    - platform: event
      event_type: versatile_thermostat_heating_failure_event
condition:
    - condition: template
      value_template: "{{ trigger.event.data.type == 'heating_failure_start' }}"
action:
    - service: persistent_notification.create
      data:
        title: "🔥 Wykryto awarię ogrzewania"
        message: >
        Termostat **{{ trigger.event.data.name }}** wykrył awarię ogrzewania.

        📊 **Szczegóły:**
        - Żądana moc: {{ (trigger.event.data.on_percent * 100) | round(0) }}%
        - Aktualna temperatura: {{ trigger.event.data.current_temp }}°C
        - Temperatura docelowa: {{ trigger.event.data.target_temp }}°C
        - Zmiana temperatury: {{ trigger.event.data.temperature_difference | round(2) }}°C

        ⚠️ Ogrzewanie działa z pełną mocą, ale temperatura nie rośnie.
        Sprawdź, czy grzejnik działa poprawnie.
        notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
```

### Trwałe powiadomienie dla wszystkich typów awarii

Ta automatyzacja obsługuje oba typy awarii (ogrzewania i chłodzenia):

```yaml
alias: "Alert anomalii ogrzewania"
description: "Powiadomienie dla wszystkich typów awarii ogrzewania"
trigger:
    - platform: event
      event_type: versatile_thermostat_heating_failure_event
condition:
    - condition: template
      value_template: "{{ trigger.event.data.type in ['heating_failure_start', 'cooling_failure_start'] }}"
action:
    - service: persistent_notification.create
      data:
        title: >
        {% if trigger.event.data.failure_type == 'heating' %}
            🔥 Wykryto awarię ogrzewania
        {% else %}
            ❄️ Wykryto awarię chłodzenia
        {% endif %}
      message: >
        Termostat **{{ trigger.event.data.name }}** wykrył anomalię.

        📊 **Szczegóły:**
        - Typ awarii: {{ trigger.event.data.failure_type }}
        - Żądana moc: {{ (trigger.event.data.on_percent * 100) | round(0) }}%
        - Aktualna temperatura: {{ trigger.event.data.current_temp }}°C
        - Temperatura docelowa: {{ trigger.event.data.target_temp }}°C
        - Zmiana temperatury: {{ trigger.event.data.temperature_difference | round(2) }}°C

        {% if trigger.event.data.failure_type == 'heating' %}
        ⚠️ Ogrzewanie działa na {{ (trigger.event.data.on_percent * 100) | round(0) }}%, ale temperatura nie rośnie.
        Sprawdź, czy grzejnik działa poprawnie.
        {% else %}
        ⚠️ Ogrzewanie jest wyłączone, ale temperatura nadal rośnie.
        Sprawdź, czy grzejnik wyłącza się poprawnie.
        {% endif %}
      notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
```

### Automatyczne usuwanie powiadomienia po rozwiązaniu awarii

Ta automatyzacja usuwa trwałe powiadomienie po rozwiązaniu awarii:

```yaml
alias: "Koniec alertu anomalii ogrzewania"
description: "Usuwa powiadomienie po rozwiązaniu awarii"
trigger:
    - platform: event
      event_type: versatile_thermostat_heating_failure_event
condition:
    - condition: template
      value_template: "{{ trigger.event.data.type in ['heating_failure_end', 'cooling_failure_end'] }}"
action:
    - service: persistent_notification.dismiss
      data:
        notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
    - service: persistent_notification.create
      data:
        title: "✅ Anomalia rozwiązana"
        message: >
        Termostat **{{ trigger.event.data.name }}** znów działa normalnie.
        notification_id: "heating_failure_resolved_{{ trigger.event.data.entity_id }}"
    # Automatycznie usuwa powiadomienie o rozwiązaniu po 1 godzinie
    - delay:
        hours: 1
    - service: persistent_notification.dismiss
      data:
        notification_id: "heating_failure_resolved_{{ trigger.event.data.entity_id }}"
```

> ![Wskazówka](../../images/tips.png) _*Uwagi*_
>
> 1. Trwałe powiadomienia pozostają wyświetlane, dopóki użytkownik ich nie zamknie lub nie zostaną usunięte przez automatyzację.
> 2. Użycie `notification_id` pozwala na aktualizację lub usunięcie konkretnego powiadomienia.
> 3. Możesz dostosować te automatyzacje, aby wysyłać powiadomienia na telefon, Telegram lub dowolną inną usługę powiadomień.
> 4. Ta funkcja działa tylko z termostatami _VTherm_ używającymi algorytmu TPI (over_switch, over_valve lub over_climate z regulacją zaworem).
