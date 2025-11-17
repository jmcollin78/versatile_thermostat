# Detekcja ruchu lub aktywności

- [Detekcja ruchu lub aktywności](#motion-or-activity-detection)
  - [Konfiguracja trybu aktywności lub detekcji ruchu](#configure-activity-mode-or-motion-detection)
  - [Zastosowanie](#usage)

Funkcja ta pozwala zmieniać preset, gdy w pomieszczeniu wykryty zostanie ruch. Jeśli nie chcesz ogrzewać pustego pomieszczenia, a tylko wtedy, gdy ktoś w nim przebywa, musisz użyć  czujnika ruchu (lub obecności) w pomieszczeniu i odpowiednio skonfigurować tę funkcję.

Ta funkcja jest często mylona z funkcją obecności. Są one komplementarne, ale niezamienne. Funkcja „ruchu” działa lokalnie w pomieszczeniu wyposażonym w czujnik ruchu, natomiast funkcja „obecności” została zaprojektowana jako globalna dla całego domu.

## Konfiguracja trybu aktywności lub detekcji ruchu

Jeśli wybrałeś funkcję detekcji ruchu:

![image](images/config-motion.png)

to potrzebne bedą:
- **Czujnik ruchu**. Stany czujnika muszą mieć wartości: `'on'` (wykryto ruch) lub `'off'` (brak ruchu).
- **Opóźnienie detekcji** (w sek.), określające jak długo należy czekać na potwierdzenie ruchu, zanim zostanie on uznany za faktycznie zaistniały. Parametr ten może być większy niż zwłoka czujnika, w przeciwnym razie detekcja nastąpi przy każdym wykryciu ruchu.
- **Opóźnienie braku aktywności** (w sek.), określające jak długo należy czekać na potwierdzenie braku ruchu, zanim przestaniemy go uwzględniać.
- **Preset "ruchu"**. Używana będzie temperatura zapisana w tym ustawieniu, gdy wykryta zostanie aktywność.
- **Preset "brak ruchu”**. Używana będzie temperatura zapisana w tym ustawieniu, gdy aktywność nie zostanie wykryta.

## Zastosowanie

Aby sprawić, że termostat będzie nasłuchiwał czujnika ruchu, należy ustawić go w specjalny tryb aktywny. Jeśli masz zainstalowaną kartę interfejsu Versatile Thermostat UI (patrz: [tutaj](additions.md#much-better-with-the-versatile-thermostat-ui-card)), ten tryb jest wyświetlany jako: ![activity preset](images/activity-preset-icon.png).
 
Następnie, możesz na żądanie ustawić termostat w tryb wykrywania ruchu.

Zachowanie będzie następujące:
- Mamy pomieszczenie z termostatem ustawionym w tryb aktywny. Tryb „ruch” to komfort (21,5°C), tryb „brak ruchu” to Eko (18,5°C), opóźnienie detekcji wynosi 30 sekund, natomiast opóźnienie braku ruchu – 5 minut.
- Pomieszczenie było przez jakiś czas puste (brak aktywności), temperatura w nim wynosi 18,5°C.
- Ktoś wchodzi do pomieszczenia – aktywność zostaje wykryta, jeśli ruch trwa co najmniej 30 sekund. Temperatura wzrasta do 21,5°C.
- Jeśli ruch trwa krócej, niż 30 sekund (szybkie przejście), temperatura pozostaje na poziomie 18,5°C.
- Jeśli temperatura wzrosła do 21,5°C, a osoba opuszcza pomieszczenie, po 5 minutach temperatura wraca do 18,5°C.
- Jeśli osoba wróci przed upływem 5 minut, temperatura pozostaje na poziomie 21,5°C.

> ![Tip](images/tips.png) _*Wskazówki*_
> 1. Podobnie jak w przypadku innych presetów, `aktywność` będzie dostępna tylko wtedy, gdy zostanie poprawnie skonfigurowana. Oznacza to, że wszystkie 4 kluczowe parametry muszą być ustawione.
> 2. Jeśli korzystasz z karty interfejsu Versatile Thermostat UI Card (patrz: [tutaj](additions.md#much-better-with-the-versatile-thermostat-ui-card)), aktywnacja detekcji ruchu jest reprezentowane jako: ![motion](images/motion-detection-icon.png).

