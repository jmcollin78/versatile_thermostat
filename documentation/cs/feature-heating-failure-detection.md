# Detekce poruchy vytápění

- [Detekce poruchy vytápění](#detekce-poruchy-vytápění)
  - [Proč tato funkce?](#proč-tato-funkce)
  - [Princip fungování](#princip-fungování)
    - [Detekce poruchy vytápění](#detekce-poruchy-vytápění-1)
    - [Detekce poruchy chlazení](#detekce-poruchy-chlazení)
  - [Konfigurace](#konfigurace)
  - [Parametry](#parametry)
  - [Exponované atributy](#exponované-atributy)
  - [Binární senzor](#binární-senzor)
  - [Události](#události)
  - [Příklady automatizace](#příklady-automatizace)
    - [Trvalé oznámení v případě poruchy vytápění](#trvalé-oznámení-v-případě-poruchy-vytápění)
    - [Trvalé oznámení pro všechny typy poruch](#trvalé-oznámení-pro-všechny-typy-poruch)
    - [Automatické odstranění oznámení po vyřešení poruchy](#automatické-odstranění-oznámení-po-vyřešení-poruchy)

## Proč tato funkce?

Detekce poruchy vytápění umožňuje sledovat správnou funkci vašeho topného systému. Detekuje dvě abnormální situace:

1. **Porucha vytápění**: termostat požaduje vysoký výkon (`on_percent` vysoké), ale teplota nestoupá. To může naznačovat:
   - vadný nebo vypnutý radiátor,
   - zablokovaný termostatický ventil,
   - nedetekované otevřené okno,
   - problém s cirkulací teplé vody (ústřední topení).

2. **Porucha chlazení**: termostat nepožaduje výkon (`on_percent` na 0), ale teplota stále stoupá. To může naznačovat:
   - radiátor, který zůstává zapnutý navzdory příkazu k vypnutí,
   - relé zablokované v poloze "zapnuto",
   - podkladové zařízení, které již nereaguje.

> ![Tip](../../images/tips.png) _*Důležité*_
>
> Tato funkce **nemění chování termostatu**. Pouze odesílá události, které vás upozorní na abnormální situaci. Je na vás, abyste vytvořili potřebné automatizace pro reakci na tyto události (oznámení, výstrahy atd.).

## Princip fungování

Tato funkce se vztahuje pouze na _VTherm_ používající algoritmus TPI (over_switch, over_valve nebo over_climate s regulací ventilem). _VTherm_ `over_climate`, který ovládá například tepelné čerpadlo, se tedy netýká. V tomto případě totiž rozhodnutí o vytápění či nevytápění činí samotné podkladové zařízení, což brání přístupu ke spolehlivým informacím.

Tato funkce se vztahuje pouze na režim Vytápění (`hvac_mode=heat`). V režimu klimatizace (`hvac_mode=cool`) se neprovádí žádná detekce, aby se zabránilo falešným poplachům.

### Detekce poruchy vytápění

1. _VTherm_ je v režimu vytápění,
2. `on_percent` je vyšší nebo roven nastavenému prahu (ve výchozím nastavení 90 %),
3. Tato situace trvá déle než doba detekce (ve výchozím nastavení 15 minut),
4. Teplota během tohoto období nestoupla.

➡️ Je odeslána událost `versatile_thermostat_heating_failure_event` s `failure_type: heating` a `type: heating_failure_start`.

Když se situace vrátí do normálu (teplota stoupá nebo `on_percent` klesá), je odeslána událost s `type: heating_failure_end`.

### Detekce poruchy chlazení

1. _VTherm_ je v režimu vytápění,
2. `on_percent` je nižší nebo roven nastavenému prahu (ve výchozím nastavení 0 %),
3. Tato situace trvá déle než doba detekce (ve výchozím nastavení 15 minut),
4. Teplota stále stoupá.

➡️ Je odeslána událost `versatile_thermostat_heating_failure_event` s `failure_type: cooling` a `type: cooling_failure_start`.

Když se situace vrátí do normálu, je odeslána událost s `type: cooling_failure_end`.

## Konfigurace

Stejně jako mnoho funkcí _VTherm_, i tuto funkci lze konfigurovat **v centrální konfiguraci** pro sdílení parametrů. Pro použití na vybraných _VTherm_ musí uživatel přidat funkci (viz menu "Funkce") a zvolit použití společných parametrů centrální konfigurace nebo zadat nové, které budou použity pouze pro tento _VTherm_.

Pro přístup:
1. Přejděte do konfigurace vašeho _VTherm_ typu "Centrální konfigurace"
2. V menu vyberte "Heating failure detection" (Detekce poruchy vytápění)
3. Poté přejděte do konfigurace příslušných _VTherm_,
4. Vyberte menu "Funkce",
5. Zaškrtněte funkci "Detekce poruch vytápění",
6. Zvolte použití parametrů centrální konfigurace nebo zadejte nové.

![Konfigurace](../../images/config-heating-failure-detection.png)

## Parametry

| Parametr                               | Popis                                                                                                    | Výchozí hodnota |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------- |
| **Aktivovat detekci poruchy vytápění** | Aktivuje nebo deaktivuje funkci                                                                          | Deaktivováno    |
| **Práh poruchy vytápění**              | Procento `on_percent`, nad kterým by vytápění mělo zvyšovat teplotu. Hodnota mezi 0 a 1 (0.9 = 90 %)     | 0.9 (90 %)      |
| **Práh poruchy chlazení**              | Procento `on_percent`, pod kterým by teplota neměla stoupat. Hodnota mezi 0 a 1 (0 = 0 %)                | 0.0 (0 %)       |
| **Doba detekce (minuty)**              | Doba čekání před vyhlášením poruchy. Umožňuje vyhnout se falešným poplachům způsobeným normálními výkyvy | 15 minut        |
| **Tolerance změny teploty (°C)**       | Minimální změna teploty ve stupních, aby byla považována za významnou. Umožňuje filtrovat šum senzorů    | 0.5 °C          |

> ![Tip](../../images/tips.png) _*Rady pro nastavení*_
>
> - **Práh vytápění**: Pokud máte falešné poplachy (detekce poruchy, i když vše funguje), zvyšte tento práh k 0.95 nebo 1.0.
> - **Práh chlazení**: Pokud chcete detekovat radiátor, který zůstává zapnutý i při nízkém `on_percent`, zvyšte tento práh k 0.05 nebo 0.1.
> - **Doba detekce**: Zvyšte tuto dobu, pokud máte místnosti s velkou tepelnou setrvačností (velké místnosti, podlahové vytápění atd.). Můžete se podívat na křivky vytápění (viz [doplňky](../../additions.md#courbes-de-régulattion-avec-plotly)) a zjistit, za jak dlouho váš teploměr stoupne po spuštění vytápění. Tato doba by měla být minimem pro tento parametr.
> - **Tolerance**: Pokud máte nepřesné nebo zašuměné senzory, zvyšte tuto hodnotu (např. 0.8 °C). Mnoho senzorů má přesnost ±0.5 °C.

## Exponované atributy

_VTherm_ s TPI vystavují následující atributy:

```yaml
is_heating_failure_detection_configured: true
heating_failure_detection_manager:
  heating_failure_state: "off"      # "on", "off", "unknown", "unavailable"
  cooling_failure_state: "off"      # "on", "off", "unknown", "unavailable"
  heating_failure_threshold: 0.9
  cooling_failure_threshold: 0.0
  detection_delay_min: 15
  temperature_change_tolerance: 0.5
  heating_tracking:                 # Sledování detekce poruchy vytápění
    is_tracking: true               # Probíhá detekce?
    initial_temperature: 19.5       # Teplota na začátku sledování
    current_temperature: 19.7       # Aktuální teplota
    remaining_time_min: 8.5         # Zbývající minuty do výstrahy
    elapsed_time_min: 6.5           # Uplynulé minuty od začátku
  cooling_tracking:                 # Sledování detekce poruchy chlazení
    is_tracking: false
    initial_temperature: null
    current_temperature: null
    remaining_time_min: null
    elapsed_time_min: null
```

## Binární senzor

Když je detekce poruchy vytápění aktivována, automaticky se vytvoří binární senzor pro každý příslušný _VTherm_:

| Entita                                        | Popis                                                      |
| --------------------------------------------- | ---------------------------------------------------------- |
| `binary_sensor.<jméno>_heating_failure_state` | Indikuje, zda je detekována porucha vytápění nebo chlazení |

Zobrazovaný název senzoru je přeložen podle jazyka vašeho Home Assistant "Stav poruchy vytápění".

Tento senzor je:
- **ON**, když je detekována porucha (vytápění nebo chlazení)
- **OFF**, když systém funguje normálně

Vlastnosti:
- **Device class**: `problem` (umožňuje nativní výstrahy Home Assistant)
- **Ikony**:
  - `mdi:radiator-off`, když je detekována porucha
  - `mdi:radiator`, když vše funguje

Tento binární senzor lze použít přímo ve vašich automatizacích jako spouštěč nebo pro vytváření výstrah prostřednictvím nativních oznámení Home Assistant.

## Události

Událost `versatile_thermostat_heating_failure_event` je odeslána při detekci nebo ukončení poruchy.

Data události:
| Pole                     | Popis                                                                                                        |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `entity_id`              | Identifikátor _VTherm_                                                                                       |
| `name`                   | Název _VTherm_                                                                                               |
| `type`                   | Typ události: `heating_failure_start`, `heating_failure_end`, `cooling_failure_start`, `cooling_failure_end` |
| `failure_type`           | Typ poruchy: `heating` nebo `cooling`                                                                        |
| `on_percent`             | Procento požadovaného výkonu v okamžiku detekce                                                              |
| `temperature_difference` | Rozdíl teplot pozorovaný během období detekce                                                                |
| `current_temp`           | Aktuální teplota                                                                                             |
| `target_temp`            | Cílová teplota                                                                                               |
| `threshold`              | Nastavený práh, který spustil detekci                                                                        |
| `detection_delay_min`    | Nastavená doba detekce                                                                                       |
| `state_attributes`       | Všechny atributy entity v okamžiku události                                                                  |

## Příklady automatizace

### Trvalé oznámení v případě poruchy vytápění

Tato automatizace vytvoří trvalé oznámení, když je detekována porucha vytápění:

```yaml
alias: "Výstraha poruchy vytápění"
description: "Vytvoří trvalé oznámení v případě poruchy vytápění"
trigger:
    - platform: event
      event_type: versatile_thermostat_heating_failure_event
condition:
    - condition: template
      value_template: "{{ trigger.event.data.type == 'heating_failure_start' }}"
action:
    - service: persistent_notification.create
      data:
        title: "🔥 Detekována porucha vytápění"
        message: >
        Termostat **{{ trigger.event.data.name }}** detekoval poruchu vytápění.

        📊 **Podrobnosti:**
        - Požadovaný výkon: {{ (trigger.event.data.on_percent * 100) | round(0) }}%
        - Aktuální teplota: {{ trigger.event.data.current_temp }}°C
        - Cílová teplota: {{ trigger.event.data.target_temp }}°C
        - Změna teploty: {{ trigger.event.data.temperature_difference | round(2) }}°C

        ⚠️ Vytápění běží na plný výkon, ale teplota nestoupá.
        Zkontrolujte, zda radiátor funguje správně.
        notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
```

### Trvalé oznámení pro všechny typy poruch

Tato automatizace řeší oba typy poruch (vytápění a chlazení):

```yaml
alias: "Výstraha anomálie vytápění"
description: "Oznámení pro všechny typy poruch vytápění"
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
            🔥 Detekována porucha vytápění
        {% else %}
            ❄️ Detekována porucha chlazení
        {% endif %}
      message: >
        Termostat **{{ trigger.event.data.name }}** detekoval anomálii.

        📊 **Podrobnosti:**
        - Typ poruchy: {{ trigger.event.data.failure_type }}
        - Požadovaný výkon: {{ (trigger.event.data.on_percent * 100) | round(0) }}%
        - Aktuální teplota: {{ trigger.event.data.current_temp }}°C
        - Cílová teplota: {{ trigger.event.data.target_temp }}°C
        - Změna teploty: {{ trigger.event.data.temperature_difference | round(2) }}°C

        {% if trigger.event.data.failure_type == 'heating' %}
        ⚠️ Vytápění běží na {{ (trigger.event.data.on_percent * 100) | round(0) }}%, ale teplota nestoupá.
        Zkontrolujte, zda radiátor funguje správně.
        {% else %}
        ⚠️ Vytápění je vypnuté, ale teplota stále stoupá.
        Zkontrolujte, zda se radiátor správně vypíná.
        {% endif %}
      notification_id: "heating_failure_{{ trigger.event.data.entity_id }}"
```

### Automatické odstranění oznámení po vyřešení poruchy

Tato automatizace odstraní trvalé oznámení, když je porucha vyřešena:

```yaml
alias: "Konec výstrahy anomálie vytápění"
description: "Odstraní oznámení, když je porucha vyřešena"
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
        title: "✅ Anomálie vyřešena"
        message: >
        Termostat **{{ trigger.event.data.name }}** opět funguje normálně.
        notification_id: "heating_failure_resolved_{{ trigger.event.data.entity_id }}"
    # Automaticky odstraní oznámení o vyřešení po 1 hodině
    - delay:
        hours: 1
    - service: persistent_notification.dismiss
      data:
        notification_id: "heating_failure_resolved_{{ trigger.event.data.entity_id }}"
```

> ![Tip](../../images/tips.png) _*Poznámky*_
>
> 1. Trvalá oznámení zůstávají zobrazena, dokud je uživatel nezavře nebo dokud nejsou odstraněna automatizací.
> 2. Použití `notification_id` umožňuje aktualizovat nebo odstranit konkrétní oznámení.
> 3. Tyto automatizace můžete upravit pro odesílání oznámení na mobil, Telegram nebo jakoukoli jinou oznamovací službu.
> 4. Tato funkce funguje pouze s _VTherm_ používajícími algoritmus TPI (over_switch, over_valve nebo over_climate s regulací ventilem).
