# Zarządzanie energią i redukcja obciążenia

- [Zarządzanie energią i redukcja obciążenia](#power-management---load-shedding)
    - [Przykład użycia:](#example-use-case)
  - [Konfiguracja zarządzania energią](#configuring-power-management)

Funkcja ta pozwala regulować zużycie energii elektrycznej przez grzejniki. Znana jako `redukcja obciążenia`, umożliwia ograniczenie poboru energii przez urządzenia grzewcze w przypadku wykrycia warunków nadmiernego zużycia. Wymagany jest **sensor całkowitego chwilowego zużycia energii** w całym domu oraz **sensor maksymalnej dopuszczalnej mocy**.

Zachowanie tej funkcji jest następujące:
1. Gdy odczytany zostanie nowy pomiar zużycia energii w domu lub sensor maksymalnej dopuszczalnej mocy,
2. Jeśli maksymalna moc zostanie przekroczona, centralne sterowanie ograniczy obciążenie wszystkich aktywnych urządzeń, zaczynając od tych najbliższych wartości zadanej. Proces trwa, dopóki wystarczająca liczba termostatów nie zostanie odłączona.
3. Jeśli dostępna jest rezerwa mocy, a część termostatów została odłączona, centralne sterowanie ponownie włączy tyle urządzeń, ile to możliwe, zaczynając od tych najbardziej oddalonych od wartości zadanej (w momencie ich odłączenia).
4. Gdy termostat się uruchamia, wykonywana jest kontrola, czy zadeklarowana moc jest dostępna. Jeśli nie, termostat zostaje przełączony w tryb ograniczenia (`shed mode`).

**Ostrzeżenie:** To nie jest **funkcja bezpieczna**, lecz mechanizm optymalizacji zużycia energii kosztem pewnego pogorszenia ogrzewania. Nadmierne zużycie energii nadal jest możliwe, w zależności od częstotliwości aktualizacji czujnika zużycia oraz rzeczywistej mocy pobieranej przez urządzenia. Zawsze należy zachować margines bezpieczeństwa.

### Przykład użycia:
1. Masz licznik energii elektrycznej ograniczony do 11 kW,
2. Okazjonalnie ładujesz pojazd elektryczny z mocą 5 kW,
3. Pozostaje 6 kW na wszystko inne, w tym ogrzewanie,
4. Masz 1 kW innych aktywnych urządzeń,
5. Deklarujesz sensor (`input_number`) dla maksymalnej dopuszczalnej mocy ustawionej na 9 kW (= 11 kW – zarezerwowana moc dla innych urządzeń – margines bezpieczeństwa).

   Zachowanie systemu

> 1. Jeśli pojazd jest ładowany, całkowite zużycie energii wynosi 6 kW (5 + 1), a termostat włączy się tylko wtedy, gdy jego zadeklarowana moc wynosi maksymalnie 3 kW (9 – 6).
> 2. Jeśli pojazd jest ładowany i dodatkowo działa inny termostat o mocy 2 kW, całkowite zużycie wynosi 8 kW (5 + 1 + 2), a kolejny termostat włączy się tylko wtedy, gdy jego zadeklarowana moc wynosi maksymalnie 1 kW (9 – 8). W przeciwnym razie pominie swoją kolej (cykl).
> 3. Jeśli pojazd nie jest ładowany, całkowite zużycie wynosi 1 kW, a termostat włączy się tylko wtedy, gdy jego zadeklarowana moc wynosi maksymalnie 8 kW (9 – 1).

## Konfiguracja zarządzania energią

Jeśli w konfiguracji głównej wybrałeś funkcję `Zarządzania energią`, skonfiguruj ją następująco:

![image](images/config-power.png)

Wymagane elementy konfiguracji:
1. **Identyfikator encji** sensora całkowitego chwilowego zużycia energii,
2. **Identyfikator encji** sensora maksymalnej dopuszczalnej mocy,
3. **Temperatura**, która ma być zastosowana, jeśli aktywowana zostanie redukcja obciążenia.

Upewnij się, że wszystkie wartości mocy używają tych samych jednostek (np. kW lub W).
Posiadanie **sensora maksymalnej dopuszczalnej mocy** pozwala na dynamiczną modyfikację wartości maksymalnej mocy przy użyciu harmonogramu lub automatyzacji.

Ze względu na scentralizowaną redukcję obciążenia nie jest możliwe nadpisanie wartości senssorów zużycia i maksymalnego zużycia na poszczególnych termostatatch. Konfiguracja musi być wykonana w ustawieniach głównych (patrz: [Konfiguracja główna](./creation.md#centralized-configuration)).


> ![Tip](images/tips.png) _*Wskazówki*_
>
> 1. Podczas redukcji obciążenia w grzejniku wybierany jest preset o nazwie `moc`. Jest to ukryty preset, którego nie można wybrać ręcznie.
> 2. Zawsze zachowuj margines bezpieczeństwa, ponieważ maksymalna moc może być chwilowo przekroczona w oczekiwaniu na kolejne obliczenie cyklu lub przez niekontrolowane urządzenia.
> 3. Jeśli nie chcesz korzystać z tej funkcji, odznacz ją w menu 'Funkcje'.
> 4. Jeśli pojedynczy termostat steruje wieloma urządzeniami, zadeklarowane zużycie energii grzewczej powinno odpowiadać całkowitej mocy wszystkich urządzeń.
> 5. Jeśli korzystasz z karty interfejsu Versatile Thermostat UI Card (patrz [tutaj](additions.md#better-with-the-versatile-thermostat-ui-card)), redukcja obciążenia jest reprezentowane jako: ![load shedding](images/power-exceeded-icon.png).
> 6. Może wystąpić opóźnienie do 20 sekund pomiędzy otrzymaniem nowej wartości z czujnika zużycia energii a uruchomieniem redukcji obciążenia dla termostatu. Opóźnienie to zapobiega przeciążeniu Home Assistanta, jeśli aktualizacje zużycia są bardzo częste.
