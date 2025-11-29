# Parę istotnych dodatków

- [Parę istotnych dodatków](#parę-istotnych-dodatków)
  - [Karta _*Versatile Thermostat UI Card*_](#karta-versatile-thermostat-ui-card)
  - [Harmonogram](#harmonogram)
  - [Krzywe regulacji z _*Plotly*_ do precyzyjnego dostrajania termostatu](#krzywe-regulacji-z-plotly-do-precyzyjnego-dostrajania-termostatu)
  - [Regulation curves with Apex-charts (thanks to @gael1980)](#regulation-curves-with-apex-charts-thanks-to-gael1980)
  - [Powiadamianie o zdarzeniach za pomocą _*AppDaemon NOTIFIER*_](#powiadamianie-o-zdarzeniach-za-pomocą-appdaemon-notifier)
  - [Indoor "Feels Like" Temperature and the "Damp Cold" Effect (thanks to @nicola-spreafico)](#indoor-feels-like-temperature-and-the-damp-cold-effect-thanks-to-nicola-spreafico)
  - [A complementary integration to anticipate setpoint changes (thanks to @RastaChaum)](#a-complementary-integration-to-anticipate-setpoint-changes-thanks-to-rastachaum)

## Karta _*Versatile Thermostat UI Card*_
Opracowano dedykowaną kartę dla termostatu _*VTherm*_ (bazującą na *Better Thermostat*). Jest ona dostępna tutaj: [karta Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card) i oferuje nowoczesny widok wszystkich statusów termostatu _*VTherm*_:

![image](https://github.com/jmcollin78/versatile-thermostat-ui-card/blob/master/assets/1.png?raw=true)

## Harmonogram

Aby w pełni wykorzystać możliwości VTherm, zalecane jest używanie go w połączeniu z [Harmonogramem](https://github.com/nielsfaber/scheduler-component). Komponent ten umożliwia tworzenie harmonogramu pracy klimatyzacji w oparciu o predefiniowane tryby. Chociaż ta funkcja jest nieco ograniczona w przypadku termostatu uniwersalnego, staje się bardzo wydajna w połączeniu z *VTherm*.

Oto przykład. Zakładając, że zainstalowałeś zarówno *VTherm*, jak i komponent *Harmonogram*, dodaj w harmonogramie:

![image](https://user-images.githubusercontent.com/1717155/119146454-ee1a9d80-ba4a-11eb-80ae-3074c3511830.png)

Wybierz grupę "klimat", wskaż jedną encję (lub więcej), wybierz "MAKE SCHEME," i klinkij click NEXT. (Możesz także wybrać "SET PRESET," ale lepszym wyborem będzie "MAKE SCHEME"):

![image](https://user-images.githubusercontent.com/1717155/119147210-aa746380-ba4b-11eb-8def-479a741c0ba7.png)

Zdefiniuj schemat trybu i zapisz go:

![image](https://user-images.githubusercontent.com/1717155/119147784-2f5f7d00-ba4c-11eb-9de4-5e62ff5e71a8.png)

W tym przykładzie ustawiony został tryb ECO na noc oraz na okres dzienny, gdy nikogo nie ma w domu, BOOST rano i COMFORT wieczorem.


## Krzywe regulacji z _*Plotly*_ do precyzyjnego dostrajania termostatu
Można uzyskać krzywą podobną do tej pokazanej na rysunku [Trochę wyników...](../../README-pl.MD#some-results) używając konfiguracji wykresu *Plotly*, wykorzystując opisane niestandardowe atrybuty termostatu [tutaj](reference.md#custom-attributes):

Wstaw między nawiasy kwadratowe `[[ ]]` swoje własne wartości.
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

Przykład krzywych uzyskanych z _*Plotly*_:

![image](images/plotly-curves.png)

## Regulation curves with Apex-charts (thanks to @gael1980)
Apex chart allows to display some great reguation curves. @Gael1980 gives us a very good example [here](https://github.com/jmcollin78/versatile_thermostat/discussions/1239).

![Apex chart by Gael1980](../../images/apex-chart-by-gael1980.png)


## Powiadamianie o zdarzeniach za pomocą _*AppDaemon NOTIFIER*_
Ta automatyzacja wykorzystuje doskonałą aplikację *AppDaemon NOTIFIER*, opracowaną przez *Horizon Domotique*, prezentowaną [tutaj](https://www.youtube.com/watch?v=chJylIK0ASo&ab_channel=HorizonDomotique), a której kod dostępny jest [tutaj](https://github.com/jlpouffier/home-assistant-config/blob/master/appdaemon/apps/notifier.py). Umożliwia ona Użytkownikowi otrzymywanie powiadomień o zdarzeniach związanych z bezpieczeństwem dowolnego termostatu *VTherm*.

Oto doskonały przykład użycia funkcji powiadomienia o zdarzeniu opisanym [tutaj](reference.md#events).
<details>

```yaml
alias: Monitorowanie trybu bezpiecznego ogrzewania
description: Wysyłanie powiadomienia, gdy termostat przejdzie w tryb bezpieczny
trigger:
  - platform: event
    event_type: versatile_thermostat_safety_event
    id: versatile_thermostat_safety_event
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
            id: versatile_thermostat_safety_event
        sequence:
          - event: NOTIFIER
            event_data:
              action: send_to_jmc
              title: >-
                Grzejnik {{ trigger.event.data.name }} - {{
                trigger.event.data.type }} Bezpieczeństwo
              message: >-
                Grzejnik {{ trigger.event.data.name }} przeszedł w tryb bezpieczny {{
                trigger.event.data.type }} ponieważ termometr przestał reagować.\n{{ trigger.event.data }}
              callback:
                - title: Wyłączenie ogrzewania
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
                Grzejnik {{ trigger.event.data.name }} - {{
                trigger.event.data.type }} Redukcja obciążenia
              message: >-
                Grzejnik {{ trigger.event.data.name }} przeszedł w tryb redukcji obciążenia {{
                trigger.event.data.type }} z powodu przekroczenia mocy maksymalnej.\n{{ trigger.event.data }}
              callback:
                - title: Wyłączenie ogrzewania
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
                Termometr grzejnika {{ trigger.event.data.name }} nie odpowiada
              message: >-
                Termometr grzejnika {{ trigger.event.data.name }} od dłuższego
                czasu nie odpowiada.\n{{ trigger.event.data }}
              image_url: /media/local/thermometre-alerte.jpg
              click_url: /lovelace-chauffage/4
              icon: mdi:radiator-disabled
              tag: radiateur_thermometre_alerte
              persistent: true
mode: queued
max: 30
```
</details>

## Indoor "Feels Like" Temperature and the "Damp Cold" Effect (thanks to @nicola-spreafico)
An brillant post to add a feature name "Feels like" or "Damp Cold". You can force the target temperature to a higher value depending on weather conditions like humidity or wind.
The post is [here](https://github.com/jmcollin78/versatile_thermostat/discussions/1211)

## A complementary integration to anticipate setpoint changes (thanks to @RastaChaum)
This integration (in beta as of 11/23/2025) proposes to anticipate the setpoint changes of your Scheduler so that the target temperature is reached at the time of the Scheduler change. It learns the behavior of your VTherm (temperature rise time, speed and temperature rise time) and applies a predictive algorithm to anticipate the Scheduler change.
The approach is very interesting and offers a good complement to _VTherm_.

It is available [here](https://github.com/RastaChaum/Intelligent-Heating-Pilot)