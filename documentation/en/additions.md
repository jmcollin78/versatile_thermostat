# Some Essential Add-Ons

- [Some Essential Add-Ons](#some-essential-add-ons)
  - [the Versatile Thermostat UI Card](#the-versatile-thermostat-ui-card)
  - [the Scheduler Component!](#the-scheduler-component)
  - [Regulation curves with Plotly to Fine-Tune Your Thermostat](#regulation-curves-with-plotly-to-fine-tune-your-thermostat)
  - [Event notification with the AppDaemon NOTIFIER](#event-notification-with-the-appdaemon-notifier)

## the Versatile Thermostat UI Card
A dedicated card for the Versatile Thermostat has been developed (based on Better Thermostat). It is available here: [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card) and offers a modern view of all the VTherm statuses:

![image](https://github.com/jmcollin78/versatile-thermostat-ui-card/blob/master/assets/1.png?raw=true)

## the Scheduler Component!

To make the most out of the Versatile Thermostat, I recommend using it with the [Scheduler Component](https://github.com/nielsfaber/scheduler-component). The scheduler component provides climate scheduling based on predefined modes. While this feature is somewhat limited with the generic thermostat, it becomes very powerful when paired with the Versatile Thermostat.

Assuming you have installed both the Versatile Thermostat and the Scheduler Component, here’s an example:

In Scheduler, add a schedule:

![image](https://user-images.githubusercontent.com/1717155/119146454-ee1a9d80-ba4a-11eb-80ae-3074c3511830.png)

Choose the "Climate" group, select one (or more) entity, pick "MAKE SCHEME," and click next:
(You can also choose "SET PRESET," but I prefer "MAKE SCHEME.")

![image](https://user-images.githubusercontent.com/1717155/119147210-aa746380-ba4b-11eb-8def-479a741c0ba7.png)

Define your mode scheme and save:

![image](https://user-images.githubusercontent.com/1717155/119147784-2f5f7d00-ba4c-11eb-9de4-5e62ff5e71a8.png)

In this example, I set ECO mode during the night and when no one is home during the day, BOOST in the morning, and COMFORT in the evening.

I hope this example helps; feel free to share your feedback!

## Regulation curves with Plotly to Fine-Tune Your Thermostat
You can obtain a curve similar to the one shown in [some results](#some-results) using a Plotly graph configuration by leveraging the thermostat's custom attributes described [here](#custom-attributes):

Replace the values between `[[ ]]` with your own.
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

Example of curves obtained with Plotly:

![image](images/plotly-curves.png)

## Event notification with the AppDaemon NOTIFIER
This automation leverages the excellent AppDaemon app named NOTIFIER, developed by Horizon Domotique, demonstrated [here](https://www.youtube.com/watch?v=chJylIK0ASo&ab_channel=HorizonDomotique), and the code is available [here](https://github.com/jlpouffier/home-assistant-config/blob/master/appdaemon/apps/notifier.py). It allows users to be notified of security-related events occurring on any Versatile Thermostat.

This is a great example of using the notifications described here: [notification](#notifications).
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