# Preset czasowy

- [Preset czasowy](#preset-czasowy)
  - [Cel](#cel)
  - [Jak to działa](#jak-to-działa)
  - [Aktywacja presetu czasowego](#aktywacja-presetu-czasowego)
  - [Anulowanie presetu czasowego](#anulowanie-presetu-czasowego)
  - [Atrybuty niestandardowe](#atrybuty-niestandardowe)
  - [Zdarzenia](#zdarzenia)
  - [Ręczne nadpisanie z automatycznym powrotem](#ręczne-nadpisanie-z-automatycznym-powrotem)
  - [Przykłady automatyzacji](#przykłady-automatyzacji)
    - [30-minutowy boost po powrocie do domu](#30-minutowy-boost-po-powrocie-do-domu)
    - [Powiadomienie na koniec boostu](#powiadomienie-na-koniec-boostu)
    - [Przycisk boost na dashboardzie](#przycisk-boost-na-dashboardzie)

## Cel

Funkcja presetu czasowego pozwala wymusić preset na _VTherm_ przez określony czas. Po upływie tego czasu oryginalny preset (ten zdefiniowany w `requested_state`) jest automatycznie przywracany.

Ta funkcja jest przydatna w kilku scenariuszach:
- **Boost ogrzewania**: Tymczasowo zwiększ temperaturę (np. preset Komfort) na 30 minut po powrocie do domu
- **Tryb gościa**: Aktywuj cieplejszy preset na kilka godzin podczas przyjmowania gości
- **Suszenie**: Wymuś wysoki preset na ograniczony czas, aby przyspieszyć suszenie pomieszczenia
- **Okazjonalne oszczędności**: Tymczasowo wymuś preset Eco podczas krótkiej nieobecności

## Jak to działa

1. Wywołujesz usługę `versatile_thermostat.set_timed_preset` z presetem i czasem trwania
2. _VTherm_ natychmiast przełącza się na określony preset
3. Uruchamiany jest timer na wskazany czas
4. Po zakończeniu timera _VTherm_ automatycznie przywraca oryginalny preset
5. Przy każdej zmianie emitowane jest zdarzenie `versatile_thermostat_timed_preset_event`

> ![Tip](images/tips.png) _*Uwagi*_
> - Preset czasowy ma pośredni priorytet: jest stosowany po kontrolach bezpieczeństwa i mocy (odciążenie), ale przed innymi funkcjami (obecność, ruch itp.)
> - Jeśli ręcznie zmienisz preset podczas aktywnego presetu czasowego, timer zostanie anulowany
> - Maksymalny czas trwania to 1440 minut (24 godziny)

## Aktywacja presetu czasowego

Aby aktywować preset czasowy, użyj usługi `versatile_thermostat.set_timed_preset`:

```yaml
service: versatile_thermostat.set_timed_preset
data:
  preset: "boost"
  duration_minutes: 30
target:
  entity_id: climate.moj_termostat
```

Parametry:
- `preset`: Nazwa presetu do aktywacji. Musi być prawidłowym presetem skonfigurowanym na _VTherm_ (np. `eco`, `comfort`, `boost`, `frost` itp.)
- `duration_minutes`: Czas trwania w minutach (od 1 do 1440)

## Anulowanie presetu czasowego

Aby anulować preset czasowy przed upływem jego czasu, użyj usługi `versatile_thermostat.cancel_timed_preset`:

```yaml
service: versatile_thermostat.cancel_timed_preset
target:
  entity_id: climate.moj_termostat
```

Gdy anulujesz preset czasowy, oryginalny preset jest natychmiast przywracany.

## Atrybuty niestandardowe

Gdy preset czasowy jest aktywny, następujące atrybuty są dostępne w sekcji `timed_preset_manager` atrybutów _VTherm_:

| Atrybut              | Znaczenie                                                                                                                     |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `is_active`          | `true` jeśli preset czasowy jest aktywny, w przeciwnym razie `false`                                                          |
| `preset`             | Nazwa aktywnego presetu czasowego (lub `null` jeśli brak)                                                                     |
| `original_preset`    | Preset przywracany po zakończeniu presetu czasowego (lub `null` jeśli brak)                                                   |
| `end_time`           | Data/czas zakończenia presetu czasowego (format ISO, lub `null` jeśli brak)                                                   |
| `remaining_time_min` | Pozostały czas w minutach do zakończenia presetu czasowego (liczba całkowita)                                                 |
| `is_manual_override` | `true`, jeśli aktywny preset czasowy jest ręcznym nadpisaniem (zobacz [poniżej](#ręczne-nadpisanie-z-automatycznym-powrotem)) |
| `resume_preset`      | Preset czasowy przerwany przez ręczne nadpisanie, wznawiany po jego zakończeniu (lub `null`)                                  |
| `resume_end_time`    | Data/godzina zakończenia przerwanego presetu czasowego (format ISO, lub `null`)                                               |

Przykład atrybutów:
```yaml
timed_preset_manager:
  is_active: true
  preset: "boost"
  original_preset: "comfort"
  end_time: "2024-01-15T14:30:00+00:00"
  remaining_time_min: 25
  is_manual_override: false
  resume_preset: null
  resume_end_time: null
```

## Zdarzenia

Zdarzenie `versatile_thermostat_timed_preset_event` jest emitowane przy zmianach presetu czasowego.

Dane zdarzenia:
- `entity_id`: Identyfikator _VTherm_
- `name`: Nazwa _VTherm_
- `state_attributes`: Atrybuty stanu _VTherm_ w chwili zdarzenia
- `type`: `start`, gdy preset czasowy (lub ręczne nadpisanie) się rozpoczyna, `end`, gdy się kończy
- `preset`: Dotyczący preset czasowy (ten, który się rozpoczyna, lub ten, który właśnie się zakończył)

Dodatkowe dane zdarzenia `start`:
- `duration_minutes`: Czas trwania presetu czasowego w minutach
- `end_time`: Data/czas zakończenia presetu czasowego (format ISO)
- `original_preset`: Preset, który zostanie przywrócony na końcu
- `manual_override`: `true`, jeśli zdarzenie dotyczy ręcznego nadpisania

Dodatkowe dane zdarzenia `end`:
- `cause`: Powód zakończenia presetu czasowego: `expired` (czas upłynął), `cancelled` (wywołano usługę `cancel_timed_preset`) lub `preset_selected` (preset wybrano ręcznie)
- `restored_preset`: Preset przywrócony po zakończeniu (może być `null`, gdy preset wybrano ręcznie)
- `manual_override`: `true`, jeśli zdarzenie dotyczy ręcznego nadpisania

## Ręczne nadpisanie z automatycznym powrotem

Gdy ręcznie zmienisz temperaturę docelową, _VTherm_ zwykle przełącza się na preset `none` i pozostaje na nim, dopóki ponownie nie wybierzesz presetu. Jeśli skonfigurowano **czas ręcznego nadpisania**, _VTherm_ po tym czasie automatycznie wraca do poprzedniego stanu.

Czas ustawia się w konfiguracji zaawansowanej (`manual_override_duration_min`, w minutach). Można go zdefiniować w konfiguracji centralnej i nadpisać dla każdego _VTherm_. Zobacz [konfiguracja zaawansowana](feature-advanced.md#czas-ręcznego-nadpisania). Wartość domyślna `0` wyłącza funkcję i zachowanie pozostaje bez zmian.

Jak to działa:
1. Ręczna zmiana temperatury docelowej (z interfejsu, z automatyzacji wywołującej `climate.set_temperature` lub z urządzenia bazowego, gdy włączono `Follow underlying temperature change`) uruchamia ręczne nadpisanie. Ręczna temperatura obowiązuje natychmiast.
2. Kolejna ręczna zmiana w trakcie nadpisania uruchamia licznik od nowa z pełnym czasem.
3. Po upływie czasu przywracany jest preset aktywny przed ręczną zmianą.
4. Jeśli w chwili ręcznej zmiany aktywny był preset czasowy, po zakończeniu nadpisania zostaje on wznowiony aż do własnego czasu zakończenia. Jeśli ten czas już minął, przywracany jest preset aktywny przed presetem czasowym.
5. Jeśli przed ręczną zmianą nie był aktywny żaden preset (`none`), nadpisanie nie jest uruchamiane.

Ręczne nadpisanie wykorzystuje mechanizm presetów czasowych: jest widoczne jako preset czasowy `none` i przetrwa restart Home Assistant.

> ![Wskazówka](images/tips.png) _*Uwagi*_
> - Wybranie presetu w trakcie ręcznego nadpisania anuluje je: obowiązuje wybrany preset i później nic nie jest przywracane.
> - Ustawienie presetu czasowego w trakcie ręcznego nadpisania zastępuje je.
> - Anulowanie presetu czasowego w trakcie ręcznego nadpisania przywraca preset aktywny przed ręczną zmianą.
> - Okno, bezpieczeństwo, ograniczanie mocy i tryb centralny zachowują swój priorytet w trakcie ręcznego nadpisania.

Atrybuty `is_manual_override`, `resume_preset` i `resume_end_time` w `timed_preset_manager` opisano w tabeli [Atrybuty niestandardowe](#atrybuty-niestandardowe). Pole `manual_override` zdarzenia `versatile_thermostat_timed_preset_event` ma wartość `true`, gdy zdarzenie dotyczy ręcznego nadpisania.

## Przykłady automatyzacji

### 30-minutowy boost po powrocie do domu

```yaml
automation:
  - alias: "Boost ogrzewania po powrocie"
    trigger:
      - platform: state
        entity_id: binary_sensor.obecnosc_dom
        to: "on"
    condition:
      - condition: numeric_state
        entity_id: climate.salon
        attribute: current_temperature
        below: 19
    action:
      - service: versatile_thermostat.set_timed_preset
        data:
          preset: "boost"
          duration_minutes: 30
        target:
          entity_id: climate.salon
```

### Powiadomienie na koniec boostu

```yaml
automation:
  - alias: "Powiadomienie o końcu boostu"
    trigger:
      - platform: event
        event_type: versatile_thermostat_timed_preset_event
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.type == 'end' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Termostat"
          message: "Boost dla {{ trigger.event.data.name }} zakończony"
```

### Przycisk boost na dashboardzie

Utwórz przycisk z typem karty `button`:

```yaml
type: button
tap_action:
  action: call-service
  service: versatile_thermostat.set_timed_preset
  data:
    preset: boost
    duration_minutes: 30
  target:
    entity_id: climate.salon
name: Boost 30 min
icon: mdi:fire
```
