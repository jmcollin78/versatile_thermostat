# Kalibracja zaworów (usługa recalibrate_valves)

- [Kalibracja zaworów (usługa recalibrate_valves)](#kalibracja-zawor%C3%B3w-us%C5%82uga-recalibrate_valves)
  - [Dlaczego ta funkcja?](#dlaczego-ta-funkcja)
  - [Jak to działa](#jak-to-dzia%C5%82a)
  - [Ograniczenia i wymagania](#ograniczenia-i-wymagania)
  - [Konfiguracja / dostęp do usługi](#konfiguracja--dost%C4%99p-do-us%C5%82ugi)
  - [Parametry usługi](#parametry-us%C5%82ugi)
  - [Szczegółowe zachowanie](#szczeg%C3%B3%C5%82owe-zachowanie)
  - [Przykłady automatyzacji](#przyk%C5%82ady-automatyzacji)

## Dlaczego ta funkcja?

Usługa `recalibrate_valves` wykonuje prostą procedurę kalibracji dla głowic termostatycznych (TRV) sterowanych przez VTherm w trybie regulacji zaworu. Tymczasowo wymusza skrajne pozycje siłowników zaworów (w pełni otwarte, a następnie w pełni zamknięte), aby pomóc w kalibracji ustawień zaworu termostatu.

Usługa jest przydatna, gdy podejrzewasz nieprawidłowe wartości otwarcia/zamknięcia, po instalacji/konserwacji urządzeń lub gdy grzejnik działa, mimo że zawór jest zgłaszany jako zamknięty.

⚠️ Rzeczywista kalibracja zależy od urządzenia wykonawczego zaworu. VTherm jedynie wysyła komendy otwierania/zamykania. Jeśli urządzenie nie reaguje prawidłowo, skontaktuj się z producentem TRV lub użyj procedury kalibracji producenta.

⚠️ Kalibracja może skrócić czas pracy na baterii w urządzeniach zasilanych bateryjnie. Używaj jej tylko wtedy, gdy jest to konieczne.

## Jak to działa

Usługa wykonuje następujące kroki dla docelowej encji:

1. Weryfikuje, że encja docelowa to `ThermostatClimateValve` (regulacja zaworu). W przeciwnym razie zwraca błąd.
2. Weryfikuje, czy każdy zawór ma skonfigurowane dwie encje `number` do otwierania i zamykania. Brak encji spowoduje odrzucenie operacji.
3. Zapamiętuje `requested_state` termostatu.
4. Ustawia VTherm w tryb OFF.
5. Czeka `delay_seconds`.
6. Dla każdego zaworu: wymusza otwarcie na 100% (wysyła zamapowaną wartość do encji `number`). Czeka `delay_seconds`.
7. Dla każdego zaworu: wymusza zamknięcie na 100% (wysyła zamapowaną wartość do encji `number`). Czeka `delay_seconds`.
8. Przywraca oryginalny `requested_state` i aktualizuje stany/atrybuty.

Podczas procedury VTherm wysyła bezpośrednie wartości do encji `number`, omijając zwykłe progi i zabezpieczenia algorytmów. Usługa działa w tle i natychmiast zwraca `{"message": "calibrage en cours"}`.

Opóźnienie między krokami określa wywołujący. Usługa przyjmuje wartość z zakresu `0`–`300` sekund (0–5 minut). W praktyce 10–60 sekund jest zwykle wystarczające w zależności od prędkości zaworu; 10 s to dobry punkt wyjścia.

## Ograniczenia i wymagania

- Usługa dostępna jest tylko dla termostatów `ThermostatClimateValve` (regulacja zaworu).
- Każdy zawór musi mieć dwie encje `number`:
  - `opening_degree_entity_id` (polecenie otwarcia)
  - `closing_degree_entity_id` (polecenie zamknięcia)
- Encje `number` mogą mieć zdefiniowane atrybuty `min` i `max`; usługa mapuje 0–100% liniowo do tego zakresu. Jeśli brakuje `min`/`max`, domyślny zakres to 0–100.
- Usługa chroni przed jednoczesnym uruchomieniem dla tej samej encji: jeśli kalibracja już działa, nowe żądanie zostanie odrzucone natychmiast.

## Konfiguracja / dostęp do usługi

Usługa zarejestrowana jest jako entity-service. Wywołaj ją, kierując się na encję `climate` w Home Assistant.

Nazwa usługi: `versatile_thermostat.recalibrate_valves`

Przykład przez Developer Tools / Services:

```yaml
service: versatile_thermostat.recalibrate_valves
target:
  entity_id: climate.my_thermostat
data:
  delay_seconds: 30
```

Usługa natychmiast zwraca:

```json
{"message": "calibrage en cours"}
```

## Parametry usługi

| Parametr        | Typ     | Opis                                                                                          |
| --------------- | ------- | --------------------------------------------------------------------------------------------- |
| `delay_seconds` | integer | Opóźnienie (sekundy) po pełnym otwarciu i po pełnym zamknięciu. Zakres: 0–300 (zalecane: 10). |

Schemat usługi ogranicza wartość do `0`–`300` sekund.

## Szczegółowe zachowanie

- Operacja działa jako zadanie w tle. Wywołujący otrzymuje natychmiastowe potwierdzenie, a postęp można śledzić w logach Home Assistant.
- Po zakończeniu operacji przywracany jest `requested_state` (tryb HVAC, docelowa temperatura i preset jeśli obecne) i stany są aktualizowane. VTherm powinien wrócić do pierwotnego stanu, o ile czujniki pozostaną stabilne.

## Przykłady automatyzacji

1) Kalibracja raz w miesiącu (przykład):

YAML poniżej uruchamia kalibrację o 03:00 pierwszego dnia każdego miesiąca:

```yaml
alias: Miesięczna kalibracja zaworów
trigger:
  - platform: time
    at: '03:00:00'
condition:
  - condition: template
    value_template: "{{ now().day == 1 }}"
  - condition: state
    entity_id: climate.my_thermostat
    state: 'off'
action:
  - service: versatile_thermostat.recalibrate_valves
    target:
      entity_id: climate.my_thermostat
    data:
      delay_seconds: 60
  - service: persistent_notification.create
    data:
      title: "🔧 Miesięczna kalibracja uruchomiona"
      message: "🔧 Rozpoczęto kalibrację zaworów dla climate.my_thermostat"
```

> ![Tip](images/tips.png) _*Porada*_
>
> - Przetestuj kalibrację na jednym VTherm przed uruchomieniem jej na wielu urządzeniach i sprawdź logi oraz wartości `number`.
> - Ustaw `delay_seconds` tak, aby fizyczny zawór miał czas osiągnąć pozycję (60 s to rozsądny początek dla większości zaworów).
