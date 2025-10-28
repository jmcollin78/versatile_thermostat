# Některé důležité doplňky

- [Některé důležité doplňky](#některé-důležité-doplňky)
  - [Karta Versatile Thermostat UI](#karta-versatile-thermostat-ui)
  - [Komponenta Scheduler!](#komponenta-scheduler)
  - [Regulační křivky s Plotly pro doladění vašeho termostatu](#regulační-křivky-s-plotly-pro-doladění-vašeho-termostatu)
  - [Oznámení událostí s AppDaemon NOTIFIER](#oznámení-událostí-s-appdaemon-notifier)

## Karta Versatile Thermostat UI
Vyhrazená karta pro Versatile Thermostat byla vyvinuta (založená na Better Thermostat). Je k dispozici zde: [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card) a nabízí moderní pohled na všechny stavy VTherm:

![image](https://github.com/jmcollin78/versatile-thermostat-ui-card/blob/master/assets/1.png?raw=true)

## Komponenta Scheduler!

Pro co nejlepší využití Versatile Thermostatu doporučuji jej používat s [Scheduler Component](https://github.com/nielsfaber/scheduler-component). Komponenta scheduler poskytuje plánování klimatizace založené na předdefinovaných režimech. Zatímco tato funkce je u generického termostatu poněkud omezená, stává se velmi výkonnou ve spojení s Versatile Thermostatem.

Za předpokladu, že máte nainstalované jak Versatile Thermostat, tak Scheduler Component, zde je příklad:

V Scheduleru přidejte plán:

![image](https://user-images.githubusercontent.com/1717155/119146454-ee1a9d80-ba4a-11eb-80ae-3074c3511830.png)

Vyberte skupinu "Climate", vyberte jednu (nebo více) entit, zvolte "MAKE SCHEME" a klikněte na další:
(Můžete také zvolit "SET PRESET", ale preferuji "MAKE SCHEME".)

![image](https://user-images.githubusercontent.com/1717155/119147210-aa746380-ba4b-11eb-8def-479a741c0ba7.png)

Definujte své schéma režimu a uložte:

![image](https://user-images.githubusercontent.com/1717155/119147784-2f5f7d00-ba4c-11eb-9de4-5e62ff5e71a8.png)

V tomto příkladu nastavuji ECO režim během noci a když nikdo není doma během dne, BOOST ráno a COMFORT večer.

Doufám, že tento příklad pomůže; neváhejte se podělit o svou zpětnou vazbu!

## Regulační křivky s Plotly pro doladění vašeho termostatu
Můžete získat křivku podobnou té ukázané v [některé výsledky](../../README-cs.md#některé-výsledky) pomocí konfigurace grafu Plotly využitím vlastních atributů termostatu popsaných [zde](reference#vlastní-atributy):

Nahraďte hodnoty mezi `[[ ]]` vašimi vlastními.
<details>

```yaml
- type: custom:plotly-graph
  entities:
    - entity: '[[climate]]'
      attribute: temperature
      yaxis: y1
      name: Consigne
    - entity: '[[climate]]'
      attribute: current_temperature
      yaxis: y1
      name: T°
    - entity: '[[climate]]'
      attribute: ema_temp
      yaxis: y1
      name: Ema
    - entity: '[[climate]]'
      attribute: on_percent
      yaxis: y2
      name: Power percent
      fill: tozeroy
      fillcolor: rgba(200, 10, 10, 0.3)
      line:
        color: rgba(200, 10, 10, 0.9)
    - entity: '[[slope]]'
      name: Slope
      fill: tozeroy
      yaxis: y9
      fillcolor: rgba(100, 100, 100, 0.3)
      line:
        color: rgba(100, 100, 100, 0.9)
  hours_to_show: 4
  refresh_interval: 10
  height: 800
  config:
    scrollZoom: true
  layout:
    margin:
      r: 50
    legend:
      x: 0
      'y': 1.2
      groupclick: togglegroup
      title:
        side: top right
    yaxis:
      visible: true
      position: 0
    yaxis2:
      visible: true
      position: 0
      fixedrange: true
      range:
        - 0
        - 1
    yaxis9:
      visible: true
      fixedrange: false
      range:
        - -2
        - 2
      position: 1
    xaxis:
      rangeselector:
        'y': 1.1
        x: 0.7
        buttons:
          - count: 1
            step: hour
          - count: 12
            step: hour
          - count: 1
            step: day
          - count: 7
            step: day
```
</details>

Příklad křivek získaných s Plotly:

![image](images/plotly-curves.png)

## Oznámení událostí s AppDaemon NOTIFIER
Tato automatizace využívá vynikající aplikaci AppDaemon s názvem NOTIFIER, vyvinutou Horizon Domotique, demonstrovanou [zde](https://www.youtube.com/watch?v=chJylIK0ASo&ab_channel=HorizonDomotique), a kód je k dispozici [zde](https://github.com/jlpouffier/home-assistant-config/blob/master/appdaemon/apps/notifier.py). Umožňuje uživatelům být upozorněni na bezpečnostní události probíhající na jakémkoli Versatile Thermostatu.

Toto je skvělý příklad použití oznámení popsaných zde: [event](#notifications).
<details>

```yaml
alias: Surveillance Mode Sécurité chauffage
description: Envoi une notification si un thermostat passe en mode sécurité ou power
trigger:
  - platform: event
    event_type: versatile_thermostat_security_event
    id: versatile_thermostat_security_event
  - platform: event
    event_type: versatile_thermostat_power_event
    id: versatile_thermostat_power_event
  - platform: event
    event_type: versatile_thermostat_temperature_event
    id: versatile_thermostat_temperature_event
condition: []
action:
  - choose:
      - conditions:
          - condition: trigger
            id: versatile_thermostat_security_event
        sequence:
          - event: NOTIFIER
            event_data:
              action: send_to_jmc
              title: >-
                Radiateur {{ trigger.event.data.name }} - {{
                trigger.event.data.type }} Sécurité
              message: >-
                Le radiateur {{ trigger.event.data.name }} est passé en {{
                trigger.event.data.type }} sécurité car le thermomètre ne répond
                plus.\n{{ trigger.event.data }}
              callback:
                - title: Stopper chauffage
                  event: stopper_chauffage
              image_url: /media/local/alerte-securite.jpg
              click_url: /lovelace-chauffage/4
              icon: mdi:radiator-off
              tag: radiateur_security_alerte
              persistent: true
      - conditions:
          - condition: trigger
            id: versatile_thermostat_power_event
        sequence:
          - event: NOTIFIER
            event_data:
              action: send_to_jmc
              title: >-
                Radiateur {{ trigger.event.data.name }} - {{
                trigger.event.data.type }} Délestage
              message: >-
                Le radiateur {{ trigger.event.data.name }} est passé en {{
                trigger.event.data.type }} délestage car la puissance max est
                dépassée.\n{{ trigger.event.data }}
              callback:
                - title: Stopper chauffage
                  event: stopper_chauffage
              image_url: /media/local/alerte-delestage.jpg
              click_url: /lovelace-chauffage/4
              icon: mdi:radiator-off
              tag: radiateur_power_alerte
              persistent: true
      - conditions:
          - condition: trigger
            id: versatile_thermostat_temperature_event
        sequence:
          - event: NOTIFIER
            event_data:
              action: send_to_jmc
              title: >-
                Le thermomètre du radiateur {{ trigger.event.data.name }} ne
                répond plus
              message: >-
                Le thermomètre du radiateur {{ trigger.event.data.name }} ne
                répond plus depuis longtemps.\n{{ trigger.event.data }}
              image_url: /media/local/thermometre-alerte.jpg
              click_url: /lovelace-chauffage/4
              icon: mdi:radiator-disabled
              tag: radiateur_thermometre_alerte
              persistent: true
mode: queued
max: 30
```
</details>
