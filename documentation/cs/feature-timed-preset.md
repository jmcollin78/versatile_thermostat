# Časově omezený preset

- [Časově omezený preset](#časově-omezený-preset)
  - [Účel](#účel)
  - [Jak to funguje](#jak-to-funguje)
  - [Aktivace časově omezeného presetu](#aktivace-časově-omezeného-presetu)
  - [Zrušení časově omezeného presetu](#zrušení-časově-omezeného-presetu)
  - [Vlastní atributy](#vlastní-atributy)
  - [Události](#události)
  - [Ruční přepsání s automatickým návratem](#ruční-přepsání-s-automatickým-návratem)
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

| Atribut              | Význam                                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------------------------- |
| `is_active`          | `true` pokud je časově omezený preset aktivní, jinak `false`                                               |
| `preset`             | Název aktivního časově omezeného presetu (nebo `null` pokud žádný)                                         |
| `original_preset`    | Preset obnovený na konci časově omezeného presetu (nebo `null` pokud žádný)                                |
| `end_time`           | Datum/čas konce časově omezeného presetu (formát ISO, nebo `null` pokud žádný)                             |
| `remaining_time_min` | Zbývající čas v minutách do konce časově omezeného presetu (celé číslo)                                    |
| `is_manual_override` | `true`, pokud je aktivní timed preset ruční přepsání (viz [níže](#ruční-přepsání-s-automatickým-návratem)) |
| `resume_preset`      | Timed preset přerušený ručním přepsáním, obnovený po jeho skončení (nebo `null`)                           |
| `resume_end_time`    | Datum/čas ukončení přerušeného timed presetu (formát ISO, nebo `null`)                                     |

Příklad atributů:
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

## Události

Událost `versatile_thermostat_timed_preset_event` je vyslána při změnách časově omezeného presetu.

Data události:
- `entity_id`: Identifikátor _VTherm_
- `name`: Název _VTherm_
- `state_attributes`: Stavové atributy _VTherm_ v okamžiku události
- `type`: `start`, když časově omezený preset (nebo ruční přepsání) začíná, `end`, když končí
- `preset`: Dotčený časově omezený preset (ten, který začíná, nebo ten, který právě skončil)

Další data události `start`:
- `duration_minutes`: Doba trvání časově omezeného presetu v minutách
- `end_time`: Datum/čas konce časově omezeného presetu (formát ISO)
- `original_preset`: Preset, který bude na konci obnoven
- `manual_override`: `true`, pokud se událost týká ručního přepsání

Další data události `end`:
- `cause`: Důvod ukončení časově omezeného presetu: `expired` (doba uplynula), `cancelled` (byla zavolána služba `cancel_timed_preset`) nebo `preset_selected` (preset byl vybrán ručně)
- `restored_preset`: Preset obnovený po skončení (může být `null`, pokud byl preset vybrán ručně)
- `manual_override`: `true`, pokud se událost týká ručního přepsání

## Ruční přepsání s automatickým návratem

Když ručně změníte cílovou teplotu, _VTherm_ obvykle přepne na preset `none` a zůstane na něm, dokud znovu nevyberete preset. Pokud je nastavena **doba ručního přepsání**, _VTherm_ se po této době automaticky vrátí.

Doba se nastavuje v pokročilé konfiguraci (`manual_override_duration_min`, v minutách). Lze ji definovat v centrální konfiguraci a přepsat pro jednotlivý _VTherm_. Viz [pokročilá konfigurace](feature-advanced.md#doba-ručního-přepsání). Výchozí hodnota `0` funkci vypíná a chování zůstává beze změny.

Jak to funguje:
1. Ruční změna cílové teploty (z UI, z automatizace volající `climate.set_temperature` nebo z podkladového zařízení, když je zapnuto `Follow underlying temperature change`) spustí ruční přepsání. Ruční teplota platí okamžitě.
2. Další ruční změna během přepsání spustí časovač znovu s plnou dobou.
3. Po vypršení časovače se obnoví preset, který byl aktivní před ruční změnou.
4. Pokud byl v okamžiku ruční změny aktivní timed preset, po skončení přepsání se obnoví až do svého vlastního času ukončení. Pokud tento čas již uplynul, obnoví se preset, který byl aktivní před timed presetem.
5. Pokud před ruční změnou nebyl aktivní žádný preset (`none`), přepsání se nespustí.

Ruční přepsání využívá mechanismus timed presetů: zobrazuje se jako timed preset `none` a přežije restart Home Assistant.

> ![Tip](images/tips.png) _*Poznámky*_
> - Výběr presetu během ručního přepsání ho zruší: platí vybraný preset a později se nic neobnovuje.
> - Nastavení timed presetu během ručního přepsání ho nahradí.
> - Zrušení timed presetu během ručního přepsání obnoví preset, který byl aktivní před ruční změnou.
> - Okno, bezpečnost, odlehčení zátěže a centrální režim si během ručního přepsání zachovávají svou prioritu.

Atributy `is_manual_override`, `resume_preset` a `resume_end_time` v `timed_preset_manager` jsou popsány v tabulce [Vlastní atributy](#vlastní-atributy). Pole `manual_override` události `versatile_thermostat_timed_preset_event` je `true`, když se událost týká ručního přepsání.

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
        value_template: "{{ trigger.event.data.type == 'end' }}"
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
