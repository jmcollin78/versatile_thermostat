# Preset czasowy

- [Preset czasowy](#preset-czasowy)
  - [Cel](#cel)
  - [Jak to działa](#jak-to-działa)
  - [Aktywacja presetu czasowego](#aktywacja-presetu-czasowego)
  - [Anulowanie presetu czasowego](#anulowanie-presetu-czasowego)
  - [Atrybuty niestandardowe](#atrybuty-niestandardowe)
  - [Zdarzenia](#zdarzenia)
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

| Atrybut                 | Znaczenie                                                                     |
| ----------------------- | ----------------------------------------------------------------------------- |
| `timed_preset_active`   | `true` jeśli preset czasowy jest aktywny, w przeciwnym razie `false`          |
| `timed_preset_preset`   | Nazwa aktywnego presetu czasowego (lub `null` jeśli brak)                     |
| `timed_preset_end_time` | Data/czas zakończenia presetu czasowego (format ISO)                          |
| `remaining_time_min`    | Pozostały czas w minutach do zakończenia presetu czasowego (liczba całkowita) |

Przykład atrybutów:
```yaml
timed_preset_manager:
  timed_preset_active: true
  timed_preset_preset: "boost"
  timed_preset_end_time: "2024-01-15T14:30:00+00:00"
  remaining_time_min: 25
```

## Zdarzenia

Zdarzenie `versatile_thermostat_timed_preset_event` jest emitowane przy zmianach presetu czasowego.

Dane zdarzenia:
- `entity_id`: Identyfikator _VTherm_
- `name`: Nazwa _VTherm_
- `timed_preset_active`: `true` jeśli preset czasowy właśnie został aktywowany, `false` jeśli właśnie został dezaktywowany
- `timed_preset_preset`: Nazwa presetu czasowego
- `old_preset`: Poprzedni preset (przed aktywacją presetu czasowego)
- `new_preset`: Nowy aktywny preset

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
        value_template: "{{ trigger.event.data.timed_preset_active == false }}"
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
