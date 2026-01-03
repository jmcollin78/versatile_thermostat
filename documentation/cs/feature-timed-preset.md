# Časově omezený preset

- [Časově omezený preset](#časově-omezený-preset)
  - [Účel](#účel)
  - [Jak to funguje](#jak-to-funguje)
  - [Aktivace časově omezeného presetu](#aktivace-časově-omezeného-presetu)
  - [Zrušení časově omezeného presetu](#zrušení-časově-omezeného-presetu)
  - [Vlastní atributy](#vlastní-atributy)
  - [Události](#události)
  - [Příklady automatizace](#příklady-automatizace)

## Účel

Funkce časově omezeného presetu umožňuje vynutit preset na _VTherm_ po určitou dobu. Po uplynutí této doby je automaticky obnoven původní preset (ten, který byl definován v `requested_state`).

Tato funkce je užitečná v několika scénářích:
- **Boost vytápění**: Dočasně zvýšit teplotu (např. preset Komfort) na 30 minut, když přijdete domů
- **Režim hostů**: Aktivovat teplejší preset na několik hodin při návštěvě hostů
- **Sušení**: Vynutit vysoký preset na omezenou dobu pro urychlení sušení místnosti
- **Příležitostné úspory**: Dočasně vynutit preset Eco během krátké nepřítomnosti

## Jak to funguje

1. Zavoláte službu `versatile_thermostat.set_timed_preset` s presetem a dobou trvání
2. _VTherm_ okamžitě přepne na zadaný preset
3. Spustí se časovač na uvedenou dobu
4. Po uplynutí časovače _VTherm_ automaticky obnoví původní preset
5. Při každé změně je vyslána událost `versatile_thermostat_timed_preset_event`

> ![Tip](images/tips.png) _*Poznámky*_
> - Časově omezený preset má střední prioritu: je aplikován po bezpečnostních kontrolách a kontrolách výkonu (odlehčení zátěže), ale před ostatními funkcemi (přítomnost, pohyb atd.)
> - Pokud ručně změníte preset, zatímco je aktivní časově omezený preset, časovač se zruší
> - Maximální doba trvání je 1440 minut (24 hodin)

## Aktivace časově omezeného presetu

Pro aktivaci časově omezeného presetu použijte službu `versatile_thermostat.set_timed_preset`:

```yaml
service: versatile_thermostat.set_timed_preset
data:
  preset: "boost"
  duration_minutes: 30
target:
  entity_id: climate.muj_termostat
```

Parametry:
- `preset`: Název presetu k aktivaci. Musí být platný preset nakonfigurovaný na _VTherm_ (např. `eco`, `comfort`, `boost`, `frost` atd.)
- `duration_minutes`: Doba trvání v minutách (mezi 1 a 1440)

## Zrušení časově omezeného presetu

Pro zrušení časově omezeného presetu před uplynutím doby použijte službu `versatile_thermostat.cancel_timed_preset`:

```yaml
service: versatile_thermostat.cancel_timed_preset
target:
  entity_id: climate.muj_termostat
```

Při zrušení časově omezeného presetu je okamžitě obnoven původní preset.

## Vlastní atributy

Když je aktivní časově omezený preset, jsou v sekci `timed_preset_manager` atributů _VTherm_ k dispozici následující atributy:

| Atribut                 | Význam                                                                  |
| ----------------------- | ----------------------------------------------------------------------- |
| `timed_preset_active`   | `true` pokud je časově omezený preset aktivní, jinak `false`            |
| `timed_preset_preset`   | Název aktivního časově omezeného presetu (nebo `null` pokud žádný)      |
| `timed_preset_end_time` | Datum/čas konce časově omezeného presetu (formát ISO)                   |
| `remaining_time_min`    | Zbývající čas v minutách do konce časově omezeného presetu (celé číslo) |

Příklad atributů:
```yaml
timed_preset_manager:
  timed_preset_active: true
  timed_preset_preset: "boost"
  timed_preset_end_time: "2024-01-15T14:30:00+00:00"
  remaining_time_min: 25
```

## Události

Událost `versatile_thermostat_timed_preset_event` je vyslána při změnách časově omezeného presetu.

Data události:
- `entity_id`: Identifikátor _VTherm_
- `name`: Název _VTherm_
- `timed_preset_active`: `true` pokud byl právě aktivován časově omezený preset, `false` pokud byl právě deaktivován
- `timed_preset_preset`: Název časově omezeného presetu
- `old_preset`: Předchozí preset (před aktivací časově omezeného presetu)
- `new_preset`: Nový aktivní preset

## Příklady automatizace

### 30minutový boost při příchodu domů

```yaml
automation:
  - alias: "Boost vytápění při příchodu"
    trigger:
      - platform: state
        entity_id: binary_sensor.pritomnost_doma
        to: "on"
    condition:
      - condition: numeric_state
        entity_id: climate.obyvaci_pokoj
        attribute: current_temperature
        below: 19
    action:
      - service: versatile_thermostat.set_timed_preset
        data:
          preset: "boost"
          duration_minutes: 30
        target:
          entity_id: climate.obyvaci_pokoj
```

### Oznámení na konci boostu

```yaml
automation:
  - alias: "Oznámení konce boostu"
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
          message: "Boost pro {{ trigger.event.data.name }} skončil"
```

### Tlačítko boostu na dashboardu

Vytvořte tlačítko s typem karty `button`:

```yaml
type: button
tap_action:
  action: call-service
  service: versatile_thermostat.set_timed_preset
  data:
    preset: boost
    duration_minutes: 30
  target:
    entity_id: climate.obyvaci_pokoj
name: Boost 30 min
icon: mdi:fire
```
