# Detekcja ruchu lub aktywności

- [Detekcja ruchu lub aktywności](#motion-or-activity-detection)
  - [Konfiguracja trybu aktywności lub detekcji ruchu](#configure-activity-mode-or-motion-detection)
  - [Zastosowanie](#usage)

Funkcja ta pozwala zmieniać ustawienia wstępne, gdy w pomieszczeniu wykryty zostanie ruch. Jeśli nie chcesz ogrzewać pomieszczenia, gdy jest ono nieużywane, a tylko wtedy, gdy ktoś w nim przebywa, potrzebujesz czujnika ruchu (lub obecności) w pomieszczeniu i odpowiedniej konfiguracji tej funkcji.

Ta funkcja jest często mylona z funkcją obecności. Są one komplementarne, ale niezamienne. Funkcja „ruchu” działa lokalnie w pomieszczeniu wyposażonym w czujnik ruchu, natomiast funkcja „obecności” została zaprojektowana jako globalna dla całego domu.

## Konfiguracja trybu aktywności lub detekcji ruchu

Jeśli wybrałeś funkcję detekcji ruchu:

![image](images/config-motion.png)

to potrzebne bedą:
- **Czujnik ruchu**. `Entity ID` czujnika ruchu. Stany czujnika muszą być `'on'` (wykryto ruch) lub `'off'` (brak ruchu).
- **Opóźnienie detekcji** (w sek.), określające jak długo należy czekać na potwierdzenie ruchu, zanim zostanie on uznany za faktycznie zaistniały. Parametr ten może być większy niż zwłoka czujnika, w przeciwnym razie detekcja nastąpi przy każdym wykryciu ruchu.
- **Opóźnienie braku aktywności** (w sek.), określające jak długo należy czekać na potwierdzenie braku ruchu, zanim przestaniemy go uwzględniać.
- **Ustawienie wstępne "ruchu"**. Używana będzie temperatura zapisana w tym ustawieniu, gdy wykryta zostanie aktywność.
- **Ustawienie wstępne "brak ruchu”**. Używana będzie temperatura zapisana w tym ustawieniu, gdy aktywność nie zostanie wykryta.

## Zastosowanie

To tell a _VTherm_ that it should listen to the motion sensor, you must set it to the special 'Activity' preset. If you have installed the Versatile Thermostat UI card (see [here](additions.md#much-better-with-the-versatile-thermostat-ui-card)), this preset is displayed as follows: ![activity preset](images/activity-preset-icon.png).

You can then, upon request, set a _VTherm_ to motion detection mode.

The behavior will be as follows:
- we have a room with a thermostat set to activity mode, the "motion" mode chosen is comfort (21.5°C), the "no motion" mode chosen is Eco (18.5°C), and the motion delay is 30 seconds on detection and 5 minutes on the end of detection.
- the room has been empty for a while (no activity detected), the setpoint temperature in this room is 18.5°.
- someone enters the room, and activity is detected if the motion is present for at least 30 seconds. The temperature then goes up to 21.5°.
- if the motion is present for less than 30 seconds (quick passage), the temperature stays at 18.5°.
- imagine the temperature has gone up to 21.5°, when the person leaves the room, after 5 minutes the temperature is returned to 18.5°.
- if the person returns before the 5 minutes, the temperature stays at 21.5°.

> ![Tip](images/tips.png) _*Notes*_
> 1. As with other presets, `Activity` will only be offered if it is correctly configured. In other words, all 4 configuration keys must be set.
> 2. If you are using the Versatile Thermostat UI card (see [here](additions.md#much-better-with-the-versatile-thermostat-ui-card)), motion detection is represented as follows: ![motion](images/motion-detection-icon.png).
